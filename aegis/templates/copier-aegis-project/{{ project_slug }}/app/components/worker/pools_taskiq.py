"""
TaskIQ task enqueueing utilities.

This module provides broker access and task enqueueing for TaskIQ-based workers.
Unlike arq which requires explicit connection pooling, TaskIQ brokers handle
their own connections internally.
"""

from typing import Any

from app.core.config import get_available_queues, get_default_queue, is_valid_queue
from app.core.log import logger

# Broker cache to avoid re-importing
_broker_cache: dict[str, Any] = {}


def get_broker(queue_type: str | None = None) -> Any:
    """
    Get the TaskIQ broker for a specific queue type.

    Args:
        queue_type: Queue type (system, load_test). Defaults to configured default.

    Returns:
        The TaskIQ broker instance for the queue.

    Raises:
        ValueError: If queue type is invalid.
    """
    if queue_type is None:
        queue_type = get_default_queue()

    if not is_valid_queue(queue_type):
        available = get_available_queues()
        raise ValueError(f"Invalid queue type '{queue_type}'. Available: {available}")

    if queue_type in _broker_cache:
        return _broker_cache[queue_type]

    # Dynamic import based on queue type
    if queue_type == "system":
        from app.components.worker.queues.system import broker

        _broker_cache[queue_type] = broker
    elif queue_type == "load_test":
        from app.components.worker.queues.load_test import broker

        _broker_cache[queue_type] = broker
    else:
        raise ValueError(f"Unknown queue type: {queue_type}")

    logger.debug(f"Loaded broker for queue: {queue_type}")
    return _broker_cache[queue_type]


def get_task(task_name: str, queue_type: str | None = None) -> Any:
    """
    Get a registered task by name from the appropriate queue.

    Args:
        task_name: Name of the task function.
        queue_type: Queue type to look in. Defaults to configured default.

    Returns:
        The TaskIQ task callable.

    Raises:
        ValueError: If task is not found.
    """
    if queue_type is None:
        queue_type = get_default_queue()

    # Direct import of tasks from queue modules
    # TaskIQ's broker.tasks dict only exists in worker process context,
    # so we import tasks directly for client-side access
    # Also cache the broker for proper shutdown later
    if queue_type == "load_test":
        from app.components.worker.queues.load_test import (
            broker,
            cpu_intensive_task,
            failure_testing_task,
            io_simulation_task,
            load_test_orchestrator,
            memory_operations_task,
        )

        _broker_cache[queue_type] = broker
        tasks = {
            "cpu_intensive_task": cpu_intensive_task,
            "io_simulation_task": io_simulation_task,
            "memory_operations_task": memory_operations_task,
            "failure_testing_task": failure_testing_task,
            "load_test_orchestrator": load_test_orchestrator,
        }
    elif queue_type == "system":
        from app.components.worker.queues.system import (
            broker,
            cleanup_temp_files,
            system_health_check,
        )

        _broker_cache[queue_type] = broker
        tasks = {
            "system_health_check": system_health_check,
            "cleanup_temp_files": cleanup_temp_files,
        }
    else:
        raise ValueError(f"Unknown queue type: {queue_type}")

    if task_name not in tasks:
        raise ValueError(f"Task '{task_name}' not found in {queue_type} queue")

    return tasks[task_name]


async def enqueue_task(
    task_name: str,
    queue_type: str | None = None,
    *args: Any,
    delay_seconds: int | None = None,
    **kwargs: Any,
) -> Any:
    """
    Enqueue a task for background processing.

    Args:
        task_name: Name of the task to enqueue.
        queue_type: Target queue type. Defaults to configured default.
        *args: Positional arguments for the task.
        delay_seconds: Optional delay before task execution.
        **kwargs: Keyword arguments for the task.

    Returns:
        TaskIQ task handle (AsyncTaskiqTask) for tracking.
    """
    if queue_type is None:
        queue_type = get_default_queue()

    task = get_task(task_name, queue_type)

    logger.info(f"Enqueueing task: {task_name} to {queue_type} queue")

    # TaskIQ uses .kiq() to enqueue tasks
    if delay_seconds:
        # TaskIQ supports delayed execution via labels
        task_handle = await task.kiq(*args, **kwargs)
        # Note: TaskIQ delay is handled differently - via scheduler or labels
        # For now, log warning if delay requested
        logger.warning(
            f"Task delay ({delay_seconds}s) requested but TaskIQ delay "
            "requires taskiq-scheduler integration"
        )
    else:
        task_handle = await task.kiq(*args, **kwargs)

    logger.debug(f"Task enqueued with ID: {task_handle.task_id}")
    return task_handle


async def get_task_result(task_id: str, timeout: float = 30.0) -> Any:
    """
    Get the result of a completed task.

    Args:
        task_id: The task ID to look up.
        timeout: Max seconds to wait for result.

    Returns:
        The task result if available.

    Raises:
        TimeoutError: If task doesn't complete within timeout.
    """
    # TaskIQ result retrieval requires the task handle or result backend
    # This is a simplified version - full implementation would use result backend
    from app.components.worker.queues.system import broker

    result_backend = broker.result_backend
    if result_backend is None:
        raise RuntimeError("No result backend configured")

    result = await result_backend.get_result(task_id)
    return result


def clear_broker_cache() -> None:
    """Clear the broker cache. Useful for testing."""
    _broker_cache.clear()
    logger.debug("Broker cache cleared")


async def shutdown_brokers() -> None:
    """
    Shut down all cached brokers to prevent connection leaks.

    Call this before exiting CLI commands to ensure Redis connections
    are properly closed and avoid 'Event loop is closed' errors.
    """
    for queue_type, broker in _broker_cache.items():
        try:
            await broker.shutdown()
            logger.debug(f"Shut down broker for queue: {queue_type}")
        except Exception as e:
            logger.debug(f"Error shutting down broker for {queue_type}: {e}")
    _broker_cache.clear()
