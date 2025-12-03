"""
CLI utility functions.

This module contains utility functions used by CLI commands for
component detection, dependency expansion, and other common tasks.
"""

import typer

from ..constants import ComponentNames, StorageBackends
from ..core.component_utils import (
    clean_component_names,
    extract_base_component_name,
    extract_engine_info,
)


def detect_scheduler_backend(components: list[str]) -> str:
    """
    Detect scheduler backend from component list.

    Args:
        components: List of component names, possibly including scheduler[backend]

    Returns:
        Backend name: "memory", "sqlite", or "postgres"
    """
    for component in components:
        base_name = extract_base_component_name(component)
        if base_name == ComponentNames.SCHEDULER:
            engine = extract_engine_info(component)
            if engine:
                # Direct scheduler[backend] syntax
                return engine
            else:
                # Check if database is also present (legacy detection)
                clean_names = clean_component_names(components)
                if ComponentNames.DATABASE in clean_names:
                    return StorageBackends.SQLITE  # Default database backend
    return StorageBackends.MEMORY  # Default to memory-only


def expand_scheduler_dependencies(components: list[str]) -> list[str]:
    """
    Expand scheduler[backend] to include required database dependencies.

    Args:
        components: List of component names

    Returns:
        Expanded component list with auto-added dependencies
    """
    result = list(components)  # Copy the list

    for component in components:
        base_name = extract_base_component_name(component)
        if base_name == ComponentNames.SCHEDULER:
            backend = extract_engine_info(component)
            if backend and backend != StorageBackends.MEMORY:
                # Auto-add database with same backend if not already present
                database_component = f"{ComponentNames.DATABASE}[{backend}]"
                existing_clean = clean_component_names(result)

                if ComponentNames.DATABASE not in existing_clean:
                    result.append(database_component)
                    typer.echo(
                        f"Auto-added {ComponentNames.DATABASE}[{backend}] for "
                        f"{ComponentNames.SCHEDULER}[{backend}] persistence"
                    )

    return result
