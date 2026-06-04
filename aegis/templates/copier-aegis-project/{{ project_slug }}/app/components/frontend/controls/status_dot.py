"""Themed status dot.

A small filled circle in a design-system color, used in place of emoji
status indicators (green/red/blue/...) so status colors follow the theme
and can be recolored centrally (e.g. success is teal, not green).
"""

import flet as ft


def status_dot(color: str, size: int = 10) -> ft.Container:
    """Return a small filled status dot in ``color``.

    Args:
        color: Fill color (pass a ``Theme.Colors`` token).
        size: Diameter in pixels.

    Returns:
        A circular ``ft.Container`` filled with ``color``.
    """
    return ft.Container(
        width=size,
        height=size,
        bgcolor=color,
        border_radius=size / 2,
    )
