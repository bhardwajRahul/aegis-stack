"""
Tests for core health logic and component status propagation.

These tests focus on the pure logic of health checking, warning propagation,
and component hierarchy without external dependencies like Redis or system metrics.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any

import pytest

from app.services.system import ComponentStatus, ComponentStatusType
from app.services.system.health import (
    get_system_status,
)



class TestComponentStatusPropagation:
    """Test warning status propagation through component hierarchies."""

    def test_component_status_creation_with_warning(self) -> None:
        """Test creating ComponentStatus with warning status."""
        status = ComponentStatus(
            name="test_component",
            status=ComponentStatusType.WARNING,
            message="Has warnings but still healthy",
            response_time_ms=100.0,
        )

        assert status.name == "test_component"
        assert status.healthy is True
        assert status.status == ComponentStatusType.WARNING
        assert status.message == "Has warnings but still healthy"

    def test_component_status_defaults_to_healthy(self) -> None:
        """Test that ComponentStatus defaults to HEALTHY status."""
        status = ComponentStatus(
            name="test_component",
            message="All good",
        )

        assert status.status == ComponentStatusType.HEALTHY

    def test_unhealthy_component_with_unhealthy_status(self) -> None:
        """Test that unhealthy components get UNHEALTHY status."""
        status = ComponentStatus(
            name="test_component",
            status=ComponentStatusType.UNHEALTHY,
            message="Something is broken",
        )

        assert status.healthy is False
        assert status.status == ComponentStatusType.UNHEALTHY

    def test_sub_component_hierarchy(self) -> None:
        """Test component with sub-components for hierarchy testing."""
        # Create sub-components with different statuses
        sub_component_healthy = ComponentStatus(
            name="sub_healthy",
            status=ComponentStatusType.HEALTHY,
            message="Sub-component is healthy",
        )

        sub_component_warning = ComponentStatus(
            name="sub_warning", 
            status=ComponentStatusType.WARNING,
            message="Sub-component has warnings",
        )

        # Create parent component
        parent_component = ComponentStatus(
            name="parent",
            status=ComponentStatusType.WARNING,  # Should propagate from sub-components
            message="Parent has sub-component warnings",
            sub_components={
                "sub_healthy": sub_component_healthy,
                "sub_warning": sub_component_warning,
            }
        )

        assert parent_component.healthy is True
        assert parent_component.status == ComponentStatusType.WARNING
        assert len(parent_component.sub_components) == 2
        assert (
            parent_component.sub_components["sub_warning"].status
            == ComponentStatusType.WARNING
        )


class TestSystemStatusWarningPropagation:
    """Test warning propagation in real system status scenarios."""

    @pytest.mark.asyncio
    async def test_system_status_with_mixed_component_health(self) -> None:
        """Test system status calculation with components having different states."""
        
        # Mock the health check registry to have controlled components
        mock_healthy_component = AsyncMock(return_value=ComponentStatus(
            name="healthy_service",
            status=ComponentStatusType.HEALTHY,
            message="Service is running well",
        ))

        mock_warning_component = AsyncMock(return_value=ComponentStatus(
            name="warning_service",
            status=ComponentStatusType.WARNING,
            message="Service has warnings",
        ))

        mock_unhealthy_component = AsyncMock(return_value=ComponentStatus(
            name="unhealthy_service",
            status=ComponentStatusType.UNHEALTHY,
            message="Service is down",
        ))

        # Mock the system metrics to avoid actual system calls
        mock_system_metrics = {
            "memory": ComponentStatus(
                name="memory",
                status=ComponentStatusType.HEALTHY,
                message="Memory usage: 50%",
            ),
            "cpu": ComponentStatus(
                name="cpu",
                status=ComponentStatusType.HEALTHY,
                message="CPU usage: 10%",
            ),
            "disk": ComponentStatus(
                name="disk",
                status=ComponentStatusType.HEALTHY,
                message="Disk usage: 30%",
            ),
        }

        with patch('app.services.system.health._health_checks', {
            'healthy_service': mock_healthy_component,
            'warning_service': mock_warning_component, 
            'unhealthy_service': mock_unhealthy_component,
        }), patch(
            'app.services.system.health._get_cached_system_metrics',
            return_value=mock_system_metrics
        ), patch(
            'app.services.system.health._get_system_info',
            return_value={"test": "info"}
        ):

            system_status = await get_system_status()

            # System should be unhealthy due to unhealthy_service
            assert system_status.overall_healthy is False

            # Check that components are present in aegis structure
            assert "aegis" in system_status.components
            aegis_component = system_status.components["aegis"]
            
            # Check that our test components are included
            assert "healthy_service" in aegis_component.sub_components
            assert "warning_service" in aegis_component.sub_components
            assert "unhealthy_service" in aegis_component.sub_components
            # System metrics grouped under backend
            assert "backend" in aegis_component.sub_components

            # Verify component statuses
            assert (
                aegis_component.sub_components["healthy_service"].status
                == ComponentStatusType.HEALTHY
            )
            assert (
                aegis_component.sub_components["warning_service"].status
                == ComponentStatusType.WARNING
            )
            assert (
                aegis_component.sub_components["unhealthy_service"].status
                == ComponentStatusType.UNHEALTHY
            )

    @pytest.mark.asyncio
    async def test_system_status_with_only_warnings_stays_healthy(self) -> None:
        """Test that system with only warnings remains overall healthy."""
        
        mock_warning_component = AsyncMock(return_value=ComponentStatus(
            name="warning_service",
            status=ComponentStatusType.WARNING,
            message="Service has warnings but functional",
        ))

        mock_system_metrics = {
            "memory": ComponentStatus(
                name="memory",
                status=ComponentStatusType.HEALTHY,
                message="Memory usage: 50%",
            ),
        }

        with patch('app.services.system.health._health_checks', {
            'warning_service': mock_warning_component,
        }), patch(
            'app.services.system.health._get_cached_system_metrics',
            return_value=mock_system_metrics
        ), patch(
            'app.services.system.health._get_system_info',
            return_value={"test": "info"}
        ):

            system_status = await get_system_status()

            # System should remain healthy since warnings don't affect overall health
            assert system_status.overall_healthy is True

            # But aegis component should propagate warning status
            aegis_component = system_status.components["aegis"]
            assert aegis_component.status == ComponentStatusType.WARNING
            assert aegis_component.healthy is True


class TestWorkerHealthLogic:
    """Test the specific worker health check logic and warning propagation."""

    def test_queue_status_determination_logic(self) -> None:
        """Test the logic for determining queue component status."""
        
        # Test case 1: Worker with no functions should be WARNING but healthy
        def check_empty_worker_status(
            queue_type: str,
            has_functions: bool,
            worker_alive: bool,
            failure_rate: float,
        ) -> tuple[bool, ComponentStatusType]:
            """Simulate the queue status logic from worker health check."""
            if not has_functions:
                queue_healthy = True  # Empty workers don't affect overall health
                queue_status = ComponentStatusType.WARNING  # But show as warning
            else:
                queue_healthy = worker_alive and failure_rate < 25
                queue_status = (
                    ComponentStatusType.HEALTHY
                    if queue_healthy
                    else ComponentStatusType.UNHEALTHY
                )
            
            return queue_healthy, queue_status

        # Empty worker (media/system queues)
        healthy, status = check_empty_worker_status("media", False, False, 100)
        assert healthy is True  # Doesn't affect system health
        assert status == ComponentStatusType.WARNING  # But shows warning

        # Active worker with good performance
        healthy, status = check_empty_worker_status("load_test", True, True, 5)
        assert healthy is True
        assert status == ComponentStatusType.HEALTHY

        # Active worker with high failure rate
        healthy, status = check_empty_worker_status("load_test", True, True, 50)
        assert healthy is False
        assert status == ComponentStatusType.UNHEALTHY

        # Active worker that's offline
        healthy, status = check_empty_worker_status("load_test", True, False, 0)
        assert healthy is False
        assert status == ComponentStatusType.UNHEALTHY

    def test_warning_propagation_to_parent_components(self) -> None:
        """Test warning propagation from queue -> queues -> worker."""

        # Simulate the propagation logic used in worker health check
        def check_warning_propagation(
            sub_components: dict[str, ComponentStatus]
        ) -> ComponentStatusType:
            """Simulate queues component status determination."""
            queues_healthy = all(
                queue.healthy for queue in sub_components.values()
            )
            
            has_warnings = any(
                queue.status == ComponentStatusType.WARNING
                for queue in sub_components.values()
            )
            
            if has_warnings and queues_healthy:
                return ComponentStatusType.WARNING
            elif queues_healthy:
                return ComponentStatusType.HEALTHY
            else:
                return ComponentStatusType.UNHEALTHY

        # Test case: Some queues have warnings, all are healthy
        sub_components = {
            "media": ComponentStatus(
                name="media",
                status=ComponentStatusType.WARNING,
                message="No tasks configured",
            ),
            "system": ComponentStatus(
                name="system", 
                status=ComponentStatusType.WARNING,
                message="No tasks configured",
            ),
            "load_test": ComponentStatus(
                name="load_test",
                status=ComponentStatusType.HEALTHY,
                message="Active with completed tasks",
            ),
        }

        queues_status = check_warning_propagation(sub_components)
        assert queues_status == ComponentStatusType.WARNING

        # Test case: All components healthy
        for component in sub_components.values():
            component.status = ComponentStatusType.HEALTHY

        queues_status = check_warning_propagation(sub_components)
        assert queues_status == ComponentStatusType.HEALTHY

        # Test case: One component unhealthy
        sub_components["load_test"].status = ComponentStatusType.UNHEALTHY

        queues_status = check_warning_propagation(sub_components)
        assert queues_status == ComponentStatusType.UNHEALTHY


class TestComponentMetadata:
    """Test component metadata handling and serialization."""

    def test_component_status_with_complex_metadata(self) -> None:
        """Test ComponentStatus with complex metadata for different component types."""
        
        # Worker component metadata
        worker_metadata = {
            "total_queued": 5,
            "total_completed": 1000,
            "total_failed": 50,
            "overall_failure_rate_percent": 4.8,
            "redis_url": "redis://localhost:6379",
            "queue_configuration": {
                "load_test": {
                    "description": "Load testing tasks",
                    "max_jobs": 50,
                    "timeout_seconds": 300,
                }
            }
        }

        worker_status = ComponentStatus(
            name="worker",
            status=ComponentStatusType.WARNING,
            message="arq worker infrastructure: 1/3 workers active",
            metadata=worker_metadata,
        )

        # Verify metadata is preserved
        assert worker_status.metadata["total_completed"] == 1000
        assert worker_status.metadata["overall_failure_rate_percent"] == 4.8
        assert "queue_configuration" in worker_status.metadata

        # Cache component metadata
        cache_metadata = {
            "implementation": "redis",
            "version": "7.0.0",
            "connected_clients": 2,
            "used_memory_human": "1.5M",
            "uptime_in_seconds": 3600,
        }

        cache_status = ComponentStatus(
            name="cache",
            status=ComponentStatusType.HEALTHY,
            message="Redis cache connection successful",
            metadata=cache_metadata,
        )

        assert cache_status.metadata["implementation"] == "redis"
        assert cache_status.metadata["uptime_in_seconds"] == 3600

    def test_component_status_serialization(self) -> None:
        """Test that ComponentStatus can be properly serialized (for API responses)."""
        
        status = ComponentStatus(
            name="test_component",
            status=ComponentStatusType.WARNING,
            message="Component with warning",
            response_time_ms=123.45,
            metadata={"key": "value", "number": 42},
            sub_components={
                "sub1": ComponentStatus(
                    name="sub1",
                    status=ComponentStatusType.HEALTHY,
                    message="Sub-component OK",
                )
            }
        )

        # Convert to dict (simulates JSON serialization)
        status_dict = status.model_dump()

        # Verify structure
        assert status_dict["name"] == "test_component"
        assert status_dict["healthy"] is True
        assert status_dict["status"] == "warning"
        assert status_dict["message"] == "Component with warning"
        assert status_dict["response_time_ms"] == 123.45
        assert status_dict["metadata"]["key"] == "value"
        assert "sub1" in status_dict["sub_components"]
        assert status_dict["sub_components"]["sub1"]["status"] == "healthy"