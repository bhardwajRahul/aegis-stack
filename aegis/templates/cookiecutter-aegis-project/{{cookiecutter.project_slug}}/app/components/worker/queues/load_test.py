"""
Load test worker queue configuration.

Handles load testing orchestration and synthetic workload tasks using native arq
patterns.
"""

from arq.connections import RedisSettings

from app.core.config import settings

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
    
    # arq configuration  
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    queue_name = "arq:queue:load_test"
    max_jobs = 50  # High concurrency for load testing
    job_timeout = 60  # Quick tasks
    keep_result = settings.WORKER_KEEP_RESULT_SECONDS
    max_tries = settings.WORKER_MAX_TRIES
    health_check_interval = 30