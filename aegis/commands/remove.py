"""
Remove command implementation.

Removes components from an existing Aegis Stack project using manual file deletion.
"""

from pathlib import Path

import typer

from ..cli.validation import (
    parse_comma_separated_list,
    validate_copier_project,
)
from ..constants import AnswerKeys, ComponentNames, Messages, StorageBackends
from ..core.components import COMPONENTS, CORE_COMPONENTS
from ..core.copier_manager import load_copier_answers
from ..core.dependency_resolver import DependencyResolver
from ..core.manual_updater import ManualUpdater
from ..core.version_compatibility import validate_version_compatibility


def remove_command(
    components: str | None = typer.Argument(
        None,
        help="Comma-separated list of components to remove (scheduler,worker,database)",
    ),
    interactive: bool = typer.Option(
        False,
        "--interactive",
        "-i",
        help="Use interactive component selection",
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
    Remove components from an existing Aegis Stack project.

    This command removes component files and updates project configuration.
    WARNING: This operation deletes files and cannot be easily undone!

    Examples:\\\\n
        - aegis remove scheduler\\\\n
        - aegis remove worker,database\\\\n
        - aegis remove scheduler --project-path ../my-project\\\\n
        - aegis --verbose remove worker (show detailed file operations)\\\\n

    Note: Core components (backend, frontend) cannot be removed.

    Global options: Use --verbose/-v before the command for detailed output.
    """

    typer.echo("Aegis Stack - Remove Components")
    typer.echo("=" * 50)

    # Resolve project path
    target_path = Path(project_path).resolve()

    # Validate it's a Copier project
    validate_copier_project(target_path, "remove")

    typer.echo(f"Project: {target_path}")

    # Check version compatibility between CLI and project template
    validate_version_compatibility(target_path, command_name="remove", force=force)

    # Validate components argument or interactive mode
    if not interactive and not components:
        typer.secho(
            "Error: components argument is required (or use --interactive)",
            fg="red",
            err=True,
        )
        typer.echo("   Usage: aegis remove scheduler,worker", err=True)
        typer.echo("   Or: aegis remove --interactive", err=True)
        raise typer.Exit(1)

    # Interactive mode
    if interactive:
        if components:
            typer.secho(
                "Warning: --interactive flag ignores component arguments",
                fg="yellow",
            )

        from ..cli.interactive import interactive_component_remove_selection

        selected_components = interactive_component_remove_selection(target_path)

        if not selected_components:
            typer.secho("\nNo components selected for removal", fg="green")
            raise typer.Exit(0)

        # Convert to comma-separated string for existing logic
        components = ",".join(selected_components)

        # Auto-confirm in interactive mode (user already confirmed during selection)
        yes = True

    # Parse and validate components
    assert components is not None  # Already validated by check above
    selected_components = parse_comma_separated_list(components, "component")

    # Validate components exist
    try:
        # Use the same validation logic as init command
        errors = DependencyResolver.validate_components(selected_components)
        if errors:
            for error in errors:
                typer.secho(f"{error}", fg="red", err=True)
            raise typer.Exit(1)

    except Exception as e:
        typer.secho(f"Component validation failed: {e}", fg="red", err=True)
        raise typer.Exit(1)

    # Load existing project configuration
    try:
        existing_answers = load_copier_answers(target_path)
    except Exception as e:
        typer.secho(f"Failed to load project configuration: {e}", fg="red", err=True)
        raise typer.Exit(1)

    # Check which components are currently enabled
    not_enabled = []
    components_to_remove = []

    for component in selected_components:
        # Check if component is core (cannot be removed)
        if component in CORE_COMPONENTS:
            typer.secho(f"Cannot remove core component: {component}", fg="yellow")
            continue

        # Check if component is enabled
        include_key = AnswerKeys.include_key(component)
        if not existing_answers.get(include_key):
            not_enabled.append(component)
        else:
            components_to_remove.append(component)

    if not_enabled:
        typer.echo(f"Not enabled: {', '.join(not_enabled)}", err=False)

    if not components_to_remove:
        typer.secho("No components to remove!", fg="green")
        raise typer.Exit(0)

    # Auto-remove redis if worker is being removed (redis has no standalone functionality)
    # Don't remove redis if cache component is using it
    if (
        ComponentNames.WORKER in components_to_remove
        and ComponentNames.REDIS not in components_to_remove
        and existing_answers.get(AnswerKeys.REDIS)
        and not existing_answers.get(
            AnswerKeys.CACHE
        )  # Future: cache component may use redis
    ):
        components_to_remove.append(ComponentNames.REDIS)
        typer.echo(
            "Auto-removing redis (no standalone functionality, only used by worker)",
            err=False,
        )

    # Check for scheduler with sqlite backend - warn about persistence
    if ComponentNames.SCHEDULER in components_to_remove:
        scheduler_backend = existing_answers.get(AnswerKeys.SCHEDULER_BACKEND)
        if scheduler_backend == StorageBackends.SQLITE:
            typer.secho("\nIMPORTANT: Scheduler Persistence Warning", fg="yellow")
            typer.echo("   Your scheduler uses SQLite for job persistence.")
            typer.echo("   The database file at data/scheduler.db will remain.")
            typer.echo()
            typer.echo("   To keep your job history: Leave the database component")
            typer.echo("   To remove all data: Also remove the database component")
            typer.echo()

    # Show what will be removed
    typer.secho("\nComponents to remove:", fg="yellow")
    for component in components_to_remove:
        if component in COMPONENTS:
            desc = COMPONENTS[component].description
            typer.echo(f"   • {component}: {desc}")

    # Confirm before proceeding
    typer.echo()
    typer.secho(
        "WARNING: This will DELETE component files from your project!", fg="yellow"
    )
    typer.echo("   Make sure you have committed your changes to git.")
    typer.echo()

    if not yes and not typer.confirm("Remove these components?"):
        typer.secho("Operation cancelled", fg="red")
        raise typer.Exit(0)

    # Run manual removal for each component
    typer.echo("\nRemoving components...")
    try:
        updater = ManualUpdater(target_path)

        # Remove each component sequentially
        for component in components_to_remove:
            typer.echo(f"\nRemoving {component}...")

            # Remove the component
            result = updater.remove_component(component)

            if not result.success:
                typer.secho(
                    f"Failed to remove {component}: {result.error_message}",
                    fg="red",
                    err=True,
                )
                raise typer.Exit(1)

            # Show results
            if result.files_deleted:
                typer.secho(f"   Removed {len(result.files_deleted)} files", fg="green")

        typer.secho("\nComponents removed successfully!", fg="green")
        Messages.print_next_steps()

    except Exception as e:
        typer.secho(f"\nFailed to remove components: {e}", fg="red", err=True)
        raise typer.Exit(1)
