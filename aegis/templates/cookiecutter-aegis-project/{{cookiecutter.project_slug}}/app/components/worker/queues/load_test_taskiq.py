"""
Load test worker queue configuration for TaskIQ.

Handles load testing orchestration and synthetic workload tasks using TaskIQ patterns.
"""

import asyncio
from datetime import UTC, datetime
from typing import Any

from app.core.config import settings
from app.core.log import logger
from app.services.load_test_workloads import (
    run_cpu_intensive,
    run_failure_testing,
    run_io_simulation,
    run_memory_operations,
)
from taskiq_redis import RedisAsyncResultBackend, RedisStreamBroker

# Use redis_url_effective for Docker vs local auto-detection
redis_url = (
    settings.redis_url_effective
    if hasattr(settings, "redis_url_effective")
    else settings.REDIS_URL
)

# Create the broker with Redis backend (using streams for acknowledgement support)
# Use unique queue_name to ensure workers don't consume from each other's streams
broker = RedisStreamBroker(
    url=redis_url, queue_name="taskiq:load_test"
).with_result_backend(RedisAsyncResultBackend(redis_url=redis_url))


@broker.task
async def cpu_intensive_task() -> dict[str, Any]:
    """CPU-bound task for load testing."""
    return await run_cpu_intensive()


@broker.task
async def io_simulation_task() -> dict[str, Any]:
    """I/O simulation task for load testing."""
    return await run_io_simulation()


@broker.task
async def memory_operations_task() -> dict[str, Any]:
    """Memory operations task for load testing."""
    return await run_memory_operations()


@broker.task
async def failure_testing_task() -> dict[str, Any]:
    """Task that randomly fails for testing error handling."""
    return await run_failure_testing()


def _get_task_by_type(task_type: str) -> Any:
    """Get the task function by type string."""
    task_map = {
        "cpu_intensive": cpu_intensive_task,
        "cpu": cpu_intensive_task,
        "io_simulation": io_simulation_task,
        "io": io_simulation_task,
        "memory_operations": memory_operations_task,
        "memory": memory_operations_task,
        "failure_testing": failure_testing_task,
        "failure": failure_testing_task,
    }
    return task_map.get(task_type, io_simulation_task)


@broker.task
async def load_test_orchestrator(
    num_tasks: int = 100,
    task_type: str = "io",
    batch_size: int = 10,
    delay_ms: int = 0,
    target_queue: str | None = None,
) -> dict[str, Any]:
    """
    Load test orchestrator that spawns many tasks to measure queue throughput.

    Args:
        num_tasks: Number of tasks to spawn for the load test
        task_type: Type of task (cpu, io, memory, failure)
        batch_size: How many tasks to send concurrently per batch
        delay_ms: Delay between batches in milliseconds
        target_queue: Which queue to test (not used in TaskIQ, kept for API compat)

    Returns:
        Comprehensive load test results with throughput metrics
    """
    start_time = datetime.now(UTC)

    logger.info(
        f"Starting load test orchestrator: {num_tasks} {task_type} tasks "
        f"(batches of {batch_size})"
    )

    # Get the task function to spawn
    task_func = _get_task_by_type(task_type)

    tasks_sent = 0
    task_handles = []

    try:
        # Spawn tasks in batches
        for batch_start in range(0, num_tasks, batch_size):
            batch_end = min(batch_start + batch_size, num_tasks)
            current_batch_size = batch_end - batch_start

            # Enqueue batch of tasks using TaskIQ's kiq()
            batch_handles = []
            for _ in range(current_batch_size):
                handle = await task_func.kiq()
                batch_handles.append(handle)
                task_handles.append(handle)

            tasks_sent += current_batch_size
            logger.info(
                f"Sent batch: {current_batch_size} tasks "
                f"(total: {tasks_sent}/{num_tasks})"
            )

            # Add configurable delay between batches if specified
            if delay_ms > 0 and batch_end < num_tasks:
                await asyncio.sleep(delay_ms / 1000.0)

        logger.info(f"All {tasks_sent} tasks enqueued")

        # Monitor task completion
        completion_result = await _monitor_task_completion(
            task_handles=task_handles,
            expected_tasks=tasks_sent,
            timeout_seconds=300,
        )

        end_time = datetime.now(UTC)
        total_duration = (end_time - start_time).total_seconds()

        result = {
            "task_type": task_type,
            "tasks_sent": tasks_sent,
            "task_ids": [str(h.task_id) for h in task_handles[:10]],
            "batch_size": batch_size,
            "delay_ms": delay_ms,
            "target_queue": target_queue,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "total_duration_seconds": round(total_duration, 2),
            **completion_result,
        }

        # Calculate overall throughput
        if result.get("tasks_completed", 0) > 0:
            result["overall_throughput_per_second"] = round(
                result["tasks_completed"] / total_duration, 2
            )
        else:
            result["overall_throughput_per_second"] = 0

        logger.info(
            f"Load test complete: {result['tasks_completed']}/{tasks_sent} "
            f"tasks in {total_duration:.1f}s"
        )
        logger.info(f"Throughput: {result['overall_throughput_per_second']} tasks/sec")

        return result

    except Exception as e:
        logger.error(f"Load test orchestrator failed: {e}")
        return {"error": str(e), "tasks_sent": tasks_sent}


