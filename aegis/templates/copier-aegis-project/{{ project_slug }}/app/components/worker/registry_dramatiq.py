"""
Worker queue registry with dynamic discovery for Dramatiq.

Discovers queue modules by scanning the queues directory and checking
for registered Dramatiq actors.
"""

import importlib
from pathlib import Path
from typing import Any

from app.core.log import logger


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
        if file.stem not in ["__init__", "__pycache__"]:
            try:
                importlib.import_module(f"app.components.worker.queues.{file.stem}")
                queues.append(file.stem)
            except (ImportError, AttributeError):
                logger.debug(f"Skipping '{file.stem}' - not a valid queue module")
                continue

    return sorted(queues)


def get_queue_metadata(queue_name: str) -> dict[str, Any]:
    """Get metadata for a queue.

    Args:
        queue_name: Name of the queue

    Returns:
        Dictionary with queue metadata
    """
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
        "redis_queue_name": f"dramatiq:{queue_name}",
        "tasks": task_names,
        "task_count": len(task_names),
        "functions": task_names,
        "max_jobs": 10,
        "timeout": 300,
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
    """Check if a queue name is valid.

    Args:
        queue_name: Name to validate

    Returns:
        True if queue exists
    """
    return queue_name in discover_worker_queues()
