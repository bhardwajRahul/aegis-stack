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
from ..i18n import t


def _translated_desc(name: str, fallback: str) -> str:
    """Get translated description for a component, with fallback."""
    key = f"component.{name}"
    result = t(key)
    return result if result != key else fallback


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

    typer.echo(t("remove.title"))
    typer.echo("=" * 50)

    # Resolve project path
    target_path = Path(project_path).resolve()

    # Validate it's a Copier project
    validate_copier_project(target_path, "remove")

    typer.echo(t("remove.project", path=target_path))

    # Check version compatibility between CLI and project template
    validate_version_compatibility(target_path, command_name="remove", force=force)

    # Validate components argument or interactive mode
    if not interactive and not components:
        typer.secho(t("remove.error_no_args"), fg="red", err=True)
        typer.echo(f"   {t('remove.usage_hint')}", err=True)
        typer.echo(f"   {t('remove.interactive_hint')}", err=True)
        raise typer.Exit(1)

    # Interactive mode
    if interactive:
        if components:
            typer.secho(t("shared.interactive_ignores_args"), fg="yellow")

        from ..cli.interactive import interactive_component_remove_selection

        selected_components = interactive_component_remove_selection(target_path)

        if not selected_components:
            typer.secho(f"\n{t('remove.no_selected')}", fg="green")
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
        typer.secho(t("remove.validation_failed", error=e), fg="red", err=True)
        raise typer.Exit(1)

    # Load existing project configuration
    try:
        existing_answers = load_copier_answers(target_path)
    except Exception as e:
        typer.secho(t("remove.load_config_failed", error=e), fg="red", err=True)
        raise typer.Exit(1)

    # Check which components are currently enabled
    not_enabled = []
    components_to_remove = []

    for component in selected_components:
        # Check if component is core (cannot be removed)
        if component in CORE_COMPONENTS:
            typer.secho(
                t("remove.cannot_remove_core", component=component), fg="yellow"
            )
            continue

        # Check if component is enabled
        include_key = AnswerKeys.include_key(component)
        if not existing_answers.get(include_key):
            not_enabled.append(component)
        else:
            components_to_remove.append(component)

    if not_enabled:
        typer.echo(t("remove.not_enabled", components=", ".join(not_enabled)))

    if not components_to_remove:
        typer.secho(t("remove.nothing_to_remove"), fg="green")
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
        typer.echo(t("remove.auto_remove_redis"))

    # Check for scheduler with sqlite backend - warn about persistence
    if ComponentNames.SCHEDULER in components_to_remove:
        scheduler_backend = existing_answers.get(AnswerKeys.SCHEDULER_BACKEND)
        if scheduler_backend == StorageBackends.SQLITE:
            typer.secho(f"\n{t('remove.scheduler_persistence_warn')}", fg="yellow")
            typer.echo(f"   {t('remove.scheduler_persistence_detail')}")
            typer.echo(f"   {t('remove.scheduler_db_remains')}")
            typer.echo()
            typer.echo(f"   {t('remove.scheduler_keep_hint')}")
            typer.echo(f"   {t('remove.scheduler_remove_hint')}")
            typer.echo()

    # Show what will be removed
    typer.secho(f"\n{t('remove.components_to_remove')}", fg="yellow")
    for component in components_to_remove:
        if component in COMPONENTS:
            desc = _translated_desc(component, COMPONENTS[component].description)
            typer.echo(f"   • {component}: {desc}")

    # Confirm before proceeding
    typer.echo()
    typer.secho(t("remove.warning_delete"), fg="yellow")
    typer.echo(f"   {t('remove.commit_hint')}")
    typer.echo()

    if not yes and not typer.confirm(t("remove.confirm")):
        typer.secho(t("shared.operation_cancelled"), fg="red")
        raise typer.Exit(0)

    # Run manual removal for each component
    try:
        updater = ManualUpdater(target_path)

        # Remove each component sequentially
        for component in components_to_remove:
            typer.echo(f"\n{t('remove.removing', component=component)}")

            # Remove the component
            result = updater.remove_component(component)

            if not result.success:
                typer.secho(
                    t(
                        "remove.failed_component",
                        component=component,
                        error=result.error_message,
                    ),
                    fg="red",
                    err=True,
                )
                raise typer.Exit(1)

            # Show results
            if result.files_deleted:
                typer.secho(
                    f"   {t('remove.removed_files', count=len(result.files_deleted))}",
                    fg="green",
                )

        typer.secho(f"\n{t('remove.success')}", fg="green")
        Messages.print_next_steps()

    except Exception as e:
        typer.secho(f"\n{t('remove.failed', error=e)}", fg="red", err=True)
        raise typer.Exit(1)
