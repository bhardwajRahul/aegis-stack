"""
Interactive CLI components.

This module contains interactive selection and prompting functions
used by CLI commands.
"""

from pathlib import Path

import typer

from ..constants import (
    AIFrameworks,
    AIProviders,
    AnswerKeys,
    ComponentNames,
    Messages,
    StorageBackends,
)
from ..core.components import COMPONENTS, CORE_COMPONENTS, ComponentSpec, ComponentType
from ..core.services import SERVICES, ServiceType, get_services_by_type

# Global variable to store AI provider selections for template generation
_ai_provider_selection: dict[str, list[str]] = {}

# Global variable to store AI framework selection for template generation
_ai_framework_selection: dict[str, str] = {}

# Global variable to store AI backend selection for template generation
_ai_backend_selection: dict[str, str] = {}

# Global variable to store AI RAG selection for template generation
_ai_rag_selection: dict[str, bool] = {}


def get_interactive_infrastructure_components() -> list[ComponentSpec]:
    """Get infrastructure components available for interactive selection."""
    # Get all infrastructure components
    infra_components = []
    for component_spec in COMPONENTS.values():
        if component_spec.type == ComponentType.INFRASTRUCTURE:
            infra_components.append(component_spec)

    # Sort by name for consistent ordering
    return sorted(infra_components, key=lambda x: x.name)


