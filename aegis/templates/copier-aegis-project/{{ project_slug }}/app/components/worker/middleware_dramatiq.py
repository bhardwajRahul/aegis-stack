"""
Dramatiq middleware for publishing worker events to Redis Streams.

Publishes job lifecycle events (started, completed, failed) and worker
lifecycle events (started, stopped) from the worker process. Middleware
hooks in Dramatiq are **sync**, so this uses sync ``redis.Redis`` for
event publishing.

Enqueue-side events (job.enqueued) are handled separately in
pools.py since middleware runs in the worker process, not
the client process.
"""

import contextlib
import threading

import dramatiq
import redis
from app.core.config import settings
from app.core.log import logger

# Redis Stream name for worker events (must match events.py)
WORKER_EVENT_STREAM = "aegis:events:worker"


def _get_redis_url() -> str:
    """Get the effective Redis URL."""
    return (
        settings.redis_url_effective
        if hasattr(settings, "redis_url_effective")
        else settings.REDIS_URL
    )


def _sync_publish(
    client: redis.Redis,
    event_type: str,
    queue_name: str,
    metadata: dict[str, str] | None = None,
) -> None:
    """Publish an event to the Redis Stream (sync)."""
    from datetime import UTC, datetime

    fields: dict[str, str] = {
        "type": event_type,
        "queue": queue_name,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    if metadata:
        fields.update(metadata)

    try:
        client.xadd(WORKER_EVENT_STREAM, fields)  # type: ignore[arg-type]
    except Exception as e:
        logger.debug(f"Failed to publish worker event: {e}")


class EventPublishMiddleware(dramatiq.Middleware):
    """Publishes worker lifecycle events to a Redis Stream."""

    HEARTBEAT_TTL = 30
    HEARTBEAT_INTERVAL = 15

    _redis: redis.Redis | None = None
    _queue_names: set[str] = set()
    _heartbeat_thread: threading.Thread | None = None
    _stop_event: threading.Event = threading.Event()

    # ------------------------------------------------------------------
    # Worker lifecycle hooks
    # ------------------------------------------------------------------

    def _heartbeat_loop(self) -> None:
        """Background thread that refreshes heartbeat keys periodically."""
        while not self._stop_event.wait(self.HEARTBEAT_INTERVAL):
            if self._redis:
                for queue_name in self._queue_names:
                    with contextlib.suppress(Exception):
                        self._redis.set(
                            f"dramatiq:heartbeat:{queue_name}",
                            "alive",
                            ex=self.HEARTBEAT_TTL,
                        )

    def before_worker_boot(
        self, broker: dramatiq.Broker, worker: dramatiq.Worker
    ) -> None:
        """Create Redis client, publish worker.started, start heartbeat."""
        try:
            self._redis = redis.from_url(_get_redis_url())
            self._queue_names = (
                worker.consumer_whitelist or broker.get_declared_queues()
            )

            # Publish started event and set initial heartbeat
            for queue_name in self._queue_names:
                _sync_publish(self._redis, "worker.started", queue_name)
                self._redis.set(
                    f"dramatiq:heartbeat:{queue_name}",
                    "alive",
                    ex=self.HEARTBEAT_TTL,
                )

            # Start background heartbeat thread
            self._stop_event.clear()
            self._heartbeat_thread = threading.Thread(
                target=self._heartbeat_loop, daemon=True
            )
            self._heartbeat_thread.start()
        except Exception as e:
            logger.debug(f"Failed to initialize event publishing: {e}")

    def before_worker_shutdown(
        self, broker: dramatiq.Broker, worker: dramatiq.Worker
    ) -> None:
        """Publish worker.stopped, stop heartbeat, close Redis client."""
        self._stop_event.set()
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=5)
            self._heartbeat_thread = None

        if self._redis:
            for queue_name in self._queue_names:
                _sync_publish(self._redis, "worker.stopped", queue_name)
                self._redis.delete(f"dramatiq:heartbeat:{queue_name}")
            self._redis.close()
            self._redis = None

    # ------------------------------------------------------------------
    # Message lifecycle hooks
    # ------------------------------------------------------------------

    def before_process_message(
        self, broker: dramatiq.Broker, message: dramatiq.Message
    ) -> None:
        """Publish job.started event before task execution."""
        if self._redis:
            _sync_publish(
                self._redis,
                "job.started",
                message.queue_name,
                {"job_id": message.message_id, "task": message.actor_name},
            )
            # Record task started in history
            from app.components.worker.task_history import record_task_started_sync

            record_task_started_sync(self._redis, message.message_id)

    def after_process_message(
        self,
        broker: dramatiq.Broker,
        message: dramatiq.Message,
        *,
        result: object | None = None,
        exception: BaseException | None = None,
    ) -> None:
        """Publish job.completed or job.failed event after task execution."""
        if self._redis:
            event_type = "job.failed" if exception else "job.completed"
            _sync_publish(
                self._redis,
                event_type,
                message.queue_name,
                {"job_id": message.message_id, "task": message.actor_name},
            )
            # Record task finished in history
            from app.components.worker.task_history import record_task_finished_sync

            record_task_finished_sync(
                self._redis,
                message.message_id,
                success=exception is None,
                error=str(exception) if exception else None,
            )
