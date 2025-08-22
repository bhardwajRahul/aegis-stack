"""
Worker queue registry with dynamic discovery.

Pure arq implementation - WorkerSettings classes are the single source of truth.
No configuration files, no abstractions, just arq as intended.
"""

import importlib
from pathlib import Path
from typing import Any

from app.core.log import logger


def get_worker_settings(queue_name: str) -> Any:
    """Import and return WorkerSettings class for a queue.

    Args:
        queue_name: Name of the queue (e.g., 'system', 'load_test')

    Returns:
        WorkerSettings class from the queue module

    Raises:
        ImportError: If queue module doesn't exist
        AttributeError: If WorkerSettings class not found
    """
    try:
        module = importlib.import_module(f"app.components.worker.queues.{queue_name}")
        return module.WorkerSettings
    except ImportError as e:
        logger.error(f"Failed to import worker queue '{queue_name}': {e}")
        raise
    except AttributeError as e:
        logger.error(f"WorkerSettings class not found in '{queue_name}' queue: {e}")
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
            # Verify the file has a WorkerSettings class
            try:
                get_worker_settings(file.stem)
                queues.append(file.stem)
            except (ImportError, AttributeError):
                logger.debug(f"Skipping '{file.stem}' - no valid WorkerSettings class")
                continue
    
    return sorted(queues)


def get_queue_metadata(queue_name: str) -> dict[str, Any]:
    """Get metadata for a queue from its WorkerSettings class.

    Args:
        queue_name: Name of the queue

    Returns:
        Dictionary with queue metadata:
        - queue_name: Redis queue name
        - max_jobs: Maximum concurrent jobs
        - timeout: Job timeout in seconds
        - functions: List of function names in this queue
        - description: Human-readable description (if available)
    """
    try:
        settings_class = get_worker_settings(queue_name)
        
        metadata = {
            "queue_name": getattr(
                settings_class, "queue_name", f"arq:queue:{queue_name}"
            ),
            "max_jobs": getattr(settings_class, "max_jobs", 10),
            "timeout": getattr(settings_class, "job_timeout", 300),
            "functions": [f.__name__ for f in getattr(settings_class, "functions", [])],
        }
        
        # Add description if available
        if hasattr(settings_class, "description"):
            metadata["description"] = settings_class.description
        elif hasattr(settings_class, "__doc__") and settings_class.__doc__:
            metadata["description"] = settings_class.__doc__.strip()
        else:
            metadata["description"] = f"{queue_name.title()} worker queue"
            
        return metadata
        
    except (ImportError, AttributeError) as e:
        logger.error(f"Failed to get metadata for queue '{queue_name}': {e}")
        return {
            "queue_name": f"arq:queue:{queue_name}",
            "max_jobs": 10,
            "timeout": 300,
            "functions": [],
            "description": f"Unknown queue: {queue_name}",
        }


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
    """Check if a queue name is valid (has a corresponding WorkerSettings).

    Args:
        queue_name: Name to validate

    Returns:
        True if queue exists and has valid WorkerSettings
    """
    return queue_name in discover_worker_queues()