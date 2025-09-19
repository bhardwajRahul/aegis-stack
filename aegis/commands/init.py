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
from ..core.component_utils import (
    clean_component_names,
    extract_base_component_name,
    restore_engine_info,
)
from ..core.components import COMPONENTS, CORE_COMPONENTS, ComponentType
from ..core.dependency_resolver import DependencyResolver
from ..core.service_resolver import ServiceResolver
from ..core.template_generator import TemplateGenerator


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
        help="Comma-separated list of services (auth). Use 'aegis services' for full list.",
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

    typer.echo("🛡️  Aegis Stack Project Initialization")
    typer.echo("=" * 50)

    # Determine output directory
    base_output_dir = Path(output_dir) if output_dir else Path.cwd()
    project_path = base_output_dir / project_name

    typer.echo(f"📁 Project will be created in: {project_path.resolve()}")

    # Check if directory already exists
    if project_path.exists():
        if not force:
            typer.echo(f"❌ Directory '{project_path}' already exists", err=True)
            typer.echo(
                "   Use --force to overwrite or choose a different name", err=True
            )
            raise typer.Exit(1)
        else:
            typer.echo(f"⚠️  Overwriting existing directory: {project_path}")

    # Interactive component selection
    # Note: components is list[str] after callback, despite str annotation
    selected_components = cast(list[str], components) if components else []
    selected_services = cast(list[str], services) if services else []
    scheduler_backend = "memory"  # Default to in-memory scheduler

    # Resolve services to components if services were provided (non-interactive mode only)
    if selected_services and not interactive:
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
                typer.echo("❌ Service-component compatibility errors:", err=True)
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
                        f"💡 Suggestion: Add missing components --components {','.join(sorted(set(selected_components + missing_components)))}",
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
                typer.echo(
                    f"📦 Services require components: {', '.join(sorted(service_components))}"
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
        if scheduler_backend != "memory":
            typer.echo(
                f"📊 Auto-detected: Scheduler with {scheduler_backend} persistence"
            )

    if interactive and not components and not services:
        selected_components, scheduler_backend, interactive_services = (
            interactive_project_selection()
        )

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
                typer.echo(f"\n📦 Auto-added dependencies: {', '.join(auto_added)}")

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

                typer.echo("\n📦 Auto-added by services:")
                for comp, requiring_services in service_component_map.items():
                    services_str = ", ".join(requiring_services)
                    typer.echo(f"   • {comp} (required by {services_str})")

    # Create template generator with scheduler backend context
    template_gen = TemplateGenerator(
        project_name, list(selected_components), scheduler_backend, selected_services
    )

    # Show selected configuration
    typer.echo()
    typer.echo(f"📁 Project Name: {project_name}")
    typer.echo("🏗️  Project Structure:")
    typer.echo(f"   ✅ Core: {', '.join(CORE_COMPONENTS)}")

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
        typer.echo(f"   📦 Infrastructure: {', '.join(infra_components)}")

    # Show selected services
    if selected_services:
        typer.echo(f"   🔧 Services: {', '.join(selected_services)}")

    # Show template files that will be generated
    template_files = template_gen.get_template_files()
    if template_files:
        typer.echo("\n📄 Component Files:")
        for file_path in template_files:
            typer.echo(f"   • {file_path}")

    # Show entrypoints that will be created
    entrypoints = template_gen.get_entrypoints()
    if entrypoints:
        typer.echo("\n🚀 Entrypoints:")
        for entrypoint in entrypoints:
            typer.echo(f"   • {entrypoint}")

    # Show worker queues that will be created
    worker_queues = template_gen.get_worker_queues()
    if worker_queues:
        typer.echo("\n👷 Worker Queues:")
        for queue in worker_queues:
            typer.echo(f"   • {queue}")

    # Show dependency information using template generator
    deps = template_gen._get_pyproject_deps()
    if deps:
        typer.echo("\n📦 Dependencies to be installed:")
        for dep in deps:
            typer.echo(f"   • {dep}")

    # Confirm before proceeding
    typer.echo()
    if not yes and not typer.confirm("🚀 Create this project?"):
        typer.echo("❌ Project creation cancelled")
        raise typer.Exit(0)

    # Handle force overwrite by completely removing existing directory
    project_path = base_output_dir / project_name
    if force and project_path.exists():
        typer.echo(f"🗑️  Removing existing directory: {project_path}")
        import shutil

        shutil.rmtree(project_path)

    # Create project using cookiecutter
    typer.echo()
    typer.echo(f"🔧 Creating project: {project_name}")

    try:
        from cookiecutter.main import cookiecutter

        # Get the template path
        template_path = (
            Path(__file__).parent.parent / "templates" / "cookiecutter-aegis-project"
        )

        # Use template generator for context
        extra_context = template_gen.get_template_context()

        # Generate project with cookiecutter
        cookiecutter(
            str(template_path),
            extra_context=extra_context,
            output_dir=str(base_output_dir),
            no_input=True,  # Don't prompt user, use our context
            overwrite_if_exists=False,  # No longer needed since we remove directory first
        )

        # Note: Comprehensive setup output is now handled by the post-generation hook
        # which provides better status reporting and automated setup

    except ImportError:
        typer.echo("❌ Error: cookiecutter not installed", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"❌ Error creating project: {e}", err=True)
        raise typer.Exit(1)