def interactive_project_selection() -> tuple[list[str], str, list[str]]:
    """
    Interactive project selection with component and service options.

    Returns:
        Tuple of (selected_components, scheduler_backend, selected_services)
    """

    Messages.print_section_header(Messages.SECTION_COMPONENT_SELECTION)
    typer.secho(
        f"Core components ({' + '.join(CORE_COMPONENTS)}) included automatically\n",
        fg="green",
    )

    selected = []
    database_engine = None  # Track database engine selection
    database_added_by_scheduler = False  # Track if database was added by scheduler
    scheduler_backend = StorageBackends.MEMORY

    # Get all infrastructure components from registry
    infra_components = get_interactive_infrastructure_components()

    typer.echo("Infrastructure Components:")

    # Process components in a specific order to handle dependencies
    component_order = ComponentNames.INFRASTRUCTURE_ORDER

    for component_name in component_order:
        # Find the component spec
        component_spec = next(
            (c for c in infra_components if c.name == component_name), None
        )
        if not component_spec:
            continue  # Skip if component doesn't exist in registry

        # Handle special worker dependency logic
        if component_name == ComponentNames.WORKER:
            if ComponentNames.REDIS in selected:
                # Redis already selected, simple worker prompt
                prompt = f"  Add {component_spec.description.lower()}?"
                if typer.confirm(prompt):
                    selected.append(ComponentNames.WORKER)
            else:
                # Redis not selected, offer to add both
                prompt = (
                    f"  Add {component_spec.description.lower()}? (will auto-add Redis)"
                )
                if typer.confirm(prompt):
                    selected.extend([ComponentNames.REDIS, ComponentNames.WORKER])
        elif component_name == ComponentNames.SCHEDULER:
            # Enhanced scheduler selection with persistence and database options
            prompt = f"  Add {component_spec.description}?"
            if typer.confirm(prompt):
                selected.append(ComponentNames.SCHEDULER)

                # Follow-up: persistence question
                typer.echo("\nScheduler Persistence:")
                persistence_prompt = (
                    "  Do you want to persist scheduled jobs? "
                    "(Enables job history, recovery after restarts)"
                )
                if typer.confirm(persistence_prompt):
                    # Database engine selection (SQLite only for now)
                    typer.echo("\nDatabase Engine:")
                    typer.echo("  SQLite will be configured for job persistence")
                    typer.echo("  (PostgreSQL support coming in future releases)")

                    # Show SQLite limitations
                    typer.secho("\nSQLite Limitations:", fg="yellow")
                    typer.echo(
                        "  • Multi-container API access works in development only "
                        "(shared volumes)"
                    )
                    typer.echo("  • Production deployment will be single-container")
                    typer.echo(
                        "  • Use PostgreSQL for full production multi-container support"
                    )

                    if typer.confirm("  Continue with SQLite?", default=True):
                        database_engine = StorageBackends.SQLITE
                        selected.append(ComponentNames.DATABASE)
                        database_added_by_scheduler = True
                        # Mark scheduler backend as sqlite
                        scheduler_backend = StorageBackends.SQLITE
                        typer.secho(
                            "Scheduler + SQLite database configured", fg="green"
                        )

                        # Show bonus backup job message only when database is added
                        typer.echo("\nBonus: Adding database backup job")
                        typer.secho(
                            "Scheduled daily database backup job included "
                            "(runs at 2 AM)",
                            fg="green",
                        )
                    else:
                        typer.echo("Scheduler persistence cancelled")
                        # Don't add database if user declines SQLite

                typer.echo()  # Extra spacing after scheduler section
        elif component_name == ComponentNames.DATABASE:
            # Skip generic database prompt if already added by scheduler
            if database_added_by_scheduler:
                continue

            # Standard database prompt (when not added by scheduler)
            prompt = f"  Add {component_spec.description}?"
            if typer.confirm(prompt):
                selected.append(ComponentNames.DATABASE)

                # Show bonus backup job message when database added with scheduler
                if ComponentNames.SCHEDULER in selected:
                    typer.echo("\nBonus: Adding database backup job")
                    typer.secho(
                        "Scheduled daily database backup job included (runs at 2 AM)",
                        fg="green",
                    )
        else:
            # Standard prompt for other components
            prompt = f"  Add {component_spec.description}?"
            if typer.confirm(prompt):
                selected.append(component_name)

    # Update selected list with engine info for display
    if ComponentNames.DATABASE in selected and database_engine:
        # Replace "database" with formatted version for display
        db_index = selected.index(ComponentNames.DATABASE)
        selected[db_index] = f"{ComponentNames.DATABASE}[{database_engine}]"

    # Update scheduler with backend info if not memory
    if (
        ComponentNames.SCHEDULER in selected
        and scheduler_backend != StorageBackends.MEMORY
    ):
        scheduler_index = selected.index(ComponentNames.SCHEDULER)
        selected[scheduler_index] = f"{ComponentNames.SCHEDULER}[{scheduler_backend}]"

    # Service selection
    selected_services = []

    if SERVICES:  # Only show services if any are available
        Messages.print_section_header(
            Messages.SECTION_SERVICE_SELECTION, newline_before=True
        )
        typer.echo(
            "Services provide business logic functionality for your application.\n"
        )

        # Group services by type for better organization
        auth_services = get_services_by_type(ServiceType.AUTH)

        if auth_services:
            typer.echo("Authentication Services:")
            for service_name, service_spec in auth_services.items():
                prompt = f"  Add {service_spec.description.lower()}?"
                if typer.confirm(prompt):
                    # Auth service requires database - provide explicit confirmation
                    typer.echo("\nDatabase Required:")
                    typer.echo("  Authentication requires a database for user storage")
                    typer.echo("  (user accounts, sessions, JWT tokens)")

                    # Check if database is already selected
                    database_already_selected = any(
                        ComponentNames.DATABASE in comp for comp in selected
                    )

                    if database_already_selected:
                        typer.secho("Database component already selected", fg="green")
                        selected_services.append(service_name)
                    else:
                        auth_confirm_prompt = "  Continue and add database component?"
                        if typer.confirm(auth_confirm_prompt, default=True):
                            selected_services.append(service_name)
                            # Note: Database will be auto-added by service resolution in init.py
                            typer.secho(
                                "Authentication + Database configured", fg="green"
                            )
                        else:
                            typer.echo("Authentication service cancelled")

        # AI & Machine Learning Services
        ai_services = get_services_by_type(ServiceType.AI)

        if ai_services:
            typer.echo("\nAI & Machine Learning Services:")
            for service_name, service_spec in ai_services.items():
                prompt = f"  Add {service_spec.description.lower()}?"
                if typer.confirm(prompt):
                    # AI service requires backend (always available) - no dependency issues
                    # Use the reusable AI configuration function
                    backend, framework, providers, rag_enabled = (
                        interactive_ai_service_config(service_name)
                    )

                    # Handle database auto-add for SQLite backend
                    if backend == StorageBackends.SQLITE:
                        database_already_selected = any(
                            ComponentNames.DATABASE in comp for comp in selected
                        )

                        if database_already_selected:
                            typer.secho(
                                "  Database already selected - usage tracking enabled",
                                fg="green",
                            )
                        else:
                            selected.append(
                                f"{ComponentNames.DATABASE}[{StorageBackends.SQLITE}]"
                            )
                            typer.secho(
                                "  Database added for usage tracking", fg="green"
                            )

                    # Build AI service string with bracket syntax for TemplateGenerator
                    # Format: ai[backend,framework,provider1,provider2,...,rag]
                    options = [backend, framework] + providers
                    if rag_enabled:
                        options.append("rag")
                    service_string = f"{service_name}[{','.join(options)}]"
                    selected_services.append(service_string)
                    typer.secho("AI service configured", fg="green")

        # Future service types can be added here as they become available
        # payment_services = get_services_by_type(ServiceType.PAYMENT)

    return selected, scheduler_backend, selected_services


