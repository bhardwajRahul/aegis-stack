"""
System worker queue configuration for TaskIQ.

Handles system maintenance and monitoring tasks using TaskIQ patterns.
"""

from datetime import UTC, datetime

from app.core.config import settings
from app.core.log import logger
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
    url=redis_url, queue_name="taskiq:system"
).with_result_backend(RedisAsyncResultBackend(redis_url=redis_url))


@broker.task
async def system_health_check() -> dict[str, str]:
    """Simple system health check task."""
    logger.info("Running system health check task")

    return {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "task": "system_health_check",
    }


@broker.task
async def cleanup_temp_files() -> dict[str, str]:
    """Simple temp file cleanup task placeholder."""
    logger.info("Running temp file cleanup task")

    return {
        "status": "completed",
        "timestamp": datetime.now(UTC).isoformat(),
        "task": "cleanup_temp_files",
    }
