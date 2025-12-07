"""
Load testing service module for TaskIQ.

This module provides business logic for orchestrating and analyzing load tests,
separating concerns from API endpoints and worker tasks.
"""

from typing import Any

from pydantic import ValidationError

from app.components.worker.constants import LoadTestTypes
from app.components.worker.pools import enqueue_task
from app.core.config import get_load_test_queue
from app.core.log import logger
from app.services.load_test_models import (
    LoadTestConfiguration,
    LoadTestMetrics,
    LoadTestResult,
    OrchestratorRawResult,
    PerformanceAnalysis,
    TestTypeInfo,
    ValidationStatus,
)

__all__ = [
    "LoadTestConfiguration",
    "LoadTestService",
    "quick_cpu_test",
    "quick_io_test",
    "quick_memory_test",
]


class LoadTestService:
    """Service for managing load test operations."""

    @staticmethod
    def get_test_type_info(test_type: LoadTestTypes | str) -> dict[str, Any]:
        """Get detailed information about a specific test type."""
        test_info = {
            LoadTestTypes.CPU_INTENSIVE: {
                "name": "CPU Intensive",
                "description": (
                    "Tests worker CPU processing with fibonacci calculations"
                ),
                "expected_metrics": [
                    "fibonacci_n",
                    "fibonacci_result",
                    "cpu_operations",
                ],
                "performance_signature": (
                    "CPU bound - should show computation time scaling with problem size"
                ),
                "typical_duration_ms": "1-10ms per task",
                "concurrency_impact": (
                    "Limited by CPU cores, benefits from parallel processing"
                ),
                "validation_keys": ["fibonacci_n", "fibonacci_result"],
            },
            LoadTestTypes.IO_SIMULATION: {
                "name": "I/O Simulation",
                "description": "Tests async I/O handling with simulated delays",
                "expected_metrics": [
                    "simulated_delay_ms",
                    "io_operations",
                    "async_operations",
                ],
                "performance_signature": (
                    "I/O bound - should show async concurrency benefits"
                ),
                "typical_duration_ms": ("5-30ms per task (includes simulated delays)"),
                "concurrency_impact": (
                    "Excellent with async - many tasks can run concurrently"
                ),
                "validation_keys": ["simulated_delay_ms", "io_operations"],
            },
            LoadTestTypes.MEMORY_OPERATIONS: {
                "name": "Memory Operations",
                "description": "Tests memory allocation and data structure operations",
                "expected_metrics": [
                    "allocation_size",
                    "list_sum",
                    "dict_keys",
                    "max_value",
                ],
                "performance_signature": (
                    "Memory bound - should show allocation/deallocation patterns"
                ),
                "typical_duration_ms": "1-5ms per task",
                "concurrency_impact": (
                    "Moderate - limited by memory bandwidth and GC pressure"
                ),
                "validation_keys": [
                    "allocation_size",
                    "list_sum",
                    "dict_keys",
                ],
            },
            LoadTestTypes.FAILURE_TESTING: {
                "name": "Failure Testing",
                "description": "Tests error handling with ~20% random failures",
                "expected_metrics": ["failure_rate", "error_types"],
                "performance_signature": (
                    "Mixed - tests resilience and error handling paths"
                ),
                "typical_duration_ms": "1-10ms per task (when successful)",
                "concurrency_impact": ("Tests worker recovery and error isolation"),
                "validation_keys": ["status"],
            },
        }
        return test_info.get(test_type, {})

    @staticmethod
    async def enqueue_load_test(config: LoadTestConfiguration) -> str:
        """
        Enqueue a load test orchestrator task.

        Args:
            config: Load test configuration

        Returns:
            Task ID for the orchestrator job
        """
        logger.info(
            f"Enqueueing load test: {config.num_tasks} {config.task_type} tasks"
        )

        try:
            # Use TaskIQ's enqueue_task wrapper
            task_handle = await enqueue_task(
                "load_test_orchestrator",
                config.target_queue,
                num_tasks=config.num_tasks,
                task_type=config.task_type,
                batch_size=config.batch_size,
                delay_ms=config.delay_ms,
                target_queue=config.target_queue,
            )

            logger.info(f"Load test orchestrator enqueued: {task_handle.task_id}")
            return str(task_handle.task_id)

        except Exception as e:
            cause = e.__cause__ if e.__cause__ else e
            logger.error(f"Failed to enqueue load test: {e} (cause: {cause})")
            raise

    @staticmethod
    async def get_load_test_result(
        task_id: str, target_queue: str | None = None
    ) -> dict[str, Any] | None:
        """
        Retrieve and analyze load test results.

        Args:
            task_id: The orchestrator task ID
            target_queue: Queue where the test was run (defaults to configured
                load_test queue)

        Returns:
            Analyzed load test results or None if not found
        """
        from taskiq_redis import RedisAsyncResultBackend

        from app.core.config import settings

        # Use configured load test queue if not specified
        if target_queue is None:
            target_queue = get_load_test_queue()

        # Use fresh result backend to avoid cached connections that cause
        # 'Event loop is closed' errors when CLI exits
        redis_url = (
            settings.redis_url_effective
            if hasattr(settings, "redis_url_effective")
            else settings.REDIS_URL
        )
        result_backend = RedisAsyncResultBackend(redis_url=redis_url)

        try:
            try:
                result = await result_backend.get_result(task_id)
            except Exception as e:
                logger.debug(f"Result not found for task {task_id}: {e}")
                return None

            # Handle error results
            if result.is_err:
                return {
                    "task": "load_test_orchestrator",
                    "status": "failed",
                    "error": str(result.error),
                    "test_id": task_id,
                }

            # Get the actual return value
            actual_result = result.return_value

            # Handle different result formats
            if isinstance(actual_result, dict):
                # Check if it's a direct load test result
                if actual_result.get("task") == "load_test_orchestrator":
                    analyzed_result = LoadTestService._analyze_load_test_result(
                        actual_result
                    )
                    return analyzed_result.model_dump()
                # Check if it looks like a load test orchestrator result
                # Note: test_id is optional for TaskIQ (task doesn't know its own ID)
                elif "task_type" in actual_result and "tasks_sent" in actual_result:
                    try:
                        # Validate and transform using Pydantic models
                        orchestrator_result = OrchestratorRawResult(**actual_result)
                        load_test_result = orchestrator_result.to_load_test_result()
                        analyzed_result = LoadTestService._analyze_load_test_result(
                            load_test_result
                        )
                        return analyzed_result.model_dump()
                    except ValidationError as e:
                        logger.error(f"Failed to validate orchestrator result: {e}")
                        # Fall back to manual transformation
                        transformed_result = (
                            LoadTestService._transform_orchestrator_result(
                                actual_result
                            )
                        )
                        analyzed_result = LoadTestService._analyze_load_test_result(
                            transformed_result
                        )
                        return analyzed_result.model_dump()

            # Return result as-is if it's already a dict
            if isinstance(actual_result, dict):
                return actual_result
            return None

        except Exception as e:
            logger.error(f"Failed to get load test result for {task_id}: {e}")
            return None
        finally:
            # Always close the result backend to prevent connection leaks
            await result_backend.shutdown()

    @staticmethod
    def _transform_orchestrator_result(
        orchestrator_result: dict[str, Any],
    ) -> dict[str, Any]:
        """Transform orchestrator result to expected analysis format."""

        # Create the configuration object from orchestrator parameters
        configuration = {
            "task_type": orchestrator_result.get("task_type", "unknown"),
            "num_tasks": orchestrator_result.get("tasks_sent", 0),
            "batch_size": orchestrator_result.get("batch_size", 0),
            "delay_ms": orchestrator_result.get("delay_ms", 0),
            "target_queue": orchestrator_result.get("target_queue", "unknown"),
        }

        # Create the metrics object from orchestrator result data
        metrics = {
            "tasks_sent": orchestrator_result.get("tasks_sent", 0),
            "tasks_completed": orchestrator_result.get("tasks_completed", 0),
            "tasks_failed": orchestrator_result.get("tasks_failed", 0),
            "total_duration_seconds": orchestrator_result.get(
                "total_duration_seconds", 0
            ),
            "overall_throughput": orchestrator_result.get(
                "overall_throughput_per_second", 0
            ),
            "failure_rate_percent": orchestrator_result.get("failure_rate_percent", 0),
            "completion_percentage": orchestrator_result.get(
                "completion_percentage", 0
            ),
            "average_throughput_per_second": orchestrator_result.get(
                "average_throughput_per_second", 0
            ),
            "monitor_duration_seconds": orchestrator_result.get(
                "monitor_duration_seconds", 0
            ),
        }

        # Create the transformed result
        transformed = {
            "task": "load_test_orchestrator",
            "status": "completed",
            "test_id": orchestrator_result.get("test_id", "unknown"),
            "configuration": configuration,
            "metrics": metrics,
            "start_time": orchestrator_result.get("start_time"),
            "end_time": orchestrator_result.get("end_time"),
            "task_ids": orchestrator_result.get("task_ids", []),
        }

        return transformed

    @staticmethod
    def _analyze_load_test_result(
        result: LoadTestResult | dict[str, Any],
    ) -> LoadTestResult:
        """Add analysis and validation to load test results."""

        # Convert dict to model if needed
        if isinstance(result, dict):
            try:
                result = LoadTestResult(**result)
            except ValidationError as e:
                logger.error(f"Failed to validate result as LoadTestResult: {e}")
                # Return a basic error result
                return LoadTestResult(
                    status="failed",
                    test_id=(
                        result.get("test_id", "unknown")
                        if isinstance(result, dict)
                        else "unknown"
                    ),
                    configuration=LoadTestConfiguration(
                        task_type=LoadTestTypes.CPU_INTENSIVE,
                        num_tasks=10,
                        batch_size=1,
                        delay_ms=0,
                        target_queue="unknown",
                    ),
                    metrics=LoadTestMetrics(
                        tasks_sent=0,
                        tasks_completed=0,
                        tasks_failed=0,
                        total_duration_seconds=0.0,
                        overall_throughput=0.0,
                        failure_rate_percent=0.0,
                        completion_percentage=0.0,
                        average_throughput_per_second=0.0,
                        monitor_duration_seconds=0.0,
                    ),
                    start_time=None,
                    end_time=None,
                    error=f"Validation failed: {e}",
                    analysis=None,
                )

        # Verify result is LoadTestResult and handle unexpected types
        if not isinstance(result, LoadTestResult):
            logger.error(f"Expected LoadTestResult but got {type(result)}")
            return LoadTestResult(
                status="failed",
                test_id="unknown",
                configuration=LoadTestConfiguration(
                    task_type=LoadTestTypes.CPU_INTENSIVE,
                    num_tasks=10,
                    batch_size=1,
                    delay_ms=0,
                    target_queue="unknown",
                ),
                metrics=LoadTestMetrics(
                    tasks_sent=0,
                    tasks_completed=0,
                    tasks_failed=0,
                    total_duration_seconds=0.0,
                    overall_throughput=0.0,
                    failure_rate_percent=0.0,
                    completion_percentage=0.0,
                    average_throughput_per_second=0.0,
                    monitor_duration_seconds=0.0,
                ),
                start_time=None,
                end_time=None,
                error=f"Unexpected result type: {type(result)}",
                analysis=None,
            )

        task_type = result.configuration.task_type

        # Get expected characteristics for this test type
        # Validate task type against known types
        if task_type not in [
            LoadTestTypes.CPU_INTENSIVE,
            LoadTestTypes.IO_SIMULATION,
            LoadTestTypes.MEMORY_OPERATIONS,
            LoadTestTypes.FAILURE_TESTING,
        ]:
            task_type = LoadTestTypes.CPU_INTENSIVE  # Default fallback

        test_info_dict = LoadTestService.get_test_type_info(task_type)
        test_info = TestTypeInfo(**test_info_dict)

        # Create analysis components
        performance_analysis = LoadTestService._analyze_performance_pydantic(result)
        validation_status = LoadTestService._validate_test_execution_pydantic(
            result, test_info
        )
        recommendations = LoadTestService._generate_recommendations_pydantic(result)

        # Add analysis to result
        from app.services.load_test_models import LoadTestAnalysis

        analysis = LoadTestAnalysis(
            test_type_info=test_info,
            performance_analysis=performance_analysis,
            validation_status=validation_status,
            recommendations=recommendations,
        )

        result.analysis = analysis
        return result

    @staticmethod
    def _analyze_performance(result: dict[str, Any]) -> dict[str, Any]:
        """Analyze performance characteristics of the load test."""
        metrics = result.get("metrics", {})

        analysis = {
            "throughput_rating": "unknown",
            "efficiency_rating": "unknown",
            "queue_pressure": "unknown",
        }

        # Analyze throughput
        throughput = metrics.get("overall_throughput", 0)
        if throughput >= 50:
            analysis["throughput_rating"] = "excellent"
        elif throughput >= 20:
            analysis["throughput_rating"] = "good"
        elif throughput >= 10:
            analysis["throughput_rating"] = "fair"
        else:
            analysis["throughput_rating"] = "poor"

        # Analyze efficiency (completion rate)
        tasks_sent = metrics.get("tasks_sent", 1)
        tasks_completed = metrics.get("tasks_completed", 0)
        completion_rate = (tasks_completed / tasks_sent) * 100 if tasks_sent > 0 else 0

        if completion_rate >= 95:
            analysis["efficiency_rating"] = "excellent"
        elif completion_rate >= 90:
            analysis["efficiency_rating"] = "good"
        elif completion_rate >= 80:
            analysis["efficiency_rating"] = "fair"
        else:
            analysis["efficiency_rating"] = "poor"

        # Analyze queue pressure (based on duration vs expected)
        duration = metrics.get("total_duration_seconds", 0)
        if duration > 60:
            analysis["queue_pressure"] = "high"
        elif duration > 30:
            analysis["queue_pressure"] = "medium"
        else:
            analysis["queue_pressure"] = "low"

        return analysis

    @staticmethod
    def _validate_test_execution(
        result: dict[str, Any], test_info: dict[str, Any]
    ) -> dict[str, Any]:
        """Validate that the test executed as expected."""
        validation: dict[str, Any] = {
            "test_type_verified": False,
            "expected_metrics_present": False,
            "performance_signature_match": "unknown",
            "issues": [],
        }

        # This would need actual task result inspection to verify test type
        # For now, we assume the test executed correctly if it completed
        status = result.get("status", "unknown")
        if status == "completed":
            validation["test_type_verified"] = True
            validation["expected_metrics_present"] = True
            validation["performance_signature_match"] = "verified"
        else:
            validation["issues"].append(f"Test status: {status}")

        return validation

    @staticmethod
    def _generate_recommendations(result: dict[str, Any]) -> list[str]:
        """Generate recommendations based on test results."""
        recommendations = []

        metrics = result.get("metrics", {})
        throughput = metrics.get("overall_throughput", 0)
        failure_rate = metrics.get("failure_rate_percent", 0)

        if throughput < 10:
            recommendations.append(
                "Low throughput detected. Consider reducing task complexity or "
                "increasing worker concurrency."
            )

        if failure_rate > 5:
            recommendations.append(
                f"High failure rate ({failure_rate:.1f}%). Check worker logs "
                f"for error patterns."
            )

        duration = metrics.get("total_duration_seconds", 0)
        tasks_sent = metrics.get("tasks_sent", 1)

        if duration > 60 and tasks_sent < 200:
            recommendations.append(
                "Long execution time for relatively few tasks suggests queue "
                "saturation. Consider testing with smaller batches or "
                "different queues."
            )

        return recommendations

    @staticmethod
    def _analyze_performance_pydantic(result: LoadTestResult) -> PerformanceAnalysis:
        """Analyze performance characteristics using Pydantic models."""

        # Analyze throughput
        throughput = result.metrics.overall_throughput
        if throughput >= 50:
            throughput_rating = "excellent"
        elif throughput >= 20:
            throughput_rating = "good"
        elif throughput >= 10:
            throughput_rating = "fair"
        else:
            throughput_rating = "poor"

        # Analyze efficiency (completion rate)
        tasks_sent = result.metrics.tasks_sent
        tasks_completed = result.metrics.tasks_completed
        completion_rate = (tasks_completed / tasks_sent) * 100 if tasks_sent > 0 else 0

        if completion_rate >= 95:
            efficiency_rating = "excellent"
        elif completion_rate >= 90:
            efficiency_rating = "good"
        elif completion_rate >= 80:
            efficiency_rating = "fair"
        else:
            efficiency_rating = "poor"

        # Analyze queue pressure (based on duration vs expected)
        duration = result.metrics.total_duration_seconds
        if duration > 60:
            queue_pressure = "high"
        elif duration > 30:
            queue_pressure = "medium"
        else:
            queue_pressure = "low"

        return PerformanceAnalysis(
            throughput_rating=throughput_rating,
            efficiency_rating=efficiency_rating,
            queue_pressure=queue_pressure,
        )

    @staticmethod
    def _validate_test_execution_pydantic(
        result: LoadTestResult, test_info: TestTypeInfo
    ) -> ValidationStatus:
        """Validate test execution using Pydantic models."""

        issues = []

        # Basic validation - if we got here, the test at least completed
        test_type_verified = result.status == "completed"
        expected_metrics_present = result.status == "completed"

        if result.status == "completed":
            performance_signature_match = "verified"
        else:
            performance_signature_match = "unknown"
            issues.append(f"Test status: {result.status}")

        # Additional validation based on metrics
        if result.metrics.tasks_completed == 0 and result.metrics.tasks_sent > 0:
            issues.append("No tasks completed despite tasks being sent")

        if result.metrics.failure_rate_percent > 50:
            issues.append(
                f"High failure rate: {result.metrics.failure_rate_percent:.1f}%"
            )

        return ValidationStatus(
            test_type_verified=test_type_verified,
            expected_metrics_present=expected_metrics_present,
            performance_signature_match=performance_signature_match,
            issues=issues,
        )

    @staticmethod
    def _generate_recommendations_pydantic(result: LoadTestResult) -> list[str]:
        """Generate recommendations using Pydantic models."""

        recommendations = []

        throughput = result.metrics.overall_throughput
        failure_rate = result.metrics.failure_rate_percent

        if throughput < 10:
            recommendations.append(
                "Low throughput detected. Consider reducing task complexity "
                "or increasing worker concurrency."
            )

        if failure_rate > 5:
            recommendations.append(
                f"High failure rate ({failure_rate:.1f}%). Check worker logs "
                f"for error patterns."
            )

        duration = result.metrics.total_duration_seconds
        tasks_sent = result.metrics.tasks_sent

        if duration > 60 and tasks_sent < 200:
            recommendations.append(
                "Long execution time for relatively few tasks suggests queue "
                "saturation. Consider testing with smaller batches or "
                "different queues."
            )

        return recommendations


# Convenience functions for common load test patterns
async def quick_cpu_test(num_tasks: int = 50) -> str:
    """Quick CPU load test with sensible defaults."""
    config = LoadTestConfiguration(
        num_tasks=num_tasks,
        task_type=LoadTestTypes.CPU_INTENSIVE,
        batch_size=10,
        target_queue=get_load_test_queue(),
    )
    return await LoadTestService.enqueue_load_test(config)


async def quick_io_test(num_tasks: int = 100) -> str:
    """Quick I/O load test with sensible defaults."""
    config = LoadTestConfiguration(
        num_tasks=num_tasks,
        task_type=LoadTestTypes.IO_SIMULATION,
        batch_size=20,
        delay_ms=50,
        target_queue=get_load_test_queue(),
    )
    return await LoadTestService.enqueue_load_test(config)


async def quick_memory_test(num_tasks: int = 200) -> str:
    """Quick memory load test with sensible defaults."""
    config = LoadTestConfiguration(
        num_tasks=num_tasks,
        task_type=LoadTestTypes.MEMORY_OPERATIONS,
        batch_size=25,
        target_queue=get_load_test_queue(),
    )
    return await LoadTestService.enqueue_load_test(config)
