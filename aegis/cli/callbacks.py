"""
Typer callback functions for CLI options.

This module contains callback functions used to validate and process
CLI options before command execution.
"""

import typer

from ..core.component_utils import (
    clean_component_names,
    restore_engine_info,
)
from ..core.dependency_resolver import DependencyResolver
from ..core.service_resolver import ServiceResolver
from ..core.services import SERVICES
from .utils import expand_scheduler_dependencies


def validate_and_resolve_components(
    ctx: typer.Context, param: typer.CallbackParam, value: str | None
) -> list[str] | None:
    """Validate and resolve component dependencies."""
    if not value:
        return None

    # Parse comma-separated string
    components_raw = [c.strip() for c in value.split(",")]

    # Check for empty components before filtering
    if any(not c for c in components_raw):
        typer.echo("❌ Empty component name is not allowed", err=True)
        raise typer.Exit(1)

    selected = [c for c in components_raw if c]

    # Expand scheduler[backend] dependencies first
    selected = expand_scheduler_dependencies(selected)

    # Validate components exist (use clean names for validation)
    clean_selected = clean_component_names(selected)
    errors = DependencyResolver.validate_components(clean_selected)
    if errors:
        for error in errors:
            typer.echo(f"❌ {error}", err=True)
        raise typer.Exit(1)

    # Resolve dependencies (using clean names)
    resolved_clean = DependencyResolver.resolve_dependencies(clean_selected)

    # Restore engine info to resolved components
    resolved = restore_engine_info(resolved_clean, selected)

    # Show dependency resolution (use clean names for dependency calculation)
    original_clean = clean_component_names(selected)
    auto_added = DependencyResolver.get_missing_dependencies(original_clean)
    if auto_added:
        typer.echo(f"📦 Auto-added dependencies: {', '.join(auto_added)}")

    # Show recommendations
    recommendations = DependencyResolver.get_recommendations(resolved_clean)
    if recommendations:
        rec_list = ", ".join(recommendations)
        typer.echo(f"💡 Recommended: {rec_list}")
        # Note: Skip interactive recommendations for now to keep it simple

    return resolved


def validate_and_resolve_services(
    ctx: typer.Context, param: typer.CallbackParam, value: str | None
) -> list[str] | None:
    """Validate and resolve service dependencies to components."""
    if not value:
        return None

    # Parse comma-separated string
    services_raw = [s.strip() for s in value.split(",")]

    # Check for empty services before filtering
    if any(not s for s in services_raw):
        typer.echo("❌ Empty service name is not allowed", err=True)
        raise typer.Exit(1)

    selected_services = [s for s in services_raw if s]

    # Validate services exist
    unknown_services = [s for s in selected_services if s not in SERVICES]
    if unknown_services:
        typer.echo(f"❌ Unknown services: {', '.join(unknown_services)}", err=True)
        available = list(SERVICES.keys())
        typer.echo(f"Available services: {', '.join(available)}", err=True)
        raise typer.Exit(1)

    # Resolve services to components
    resolved_components, service_added = ServiceResolver.resolve_service_dependencies(
        selected_services
    )

    # Show what components were added by services
    if service_added:
        typer.echo(f"📦 Services require components: {', '.join(service_added)}")

    return selected_services
