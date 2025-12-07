"""
Worker queue registry with dynamic discovery for TaskIQ.

Pure TaskIQ implementation - broker instances are the single source of truth.
No configuration files, no abstractions, just TaskIQ as intended.
"""

import importlib
from pathlib import Path
from typing import Any

from app.core.log import logger


def get_broker(queue_name: str) -> Any:
    """Import and return broker instance for a queue.

    Args:
        queue_name: Name of the queue (e.g., 'system', 'load_test')

    Returns:
        TaskIQ broker instance from the queue module

    Raises:
        ImportError: If queue module doesn't exist
        AttributeError: If broker instance not found
    """
    try:
        module = importlib.import_module(f"app.components.worker.queues.{queue_name}")
        return module.broker
    except ImportError as e:
        logger.error(f"Failed to import worker queue '{queue_name}': {e}")
        raise
    except AttributeError as e:
        logger.error(f"broker instance not found in '{queue_name}' queue: {e}")
        raise


def discover_worker_queues() -> list[str]:
    """Discover all worker queues from the queues directory.

    Scans app/components/worker/queues/ for Python files and treats each
    file as a potential queue. Excludes __init__.py and other non-queue files.

    Returns:
        Sorted list of queue names
    """
    queues_dir = Path(__file__).parent / "queues"

    if not queues_dir.exists():
        logger.warning(f"Worker queues directory not found: {queues_dir}")
        return []

    queue_files = queues_dir.glob("*.py")
    queues = []

    for file in queue_files:
        # Skip __init__.py and other special files
        if file.stem not in ["__init__", "__pycache__"]:
            # Verify the file has a broker instance
            try:
                get_broker(file.stem)
                queues.append(file.stem)
            except (ImportError, AttributeError):
                logger.debug(f"Skipping '{file.stem}' - no valid broker instance")
                continue

    return sorted(queues)


def get_queue_metadata(queue_name: str) -> dict[str, Any]:
    """Get metadata for a queue.

    Args:
        queue_name: Name of the queue

    Returns:
        Dictionary with queue metadata:
        - queue_name: Queue identifier
        - tasks: List of registered task names
        - description: Human-readable description
    """
    # Direct import of task names from queue modules
    # TaskIQ's broker.tasks dict only exists in worker process context,
    # so we define task names explicitly for client-side access
    if queue_name == "load_test":
        task_names = [
            "cpu_intensive_task",
            "io_simulation_task",
            "memory_operations_task",
            "failure_testing_task",
            "load_test_orchestrator",
        ]
    elif queue_name == "system":
        task_names = [
            "system_health_check",
            "cleanup_temp_files",
        ]
    else:
        task_names = []

    metadata = {
        "queue_name": queue_name,
        "stream_name": f"taskiq:{queue_name}",  # Redis stream name for TaskIQ health checks
        "tasks": task_names,
        "task_count": len(task_names),
        "functions": task_names,  # Alias for health check compatibility
        "max_jobs": 10,  # Default concurrency (matches env WORKER_CONCURRENCY)
        "timeout": 300,  # Default timeout in seconds
        "description": f"{queue_name.replace('_', ' ').title()} worker queue",
    }

    return metadata


def get_all_queue_metadata() -> dict[str, dict[str, Any]]:
    """Get metadata for all discovered worker queues.

    Returns:
        Dictionary mapping queue names to their metadata
    """
    metadata = {}
    for queue_name in discover_worker_queues():
        metadata[queue_name] = get_queue_metadata(queue_name)
    return metadata


def validate_queue_name(queue_name: str) -> bool:
    """Check if a queue name is valid (has a corresponding broker).

    Args:
        queue_name: Name to validate

    Returns:
        True if queue exists and has valid broker instance
    """
    return queue_name in discover_worker_queues()
