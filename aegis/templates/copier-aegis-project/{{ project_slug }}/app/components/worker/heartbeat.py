"""
Worker heartbeat for rolling-deploy drain detection.

Each worker SETEXs ``worker:<host>:<pid>:busy`` for the duration of a
job. The ``aegis deploy --rolling`` command polls ``KEYS worker:*:busy``
after setting the pause flag and proceeds once empty (or aborts on
timeout). Keeping the signal in Redis — rather than in broker
internals — means the same deploy-side drain check works regardless of
queue library (taskiq, dramatiq, arq).

Best-effort: a Redis blip must never fail a job, so callers should not
propagate exceptions from these helpers.
"""

from __future__ import annotations

import os
import socket

import redis as sync_redis
import redis.asyncio as aioredis
from app.core.log import logger

BUSY_KEY_PREFIX = "worker:"
BUSY_KEY_SUFFIX = ":busy"
DEFAULT_TTL_SECONDS = 30

_worker_id: str | None = None


def worker_id() -> str:
    """Return a stable identifier for this worker process."""
    global _worker_id
    if _worker_id is None:
        _worker_id = f"{socket.gethostname()}:{os.getpid()}"
    return _worker_id


def busy_key(wid: str | None = None) -> str:
    return f"{BUSY_KEY_PREFIX}{wid or worker_id()}{BUSY_KEY_SUFFIX}"


async def mark_busy(
    redis: aioredis.Redis, ttl_seconds: int = DEFAULT_TTL_SECONDS
) -> None:
    """Mark this worker as actively executing a job.

    The key carries a TTL so a worker that dies mid-job (or whose
    network drops) eventually disappears from the drain check rather
    than blocking deploys forever.
    """
    try:
        await redis.set(busy_key(), "1", ex=ttl_seconds)
    except Exception as exc:
        logger.debug("heartbeat mark_busy failed: %s", exc)


async def mark_idle(redis: aioredis.Redis) -> None:
    """Mark this worker as idle (no job in flight)."""
    try:
        await redis.delete(busy_key())
    except Exception as exc:
        logger.debug("heartbeat mark_idle failed: %s", exc)


def mark_busy_sync(
    redis: sync_redis.Redis, ttl_seconds: int = DEFAULT_TTL_SECONDS
) -> None:
    """Sync variant of :func:`mark_busy` for dramatiq middleware."""
    try:
        redis.set(busy_key(), "1", ex=ttl_seconds)
    except Exception as exc:
        logger.debug("heartbeat mark_busy_sync failed: %s", exc)


def mark_idle_sync(redis: sync_redis.Redis) -> None:
    """Sync variant of :func:`mark_idle` for dramatiq middleware."""
    try:
        redis.delete(busy_key())
    except Exception as exc:
        logger.debug("heartbeat mark_idle_sync failed: %s", exc)
