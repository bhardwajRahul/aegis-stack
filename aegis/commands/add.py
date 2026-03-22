"""
Add command implementation.

Adds components to an existing Aegis Stack project using Copier's update mechanism.
"""

from pathlib import Path

import typer

from ..cli.utils import detect_scheduler_backend
from ..cli.validation import (
    parse_comma_separated_list,
    validate_copier_project,
    validate_git_repository,
)
from ..constants import AnswerKeys, ComponentNames, Messages, StorageBackends
from ..core.component_utils import extract_base_component_name, extract_engine_info
from ..core.components import COMPONENTS, CORE_COMPONENTS
from ..core.copier_manager import load_copier_answers
from ..core.dependency_resolver import DependencyResolver
from ..core.manual_updater import ManualUpdater
from ..core.project_map import render_project_map
from ..core.version_compatibility import validate_version_compatibility
from ..i18n import t


def _translated_desc(name: str, fallback: str) -> str:
    """Get translated description for a component, with fallback."""
    key = f"component.{name}"
    result = t(key)
    return result if result != key else fallback


def add_command(
    components: str | None = typer.Argument(
        None,
        help="Comma-separated list of components to add (scheduler,worker,database)",
    ),
    interactive: bool = typer.Option(
        False,
        "--interactive",
        "-i",
        help="Use interactive component selection",
    ),
    backend: str | None = typer.Option(
        None,
        "--backend",
        "-b",
        help="Scheduler backend: 'memory' (default) or 'sqlite' (enables persistence)",
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
    Add components to an existing Aegis Stack project.

    This command uses Copier's update mechanism to add new components
    to a project that was generated with 'aegis init'.

    Examples:

        - aegis add scheduler

        - aegis add worker,database

        - aegis add scheduler --project-path ../my-project

        - aegis --verbose add worker (show detailed file operations)

    Note: This command only works with projects generated using Copier
    (the default since v0.2.0).

    Global options: Use --verbose/-v before the command for detailed output.
    """

    typer.echo(t("add.title"))
    typer.echo("=" * 50)

    # Resolve project path
    target_path = Path(project_path).resolve()

    # Validate it's a Copier project
    validate_copier_project(target_path, "add")

    typer.echo(t("add.project", path=target_path))

    # Check version compatibility between CLI and project template
    validate_version_compatibility(target_path, command_name="add", force=force)

    # Validate components argument or interactive mode
    if not interactive and not components:
        typer.secho(t("add.error_no_args"), fg="red", err=True)
        typer.echo(f"   {t('add.usage_hint')}", err=True)
        typer.echo(f"   {t('add.interactive_hint')}", err=True)
        raise typer.Exit(1)

    # Interactive mode
    if interactive:
        if components:
            typer.secho(t("shared.interactive_ignores_args"), fg="yellow")

        from ..cli.interactive import interactive_component_add_selection

        selected_components, scheduler_backend = interactive_component_add_selection(
            target_path
        )

        if not selected_components:
            typer.secho(f"\n{t('shared.no_components_selected')}", fg="green")
            raise typer.Exit(0)

        # Convert to comma-separated string for existing logic
        components = ",".join(selected_components)

        # Auto-confirm in interactive mode
        yes = True

    # Verify project is in a git repository (required for Copier updates)
    validate_git_repository(target_path)

    # Parse and validate components
    assert components is not None  # Already validated by check above
    selected_components = parse_comma_separated_list(components, "component")
    components_raw = selected_components  # Keep for bracket syntax parsing

    # Parse bracket syntax for scheduler backend (e.g., "scheduler[sqlite]")
    # Bracket syntax takes precedence over --backend flag
    for comp in components_raw:
        try:
            base_name = extract_base_component_name(comp)
            if base_name == ComponentNames.SCHEDULER:
                engine = extract_engine_info(comp)
                if engine:
                    if backend and backend != engine:
                        typer.secho(
                            t("add.bracket_override", engine=engine, backend=backend),
                            fg="yellow",
                        )
                    backend = engine
        except ValueError as e:
            typer.secho(t("add.invalid_format", error=e), fg="red", err=True)
            raise typer.Exit(1)

    # Extract base component names for validation (removes bracket syntax)
    base_components = []
    for comp in selected_components:
        try:
            base_name = extract_base_component_name(comp)
            base_components.append(base_name)
        except ValueError as e:
            typer.secho(t("add.invalid_format", error=e), fg="red", err=True)
            raise typer.Exit(1)

    # Validate components exist and resolve dependencies
    try:
        # Validate component names and resolve dependencies
        errors = DependencyResolver.validate_components(base_components)
        if errors:
            for error in errors:
                typer.secho(f"{error}", fg="red", err=True)
            raise typer.Exit(1)

        # Resolve dependencies
        resolved_components = DependencyResolver.resolve_dependencies(base_components)

        # Show dependency resolution
        auto_added = DependencyResolver.get_missing_dependencies(base_components)
        if auto_added:
            typer.echo(t("add.auto_added_deps", deps=", ".join(auto_added)))

    except typer.Exit:
        raise
    except Exception as e:
        typer.secho(t("add.validation_failed", error=e), fg="red", err=True)
        raise typer.Exit(1)

    # Load existing project configuration
    try:
        existing_answers = load_copier_answers(target_path)
    except Exception as e:
        typer.secho(t("add.load_config_failed", error=e), fg="red", err=True)
        raise typer.Exit(1)

    # Check which components are already enabled
    already_enabled = []
    for component in resolved_components:
        # Check if component is already enabled in answers
        include_key = AnswerKeys.include_key(component)
        if existing_answers.get(include_key) is True:
            already_enabled.append(component)

    if already_enabled:
        typer.echo(t("add.already_enabled", components=", ".join(already_enabled)))

    # Filter out already enabled and core components
    components_to_add = [
        c
        for c in resolved_components
        if c not in already_enabled and c not in CORE_COMPONENTS
    ]

    if not components_to_add:
        typer.secho(t("add.all_enabled"), fg="green")
        raise typer.Exit(0)

    # Detect scheduler backend if adding scheduler
    scheduler_backend = StorageBackends.MEMORY
    if ComponentNames.SCHEDULER in components_to_add:
        # Use explicit backend flag/bracket syntax if provided, otherwise detect
        scheduler_backend = backend or detect_scheduler_backend(components_to_add)

        # Validate backend (only memory and sqlite supported)
        valid_backends = [StorageBackends.MEMORY, StorageBackends.SQLITE]
        if scheduler_backend not in valid_backends:
            typer.secho(
                t("add.invalid_scheduler_backend", backend=scheduler_backend),
                fg="red",
                err=True,
            )
            typer.echo(
                f"   {t('add.valid_backends', options=', '.join(valid_backends))}",
                err=True,
            )
            if scheduler_backend == StorageBackends.POSTGRES:
                typer.echo(f"   {t('add.postgres_coming')}", err=True)
            raise typer.Exit(1)

        # Auto-add database component for sqlite backend
        if (
            scheduler_backend == StorageBackends.SQLITE
            and ComponentNames.DATABASE not in components_to_add
        ):
            components_to_add.append(ComponentNames.DATABASE)
            typer.echo(t("add.auto_added_db"))

    # Show what will be added
    typer.echo(f"\n{t('add.components_to_add')}")
    for component in components_to_add:
        if component in COMPONENTS:
            desc = _translated_desc(component, COMPONENTS[component].description)
            typer.echo(f"   • {component}: {desc}")

    if (
        ComponentNames.SCHEDULER in components_to_add
        and scheduler_backend != StorageBackends.MEMORY
    ):
        typer.echo(f"\n{t('add.scheduler_backend', backend=scheduler_backend)}")

    # Confirm before proceeding
    typer.echo()
    if not yes and not typer.confirm(t("add.confirm"), default=True):
        typer.secho(t("shared.operation_cancelled"), fg="red")
        raise typer.Exit(0)

    # Prepare update data for Copier
    update_data: dict[str, bool | str] = {}

    for component in components_to_add:
        include_key = AnswerKeys.include_key(component)
        update_data[include_key] = True

    # Add scheduler backend configuration if adding scheduler
    if ComponentNames.SCHEDULER in components_to_add:
        update_data[AnswerKeys.SCHEDULER_BACKEND] = scheduler_backend
        update_data[AnswerKeys.SCHEDULER_WITH_PERSISTENCE] = (
            scheduler_backend == StorageBackends.SQLITE
        )

    # Add database engine configuration if adding database
    if ComponentNames.DATABASE in components_to_add:
        # SQLite is the only supported engine for now
        update_data[AnswerKeys.DATABASE_ENGINE] = StorageBackends.SQLITE

    # Add components using ManualUpdater
    # This is the standard approach for adding components at the same template version
    # (Copier's run_update is designed for template VERSION upgrades, not component additions)
    try:
        updater = ManualUpdater(target_path)

        # Add each component sequentially
        for component in components_to_add:
            typer.echo(f"\n{t('add.adding', component=component)}")

            # Prepare component-specific data
            component_data: dict[str, bool | str] = {}
            if (
                component == ComponentNames.SCHEDULER
                and AnswerKeys.SCHEDULER_BACKEND in update_data
            ):
                component_data[AnswerKeys.SCHEDULER_BACKEND] = update_data[
                    AnswerKeys.SCHEDULER_BACKEND
                ]
                component_data[AnswerKeys.SCHEDULER_WITH_PERSISTENCE] = update_data.get(
                    AnswerKeys.SCHEDULER_WITH_PERSISTENCE, False
                )
            elif (
                component == ComponentNames.DATABASE
                and AnswerKeys.DATABASE_ENGINE in update_data
            ):
                component_data[AnswerKeys.DATABASE_ENGINE] = update_data[
                    AnswerKeys.DATABASE_ENGINE
                ]

            # Add the component
            result = updater.add_component(component, component_data)

            if not result.success:
                typer.secho(
                    t(
                        "add.failed_component",
                        component=component,
                        error=result.error_message,
                    ),
                    fg="red",
                    err=True,
                )
                raise typer.Exit(1)

            # Show results
            if result.files_modified:
                typer.secho(
                    f"   {t('add.added_files', count=len(result.files_modified))}",
                    fg="green",
                )
            if result.files_skipped:
                typer.secho(
                    f"   {t('add.skipped_files', count=len(result.files_skipped))}",
                    fg="yellow",
                )

        typer.secho(f"\n{t('add.success')}", fg="green")

        # Show project map with newly added components highlighted
        typer.echo()
        render_project_map(target_path, highlight=components_to_add)

        # Note: Shared file updates are already shown during the update process
        # Just provide next steps

        if len(components_to_add) > 0:
            Messages.print_review_changes()

        Messages.print_next_steps()

    except Exception as e:
        typer.secho(f"\n{t('add.failed', error=e)}", fg="red", err=True)
        raise typer.Exit(1)
