"""
Add service command implementation.

Adds services (auth, AI, etc.) to an existing Aegis Stack project using Copier's update mechanism.
"""

from pathlib import Path

import typer

from ..cli.utils import detect_scheduler_backend
from ..core.components import COMPONENTS, CORE_COMPONENTS, SchedulerBackend
from ..core.copier_manager import is_copier_project, load_copier_answers
from ..core.manual_updater import ManualUpdater
from ..core.service_resolver import ServiceResolver
from ..core.services import SERVICES


def add_service_command(
    services: str | None = typer.Argument(
        None,
        help="Comma-separated list of services to add (auth,ai)",
    ),
    interactive: bool = typer.Option(
        False,
        "--interactive",
        "-i",
        help="Use interactive service selection",
    ),
    project_path: str = typer.Option(
        ".",
        "--project-path",
        "-p",
        help="Path to the Aegis Stack project (default: current directory)",
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """
    Add services to an existing Aegis Stack project.

    This command uses Copier's update mechanism to add new services (auth, AI, etc.)
    to a project that was generated with 'aegis init'.

    Examples:

        - aegis add-service auth

        - aegis add-service auth,ai

        - aegis add-service auth --project-path ../my-project

    Note: This command only works with projects generated using Copier
    (the default since v0.2.0). Services may auto-add required components.
    """

    typer.echo("Aegis Stack - Add Services")
    typer.echo("=" * 50)

    # Resolve project path
    target_path = Path(project_path).resolve()

    # Validate it's a Copier project
    if not is_copier_project(target_path):
        typer.secho(
            f"Project at {target_path} was not generated with Copier.",
            fg="red",
            err=True,
        )
        typer.echo(
            "   The 'aegis add service' command only works with Copier-generated projects.",
            err=True,
        )
        typer.echo(
            "   To add services, regenerate the project with the services included.",
            err=True,
        )
        raise typer.Exit(1)

    typer.echo(f"Project: {target_path}")

    # Validate services argument or interactive mode
    if not interactive and not services:
        typer.secho(
            "Error: services argument is required (or use --interactive)",
            fg="red",
            err=True,
        )
        typer.echo("   Usage: aegis add service auth,ai", err=True)
        typer.echo("   Or: aegis add service --interactive", err=True)
        raise typer.Exit(1)

    # Interactive mode
    if interactive:
        if services:
            typer.secho(
                "Warning: --interactive flag ignores service arguments",
                fg="yellow",
            )

        from ..cli.interactive import interactive_service_selection

        selected_services = interactive_service_selection(target_path)

        if not selected_services:
            typer.secho("\nNo services selected", fg="green")
            raise typer.Exit(0)

        # Convert to comma-separated string for existing logic
        services = ",".join(selected_services)

        # Auto-confirm in interactive mode
        yes = True

    # Verify project is in a git repository (required for Copier updates)
    git_dir = target_path / ".git"
    if not git_dir.exists():
        typer.secho("\nProject is not in a git repository", fg="red", err=True)
        typer.echo("   Copier updates require git for change tracking", err=True)
        typer.echo(
            "   Projects created with 'aegis init' should have git initialized automatically",
            err=True,
        )
        typer.echo(
            "   If you created this project manually, run: git init && git add . && git commit -m 'Initial commit'",
            err=True,
        )
        raise typer.Exit(1)

    # Parse and validate services
    assert services is not None  # Already validated by check above
    services_raw = [s.strip() for s in services.split(",")]

    # Check for empty services
    if any(not s for s in services_raw):
        typer.secho("Empty service name is not allowed", fg="red", err=True)
        raise typer.Exit(1)

    selected_services = [s for s in services_raw if s]

    # Validate services exist
    try:
        errors = ServiceResolver.validate_services(selected_services)
        if errors:
            for error in errors:
                typer.secho(f"{error}", fg="red", err=True)
            raise typer.Exit(1)
    except Exception as e:
        typer.secho(f"Service validation failed: {e}", fg="red", err=True)
        raise typer.Exit(1)

    # Load existing project configuration
    try:
        existing_answers = load_copier_answers(target_path)
    except Exception as e:
        typer.secho(f"Failed to load project configuration: {e}", fg="red", err=True)
        raise typer.Exit(1)

    # Check which services are already enabled
    already_enabled = []
    for service in selected_services:
        # Check if service is already enabled in answers
        include_key = f"include_{service}"
        if existing_answers.get(include_key) is True:
            already_enabled.append(service)

    if already_enabled:
        typer.echo(f"Already enabled: {', '.join(already_enabled)}", err=False)

    # Filter out already enabled services
    services_to_add = [s for s in selected_services if s not in already_enabled]

    if not services_to_add:
        typer.secho("All requested services are already enabled!", fg="green")
        raise typer.Exit(0)

    # Resolve service dependencies to components
    try:
        required_components, _ = ServiceResolver.resolve_service_dependencies(
            services_to_add
        )
    except ValueError as e:
        typer.secho(f"Failed to resolve service dependencies: {e}", fg="red", err=True)
        raise typer.Exit(1)

    # Check which components are already enabled
    enabled_components = []
    missing_components = []

    for component in required_components:
        include_key = f"include_{component}"
        if existing_answers.get(include_key) is True or component in CORE_COMPONENTS:
            enabled_components.append(component)
        else:
            missing_components.append(component)

    # Show what will be added
    typer.echo("\nServices to add:")
    for service in services_to_add:
        if service in SERVICES:
            desc = SERVICES[service].description
            typer.echo(f"   • {service}: {desc}")

    # Show component requirements
    if missing_components:
        typer.echo("\nRequired components (will be auto-added):")
        for component in missing_components:
            if component in COMPONENTS:
                desc = COMPONENTS[component].description
                typer.echo(f"   • {component}: {desc}")

    if enabled_components:
        # Filter out core components from display
        non_core_enabled = [c for c in enabled_components if c not in CORE_COMPONENTS]
        if non_core_enabled:
            typer.secho(
                f"\nAlready have required components: {', '.join(non_core_enabled)}",
                fg="green",
            )

    # Confirm before proceeding
    typer.echo()
    if not yes and not typer.confirm("Add these services?"):
        typer.secho("Operation cancelled", fg="red")
        raise typer.Exit(0)

    # Prepare update data for ManualUpdater
    update_data: dict[str, bool | str] = {}

    # Add service flags
    for service in services_to_add:
        include_key = f"include_{service}"
        update_data[include_key] = True

    # Add missing component flags
    for component in missing_components:
        include_key = f"include_{component}"
        update_data[include_key] = True

    # Add services using ManualUpdater
    typer.echo("\nUpdating project...")
    try:
        updater = ManualUpdater(target_path)

        # Add missing components first
        for component in missing_components:
            typer.echo(f"\nAdding required component: {component}...")

            # Prepare component-specific data
            component_data: dict[str, bool | str] = {}

            # Handle scheduler backend if needed
            if component == "scheduler":
                scheduler_backend = detect_scheduler_backend([component])
                component_data["scheduler_backend"] = scheduler_backend
                component_data["scheduler_with_persistence"] = (
                    scheduler_backend == SchedulerBackend.SQLITE.value
                )
            elif component == "database":
                component_data["database_engine"] = "sqlite"

            # Add the component
            result = updater.add_component(component, component_data)

            if not result.success:
                typer.secho(
                    f"Failed to add component {component}: {result.error_message}",
                    fg="red",
                    err=True,
                )
                raise typer.Exit(1)

            if result.files_modified:
                typer.secho(f"   Added {len(result.files_modified)} files", fg="green")
            if result.files_skipped:
                typer.secho(
                    f"   Skipped {len(result.files_skipped)} existing files",
                    fg="yellow",
                )

        # Now add each service sequentially
        for service in services_to_add:
            typer.echo(f"\nAdding service: {service}...")

            # Prepare service-specific data
            service_data: dict[str, bool | str] = {}

            # For AI service, set default providers
            if service == "ai":
                service_data["ai_providers"] = "openai"

            # Add the service (services are added like components)
            result = updater.add_component(service, service_data)

            if not result.success:
                typer.secho(
                    f"Failed to add service {service}: {result.error_message}",
                    fg="red",
                    err=True,
                )
                raise typer.Exit(1)

            # Show results
            if result.files_modified:
                typer.secho(f"   Added {len(result.files_modified)} files", fg="green")
            if result.files_skipped:
                typer.secho(
                    f"   Skipped {len(result.files_skipped)} existing files",
                    fg="yellow",
                )

        typer.secho("\nServices added successfully!", fg="green")

        # Provide next steps
        if len(services_to_add) > 0 or len(missing_components) > 0:
            typer.echo("\nReview changes:")
            typer.echo("   git diff docker-compose.yml")
            typer.echo("   git diff pyproject.toml")

        typer.echo("\nNext steps:")
        typer.echo("   1. Run 'make check' to verify the update")
        typer.echo("   2. Test your application")
        typer.echo("   3. Commit the changes with: git add . && git commit")

        # Service-specific guidance
        if "auth" in services_to_add:
            project_slug = existing_answers.get("project_slug", "my-project")
            typer.echo("\nAuth Service Setup:")
            typer.echo("   1. Run 'make migrate' to apply auth migrations")
            typer.echo(
                f"   2. Create test users with CLI: '{project_slug} auth create-test-users'"
            )
            typer.echo("   3. Check auth routes at /api/auth/docs")

        if "ai" in services_to_add:
            project_slug = existing_answers.get("project_slug", "my-project")
            typer.echo("\nAI Service Setup:")
            typer.echo(
                "   1. Set AI_PROVIDER in .env (openai, anthropic, google, groq)"
            )
            typer.echo("   2. Set provider API key (OPENAI_API_KEY, etc.)")
            typer.echo(f"   3. Test with CLI: '{project_slug} ai chat'")

    except Exception as e:
        typer.secho(f"\nFailed to add services: {e}", fg="red", err=True)
        raise typer.Exit(1)
