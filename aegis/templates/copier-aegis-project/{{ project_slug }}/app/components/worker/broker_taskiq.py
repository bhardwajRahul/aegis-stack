"""
Pause-aware TaskIQ broker for rolling deploys.

Wraps ``RedisStreamBroker`` so the consume loop gates on a Redis flag
(``aegis:queue:paused``) before pulling each batch from the stream. During a
rolling deploy (``aegis deploy --rolling``), the deploy script SETs the
flag, waits for in-flight jobs to drain via the per-worker heartbeat
key, then restarts worker containers. Workers that finish their current
job during the pause sit idle on the gate instead of consuming a new
message that would be killed by SIGTERM.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
from taskiq import AckableMessage
from taskiq_redis import RedisStreamBroker
from taskiq_redis.redis_broker import logger as _broker_logger

PAUSE_KEY = "aegis:queue:paused"
PAUSE_POLL_SECONDS = 1.0


class PausableRedisStreamBroker(RedisStreamBroker):
    """``RedisStreamBroker`` that gates ``listen()`` on a pause flag.

    The gate is checked before every ``XREADGROUP`` and before the
    pending/autoclaim sweep, so a paused worker never pulls a new
    message from the stream. Already-executing jobs are unaffected
    (the deploy script's drain wait handles those via the heartbeat).
    """

    async def _is_paused(self, conn: aioredis.Redis) -> bool:
        try:
            return bool(await conn.get(PAUSE_KEY))
        except Exception as exc:
            _broker_logger.debug("pause flag check failed: %s", exc)
            return False

    async def _wait_while_paused(self, conn: aioredis.Redis) -> None:
        while await self._is_paused(conn):
            await asyncio.sleep(PAUSE_POLL_SECONDS)

    async def listen(self) -> AsyncGenerator[AckableMessage]:
        """Re-implementation of ``RedisStreamBroker.listen`` with a pause gate.

        Mirrors the upstream loop (see ``taskiq_redis.redis_broker``):
        ``xreadgroup`` for new messages, then ``xautoclaim`` for
        pending/unacknowledged ones. A pause-flag check sits at the top
        of each iteration so neither fetch happens while paused.
        """
        async with aioredis.Redis(connection_pool=self.connection_pool) as redis_conn:
            while True:
                await self._wait_while_paused(redis_conn)

                _broker_logger.debug("Starting fetching new messages")
                fetched = await redis_conn.xreadgroup(
                    self.consumer_group_name,
                    self.consumer_name,
                    {
                        self.queue_name: ">",
                        **self.additional_streams,  # type: ignore[dict-item]
                    },
                    block=self.block,
                    noack=False,
                    count=self.count,
                )
                for _, msg_list in fetched:
                    for msg_id, msg in msg_list:
                        yield AckableMessage(
                            data=msg[b"data"],
                            ack=self._ack_generator(msg_id),
                        )

                if await self._is_paused(redis_conn):
                    continue

                for stream in [self.queue_name, *self.additional_streams.keys()]:
                    lock = redis_conn.lock(
                        f"autoclaim:{self.consumer_group_name}:{stream}",
                    )
                    if await lock.locked():
                        continue
                    async with lock:
                        pending = await redis_conn.xautoclaim(
                            name=stream,
                            groupname=self.consumer_group_name,
                            consumername=self.consumer_name,
                            min_idle_time=self.idle_timeout,
                            count=self.unacknowledged_batch_size,
                        )
                        for msg_id, msg in pending[1]:
                            yield AckableMessage(
                                data=msg[b"data"],
                                ack=self._ack_generator(msg_id),
                            )
