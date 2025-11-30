# app/components/backend/shutdown/cleanup.py
"""
Auto-discovered cleanup shutdown hook.

This hook performs cleanup when the backend shuts down.
"""

from app.core.log import logger


async def shutdown_hook() -> None:
    """Auto-discovered shutdown hook for cleanup."""
    logger.info("Running backend cleanup...")
    logger.info("Backend shutdown cleanup complete")