def get_ai_provider_selection(service_name: str = "ai") -> list[str]:
    """
    Get AI provider selection from interactive session.

    Args:
        service_name: Name of the AI service (defaults to "ai")

    Returns:
        List of selected provider names, or default providers if none selected
    """
    return _ai_provider_selection.get(service_name, ["openai"])


def get_ai_framework_selection(service_name: str = "ai") -> str:
    """
    Get AI framework selection from interactive session.

    Args:
        service_name: Name of the AI service (defaults to "ai")

    Returns:
        Selected framework name, or default (pydantic-ai) if none selected
    """
    return _ai_framework_selection.get(service_name, AIFrameworks.PYDANTIC_AI)


def clear_ai_provider_selection() -> None:
    """Clear stored AI provider selection (useful for testing)."""
    global _ai_provider_selection
    _ai_provider_selection.clear()


def clear_ai_framework_selection() -> None:
    """Clear stored AI framework selection (useful for testing)."""
    global _ai_framework_selection
    _ai_framework_selection.clear()


def get_ai_backend_selection(service_name: str = "ai") -> str:
    """
    Get AI backend selection from interactive session or CLI.

    Args:
        service_name: Name of the AI service (defaults to "ai")

    Returns:
        Selected backend name, or default (memory) if none selected
    """
    return _ai_backend_selection.get(service_name, StorageBackends.MEMORY)


def clear_ai_backend_selection() -> None:
    """Clear stored AI backend selection (useful for testing)."""
    global _ai_backend_selection
    _ai_backend_selection.clear()


def get_ai_rag_selection(service_name: str = "ai") -> bool:
    """
    Get AI RAG selection from interactive session.

    Args:
        service_name: Name of the AI service (defaults to "ai")

    Returns:
        True if RAG is enabled, False otherwise
    """
    return _ai_rag_selection.get(service_name, False)


def clear_ai_rag_selection() -> None:
    """Clear stored AI RAG selection (useful for testing)."""
    global _ai_rag_selection
    _ai_rag_selection.clear()


def set_ai_service_config(
    service_name: str = "ai",
    framework: str | None = None,
    backend: str | None = None,
    providers: list[str] | None = None,
) -> None:
    """
    Set AI service configuration from CLI arguments or bracket syntax.

    This allows non-interactive mode to set AI config parsed from ai[...] syntax.

    Args:
        service_name: Name of the AI service (defaults to "ai")
        framework: AI framework (pydantic-ai or langchain)
        backend: Storage backend (memory or sqlite)
        providers: List of AI providers
    """
    global _ai_framework_selection, _ai_backend_selection, _ai_provider_selection

    if framework is not None:
        _ai_framework_selection[service_name] = framework
    if backend is not None:
        _ai_backend_selection[service_name] = backend
    if providers is not None:
        _ai_provider_selection[service_name] = providers


def clear_all_ai_selections() -> None:
    """Clear all AI selections (useful for testing)."""
    clear_ai_provider_selection()
    clear_ai_framework_selection()
    clear_ai_backend_selection()


