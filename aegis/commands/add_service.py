"""
Add service command implementation.

Adds services (auth, AI, etc.) to an existing Aegis Stack project using Copier's update mechanism.
"""

from pathlib import Path

import typer

from ..cli.callbacks import _split_service_list
from ..cli.utils import detect_scheduler_backend
from ..cli.validation import (
    validate_copier_project,
    validate_git_repository,
)
from ..constants import AnswerKeys, ComponentNames, Messages, StorageBackends
from ..core.component_utils import extract_base_service_name
from ..core.components import COMPONENTS, CORE_COMPONENTS
from ..core.copier_manager import load_copier_answers
from ..core.manual_updater import ManualUpdater
from ..core.migration_generator import (
    MIGRATION_SPECS,
    bootstrap_alembic,
    generate_migration,
    service_has_migration,
)
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

    typer.secho("Aegis Stack - Add Services", fg=typer.colors.BLUE, bold=True)
    typer.echo("=" * 50)

    # Resolve project path
    target_path = Path(project_path).resolve()

    # Validate it's a Copier project
    validate_copier_project(target_path, "add-service")

    typer.echo(f"{typer.style('Project:', fg=typer.colors.CYAN)} {target_path}")

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
    validate_git_repository(target_path)

    # Parse services (respecting bracket syntax like ai[langchain,sqlite])
    assert services is not None  # Already validated by check above
    selected_services = _split_service_list(services)

    # Create mapping: full name -> base name (for bracket syntax like ai[langchain,sqlite])
    # This is done once and used throughout to keep things DRY
    service_base_map: dict[str, str] = {
        s: extract_base_service_name(s) for s in selected_services
    }

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
        # Check if service is already enabled in answers (use base name for bracket syntax)
        base_service = service_base_map[service]
        include_key = AnswerKeys.include_key(base_service)
        if existing_answers.get(include_key) is True:
            already_enabled.append(service)

    if already_enabled:
        typer.echo(f"Already enabled: {', '.join(already_enabled)}", err=False)

    # Filter out already enabled services
    services_to_add = [s for s in selected_services if s not in already_enabled]

    if not services_to_add:
        typer.secho("All requested services are already enabled!", fg="green")
        raise typer.Exit(0)

    # Handle AI service interactive configuration
    # We need to check if AI service is being added and prompt for configuration
    ai_config: dict[str, str | list[str]] = {}
    for i, service in enumerate(services_to_add):
        base_service = service_base_map[service]
        if base_service == AnswerKeys.SERVICE_AI:
            if not service.startswith("ai["):
                # AI service without bracket syntax - prompt for configuration
                from ..cli.interactive import interactive_ai_service_config

                backend, framework, providers = interactive_ai_service_config(
                    base_service
                )

                # Store config for later use
                ai_config["backend"] = backend
                ai_config["framework"] = framework
                ai_config["providers"] = providers

                # Build bracket syntax and update the service entry
                options = [backend, framework] + providers
                service_string = f"{base_service}[{','.join(options)}]"
                services_to_add[i] = service_string

                # Update the mapping with the new full service name
                service_base_map[service_string] = base_service
                # Remove old mapping entry
                del service_base_map[service]
            else:
                # AI service with bracket syntax - parse backend from options
                # Format: ai[backend,framework,provider1,provider2,...]
                from ..core.ai_service_parser import parse_ai_service_config

                config = parse_ai_service_config(service)
                ai_config["backend"] = config.backend
                ai_config["framework"] = config.framework
                ai_config["providers"] = config.providers

    # Resolve service dependencies to components
    try:
        required_components, _ = ServiceResolver.resolve_service_dependencies(
            services_to_add
        )
    except ValueError as e:
        typer.secho(f"Failed to resolve service dependencies: {e}", fg="red", err=True)
        raise typer.Exit(1)

    # If AI service selected SQLite backend, ensure database is in required components
    if (
        ai_config.get("backend") == StorageBackends.SQLITE
        and ComponentNames.DATABASE not in required_components
    ):
        required_components.append(ComponentNames.DATABASE)

    # Check which components are already enabled
    enabled_components = []
    missing_components = []

    for component in required_components:
        include_key = AnswerKeys.include_key(component)
        if existing_answers.get(include_key) is True or component in CORE_COMPONENTS:
            enabled_components.append(component)
        else:
            missing_components.append(component)

    # Show what will be added
    typer.secho("\nServices to add:", fg=typer.colors.CYAN, bold=True)
    for service in services_to_add:
        base_service = service_base_map[service]
        if base_service in SERVICES:
            desc = SERVICES[base_service].description
            typer.echo(f"   • {service}: {desc}")

    # Show component requirements
    if missing_components:
        typer.secho(
            "\nRequired components (will be auto-added):", fg=typer.colors.YELLOW
        )
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
        include_key = AnswerKeys.include_key(service)
        update_data[include_key] = True

    # Add missing component flags
    for component in missing_components:
        include_key = AnswerKeys.include_key(component)
        update_data[include_key] = True

    # Add services using ManualUpdater
    typer.secho("\nUpdating project...", fg=typer.colors.CYAN, bold=True)
    try:
        updater = ManualUpdater(target_path)

        # Add missing components first
        for component in missing_components:
            typer.secho(
                f"\nAdding required component: {component}...", fg=typer.colors.CYAN
            )

            # Prepare component-specific data
            component_data: dict[str, bool | str] = {}

            # Handle scheduler backend if needed
            if component == ComponentNames.SCHEDULER:
                scheduler_backend = detect_scheduler_backend([component])
                component_data[AnswerKeys.SCHEDULER_BACKEND] = scheduler_backend
                component_data[AnswerKeys.SCHEDULER_WITH_PERSISTENCE] = (
                    scheduler_backend == StorageBackends.SQLITE
                )
            elif component == ComponentNames.DATABASE:
                component_data[AnswerKeys.DATABASE_ENGINE] = StorageBackends.SQLITE

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
            typer.secho(f"\nAdding service: {service}...", fg=typer.colors.CYAN)

            # Prepare service-specific data
            service_data: dict[str, bool | str] = {}

            # Get base service name (strips variant syntax like [langchain,sqlite])
            base_service = service_base_map[service]

            # For AI service, use the captured configuration
            if base_service == AnswerKeys.SERVICE_AI:
                # Use providers from interactive config, or default to openai
                providers = ai_config.get("providers", ["openai"])
                if isinstance(providers, list):
                    service_data[AnswerKeys.AI_PROVIDERS] = ",".join(providers)
                else:
                    service_data[AnswerKeys.AI_PROVIDERS] = str(providers)

                # Set backend and framework for pyproject.toml regeneration
                # This ensures alembic is included when sqlite backend is selected
                backend = ai_config.get("backend", StorageBackends.MEMORY)
                framework = ai_config.get("framework", "pydantic-ai")
                service_data[AnswerKeys.AI_BACKEND] = backend
                service_data[AnswerKeys.AI_FRAMEWORK] = framework

            # Add the service (services are added like components)
            # Use base_service for file lookup, not the full variant name
            result = updater.add_component(base_service, service_data)

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

        # Generate migrations for services that need them
        for service in services_to_add:
            base_service = service_base_map[service]
            if base_service not in MIGRATION_SPECS:
                continue

            # AI service only needs migrations with SQLite backend (not memory)
            if base_service == AnswerKeys.SERVICE_AI:
                ai_backend = ai_config.get("backend", StorageBackends.MEMORY)
                if ai_backend == StorageBackends.MEMORY:
                    continue  # Skip migrations for memory backend

            alembic_dir = target_path / "alembic"
            if not alembic_dir.exists():
                typer.secho(
                    "\nBootstrapping alembic infrastructure...", fg=typer.colors.CYAN
                )
                created = bootstrap_alembic(
                    target_path, updater.jinja_env, updater.answers
                )
                for f in created:
                    typer.echo(f"   Created: {f}")

            if not service_has_migration(target_path, base_service):
                migration_path = generate_migration(target_path, base_service)
                if migration_path:
                    typer.secho(
                        f"   Generated migration: {migration_path.name}", fg="green"
                    )

        # Auto-run migrations for services that need them
        # Exclude AI service with memory backend (doesn't need migrations)
        ai_needs_migrations = (
            ai_config.get("backend", StorageBackends.MEMORY) != StorageBackends.MEMORY
        )
        services_with_migrations = [
            s
            for s in services_to_add
            if service_base_map[s] in MIGRATION_SPECS
            and (service_base_map[s] != AnswerKeys.SERVICE_AI or ai_needs_migrations)
        ]
        if services_with_migrations:
            typer.secho("\nApplying database migrations...", fg=typer.colors.CYAN)
            from ..core.post_gen_tasks import run_migrations

            migration_success = run_migrations(target_path, include_migrations=True)

            if not migration_success:
                typer.secho(
                    "Warning: Auto-migration failed. Run 'make migrate' manually.",
                    fg="yellow",
                )

        typer.secho("\nServices added successfully!", fg="green")

        # Provide next steps
        if len(services_to_add) > 0 or len(missing_components) > 0:
            Messages.print_review_changes()

        Messages.print_next_steps()

        # Service-specific guidance (use base service names for comparison)
        base_services_added = [service_base_map[s] for s in services_to_add]

        if AnswerKeys.SERVICE_AUTH in base_services_added:
            project_slug = existing_answers.get(AnswerKeys.PROJECT_SLUG, "my-project")
            typer.secho("\nAuth Service Setup:", fg=typer.colors.CYAN, bold=True)
            cmd = typer.style(f"{project_slug} auth create-test-users", bold=True)
            typer.echo(f"   1. Create test users: {cmd}")
            url = typer.style("http://localhost:8000/docs", bold=True)
            typer.echo(f"   2. View auth routes: {url}")

        if AnswerKeys.SERVICE_AI in base_services_added:
            project_slug = existing_answers.get(AnswerKeys.PROJECT_SLUG, "my-project")
            typer.secho("\nAI Service Setup:", fg=typer.colors.CYAN, bold=True)
            typer.echo(
                f"   1. Set {typer.style('AI_PROVIDER', bold=True)} in .env (openai, anthropic, google, groq)"
            )
            typer.echo(
                f"   2. Set provider API key ({typer.style('OPENAI_API_KEY', bold=True)}, etc.)"
            )
            cmd = typer.style(f"{project_slug} ai chat", bold=True)
            typer.echo(f"   3. Test with CLI: {cmd}")

    except Exception as e:
        typer.secho(f"\nFailed to add services: {e}", fg="red", err=True)
        raise typer.Exit(1)
