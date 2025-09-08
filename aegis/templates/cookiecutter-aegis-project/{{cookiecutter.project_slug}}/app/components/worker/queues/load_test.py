"""
Load test worker queue configuration.

Handles load testing orchestration and synthetic workload tasks using native arq
patterns.
"""

from arq.connections import RedisSettings

# Import load test tasks
from app.components.worker.tasks.load_tasks import (
    cpu_intensive_task,
    failure_testing_task,
    io_simulation_task,
    memory_operations_task,
)
from app.components.worker.tasks.system_tasks import (
    load_test_orchestrator,
)
from app.core.config import settings


class WorkerSettings:
    """Load testing worker configuration."""

    # Human-readable description
    description = "Load testing and performance testing"

    # Task functions for this queue
    functions = [
        # Load test orchestrator
        load_test_orchestrator,
        # Synthetic workload tasks
        cpu_intensive_task,
        io_simulation_task,
        memory_operations_task,
        failure_testing_task,
    ]

    # arq configuration with improved connection settings
    base_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    redis_settings = RedisSettings(
        host=base_settings.host,
        port=base_settings.port,
        database=base_settings.database,
        password=base_settings.password,
        conn_timeout=settings.REDIS_CONN_TIMEOUT,
        conn_retries=settings.REDIS_CONN_RETRIES,
        conn_retry_delay=settings.REDIS_CONN_RETRY_DELAY,
    )
    queue_name = "arq:queue:load_test"
    max_jobs = 50  # High concurrency for load testing
    job_timeout = 60  # Quick tasks
    keep_result = settings.WORKER_KEEP_RESULT_SECONDS
    max_tries = settings.WORKER_MAX_TRIES
    health_check_interval = settings.WORKER_HEALTH_CHECK_INTERVAL