def interactive_ai_service_config(
    service_name: str = AnswerKeys.SERVICE_AI,
) -> tuple[str, str, list[str], bool]:
    """
    Interactive AI service configuration prompts.

    Prompts user for framework, backend, provider, and RAG selection.
    Stores selections in global state for template generation.

    Args:
        service_name: Name of the AI service (defaults to "ai")

    Returns:
        Tuple of (backend, framework, providers, rag_enabled)
    """
    global \
        _ai_framework_selection, \
        _ai_backend_selection, \
        _ai_provider_selection, \
        _ai_rag_selection

    # Framework selection
    typer.echo("\nAI Framework Selection:")
    typer.echo("  Choose your AI framework:")
    typer.echo("    1. PydanticAI - Type-safe, Pythonic AI framework (default)")
    typer.echo("    2. LangChain - Popular framework with extensive integrations")

    use_langchain = typer.confirm(
        "  Use LangChain instead of PydanticAI?", default=False
    )
    framework = AIFrameworks.LANGCHAIN if use_langchain else AIFrameworks.PYDANTIC_AI
    _ai_framework_selection[service_name] = framework
    typer.secho(f"  Selected framework: {framework}", fg="green")

    # AI Backend Selection
    typer.echo("\nLLM Usage Tracking:")
    use_sqlite = typer.confirm(
        "  Enable usage tracking with SQLite? (token counts, costs)",
        default=False,
    )

    backend = StorageBackends.SQLITE if use_sqlite else StorageBackends.MEMORY
    _ai_backend_selection[service_name] = backend

    # Provider selection
    typer.echo("\nAI Provider Selection:")
    typer.echo("  Choose AI providers to include (multiple selection supported)")
    typer.echo("  Provider Options:")

    providers: list[str] = []

    # Ask about each provider
    for (
        provider_id,
        name,
        description,
        pricing,
        recommended,
    ) in AIProviders.PROVIDER_INFO:
        recommend_text = " (Recommended)" if recommended else ""
        if typer.confirm(
            f"    ☐ {name} - {description} ({pricing}){recommend_text}?",
            default=recommended,
        ):
            providers.append(provider_id)

    # Handle no providers selected
    if not providers:
        typer.secho(
            "  No providers selected, adding recommended defaults...",
            fg="yellow",
        )
        providers = list(AIProviders.INTERACTIVE_DEFAULTS)

    # Show selected providers
    typer.secho(f"\n  Selected providers: {', '.join(providers)}", fg="green")
    typer.echo("  Dependencies will be optimized for your selection")

    # Store provider selection in global context for template generation
    _ai_provider_selection[service_name] = providers

    # RAG selection
    typer.echo("\nRAG (Retrieval-Augmented Generation):")
    rag_enabled = typer.confirm(
        "  Enable RAG for document indexing and semantic search?",
        default=True,
    )
    _ai_rag_selection[service_name] = rag_enabled
    if rag_enabled:
        typer.secho("  RAG enabled with ChromaDB vector store", fg="green")

    return backend, framework, providers, rag_enabled


def interactive_component_add_selection(project_path: Path) -> tuple[list[str], str]:
    """
    Interactive component selection for adding to existing project.

    Shows currently enabled components (grayed out) and available
    components to add (selectable). Handles dependency resolution.

    Args:
        project_path: Path to the existing project

    Returns:
        Tuple of (selected_components, scheduler_backend)
    """
    from ..core.copier_manager import load_copier_answers

    # Load current project state
    try:
        current_answers = load_copier_answers(project_path)
    except Exception as e:
        typer.secho(f"Failed to load project configuration: {e}", fg="red", err=True)
        raise typer.Exit(1)

    Messages.print_section_header(
        Messages.SECTION_COMPONENT_SELECTION, newline_before=True
    )

    # Show currently enabled components
    enabled_components = []
    for component in ComponentNames.INFRASTRUCTURE_ORDER:
        if current_answers.get(AnswerKeys.include_key(component)):
            enabled_components.append(component)

    if enabled_components:
        typer.secho(f"Currently enabled: {', '.join(enabled_components)}", fg="green")
    else:
        typer.secho("Currently enabled: backend, frontend (core only)", fg="green")

    typer.echo("\nAvailable Components:\n")

    selected = []
    scheduler_backend = StorageBackends.MEMORY

    # Get all infrastructure components in order
    component_order = ComponentNames.INFRASTRUCTURE_ORDER

    for component_name in component_order:
        # Skip if already enabled
        if component_name in enabled_components:
            typer.secho(f"  {component_name} - Already enabled", fg="green")
            continue

        # Skip if already selected in this session (e.g., database auto-added by scheduler)
        if component_name in selected:
            continue

        # Find the component spec
        component_spec = COMPONENTS.get(component_name)
        if not component_spec:
            continue

        # Handle special logic for each component
        if component_name == ComponentNames.WORKER:
            if (
                ComponentNames.REDIS in enabled_components
                or ComponentNames.REDIS in selected
            ):
                # Redis already available
                prompt = f"  Add {component_spec.description.lower()}?"
                if typer.confirm(prompt):
                    selected.append(ComponentNames.WORKER)
            else:
                # Need to add redis too
                prompt = (
                    f"  Add {component_spec.description.lower()}? (will auto-add Redis)"
                )
                if typer.confirm(prompt):
                    selected.extend([ComponentNames.REDIS, ComponentNames.WORKER])

        elif component_name == ComponentNames.SCHEDULER:
            prompt = f"  Add {component_spec.description}?"
            if typer.confirm(prompt):
                selected.append(ComponentNames.SCHEDULER)

                # Check if database is available or will be added
                database_available = (
                    ComponentNames.DATABASE in enabled_components
                    or ComponentNames.DATABASE in selected
                )

                if database_available:
                    # Database already available - offer persistence
                    typer.echo("\nScheduler Persistence:")
                    if typer.confirm("  Enable job persistence with SQLite?"):
                        scheduler_backend = StorageBackends.SQLITE
                        typer.secho(
                            "  Scheduler will use SQLite for job persistence",
                            fg="green",
                        )
                    else:
                        typer.echo(
                            "  Scheduler will use memory backend (no persistence)"
                        )
                else:
                    # Ask if they plan to add database
                    typer.echo("\nScheduler Persistence:")
                    typer.echo("  Job persistence requires SQLite database component")
                    if typer.confirm("  Add database component for job persistence?"):
                        selected.append(ComponentNames.DATABASE)
                        scheduler_backend = StorageBackends.SQLITE
                        typer.secho(
                            "  Database will be added - scheduler will use SQLite",
                            fg="green",
                        )
                    else:
                        typer.echo(
                            "  Scheduler will use memory backend (no persistence)"
                        )

        elif component_name == ComponentNames.REDIS:
            # Only offer if not already added by worker
            if ComponentNames.REDIS not in selected:
                prompt = f"  Add {component_spec.description}?"
                if typer.confirm(prompt):
                    selected.append(ComponentNames.REDIS)

        else:
            # Standard prompt for other components
            prompt = f"  Add {component_spec.description}?"
            if typer.confirm(prompt):
                selected.append(component_name)

    return selected, scheduler_backend


