"""
Health context models for AI chat integration.

This module provides data structures for managing system health context injection
into AI chat conversations, giving Illiana awareness of system state.
"""

from datetime import datetime
from typing import Any

from app.services.system.models import SystemStatus
from pydantic import BaseModel, Field


class HealthContext(BaseModel):
    """
    Context from system health for injection into AI prompts.

    Holds system status and provides formatting methods for prompt injection
    and metadata storage.
    """

    status: SystemStatus = Field(..., description="System health status")
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When health was fetched",
    )

    def format_for_prompt(self, verbose: bool = False) -> str:
        """
        Format health data for injection into system prompt.

        Args:
            verbose: Whether to include detailed component info

        Returns:
            Compact markdown string for prompt injection
        """
        lines = []

        # Header with overall health
        healthy_count = len(self.status.healthy_components)
        total_count = len(self.status._get_all_components_flat())
        health_pct = self.status.health_percentage

        status_emoji = "OK" if self.status.overall_healthy else "DEGRADED"
        health_str = f"{health_pct:.0f}% - {healthy_count}/{total_count} components"
        lines.append(f"Health: {status_emoji} ({health_str})")

        # System resources (CPU, Memory, Disk)
        resources = self._extract_system_resources()
        if resources:
            resource_parts = []
            if "cpu" in resources:
                resource_parts.append(f"CPU {resources['cpu']:.0f}%")
            if "memory" in resources:
                resource_parts.append(f"Mem {resources['memory']:.0f}%")
            if "disk" in resources:
                resource_parts.append(f"Disk {resources['disk']:.0f}%")
            if resource_parts:
                lines.append(f"Resources: {' | '.join(resource_parts)}")

        # Database status
        db_info = self._extract_database_info()
        if db_info:
            db_parts = [db_info["status"]]
            if db_info.get("table_count"):
                db_parts.append(f"{db_info['table_count']} tables")
            if db_info.get("total_rows"):
                db_parts.append(f"{db_info['total_rows']:,} rows")
            lines.append(f"Database: {', '.join(db_parts)}")

        # Cache status
        cache_info = self._extract_cache_info()
        if cache_info:
            cache_parts = [cache_info["status"]]
            if cache_info.get("hit_rate") is not None:
                cache_parts.append(f"hit rate {cache_info['hit_rate']:.0f}%")
            if cache_info.get("total_keys"):
                cache_parts.append(f"{cache_info['total_keys']:,} keys")
            lines.append(f"Cache: {', '.join(cache_parts)}")

        # Worker status
        worker_info = self._extract_worker_info()
        if worker_info:
            # Header with active/total workers
            active = worker_info.get("active_workers", 0)
            configured = worker_info.get("configured_queues", 0)
            if configured:
                lines.append(f"Workers: {active}/{configured} active")
            else:
                lines.append(f"Workers: {active} active")

            # Queue details
            queues = worker_info.get("queues", [])
            if queues:
                queue_statuses = []
                for q in queues:
                    name = q["name"]
                    if q.get("worker_alive"):
                        # Determine if busy or idle
                        ongoing = q.get("jobs_ongoing", 0)
                        status = "busy" if ongoing > 0 else "idle"
                    else:
                        status = "offline"
                    queue_statuses.append(f"{name} ({status})")
                lines.append(f"  Queues: {', '.join(queue_statuses)}")

            # Job stats
            total_queued = worker_info.get("total_queued", 0)
            total_completed = worker_info.get("total_completed", 0)
            total_failed = worker_info.get("total_failed", 0)
            total_ongoing = worker_info.get("total_ongoing", 0)
            job_parts = []
            if total_ongoing:
                job_parts.append(f"{total_ongoing} running")
            job_parts.append(f"{total_queued} queued")
            job_parts.append(f"{total_completed} completed")
            if total_failed:
                job_parts.append(f"{total_failed} failed")
            lines.append(f"  Jobs: {', '.join(job_parts)}")

        # Scheduler status
        scheduler_info = self._extract_scheduler_info()
        if scheduler_info:
            total = scheduler_info.get("total_tasks", 0)
            active = scheduler_info.get("active_tasks", 0)
            paused = scheduler_info.get("paused_tasks", 0)

            if total:
                if paused:
                    lines.append(
                        f"Scheduler: {active}/{total} active ({paused} paused)"
                    )
                else:
                    lines.append(f"Scheduler: {active} active tasks")
            else:
                lines.append("Scheduler: No tasks configured")

            # Show upcoming tasks (next 3 for brevity)
            upcoming = scheduler_info.get("upcoming_tasks", [])
            if upcoming:
                task_strs = []
                for task in upcoming[:3]:
                    name = task.get("name", task.get("job_id", "Unknown"))
                    schedule = task.get("schedule", "")
                    task_strs.append(f"{name} ({schedule})")
                lines.append(f"  Next: {', '.join(task_strs)}")

        # AI service status
        ai_info = self._extract_ai_service_info()
        if ai_info:
            ai_line = f"AI: {ai_info['status']}"
            if ai_info.get("provider"):
                ai_line += f" | Provider: {ai_info['provider']}"
            if ai_info.get("model"):
                ai_line += f" | Model: {ai_info['model']}"
            lines.append(ai_line)

        # Unhealthy components with details
        issues = self._extract_issues()
        if issues:
            lines.append("Issues:")
            for name, message in issues[:5]:
                lines.append(f"  - {name}: {message}")

        return "\n".join(lines)

    def _extract_system_resources(self) -> dict[str, float]:
        """Extract CPU, memory, disk percentages from health status."""
        resources: dict[str, float] = {}

        # Navigate to backend component which contains system metrics
        aegis = self.status.components.get("aegis")
        if not aegis:
            return resources

        components = aegis.sub_components.get("components")
        if not components:
            return resources

        backend = components.sub_components.get("backend")
        if not backend:
            return resources

        # Extract from sub_components (cpu, memory, disk)
        for metric_name in ["cpu", "memory", "disk"]:
            metric = backend.sub_components.get(metric_name)
            if metric and metric.metadata:
                percent = metric.metadata.get("percent_used")
                if percent is not None:
                    resources[metric_name] = percent

        return resources

    def _extract_database_info(self) -> dict[str, Any]:
        """Extract database info from health status."""
        info: dict[str, Any] = {}

        aegis = self.status.components.get("aegis")
        if not aegis:
            return info

        components = aegis.sub_components.get("components")
        if not components:
            return info

        database = components.sub_components.get("database")
        if not database:
            return info

        info["status"] = database.status.value
        if database.metadata:
            info["table_count"] = database.metadata.get("table_count")
            info["total_rows"] = database.metadata.get("total_rows")
            info["file_size"] = database.metadata.get("file_size_human")

        return info

    def _extract_cache_info(self) -> dict[str, Any]:
        """Extract cache/Redis info from health status."""
        info: dict[str, Any] = {}

        aegis = self.status.components.get("aegis")
        if not aegis:
            return info

        components = aegis.sub_components.get("components")
        if not components:
            return info

        cache = components.sub_components.get("cache")
        if not cache:
            return info

        info["status"] = cache.status.value
        if cache.metadata:
            info["hit_rate"] = cache.metadata.get("hit_rate_percent")
            info["total_keys"] = cache.metadata.get("total_keys")
            info["memory"] = cache.metadata.get("used_memory_human")

        return info

    def _extract_worker_info(self) -> dict[str, Any]:
        """Extract worker queue info from health status."""
        info: dict[str, Any] = {}

        aegis = self.status.components.get("aegis")
        if not aegis:
            return info

        components = aegis.sub_components.get("components")
        if not components:
            return info

        worker = components.sub_components.get("worker")
        if not worker:
            return info

        info["status"] = worker.status.value
        if worker.metadata:
            info["total_queued"] = worker.metadata.get("total_queued", 0)
            info["total_completed"] = worker.metadata.get("total_completed", 0)
            info["total_failed"] = worker.metadata.get("total_failed", 0)
            info["total_ongoing"] = worker.metadata.get("total_ongoing", 0)
            info["failure_rate"] = worker.metadata.get("overall_failure_rate_percent")

        # Extract queue details from subcomponents
        queues_component = worker.sub_components.get("queues")
        if queues_component:
            if queues_component.metadata:
                info["active_workers"] = queues_component.metadata.get("active_workers")
                info["configured_queues"] = queues_component.metadata.get(
                    "configured_queues"
                )

            # Get individual queue status
            queue_details: list[dict[str, Any]] = []
            for queue_name, queue in queues_component.sub_components.items():
                queue_info = {
                    "name": queue_name,
                    "status": queue.status.value,
                    "healthy": queue.healthy,
                }
                if queue.metadata:
                    queue_info["worker_alive"] = queue.metadata.get("worker_alive")
                    queue_info["jobs_queued"] = queue.metadata.get("queued_jobs", 0)
                    queue_info["jobs_completed"] = queue.metadata.get(
                        "jobs_completed", 0
                    )
                    queue_info["jobs_failed"] = queue.metadata.get("jobs_failed", 0)
                    queue_info["jobs_ongoing"] = queue.metadata.get("jobs_ongoing", 0)
                queue_details.append(queue_info)

            if queue_details:
                info["queues"] = queue_details

        return info

    def _extract_scheduler_info(self) -> dict[str, Any]:
        """Extract scheduler info from health status."""
        info: dict[str, Any] = {}

        aegis = self.status.components.get("aegis")
        if not aegis:
            return info

        components = aegis.sub_components.get("components")
        if not components:
            return info

        scheduler = components.sub_components.get("scheduler")
        if not scheduler:
            return info

        info["status"] = scheduler.status.value
        if scheduler.metadata:
            info["total_tasks"] = scheduler.metadata.get("total_tasks", 0)
            info["active_tasks"] = scheduler.metadata.get("active_tasks", 0)
            info["paused_tasks"] = scheduler.metadata.get("paused_tasks", 0)
            info["scheduler_state"] = scheduler.metadata.get("scheduler_state")
            info["upcoming_tasks"] = scheduler.metadata.get("upcoming_tasks", [])

        return info

    def _extract_ai_service_info(self) -> dict[str, Any]:
        """Extract AI service info from health status."""
        info: dict[str, Any] = {}

        aegis = self.status.components.get("aegis")
        if not aegis:
            return info

        services = aegis.sub_components.get("services")
        if not services:
            return info

        ai = services.sub_components.get("ai")
        if not ai:
            return info

        info["status"] = ai.status.value
        info["message"] = ai.message
        if ai.metadata:
            info["provider"] = ai.metadata.get("provider")
            info["model"] = ai.metadata.get("model")

        return info

    def _extract_issues(self) -> list[tuple[str, str]]:
        """Extract unhealthy components with their error messages."""
        issues = []
        for name, component in self.status._get_all_components_flat():
            if not component.healthy:
                # Skip parent containers (focus on actual issues)
                if component.sub_components:
                    continue
                # Get friendly name (last part of dotted path)
                friendly_name = name.split(".")[-1]
                issues.append((friendly_name, component.message))
        return issues

    def to_metadata(self) -> dict[str, Any]:
        """
        Convert health context to metadata format for storage in response.

        Returns:
            Summary metadata dictionary
        """
        return {
            "overall_healthy": self.status.overall_healthy,
            "health_percentage": self.status.health_percentage,
            "healthy_count": len(self.status.healthy_components),
            "total_count": len(self.status._get_all_components_flat()),
            "unhealthy_components": self.status.unhealthy_components[:5],
            "timestamp": self.timestamp.isoformat(),
        }


__all__ = ["HealthContext"]
