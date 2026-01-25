"""
Layout calculations for diagram visualization.

Provides positioning algorithms for tree and radial layouts.
"""

from dataclasses import dataclass
from enum import Enum

from app.services.system.models import ComponentStatus


class LayoutType(Enum):
    """Supported diagram layout types."""

    TREE = "tree"
    RADIAL = "radial"


@dataclass
class NodePosition:
    """Position data for a diagram node."""

    x: float  # Normalized X position (-1 to 1)
    y: float  # Normalized Y position (-1 to 1)
    component_name: str
    component_data: ComponentStatus


# Manual radial positions for optimal visual layout
# Coordinates are normalized (-1 to 1), centered at (0, 0)
# These positions are hand-tuned: compact layout
RADIAL_POSITIONS: dict[str, tuple[float, float]] = {
    "backend": (0.0, -0.15),  # Center - the hub
    "database": (-0.45, -0.23),  # Left of center
    "cache": (-0.20, 0.13),  # Bottom-left
    "worker": (-0.28, -0.45),  # Upper-left
    "scheduler": (0.28, -0.45),  # Upper-right
    "ollama": (0.45, -0.23),  # Right of center
    "service_ai": (0.50, -0.03),  # Right
    "service_auth": (0.20, 0.13),  # Bottom-right
    "service_comms": (-0.50, -0.03),  # Left
}


def get_connections(components: dict[str, ComponentStatus]) -> list[tuple[str, str]]:
    """
    Get connection pairs between components.

    Backend (Server) is the central hub connecting to all components.
    Additional connections show component relationships.

    Args:
        components: Dictionary of component names to their status

    Returns:
        List of (parent, child) connection tuples
    """
    connections: list[tuple[str, str]] = []

    # All components connect through backend
    for name in components:
        if name != "backend":
            connections.append(("backend", name))

    # Inference → AI Service
    if "ollama" in components and "service_ai" in components:
        connections.append(("ollama", "service_ai"))

    return connections


def calculate_tree_positions(
    components: dict[str, ComponentStatus],
) -> list[NodePosition]:
    """
    Calculate tree layout positions with backend at top.

    Arranges components in a 3-tier hierarchical tree structure:
    - Backend (Server) at top center
    - Infrastructure components in second row (database, cache, worker, scheduler, ollama)
    - Services in bottom row

    Args:
        components: Dictionary of component names to their status

    Returns:
        List of NodePosition objects with normalized coordinates
    """
    positions: list[NodePosition] = []

    # Separate into categories
    backend_data = components.get("backend")

    # Infrastructure components (includes scheduler)
    infra_names = [
        name
        for name in components
        if name != "backend" and not name.startswith("service_")
    ]

    # Services at bottom
    service_names = [name for name in components if name.startswith("service_")]

    # Tier 1: Backend at top center
    if backend_data:
        positions.append(
            NodePosition(
                x=0.0, y=-0.40, component_name="backend", component_data=backend_data
            )
        )

    # Tier 2: Infrastructure components
    if infra_names:
        count = len(infra_names)
        spacing = 1.3 / max(count - 1, 1) if count > 1 else 0
        start_x = -1.3 / 2 if count > 1 else 0.0

        for i, name in enumerate(sorted(infra_names)):
            x = start_x + (i * spacing) if count > 1 else 0.0
            positions.append(
                NodePosition(
                    x=x,
                    y=-0.05,
                    component_name=name,
                    component_data=components[name],
                )
            )

    # Tier 3: Services in bottom row
    if service_names:
        count = len(service_names)
        spacing = 1.1 / max(count - 1, 1) if count > 1 else 0
        start_x = -1.1 / 2 if count > 1 else 0.0

        for i, name in enumerate(sorted(service_names)):
            x = start_x + (i * spacing) if count > 1 else 0.0
            positions.append(
                NodePosition(
                    x=x,
                    y=0.25,
                    component_name=name,
                    component_data=components[name],
                )
            )

    return positions


def calculate_radial_positions(
    components: dict[str, ComponentStatus],
) -> list[NodePosition]:
    """
    Calculate radial layout positions using manual coordinates.

    Uses hand-tuned positions from RADIAL_POSITIONS dict for optimal
    visual layout. Falls back to algorithmic placement for unknown components.

    Args:
        components: Dictionary of component names to their status

    Returns:
        List of NodePosition objects with normalized coordinates
    """
    positions: list[NodePosition] = []

    for name, data in components.items():
        if name in RADIAL_POSITIONS:
            x, y = RADIAL_POSITIONS[name]
        else:
            # Fallback for unknown components - place in outer ring
            import math

            unknown_names = [n for n in components if n not in RADIAL_POSITIONS]
            index = unknown_names.index(name) if name in unknown_names else 0
            count = len(unknown_names)
            angle = (2 * math.pi * index / max(count, 1)) - (math.pi / 2)
            x = 0.6 * math.cos(angle)
            y = 0.6 * math.sin(angle)

        positions.append(
            NodePosition(x=x, y=y, component_name=name, component_data=data)
        )

    return positions


def calculate_positions(
    components: dict[str, ComponentStatus],
    layout_type: LayoutType,
) -> list[NodePosition]:
    """
    Calculate node positions for the specified layout type.

    Args:
        components: Dictionary of component names to their status
        layout_type: The layout algorithm to use

    Returns:
        List of NodePosition objects with normalized coordinates
    """
    if layout_type == LayoutType.TREE:
        return calculate_tree_positions(components)
    else:
        return calculate_radial_positions(components)