def interactive_component_remove_selection(project_path: Path) -> list[str]:
    """
    Interactive component selection for removing from project.

    Shows currently enabled components (selectable) and core components
    (grayed out, cannot remove). Displays deletion warnings.

    Args:
        project_path: Path to the existing project

    Returns:
        List of components to remove
    """
    from ..core.copier_manager import load_copier_answers

    # Load current project state
    try:
        current_answers = load_copier_answers(project_path)
    except Exception as e:
        typer.secho(f"Failed to load project configuration: {e}", fg="red", err=True)
        raise typer.Exit(1)

    typer.echo()
    typer.secho(Messages.SECTION_COMPONENT_REMOVAL, fg="yellow")
    typer.echo(Messages.SEPARATOR)
    typer.secho(
        "WARNING: This will DELETE component files from your project!", fg="yellow"
    )
    typer.echo()

    # Find enabled components
    enabled_removable = []
    for component in ComponentNames.INFRASTRUCTURE_ORDER:
        if current_answers.get(AnswerKeys.include_key(component)):
            enabled_removable.append(component)

    if not enabled_removable:
        typer.echo("No optional components to remove")
        typer.echo("   (Core components backend + frontend cannot be removed)")
        return []

    typer.echo("Currently enabled components:\n")

    # Show core components (not removable)
    typer.echo("  backend - Core component (cannot remove)")
    typer.echo("  frontend - Core component (cannot remove)")
    typer.echo()

    # Show removable components
    selected = []
    for component_name in enabled_removable:
        component_spec = COMPONENTS.get(component_name)
        if component_spec:
            prompt = f"  Remove {component_spec.description.lower()}?"
            if typer.confirm(prompt):
                selected.append(component_name)

    return selected


