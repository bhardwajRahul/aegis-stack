"""
Typer callback functions for CLI options.

This module contains callback functions used to validate and process
CLI options before command execution.
"""

import typer

from ..constants import ComponentNames, Messages, WorkerBackends
from ..core.ai_service_parser import is_ai_service_with_options, parse_ai_service_config
from ..core.component_utils import (
    clean_component_names,
    extract_base_component_name,
    extract_base_service_name,
    extract_engine_info,
    restore_engine_info,
)
from ..core.dependency_resolver import DependencyResolver
from ..core.service_resolver import ServiceResolver
from ..core.services import SERVICES
from .interactive import set_ai_service_config
from .utils import expand_scheduler_dependencies


def validate_and_resolve_components(
    ctx: typer.Context, param: typer.CallbackParam, value: str | None
) -> list[str] | None:
    """Validate and resolve component dependencies."""
    if not value:
        return None

    # Skip validation during help generation, but not for tests
    # Mock objects don't have a real resilient_parsing attribute set to True
    if hasattr(ctx, "resilient_parsing") and ctx.resilient_parsing is True:
        return None

    # Parse comma-separated string
    components_raw = [c.strip() for c in value.split(",")]

    # Check for empty components before filtering
    if any(not c for c in components_raw):
        typer.secho(Messages.EMPTY_COMPONENT_NAME, fg="red", err=True)
        raise typer.Exit(1)

    selected = [c for c in components_raw if c]

    # Expand scheduler[backend] dependencies first
    selected = expand_scheduler_dependencies(selected)

    # Validate worker backend options
    for component in selected:
        base_name = extract_base_component_name(component)
        if base_name == ComponentNames.WORKER:
            backend = extract_engine_info(component)
            if backend and backend not in WorkerBackends.ALL:
                typer.secho(
                    f"Invalid worker backend '{backend}'. "
                    f"Available: {', '.join(WorkerBackends.ALL)}",
                    fg="red",
                    err=True,
                )
                raise typer.Exit(1)

    # Validate components exist (use clean names for validation)
    clean_selected = clean_component_names(selected)
    errors = DependencyResolver.validate_components(clean_selected)
    if errors:
        for error in errors:
            typer.secho(error, fg="red", err=True)
        raise typer.Exit(1)

    # Resolve dependencies (using clean names)
    resolved_clean = DependencyResolver.resolve_dependencies(clean_selected)

    # Restore engine info to resolved components
    resolved = restore_engine_info(resolved_clean, selected)

    # Show dependency resolution (use clean names for dependency calculation)
    original_clean = clean_component_names(selected)
    auto_added = DependencyResolver.get_missing_dependencies(original_clean)
    if auto_added:
        typer.echo(f"Auto-added dependencies: {', '.join(auto_added)}")

    # Show recommendations
    recommendations = DependencyResolver.get_recommendations(resolved_clean)
    if recommendations:
        rec_list = ", ".join(recommendations)
        typer.echo(f"Recommended: {rec_list}")
        # Note: Skip interactive recommendations for now to keep it simple

    return resolved


def _split_service_list(value: str) -> list[str]:
    """
    Split comma-separated service list respecting bracket syntax.

    Handles ai[langchain, openai] where commas inside brackets are preserved.

    Args:
        value: Comma-separated service string like "ai[langchain, openai], auth"

    Returns:
        List of service strings with brackets preserved
    """
    services = []
    current = ""
    bracket_depth = 0

    for char in value:
        if char == "[":
            bracket_depth += 1
            current += char
        elif char == "]":
            # Only decrement if we're inside brackets to prevent negative depth
            # from mismatched brackets like "ai],auth"
            if bracket_depth > 0:
                bracket_depth -= 1
            current += char
        elif char == "," and bracket_depth == 0:
            # Only split on comma if we're not inside brackets
            if current.strip():
                services.append(current.strip())
            current = ""
        else:
            current += char

    # Don't forget the last service
    if current.strip():
        services.append(current.strip())

    return services


def validate_and_resolve_services(
    ctx: typer.Context, param: typer.CallbackParam, value: str | None
) -> list[str] | None:
    """Validate and resolve service dependencies to components."""
    if not value:
        return None

    # Skip validation during help generation, but not for tests
    # Mock objects don't have a real resilient_parsing attribute set to True
    if hasattr(ctx, "resilient_parsing") and ctx.resilient_parsing is True:
        return None

    # Parse comma-separated string, respecting bracket syntax
    services_raw = _split_service_list(value)

    # Check for empty services before filtering
    if any(not s for s in services_raw):
        typer.secho(Messages.EMPTY_SERVICE_NAME, fg="red", err=True)
        raise typer.Exit(1)

    selected_services = [s for s in services_raw if s]

    # Validate services exist (extract base name to support bracket syntax like ai[langchain, openai])
    unknown_services = [
        s for s in selected_services if extract_base_service_name(s) not in SERVICES
    ]
    if unknown_services:
        typer.secho(
            f"Unknown services: {', '.join(unknown_services)}", fg="red", err=True
        )
        available = list(SERVICES.keys())
        typer.echo(f"Available services: {', '.join(available)}", err=True)
        raise typer.Exit(1)

    # Parse AI service bracket syntax and store config
    for service in selected_services:
        if is_ai_service_with_options(service):
            try:
                ai_config = parse_ai_service_config(service)
                set_ai_service_config(
                    service_name="ai",
                    framework=ai_config.framework,
                    backend=ai_config.backend,
                    providers=ai_config.providers,
                )
                typer.echo(
                    f"AI service: framework={ai_config.framework}, "
                    f"backend={ai_config.backend}, "
                    f"providers={','.join(ai_config.providers)}"
                )
            except ValueError as e:
                typer.secho(f"Invalid AI service syntax: {e}", fg="red", err=True)
                raise typer.Exit(1)

    # Resolve services to components
    resolved_components, service_added = ServiceResolver.resolve_service_dependencies(
        selected_services
    )

    # Show what components were added by services
    if service_added:
        typer.echo(f"Services require components: {', '.join(service_added)}")

    return selected_services
