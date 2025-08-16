"""
Media worker queue configuration.

Handles image processing, file operations, and media transformations using native
arq patterns.
"""

from typing import Any

from arq.connections import RedisSettings

from app.core.config import settings

# Import media tasks (when available)
# from app.components.worker.tasks.media_tasks import (
#     image_resize,
#     video_encode, 
#     file_convert,
# )


class WorkerSettings:
    """Media processing worker configuration."""
    
    # Human-readable description
    description = "Image and file processing"
    
    # Task functions for this queue
    functions: list[Any] = [
        # Media processing tasks will be added here
        # Example: image_resize, video_encode, file_convert
    ]
    
    # arq configuration
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL) 
    queue_name = "arq:queue:media"
    max_jobs = 10  # I/O-bound file operations
    job_timeout = 600  # 10 minutes - file processing can take time
    keep_result = settings.WORKER_KEEP_RESULT_SECONDS
    max_tries = settings.WORKER_MAX_TRIES
    health_check_interval = 30