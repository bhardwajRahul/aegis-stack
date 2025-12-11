"""
Remove service command implementation.

Removes services (auth, AI, etc.) from an existing Aegis Stack project.
"""

from pathlib import Path

import typer

from ..cli.validation import (
    parse_comma_separated_list,
    validate_copier_project,
)
from ..constants import AnswerKeys, Messages
from ..core.copier_manager import load_copier_answers
from ..core.manual_updater import ManualUpdater
from ..core.service_resolver import ServiceResolver
from ..core.services import SERVICES
from ..core.version_compatibility import validate_version_compatibility


def remove_service_command(
    services: str | None = typer.Argument(
        None,
        help="Comma-separated list of services to remove (auth,ai,comms)",
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
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force through version mismatch warnings",
    ),
) -> None:
    """
    Remove services from an existing Aegis Stack project.

    This command removes service files and updates project configuration.
    WARNING: This operation deletes files and cannot be easily undone!

    Examples:

        - aegis remove-service auth

        - aegis remove-service auth,ai

        - aegis remove-service auth --project-path ../my-project

        - aegis --verbose remove-service auth (show detailed file operations)

    Note: Removing a service does not remove its required components.
    Use 'aegis remove' to remove components separately.

    Global options: Use --verbose/-v before the command for detailed output.
    """

    typer.echo("Aegis Stack - Remove Services")
    typer.echo("=" * 50)

    # Resolve project path
    target_path = Path(project_path).resolve()

    # Validate it's a Copier project
    validate_copier_project(target_path, "remove-service")

    typer.echo(f"Project: {target_path}")

    # Check version compatibility between CLI and project template
    validate_version_compatibility(
        target_path, command_name="remove-service", force=force
    )

    # Validate services argument or interactive mode
    if not interactive and not services:
        typer.secho(
            "Error: services argument is required (or use --interactive)",
            fg="red",
            err=True,
        )
        typer.echo("   Usage: aegis remove-service auth,ai", err=True)
        typer.echo("   Or: aegis remove-service --interactive", err=True)
        raise typer.Exit(1)

    # Interactive mode
    if interactive:
        if services:
            typer.secho(
                "Warning: --interactive flag ignores service arguments",
                fg="yellow",
            )

        from ..cli.interactive import interactive_service_remove_selection

        selected_services = interactive_service_remove_selection(target_path)

        if not selected_services:
            typer.secho("\nNo services selected for removal", fg="green")
            raise typer.Exit(0)

        # Convert to comma-separated string for existing logic
        services = ",".join(selected_services)

        # Auto-confirm in interactive mode (user already confirmed during selection)
        yes = True

    # Parse and validate services
    assert services is not None  # Already validated by check above
    selected_services = parse_comma_separated_list(services, "service")

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

    # Check which services are currently enabled
    not_enabled = []
    services_to_remove = []

    for service in selected_services:
        # Check if service is enabled
        include_key = AnswerKeys.include_key(service)
        if not existing_answers.get(include_key):
            not_enabled.append(service)
        else:
            services_to_remove.append(service)

    if not_enabled:
        typer.echo(f"Not enabled: {', '.join(not_enabled)}", err=False)

    if not services_to_remove:
        typer.secho("No services to remove!", fg="green")
        raise typer.Exit(0)

    # Show what will be removed
    typer.secho("\nServices to remove:", fg="yellow")
    for service in services_to_remove:
        if service in SERVICES:
            desc = SERVICES[service].description
            typer.echo(f"   • {service}: {desc}")

    # Warn about auth-specific data
    if AnswerKeys.SERVICE_AUTH in services_to_remove:
        typer.secho("\nIMPORTANT: Auth Service Warning", fg="yellow")
        typer.echo("   Removing auth service will delete:")
        typer.echo("   • User authentication API endpoints")
        typer.echo("   • User model and authentication services")
        typer.echo("   • JWT token handling code")
        typer.echo("   Note: Database tables and alembic migrations are NOT deleted.")
        typer.echo()

    # Confirm before proceeding
    typer.echo()
    typer.secho(
        "WARNING: This will DELETE service files from your project!", fg="yellow"
    )

    if not yes and not typer.confirm("Remove these services?"):
        typer.secho("Operation cancelled", fg="red")
        raise typer.Exit(0)

    # Remove services using ManualUpdater
    typer.echo("\nRemoving services...")
    try:
        updater = ManualUpdater(target_path)

        for service in services_to_remove:
            typer.echo(f"\nRemoving service: {service}...")

            # Remove the service
            result = updater.remove_component(service)

            if not result.success:
                typer.secho(
                    f"Failed to remove service {service}: {result.error_message}",
                    fg="red",
                    err=True,
                )
                raise typer.Exit(1)

            # Show results
            if result.files_deleted:
                typer.secho(f"   Removed {len(result.files_deleted)} files", fg="green")

        typer.secho("\nServices removed successfully!", fg="green")

        # Provide next steps
        Messages.print_review_changes()
        Messages.print_next_steps()

        # Note about remaining components
        typer.echo("\nNote: Service dependencies (database, etc.) were NOT removed.")
        typer.echo("Use 'aegis remove <component>' to remove components separately.")

    except Exception as e:
        typer.secho(f"\nFailed to remove services: {e}", fg="red", err=True)
        raise typer.Exit(1)
