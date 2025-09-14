"""
Interactive CLI components.

This module contains interactive selection and prompting functions
used by CLI commands.
"""

import typer

from ..core.components import COMPONENTS, CORE_COMPONENTS, ComponentSpec, ComponentType


def get_interactive_infrastructure_components() -> list[ComponentSpec]:
    """Get infrastructure components available for interactive selection."""
    # Get all infrastructure components
    infra_components = []
    for component_spec in COMPONENTS.values():
        if component_spec.type == ComponentType.INFRASTRUCTURE:
            infra_components.append(component_spec)

    # Sort by name for consistent ordering
    return sorted(infra_components, key=lambda x: x.name)


def interactive_component_selection() -> tuple[list[str], str]:
    """
    Interactive component selection with dependency awareness.

    Returns:
        Tuple of (selected_components, scheduler_backend)
    """

    typer.echo("🎯 Component Selection")
    typer.echo("=" * 40)
    typer.echo(
        f"✅ Core components ({' + '.join(CORE_COMPONENTS)}) included automatically\n"
    )

    selected = []
    database_engine = None  # Track database engine selection
    database_added_by_scheduler = False  # Track if database was added by scheduler
    scheduler_backend = "memory"  # Track scheduler backend: memory, sqlite, postgres

    # Get all infrastructure components from registry
    infra_components = get_interactive_infrastructure_components()

    typer.echo("🏗️  Infrastructure Components:")

    # Process components in a specific order to handle dependencies
    component_order = ["redis", "worker", "scheduler", "database"]

    for component_name in component_order:
        # Find the component spec
        component_spec = next(
            (c for c in infra_components if c.name == component_name), None
        )
        if not component_spec:
            continue  # Skip if component doesn't exist in registry

        # Handle special worker dependency logic
        if component_name == "worker":
            if "redis" in selected:
                # Redis already selected, simple worker prompt
                prompt = f"  Add {component_spec.description.lower()}?"
                if typer.confirm(prompt):
                    selected.append("worker")
            else:
                # Redis not selected, offer to add both
                prompt = (
                    f"  Add {component_spec.description.lower()}? (will auto-add Redis)"
                )
                if typer.confirm(prompt):
                    selected.extend(["redis", "worker"])
        elif component_name == "scheduler":
            # Enhanced scheduler selection with persistence and database options
            prompt = f"  Add {component_spec.description}?"
            if typer.confirm(prompt):
                selected.append("scheduler")

                # Follow-up: persistence question
                typer.echo("\n💾 Scheduler Persistence:")
                persistence_prompt = (
                    "  Do you want to persist scheduled jobs? "
                    "(Enables job history, recovery after restarts)"
                )
                if typer.confirm(persistence_prompt):
                    # Database engine selection (SQLite only for now)
                    typer.echo("\n🗃️  Database Engine:")
                    typer.echo("  SQLite will be configured for job persistence")
                    typer.echo("  (PostgreSQL support coming in future releases)")

                    # Show SQLite limitations
                    typer.echo("\n⚠️  SQLite Limitations:")
                    typer.echo(
                        "  • Multi-container API access works in development only "
                        "(shared volumes)"
                    )
                    typer.echo("  • Production deployment will be single-container")
                    typer.echo(
                        "  • Use PostgreSQL for full production multi-container support"
                    )

                    if typer.confirm("  Continue with SQLite?", default=True):
                        database_engine = "sqlite"
                        selected.append("database")
                        database_added_by_scheduler = True
                        # Mark scheduler backend as sqlite
                        scheduler_backend = "sqlite"
                        typer.echo("✅ Scheduler + SQLite database configured")

                        # Show bonus backup job message only when database is added
                        typer.echo("\n🎯 Bonus: Adding database backup job")
                        typer.echo(
                            "✅ Scheduled daily database backup job included "
                            "(runs at 2 AM)"
                        )
                    else:
                        typer.echo("⏹️  Scheduler persistence cancelled")
                        # Don't add database if user declines SQLite

                typer.echo()  # Extra spacing after scheduler section
        elif component_name == "database":
            # Skip generic database prompt if already added by scheduler
            if database_added_by_scheduler:
                continue

            # Standard database prompt (when not added by scheduler)
            prompt = f"  Add {component_spec.description}?"
            if typer.confirm(prompt):
                selected.append("database")

                # Show bonus backup job message when database added with scheduler
                if "scheduler" in selected:
                    typer.echo("\n🎯 Bonus: Adding database backup job")
                    typer.echo(
                        "✅ Scheduled daily database backup job included (runs at 2 AM)"
                    )
        else:
            # Standard prompt for other components
            prompt = f"  Add {component_spec.description}?"
            if typer.confirm(prompt):
                selected.append(component_name)

    # Update selected list with engine info for display
    if "database" in selected and database_engine:
        # Replace "database" with formatted version for display
        db_index = selected.index("database")
        selected[db_index] = f"database[{database_engine}]"

    # Update scheduler with backend info if not memory
    if "scheduler" in selected and scheduler_backend != "memory":
        scheduler_index = selected.index("scheduler")
        selected[scheduler_index] = f"scheduler[{scheduler_backend}]"

    return selected, scheduler_backend
