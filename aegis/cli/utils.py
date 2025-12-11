"""
CLI utility functions.

This module contains utility functions used by CLI commands for
component detection, dependency expansion, and other common tasks.
"""

import typer

from ..constants import AnswerKeys, ComponentNames, StorageBackends, WorkerBackends
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


def detect_worker_backend(components: list[str]) -> str:
    """
    Detect worker backend from component list.

    Args:
        components: List of component names, possibly including worker[backend]

    Returns:
        Backend name: "arq" or "taskiq"
    """
    for component in components:
        base_name = extract_base_component_name(component)
        if base_name == ComponentNames.WORKER:
            engine = extract_engine_info(component)
            if engine:
                return engine
    return WorkerBackends.ARQ  # Default to arq


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


def detect_ai_backend(services: list[str]) -> str:
    """
    Detect AI backend from service list.

    Args:
        services: List of service names, possibly including ai[backend]

    Returns:
        Backend name: "memory" or "sqlite"
    """
    for service in services:
        base_name = extract_base_component_name(service)
        if base_name == AnswerKeys.SERVICE_AI:
            engine = extract_engine_info(service)
            if engine:
                return engine
    return StorageBackends.MEMORY  # Default to memory


def expand_ai_dependencies(
    services: list[str], existing_components: list[str]
) -> list[str]:
    """
    Expand ai[backend] to include required database component.

    Args:
        services: List of service names
        existing_components: List of already selected components

    Returns:
        List of components to auto-add for AI persistence
    """
    auto_added: list[str] = []

    for service in services:
        base_name = extract_base_component_name(service)
        if base_name == AnswerKeys.SERVICE_AI:
            backend = extract_engine_info(service)
            if backend and backend != StorageBackends.MEMORY:
                # Auto-add database with same backend if not already present
                database_component = f"{ComponentNames.DATABASE}[{backend}]"
                existing_clean = clean_component_names(existing_components)

                if ComponentNames.DATABASE not in existing_clean:
                    auto_added.append(database_component)
                    typer.echo(
                        f"Auto-added {ComponentNames.DATABASE}[{backend}] for "
                        f"{AnswerKeys.SERVICE_AI}[{backend}] persistence"
                    )

    return auto_added
