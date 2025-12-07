"""
Load testing worker tasks for arq.

Thin wrappers around shared workload functions from load_test_workloads service.
"""

from typing import Any

from app.services.load_test_workloads import (
    run_cpu_intensive,
    run_failure_testing,
    run_io_simulation,
    run_memory_operations,
)


async def cpu_intensive_task(ctx: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    """CPU-intensive load testing task."""
    task_id = ctx.get("job_id", "unknown")
    return await run_cpu_intensive(task_id=task_id)


async def io_simulation_task(ctx: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    """I/O simulation load testing task."""
    task_id = ctx.get("job_id", "unknown")
    return await run_io_simulation(task_id=task_id)


async def memory_operations_task(ctx: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    """Memory operations load testing task."""
    task_id = ctx.get("job_id", "unknown")
    return await run_memory_operations(task_id=task_id)


async def failure_testing_task(ctx: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    """Failure testing task for error handling validation."""
    task_id = ctx.get("job_id", "unknown")
    return await run_failure_testing(task_id=task_id)