def interactive_service_selection(project_path: Path) -> list[str]:
    """
    Interactive service selection for adding to existing project.

    Shows available services with their descriptions and required components.
    Warns if required components are missing.

    Args:
        project_path: Path to the existing project

    Returns:
        List of services to add
    """
    from ..core.copier_manager import load_copier_answers

    # Load current project state
    try:
        current_answers = load_copier_answers(project_path)
    except Exception as e:
        typer.secho(f"Failed to load project configuration: {e}", fg="red", err=True)
        raise typer.Exit(1)

    Messages.print_section_header(
        Messages.SECTION_SERVICE_SELECTION, newline_before=True
    )
    typer.echo("Services provide business logic functionality for your application.\n")

    # Find already enabled services
    enabled_services = []
    for service_name in SERVICES:
        if current_answers.get(AnswerKeys.include_key(service_name)):
            enabled_services.append(service_name)

    # Find enabled components
    enabled_components = set(CORE_COMPONENTS)  # Always have core components
    for component in ComponentNames.INFRASTRUCTURE_ORDER:
        if current_answers.get(AnswerKeys.include_key(component)):
            enabled_components.add(component)

    if enabled_services:
        typer.echo("Currently enabled services:")
        for service_name in enabled_services:
            service_spec = SERVICES[service_name]
            typer.secho(f"  {service_name}: {service_spec.description}", fg="green")
        typer.echo()

    # Show available services grouped by type
    selected_services = []

    # Authentication Services
    auth_services = get_services_by_type(ServiceType.AUTH)
    if auth_services:
        typer.echo("Authentication Services:")
        for service_name, service_spec in auth_services.items():
            # Skip if already enabled
            if service_name in enabled_services:
                typer.secho(f"  {service_name} - Already enabled", fg="green")
                continue

            # Check component requirements
            missing_components = [
                comp
                for comp in service_spec.required_components
                if comp not in enabled_components
            ]

            if missing_components:
                requirement_text = f" (will auto-add: {', '.join(missing_components)})"
            else:
                requirement_text = ""

            prompt = f"  Add {service_spec.description.lower()}{requirement_text}?"
            if typer.confirm(prompt):
                selected_services.append(service_name)

                if missing_components:
                    typer.echo(
                        f"    Required components will be added: {', '.join(missing_components)}"
                    )

    # AI & Machine Learning Services
    ai_services = get_services_by_type(ServiceType.AI)
    if ai_services:
        typer.echo("\nAI & Machine Learning Services:")
        for service_name, service_spec in ai_services.items():
            # Skip if already enabled
            if service_name in enabled_services:
                typer.secho(f"  {service_name} - Already enabled", fg="green")
                continue

            # Check component requirements
            missing_components = [
                comp
                for comp in service_spec.required_components
                if comp not in enabled_components
            ]

            if missing_components:
                requirement_text = f" (will auto-add: {', '.join(missing_components)})"
            else:
                requirement_text = ""

            prompt = f"  Add {service_spec.description.lower()}{requirement_text}?"
            if typer.confirm(prompt):
                selected_services.append(service_name)

                if missing_components:
                    typer.echo(
                        f"    Required components will be added: {', '.join(missing_components)}"
                    )

    # Payment Services (when they exist)
    payment_services = get_services_by_type(ServiceType.PAYMENT)
    if payment_services:
        typer.echo("\nPayment Services:")
        for service_name, service_spec in payment_services.items():
            if service_name in enabled_services:
                typer.secho(f"  {service_name} - Already enabled", fg="green")
                continue

            missing_components = [
                comp
                for comp in service_spec.required_components
                if comp not in enabled_components
            ]

            requirement_text = (
                f" (will auto-add: {', '.join(missing_components)})"
                if missing_components
                else ""
            )

            prompt = f"  Add {service_spec.description.lower()}{requirement_text}?"
            if typer.confirm(prompt):
                selected_services.append(service_name)

                if missing_components:
                    typer.echo(
                        f"    Required components will be added: {', '.join(missing_components)}"
                    )

    return selected_services


def interactive_service_remove_selection(project_path: Path) -> list[str]:
    """
    Interactive service selection for removing from existing project.

    Shows currently enabled services and allows user to select which to remove.

    Args:
        project_path: Path to the existing project

    Returns:
        List of services to remove
    """
    from ..core.copier_manager import load_copier_answers

    # Load current project state
    try:
        current_answers = load_copier_answers(project_path)
    except Exception as e:
        typer.secho(f"Failed to load project configuration: {e}", fg="red", err=True)
        raise typer.Exit(1)

    Messages.print_section_header(Messages.SECTION_SERVICE_REMOVAL, newline_before=True)
    typer.secho("WARNING: Removing services deletes files permanently!\n", fg="yellow")

    # Find enabled services
    enabled_services = []
    for service_name in SERVICES:
        if current_answers.get(AnswerKeys.include_key(service_name)):
            enabled_services.append(service_name)

    if not enabled_services:
        typer.echo("No services are currently enabled.")
        typer.echo("   (Core components backend + frontend cannot be removed)")
        return []

    typer.echo("Currently enabled services:")
    for service_name in enabled_services:
        service_spec = SERVICES[service_name]
        typer.secho(f"  • {service_name}: {service_spec.description}", fg="cyan")
    typer.echo()

    # Ask which to remove
    selected_services = []

    for service_name in enabled_services:
        service_spec = SERVICES[service_name]

        prompt = f"  Remove {service_name} ({service_spec.description})?"
        if typer.confirm(prompt, default=False):
            selected_services.append(service_name)
            typer.secho(f"    Will remove: {service_name}", fg="yellow")

    return selected_services
