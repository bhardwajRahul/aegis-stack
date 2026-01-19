"""
Init command implementation.
"""

from pathlib import Path
from typing import cast

import typer

from ..cli.callbacks import (
    validate_and_resolve_components,
    validate_and_resolve_services,
)
from ..cli.interactive import interactive_project_selection
from ..cli.utils import detect_scheduler_backend
from ..cli.validators import validate_project_name
from ..config.defaults import DEFAULT_PYTHON_VERSION, SUPPORTED_PYTHON_VERSIONS
from ..constants import StorageBackends
from ..core.ai_service_parser import BACKENDS, FRAMEWORKS, PROVIDERS
from ..core.component_utils import (
    clean_component_names,
    extract_base_component_name,
    restore_engine_info,
)
from ..core.components import (
    COMPONENTS,
    CORE_COMPONENTS,
    ComponentType,
)
from ..core.dependency_resolver import DependencyResolver
from ..core.service_resolver import ServiceResolver
from ..core.template_generator import TemplateGenerator

# Build services help text dynamically from constants
_SERVICES_HELP = (
    f"Services: auth, ai. AI options: ai[framework,backend,providers] "
    f"where framework={'|'.join(sorted(FRAMEWORKS))}, "
    f"backend={'|'.join(sorted(BACKENDS))}, "
    f"providers={'|'.join(sorted(PROVIDERS))}"
)