async def _monitor_task_completion(
    task_handles: list[Any],
    expected_tasks: int,
    timeout_seconds: int = 300,
    poll_interval: float = 2.0,
) -> dict[str, Any]:
    """
    Monitor task completion using TaskIQ result backend.

    Args:
        task_handles: List of AsyncTaskiqTask handles
        expected_tasks: Number of tasks expected to complete
        timeout_seconds: Maximum time to wait
        poll_interval: How often to check for completion

    Returns:
        Completion statistics
    """
    start_monitor = datetime.now(UTC)
    tasks_completed = 0
    tasks_failed = 0
    last_progress_time = start_monitor
    last_completed = 0

    completed_ids: set[str] = set()

    try:
        while True:
            # Check each task handle for completion
            for handle in task_handles:
                task_id = str(handle.task_id)
                if task_id in completed_ids:
                    continue

                # Check if result is ready
                try:
                    is_ready = await handle.is_ready()
                    if is_ready:
                        completed_ids.add(task_id)
                        # Check if it succeeded or failed
                        try:
                            result = await handle.get_result()
                            if result.is_err:
                                tasks_failed += 1
                            else:
                                tasks_completed += 1
                        except Exception:
                            # If we can't get result, count as completed
                            tasks_completed += 1
                except Exception:
                    # Handle not ready or error checking
                    pass

            tasks_done = tasks_completed + tasks_failed
            elapsed = (datetime.now(UTC) - start_monitor).total_seconds()
            throughput = tasks_completed / elapsed if elapsed > 0 else 0

            # Track progress
            if tasks_completed > last_completed:
                last_progress_time = datetime.now(UTC)
                last_completed = tasks_completed

            # Progress logging
            if tasks_done % 10 == 0 or tasks_done == expected_tasks:
                progress_pct = (
                    (tasks_done / expected_tasks * 100) if expected_tasks > 0 else 0
                )
                logger.info(
                    f"Progress: {tasks_done}/{expected_tasks} "
                    f"({progress_pct:.0f}% - completed: {tasks_completed}, "
                    f"failed: {tasks_failed}) throughput: {throughput:.1f} tasks/sec"
                )

            # Check completion
            if tasks_done >= expected_tasks:
                logger.info(
                    f"All tasks completed: {tasks_completed} success, {tasks_failed} failed"
                )
                break

            # Check timeout
            if elapsed > timeout_seconds:
                logger.warning(f"Load test timed out after {timeout_seconds}s")
                break

            # Check if stuck
            stuck_duration = (datetime.now(UTC) - last_progress_time).total_seconds()
            if stuck_duration > 30 and tasks_done > 0:
                logger.warning(
                    f"No progress for {stuck_duration:.0f}s, stopping monitor"
                )
                break

            await asyncio.sleep(poll_interval)

    except Exception as e:
        logger.error(f"Task monitoring error: {e}")

    final_elapsed = (datetime.now(UTC) - start_monitor).total_seconds()

    return {
        "tasks_completed": tasks_completed,
        "tasks_failed": tasks_failed,
        "monitor_duration_seconds": round(final_elapsed, 2),
        "average_throughput_per_second": round(tasks_completed / final_elapsed, 2)
        if final_elapsed > 0
        else 0,
        "completion_percentage": round((tasks_completed / expected_tasks * 100), 1)
        if expected_tasks > 0
        else 0,
        "failure_rate_percent": round((tasks_failed / expected_tasks * 100), 1)
        if expected_tasks > 0
        else 0,
    }
