"""
Add command implementation.

Adds components to an existing Aegis Stack project using Copier's update mechanism.
"""

from pathlib import Path

import typer

from ..cli.utils import detect_scheduler_backend
from ..core.components import COMPONENTS, CORE_COMPONENTS
from ..core.copier_manager import (
    is_copier_project,
    load_copier_answers,
)
from ..core.dependency_resolver import DependencyResolver
from ..core.manual_updater import ManualUpdater


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
    project_path: str = typer.Option(
        ".",
        "--project-path",
        "-p",
        help="Path to the Aegis Stack project (default: current directory)",
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """
    Add components to an existing Aegis Stack project.

    This command uses Copier's update mechanism to add new components
    to a project that was generated with 'aegis init'.

    Examples:\\n
        - aegis add scheduler\\n
        - aegis add worker,database\\n
        - aegis add scheduler --project-path ../my-project\\n

    Note: This command only works with projects generated using Copier
    (the default since v0.2.0).
    """

    typer.echo("🛡️  Aegis Stack - Add Components")
    typer.echo("=" * 50)

    # Resolve project path
    target_path = Path(project_path).resolve()

    # Validate it's a Copier project
    if not is_copier_project(target_path):
        typer.echo(
            f"❌ Project at {target_path} was not generated with Copier.", err=True
        )
        typer.echo(
            "   The 'aegis add' command only works with Copier-generated projects.",
            err=True,
        )
        typer.echo(
            "   To add components, regenerate the project with the new components included.",
            err=True,
        )
        raise typer.Exit(1)

    typer.echo(f"📁 Project: {target_path}")

    # Validate components argument or interactive mode
    if not interactive and not components:
        typer.echo(
            "❌ Error: components argument is required (or use --interactive)", err=True
        )
        typer.echo("   Usage: aegis add scheduler,worker", err=True)
        typer.echo("   Or: aegis add --interactive", err=True)
        raise typer.Exit(1)

    # Interactive mode
    if interactive:
        if components:
            typer.echo(
                "⚠️  Warning: --interactive flag ignores component arguments",
                err=False,
            )

        from ..cli.interactive import interactive_component_add_selection

        selected_components, scheduler_backend = interactive_component_add_selection(
            target_path
        )

        if not selected_components:
            typer.echo("\n✅ No components selected")
            raise typer.Exit(0)

        # Convert to comma-separated string for existing logic
        components = ",".join(selected_components)

        # Auto-confirm in interactive mode
        yes = True

    # Verify project is in a git repository (required for Copier updates)
    git_dir = target_path / ".git"
    if not git_dir.exists():
        typer.echo("\n❌ Project is not in a git repository", err=True)
        typer.echo("   Copier updates require git for change tracking", err=True)
        typer.echo(
            "   💡 Projects created with 'aegis init' should have git initialized automatically",
            err=True,
        )
        typer.echo(
            "   💡 If you created this project manually, run: git init && git add . && git commit -m 'Initial commit'",
            err=True,
        )
        raise typer.Exit(1)

    # Parse and validate components
    assert components is not None  # Already validated by check above
    components_raw = [c.strip() for c in components.split(",")]

    # Check for empty components
    if any(not c for c in components_raw):
        typer.echo("❌ Empty component name is not allowed", err=True)
        raise typer.Exit(1)

    selected_components = [c for c in components_raw if c]

    # Validate components exist and resolve dependencies
    try:
        # Validate component names and resolve dependencies
        errors = DependencyResolver.validate_components(selected_components)
        if errors:
            for error in errors:
                typer.echo(f"❌ {error}", err=True)
            raise typer.Exit(1)

        # Resolve dependencies
        resolved_components = DependencyResolver.resolve_dependencies(
            selected_components
        )

        # Show dependency resolution
        auto_added = DependencyResolver.get_missing_dependencies(selected_components)
        if auto_added:
            typer.echo(f"📦 Auto-added dependencies: {', '.join(auto_added)}")

    except Exception as e:
        typer.echo(f"❌ Component validation failed: {e}", err=True)
        raise typer.Exit(1)

    # Load existing project configuration
    try:
        existing_answers = load_copier_answers(target_path)
    except Exception as e:
        typer.echo(f"❌ Failed to load project configuration: {e}", err=True)
        raise typer.Exit(1)

    # Check which components are already enabled
    already_enabled = []
    for component in resolved_components:
        # Check if component is already enabled in answers
        include_key = f"include_{component}"
        if existing_answers.get(include_key) is True:
            already_enabled.append(component)

    if already_enabled:
        typer.echo(f"ℹ️  Already enabled: {', '.join(already_enabled)}", err=False)

    # Filter out already enabled and core components
    components_to_add = [
        c
        for c in resolved_components
        if c not in already_enabled and c not in CORE_COMPONENTS
    ]

    if not components_to_add:
        typer.echo("✅ All requested components are already enabled!")
        raise typer.Exit(0)

    # Detect scheduler backend if adding scheduler
    scheduler_backend = "memory"
    if "scheduler" in components_to_add:
        scheduler_backend = detect_scheduler_backend(components_to_add)

    # Show what will be added
    typer.echo("\n🔧 Components to add:")
    for component in components_to_add:
        if component in COMPONENTS:
            desc = COMPONENTS[component].description
            typer.echo(f"   • {component}: {desc}")

    if "scheduler" in components_to_add and scheduler_backend != "memory":
        typer.echo(f"\n📊 Scheduler backend: {scheduler_backend}")

    # Confirm before proceeding
    typer.echo()
    if not yes and not typer.confirm("🚀 Add these components?"):
        typer.echo("❌ Operation cancelled")
        raise typer.Exit(0)

    # Prepare update data for Copier
    update_data: dict[str, bool | str] = {}

    for component in components_to_add:
        include_key = f"include_{component}"
        update_data[include_key] = True

    # Add scheduler backend configuration if adding scheduler
    if "scheduler" in components_to_add:
        update_data["scheduler_backend"] = scheduler_backend
        update_data["scheduler_with_persistence"] = scheduler_backend == "sqlite"

    # Add components using ManualUpdater
    # This is the standard approach for adding components at the same template version
    # (Copier's run_update is designed for template VERSION upgrades, not component additions)
    typer.echo("\n🔄 Updating project...")
    try:
        updater = ManualUpdater(target_path)

        # Add each component sequentially
        for component in components_to_add:
            typer.echo(f"\n📦 Adding {component}...")

            # Prepare component-specific data
            component_data: dict[str, bool | str] = {}
            if component == "scheduler" and "scheduler_backend" in update_data:
                component_data["scheduler_backend"] = update_data["scheduler_backend"]
                component_data["scheduler_with_persistence"] = update_data.get(
                    "scheduler_with_persistence", False
                )

            # Add the component
            result = updater.add_component(component, component_data)

            if not result.success:
                typer.echo(
                    f"❌ Failed to add {component}: {result.error_message}", err=True
                )
                raise typer.Exit(1)

            # Show results
            if result.files_modified:
                typer.echo(f"   ✅ Added {len(result.files_modified)} files")
            if result.files_skipped:
                typer.echo(f"   ⚠️  Skipped {len(result.files_skipped)} existing files")

        typer.echo("\n✅ Components added successfully!")

        # Note: Shared file updates are already shown during the update process
        # Just provide next steps

        if len(components_to_add) > 0:
            typer.echo("\n💡 Review changes:")
            typer.echo("   git diff docker-compose.yml")
            typer.echo("   git diff pyproject.toml")

        typer.echo("\n📝 Next steps:")
        typer.echo("   1. Run 'make check' to verify the update")
        typer.echo("   2. Test your application")
        typer.echo("   3. Commit the changes with: git add . && git commit")

    except Exception as e:
        typer.echo(f"\n❌ Failed to add components: {e}", err=True)
        raise typer.Exit(1)