def init_command(
    project_name: str = typer.Argument(
        ..., help="Name of the new Aegis Stack project to create"
    ),
    components: str | None = typer.Option(
        None,
        "--components",
        "-c",
        callback=validate_and_resolve_components,
        help="Comma-separated list of components (redis,worker,scheduler,database)",
    ),
    services: str | None = typer.Option(
        None,
        "--services",
        "-s",
        callback=validate_and_resolve_services,
        help=_SERVICES_HELP,
    ),
    python_version: str = typer.Option(
        DEFAULT_PYTHON_VERSION,
        "--python-version",
        help="Python version for generated project (3.11, 3.12, 3.13, or 3.14)",
    ),
    interactive: bool = typer.Option(
        True,
        "--interactive/--no-interactive",
        "-i/-ni",
        help="Use interactive component selection",
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Overwrite existing directory if it exists"
    ),
    output_dir: str | None = typer.Option(
        None,
        "--output-dir",
        "-o",
        help="Directory to create the project in (default: current directory)",
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
    to_version: str | None = typer.Option(
        None,
        "--to-version",
        help="Generate from specific template version (tag, commit, or branch)",
    ),
    skip_llm_sync: bool = typer.Option(
        False,
        "--skip-llm-sync",
        help="Skip LLM catalog sync after project generation (AI service only)",
    ),
    dev: bool = typer.Option(
        False,
        "--dev",
        help="Dev mode: read templates from working tree (uncommitted changes)",
    ),
) -> None:
    """
    Initialize a new Aegis Stack project with battle-tested component combinations.

    This command creates a complete project structure with your chosen components,
    ensuring all dependencies and configurations are compatible and tested.

    Examples:\\n
        - aegis init my-app\\n
        - aegis init my-app --components redis,worker\\n
        - aegis init my-app --components redis,worker,scheduler,database --no-interactive\\n
        - aegis init my-app --services auth --no-interactive\\n
    """  # noqa

    # Validate project name first
    validate_project_name(project_name)

    # Validate Python version
    if python_version not in SUPPORTED_PYTHON_VERSIONS:
        typer.secho(
            f"Invalid Python version '{python_version}'. Must be one of: {', '.join(SUPPORTED_PYTHON_VERSIONS)}",
            fg="red",
            err=True,
        )
        raise typer.Exit(1)

    typer.secho("Aegis Stack Project Initialization", fg=typer.colors.BLUE, bold=True)

    # Determine output directory
    base_output_dir = Path(output_dir) if output_dir else Path.cwd()
    project_path = base_output_dir / project_name

    typer.echo(
        f"{typer.style('Location:', fg=typer.colors.CYAN)} {project_path.resolve()}"
    )

    if to_version:
        typer.echo(
            f"{typer.style('Template Version:', fg=typer.colors.CYAN)} {to_version}"
        )

    # Check if directory already exists
    if project_path.exists():
        if not force:
            typer.secho(
                f"Directory '{project_path}' already exists", fg="red", err=True
            )
            typer.echo(
                "   Use --force to overwrite or choose a different name", err=True
            )
            raise typer.Exit(1)
        else:
            typer.secho(f"Overwriting existing directory: {project_path}", fg="yellow")

    # Interactive component selection
    # Note: components is list[str] after callback, despite str annotation
    selected_components = cast(list[str], components) if components else []
    selected_services = cast(list[str], services) if services else []
    scheduler_backend = StorageBackends.MEMORY  # Default to in-memory scheduler

    # Resolve services to components if services were provided
    # This runs in both interactive and non-interactive modes when --services is specified
    if selected_services:
        # Check if --components was explicitly provided
        components_explicitly_provided = components is not None

        if components_explicitly_provided:
            # In non-interactive mode with explicit --components, validate compatibility
            # Include core components (always present) for validation
            components_for_validation = list(set(selected_components + CORE_COMPONENTS))
            errors = ServiceResolver.validate_service_component_compatibility(
                selected_services, components_for_validation
            )
            if errors:
                typer.secho(
                    "Service-component compatibility errors:", fg="red", err=True
                )
                for error in errors:
                    typer.echo(f"   • {error}", err=True)

                # Show suggestion
                missing_components = (
                    ServiceResolver.get_missing_components_for_services(
                        selected_services, components_for_validation
                    )
                )
                if missing_components:
                    typer.echo(
                        f"Suggestion: Add missing components --components {','.join(sorted(set(selected_components + missing_components)))}",
                        err=True,
                    )
                    typer.echo(
                        "   Or remove --components to let services auto-add dependencies.",
                        err=True,
                    )
                typer.echo(
                    "   Alternatively, use interactive mode to auto-add service dependencies.",
                    err=True,
                )
                raise typer.Exit(1)
        else:
            # No --components provided, auto-add required components for services
            service_components, _ = ServiceResolver.resolve_service_dependencies(
                selected_services
            )
            if service_components:
                typer.secho(
                    f"Services require components: {', '.join(sorted(service_components))}",
                    fg=typer.colors.YELLOW,
                )
            selected_components = service_components

        # Resolve service dependencies and merge with any explicitly selected components
        service_components, _ = ServiceResolver.resolve_service_dependencies(
            selected_services
        )
        # Merge service-required components with explicitly selected components
        all_components = list(set(selected_components + service_components))
        selected_components = all_components

    # Auto-detect scheduler backend when components are specified
    if selected_components:
        scheduler_backend = detect_scheduler_backend(selected_components)
        if scheduler_backend != StorageBackends.MEMORY:
            typer.secho(
                f"Auto-detected: Scheduler with {scheduler_backend} persistence",
                fg=typer.colors.YELLOW,
            )

    if interactive and not components and not services:
        (
            selected_components,
            scheduler_backend,
            interactive_services,
            interactive_skip_llm_sync,
        ) = interactive_project_selection()
        # Use interactive selection if user chose to skip (overrides CLI default)
        if interactive_skip_llm_sync:
            skip_llm_sync = True

        # Resolve dependencies for interactively selected components
        if selected_components:
            # Clean component names for dependency resolution (remove engine info)
            # Save original with engine info
            original_selected = list(selected_components)
            clean_components = clean_component_names(selected_components)

            resolved_clean = DependencyResolver.resolve_dependencies(clean_components)

            # Restore engine info for display components
            selected_components = restore_engine_info(resolved_clean, original_selected)

            # Calculate auto-added components using clean names
            clean_selected_only = clean_component_names(
                [c for c in selected_components if c not in CORE_COMPONENTS]
            )
            auto_added = DependencyResolver.get_missing_dependencies(
                clean_selected_only
            )
            if auto_added:
                typer.secho(
                    f"\nAuto-added dependencies: {', '.join(auto_added)}",
                    fg=typer.colors.YELLOW,
                )

        # Merge interactively selected services with any already selected services
        selected_services = list(set(selected_services + interactive_services))

        # Handle service dependencies for interactively selected services
        if interactive_services:
            # Track originally selected components before service resolution
            originally_selected_components = selected_components.copy()

            service_components, _ = ServiceResolver.resolve_service_dependencies(
                interactive_services
            )
            # Merge service-required components with selected components
            all_components = list(set(selected_components + service_components))
            selected_components = all_components

            # Show which components were auto-added by services
            service_added_components = [
                comp
                for comp in service_components
                if comp not in originally_selected_components
                and comp not in CORE_COMPONENTS
            ]
            if service_added_components:
                # Create a mapping of which services require which components
                service_component_map = {}
                for service_name in interactive_services:
                    service_deps = ServiceResolver.resolve_service_dependencies(
                        [service_name]
                    )[0]
                    for comp in service_deps:
                        if comp in service_added_components:
                            if comp not in service_component_map:
                                service_component_map[comp] = []
                            service_component_map[comp].append(service_name)

                typer.secho("\nAuto-added by services:", fg=typer.colors.YELLOW)
                for comp, requiring_services in service_component_map.items():
                    services_str = ", ".join(requiring_services)
                    typer.echo(
                        f"   • {comp} {typer.style(f'(required by {services_str})', dim=True)}"
                    )

    # Create template generator with scheduler backend context
    template_gen = TemplateGenerator(
        project_name,
        list(selected_components),
        scheduler_backend,
        selected_services,
        python_version,
    )

    # Show selected configuration
    typer.echo()
    typer.secho("Project Configuration", fg=typer.colors.CYAN, bold=True)
    typer.echo(f"   {typer.style('Name:', fg=typer.colors.CYAN)} {project_name}")
    typer.echo(
        f"   {typer.style('Core:', fg=typer.colors.CYAN)} {', '.join(CORE_COMPONENTS)}"
    )

    # Show infrastructure components
    infra_components = []
    for name in selected_components:
        # Handle database[engine] format
        base_name = extract_base_component_name(name)
        if (
            base_name in COMPONENTS
            and COMPONENTS[base_name].type == ComponentType.INFRASTRUCTURE
        ):
            infra_components.append(name)

    if infra_components:
        typer.echo(
            f"   {typer.style('Infrastructure:', fg=typer.colors.CYAN)} {', '.join(infra_components)}"
        )

    # Show selected services
    if selected_services:
        typer.echo(
            f"   {typer.style('Services:', fg=typer.colors.CYAN)} {', '.join(selected_services)}"
        )

    # Show template files that will be generated
    template_files = template_gen.get_template_files()
    if template_files:
        typer.secho("\nComponent Files:", fg=typer.colors.CYAN, bold=True)
        for file_path in template_files:
            typer.echo(f"   • {file_path}")

    # Show entrypoints that will be created
    entrypoints = template_gen.get_entrypoints()
    if entrypoints:
        typer.secho("\nEntrypoints:", fg=typer.colors.CYAN, bold=True)
        for entrypoint in entrypoints:
            typer.echo(f"   • {entrypoint}")

    # Show worker queues that will be created
    worker_queues = template_gen.get_worker_queues()
    if worker_queues:
        typer.secho("\nWorker Queues:", fg=typer.colors.CYAN, bold=True)
        for queue in worker_queues:
            typer.echo(f"   • {queue}")

    # Show dependency information using template generator
    deps = template_gen._get_pyproject_deps()
    if deps:
        typer.secho("\nDependencies to be installed:", fg=typer.colors.CYAN, bold=True)
        for dep in deps:
            typer.echo(f"   • {dep}")

    # Confirm before proceeding
    typer.echo()
    if not yes and not typer.confirm("Create this project?", default=True):
        typer.secho("Project creation cancelled", fg="red")
        raise typer.Exit(0)

    # Handle force overwrite by completely removing existing directory
    project_path = base_output_dir / project_name
    if force and project_path.exists():
        typer.echo(f"Removing existing directory: {project_path}")
        import shutil

        shutil.rmtree(project_path)

    # Create project using Copier template engine
    typer.echo()
    typer.secho(f"Creating project: {project_name}", fg=typer.colors.BLUE, bold=True)

    try:
        from ..core.copier_manager import generate_with_copier

        generate_with_copier(
            template_gen,
            base_output_dir,
            vcs_ref=to_version,
            skip_llm_sync=skip_llm_sync,
            dev_mode=dev,
        )

        # Note: Comprehensive setup output is now handled by the post-generation hook
        # which provides better status reporting and automated setup

    except Exception as e:
        typer.secho(f"Error creating project: {e}", fg="red", err=True)
        raise typer.Exit(1)
