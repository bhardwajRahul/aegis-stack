"""
Shared UI helpers for status presentation across CLI and frontend.

Provides a single source of truth for mapping ComponentStatusType to
icons and semantic colors, so CLI and dashboard remain consistent.
"""

from .models import ComponentStatusType


def get_status_icon(status: ComponentStatusType) -> str:
    """Return the display icon for a given status.

    Note: INFO icon intentionally includes a trailing space for terminal alignment.
    """
    if status == ComponentStatusType.HEALTHY:
        return "✅"
    if status == ComponentStatusType.INFO:
        return "ℹ️ "
    if status == ComponentStatusType.WARNING:
        return "⚠️"
    if status == ComponentStatusType.UNHEALTHY:
        return "❌"
    return "❓"


def get_status_color_name(status: ComponentStatusType) -> str:
    """Return a semantic color name for a given status (CLI friendly).

    Frontend can adapt these semantic names to theme-specific colors.
    """
    if status == ComponentStatusType.HEALTHY:
        return "green"
    if status == ComponentStatusType.INFO:
        return "blue"
    if status == ComponentStatusType.WARNING:
        return "yellow"
    if status == ComponentStatusType.UNHEALTHY:
        return "red"
    return "white"


def get_component_label(component_name: str) -> str:
    """Map component keys to user-facing labels (brand or friendly name)."""
    mapping = {
        "backend": "FastAPI",
        "frontend": "Flet",
        "cache": "Redis",
        "worker": "arq",
        "scheduler": "APScheduler",
    }
    return mapping.get(component_name, component_name.title())
