"""
Shared Dramatiq broker initialization.

Dramatiq uses a single global broker. This module initializes a RedisBroker
once; queue modules import ``broker`` from here to register actors.

The broker is configured with:
- Results middleware for retrieving task return values
- EventPublishMiddleware for publishing lifecycle events to Redis Streams
"""

import dramatiq
from app.components.worker.middleware import EventPublishMiddleware
from app.core.config import settings
from dramatiq.brokers.redis import RedisBroker
from dramatiq.middleware import AsyncIO
from dramatiq.results import Results
from dramatiq.results.backends.redis import RedisBackend

# Use redis_url_effective for Docker vs local auto-detection
redis_url = (
    settings.redis_url_effective
    if hasattr(settings, "redis_url_effective")
    else settings.REDIS_URL
)

# Result backend for storing task return values
result_backend = RedisBackend(url=redis_url)

# Create a single global RedisBroker
broker = RedisBroker(url=redis_url)
broker.add_middleware(AsyncIO())
broker.add_middleware(Results(backend=result_backend))
broker.add_middleware(EventPublishMiddleware())

# Set as the global broker so @dramatiq.actor uses it
dramatiq.set_broker(broker)
