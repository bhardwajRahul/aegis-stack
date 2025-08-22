"""
System worker queue configuration.

Handles system maintenance and monitoring tasks using native arq patterns.
"""

from arq.connections import RedisSettings

from app.core.config import settings

# Import system tasks
from app.components.worker.tasks.simple_system_tasks import (
    system_health_check,
    cleanup_temp_files,
)

class WorkerSettings:
    """System maintenance worker configuration."""
    
    # Human-readable description
    description = "System maintenance and monitoring tasks"
    
    # Task functions for this queue
    functions = [
        system_health_check,
        cleanup_temp_files,
    ]
    
    # arq configuration
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    queue_name = "arq:queue:system"
    max_jobs = 15  # Moderate concurrency for administrative operations
    job_timeout = 300  # 5 minutes
    keep_result = settings.WORKER_KEEP_RESULT_SECONDS
    max_tries = settings.WORKER_MAX_TRIES
    health_check_interval = 30