"""
System worker queue configuration for Dramatiq.

Handles system maintenance and monitoring tasks using Dramatiq patterns.
"""

from datetime import UTC, datetime

# Import broker to ensure it is initialised before actors are registered
import app.components.worker.broker  # noqa: F401
import dramatiq
from app.core.log import logger


@dramatiq.actor(queue_name="system", store_results=True)
async def system_health_check() -> dict[str, str]:
    """Simple system health check task."""
    logger.debug("Running system health check task")

    return {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "task": "system_health_check",
    }


@dramatiq.actor(queue_name="system", store_results=True)
async def cleanup_temp_files() -> dict[str, str]:
    """Simple temp file cleanup task placeholder."""
    logger.info("Running temp file cleanup task")

    return {
        "status": "completed",
        "timestamp": datetime.now(UTC).isoformat(),
        "task": "cleanup_temp_files",
    }
