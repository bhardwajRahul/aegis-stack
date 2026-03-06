"""
TaskIQ middleware for publishing worker events to Redis Streams.

Publishes job lifecycle events (started, completed, failed) from the worker
process. Enqueue-side events (job.enqueued) are handled separately in
pools_taskiq.py since middleware startup/shutdown run in the worker process,
not the client process.
"""

from typing import Any

import redis.asyncio as aioredis
from app.components.worker.events import publish_event
from app.core.config import settings
from app.core.log import logger
from taskiq import TaskiqMessage, TaskiqMiddleware, TaskiqResult


class EventPublishMiddleware(TaskiqMiddleware):
    """Publishes worker lifecycle events to a Redis Stream."""

    _redis: aioredis.Redis | None = None
    _queue_name: str = "unknown"

    def set_queue_name(self, queue_name: str) -> "EventPublishMiddleware":
        """Set the queue name for this middleware instance."""
        self._queue_name = queue_name
        return self

    async def startup(self) -> None:
        """Create Redis client and publish worker.started event."""
        try:
            redis_url = (
                settings.redis_url_effective
                if hasattr(settings, "redis_url_effective")
                else settings.REDIS_URL
            )
            self._redis = aioredis.from_url(redis_url)
            await publish_event(self._redis, "worker.started", self._queue_name)
        except Exception as e:
            logger.debug(f"Failed to initialize event publishing: {e}")

    async def shutdown(self) -> None:
        """Publish worker.stopped event and close Redis client."""
        if self._redis:
            await publish_event(self._redis, "worker.stopped", self._queue_name)
            await self._redis.aclose()
            self._redis = None

    async def pre_execute(self, message: TaskiqMessage) -> TaskiqMessage:
        """Publish job.started event before task execution."""
        if self._redis:
            await publish_event(
                self._redis,
                "job.started",
                self._queue_name,
                {"job_id": message.task_id, "task": message.task_name},
            )
        return message

    async def post_execute(
        self, message: TaskiqMessage, result: TaskiqResult[Any]
    ) -> None:
        """Publish job.completed or job.failed event after task execution."""
        if self._redis:
            event_type = "job.failed" if result.is_err else "job.completed"
            await publish_event(
                self._redis,
                event_type,
                self._queue_name,
                {"job_id": message.task_id, "task": message.task_name},
            )
