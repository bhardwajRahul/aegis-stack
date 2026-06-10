"""
Interactive CLI components.

This module contains interactive selection and prompting functions
used by CLI commands.
"""

import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

import questionary
import typer

from ..constants import (
    AIFrameworks,
    AIProviders,
    AnswerKeys,
    AuthLevels,
    ComponentNames,
    Messages,
    OllamaMode,
    StorageBackends,
    WorkerBackends,
)
from ..core.components import COMPONENTS, CORE_COMPONENTS, ComponentSpec, ComponentType
from ..core.services import (
    SERVICE_TYPE_I18N_KEYS,
    SERVICES,
    ServiceType,
    get_services_by_type,
)
from ..i18n import t


def _translated_desc(name: str, fallback: str) -> str:
    """Get translated description for a component or service, with fallback."""
    # Try component.* first, then service.*
    for prefix in ("component", "service"):
        key = f"{prefix}.{name}"
        result = t(key)
        if result != key:
            return result
    return fallback


# Global variable to store AI provider selections for template generation
_ai_provider_selection: dict[str, list[str]] = {}

# Global variable to store AI framework selection for template generation
_ai_framework_selection: dict[str, str] = {}

# Global variable to store AI backend selection for template generation
_ai_backend_selection: dict[str, str] = {}

# Global variable to store AI RAG selection for template generation
_ai_rag_selection: dict[str, bool] = {}

# Global variable to store AI voice selection for template generation
_ai_voice_selection: dict[str, bool] = {}

# Global variable to store skip LLM sync selection for template generation
_skip_llm_sync_selection: dict[str, bool] = {}

# Global variable to store Ollama mode selection for template generation
_ollama_mode_selection: dict[str, str] = {}

# Global variable to store auth level selection for template generation
_auth_level_selection: dict[str, str] = {}

# Global variable to store database engine selection for template generation
_database_engine_selection: str | None = None


def select_database_engine(context: str = "Database") -> str:
    """
    Interactive database engine selection using arrow keys.

    Remembers the selection so subsequent calls return the same value
    without prompting again.

    Args:
        context: Description of what the database is for (e.g., "Scheduler", "AI")

    Returns:
        Selected database engine (sqlite or postgres)
    """
    global _database_engine_selection

    # If already selected, reuse that choice
    if _database_engine_selection is not None:
        typer.secho(
            f"  {t('interactive.db_reuse', engine=_database_engine_selection.upper())}",
            fg="green",
        )
        return _database_engine_selection

    typer.echo(f"\n{t('interactive.db_engine_label', context=context)}")

    choices = [
        questionary.Choice(
            title=t("interactive.db_sqlite"),
            value=StorageBackends.SQLITE,
        ),
        questionary.Choice(
            title=t("interactive.db_postgres"),
            value=StorageBackends.POSTGRES,
        ),
    ]

    result = questionary.select(
        t("interactive.db_select"),
        choices=choices,
        default=StorageBackends.SQLITE,
    ).ask()

    # Handle Ctrl+C or escape
    if result is None:
        raise typer.Abort()

    _database_engine_selection = result
    return result


def get_database_engine_selection() -> str | None:
    """Get the current database engine selection."""
    return _database_engine_selection


def clear_database_engine_selection() -> None:
    """Clear stored database engine selection (useful for testing)."""
    global _database_engine_selection
    _database_engine_selection = None


def select_worker_backend() -> str:
    """
    Interactive worker backend selection using arrow keys.

    Returns:
        Selected backend: "arq", "taskiq", or "dramatiq"
    """
    typer.echo(f"\n{t('interactive.worker_label')}")

    choices = [
        questionary.Choice(
            title=t("interactive.worker_arq"),
            value=WorkerBackends.ARQ,
        ),
        questionary.Choice(
            title=t("interactive.worker_dramatiq"),
            value=WorkerBackends.DRAMATIQ,
        ),
        questionary.Choice(
            title=t("interactive.worker_taskiq"),
            value=WorkerBackends.TASKIQ,
        ),
    ]

    result = questionary.select(
        t("interactive.worker_select"),
        choices=choices,
        default=WorkerBackends.ARQ,
    ).ask()

    if result is None:
        raise typer.Abort()

    return result


def set_database_engine_selection(engine: str | None) -> None:
    """
    Pre-set database engine selection (for testing or CLI args).

    Args:
        engine: Database engine (sqlite, postgres) or None to clear
    """
    global _database_engine_selection
    _database_engine_selection = engine


def get_interactive_infrastructure_components() -> list[ComponentSpec]:
    """Get infrastructure components available for interactive selection."""
    # Get all infrastructure components
    infra_components = []
    for component_spec in COMPONENTS.values():
        if component_spec.type == ComponentType.INFRASTRUCTURE:
            infra_components.append(component_spec)

    # Sort by name for consistent ordering
    return sorted(infra_components, key=lambda x: x.name)


@dataclass
class ProjectSelection:
    """Mutable selection state threaded through the init-flow steps.

    Replaces the loose locals (and the positional 4-tuple they fed) so a
    future wizard renderer (issue #487) can re-render, preview, or revisit
    selections from one object instead of module globals.
    """

    components: list[str] = field(default_factory=list)
    services: list[str] = field(default_factory=list)
    scheduler_backend: str = StorageBackends.MEMORY
    database_engine: str | None = None
    database_added_by_scheduler: bool = False


class SelectionUI(Protocol):
    """Presentation seam for the init-flow selection engine.

    Steps hold the selection rules and talk only to this protocol; the
    renderer decides how a question looks. ``TyperSelectionUI`` is the
    quick-setup renderer (one-line confirms); issue #487's guided wizard
    is a second implementation (panels, learn-more) over the same steps.
    """

    def section(self, title: str, *, newline_before: bool = False) -> None: ...

    def confirm(self, prompt: str, *, default: bool = True) -> bool: ...

    def echo(self, message: str = "") -> None: ...

    def success(self, message: str) -> None: ...

    def choose_worker_backend(self) -> str: ...

    def choose_database_engine(self, context: str) -> str: ...

    def configure_auth(self, service_name: str) -> str: ...

    def configure_ai(
        self, service_name: str
    ) -> tuple[str, str, list[str], bool, bool]: ...


class TyperSelectionUI:
    """Quick-setup renderer: plain Typer prompts, one line per question.

    Delegates to the module-level prompt helpers via call-time global
    lookup so existing test patches (``typer.confirm``,
    ``select_worker_backend``, ...) keep working unchanged.
    """

    def section(self, title: str, *, newline_before: bool = False) -> None:
        Messages.print_section_header(title, newline_before=newline_before)

    def confirm(self, prompt: str, *, default: bool = True) -> bool:
        return typer.confirm(prompt, default=default)

    def echo(self, message: str = "") -> None:
        typer.echo(message)

    def success(self, message: str) -> None:
        typer.secho(message, fg="green")

    def choose_worker_backend(self) -> str:
        return select_worker_backend()

    def choose_database_engine(self, context: str) -> str:
        return select_database_engine(context=context)

    def configure_auth(self, service_name: str) -> str:
        return interactive_auth_service_config(service_name)

    def configure_ai(self, service_name: str) -> tuple[str, str, list[str], bool, bool]:
        return interactive_ai_service_config(service_name)


def _step_worker(spec: ComponentSpec, state: ProjectSelection, ui: SelectionUI) -> None:
    """Worker prompt; bundles redis (hard dependency) when not yet selected."""
    desc = _translated_desc(spec.name, spec.description)
    redis_selected = ComponentNames.REDIS in state.components
    prompt_key = (
        "interactive.add_prompt" if redis_selected else "interactive.add_with_redis"
    )
    if not ui.confirm(f"  {t(prompt_key, description=desc)}"):
        return

    backend = ui.choose_worker_backend()
    worker = (
        ComponentNames.WORKER
        if backend == WorkerBackends.ARQ
        else f"{ComponentNames.WORKER}[{backend}]"
    )
    if not redis_selected:
        state.components.append(ComponentNames.REDIS)
    state.components.append(worker)
    ui.success(t("interactive.worker_configured", backend=backend))


def _step_scheduler(
    spec: ComponentSpec, state: ProjectSelection, ui: SelectionUI
) -> None:
    """Scheduler prompt with the persistence mini-wizard (engine + database)."""
    desc = _translated_desc(spec.name, spec.description)
    if not ui.confirm(f"  {t('interactive.add_prompt', description=desc)}"):
        return

    state.components.append(ComponentNames.SCHEDULER)

    ui.echo(f"\n{t('interactive.scheduler_persistence')}")
    if ui.confirm(f"  {t('interactive.persist_prompt')}"):
        engine = ui.choose_database_engine("Scheduler")
        if engine == StorageBackends.POSTGRES:
            state.components.append(
                f"{ComponentNames.DATABASE}[{StorageBackends.POSTGRES}]"
            )
        else:
            state.components.append(ComponentNames.DATABASE)
        state.database_engine = engine
        state.database_added_by_scheduler = True
        state.scheduler_backend = engine
        ui.success(t("interactive.scheduler_db_configured", engine=engine.upper()))

        # Bonus backup job only applies once a database is in the mix.
        ui.echo(f"\n{t('interactive.bonus_backup')}")
        ui.success(t("interactive.backup_desc"))

    ui.echo()  # Extra spacing after scheduler section


def _step_database(
    spec: ComponentSpec, state: ProjectSelection, ui: SelectionUI
) -> None:
    """Database prompt; skipped when the scheduler step already added one."""
    if state.database_added_by_scheduler:
        return

    desc = _translated_desc(spec.name, spec.description)
    if not ui.confirm(f"  {t('interactive.add_prompt', description=desc)}"):
        return

    state.components.append(ComponentNames.DATABASE)
    if ComponentNames.SCHEDULER in state.components:
        ui.echo(f"\n{t('interactive.bonus_backup')}")
        ui.success(t("interactive.backup_desc"))


def _step_generic_component(
    spec: ComponentSpec, state: ProjectSelection, ui: SelectionUI
) -> None:
    """Plain confirm-and-add for components without special rules."""
    desc = _translated_desc(spec.name, spec.description)
    if ui.confirm(f"  {t('interactive.add_prompt', description=desc)}"):
        state.components.append(spec.name)


ComponentStep = Callable[[ComponentSpec, ProjectSelection, SelectionUI], None]

# Components with selection rules beyond confirm-and-add. Anything not
# listed gets the generic step.
_COMPONENT_STEPS: dict[str, ComponentStep] = {
    ComponentNames.WORKER: _step_worker,
    ComponentNames.SCHEDULER: _step_scheduler,
    ComponentNames.DATABASE: _step_database,
}


def run_project_selection(ui: SelectionUI) -> ProjectSelection:
    """Drive the init-flow selection steps against the given renderer.

    Holds all selection rules; ``ui`` decides presentation only. Returns
    the populated ``ProjectSelection`` (components carry bracket syntax,
    e.g. ``scheduler[sqlite]``, exactly as the resolvers expect).
    """
    state = ProjectSelection()

    ui.section(t("interactive.component_selection"))
    ui.success(
        t("interactive.core_included", components=" + ".join(CORE_COMPONENTS)) + "\n"
    )
    ui.echo(t("interactive.infra_header"))

    # Process components in registry order to handle dependencies.
    for component_name in ComponentNames.INFRASTRUCTURE_ORDER:
        spec = COMPONENTS.get(component_name)
        if spec is None or spec.type != ComponentType.INFRASTRUCTURE:
            continue
        step = _COMPONENT_STEPS.get(component_name, _step_generic_component)
        step(spec, state, ui)

    # Rewrite plain names with engine/backend bracket info for display
    # and downstream resolution.
    if ComponentNames.DATABASE in state.components and state.database_engine:
        db_index = state.components.index(ComponentNames.DATABASE)
        state.components[db_index] = (
            f"{ComponentNames.DATABASE}[{state.database_engine}]"
        )
    if (
        ComponentNames.SCHEDULER in state.components
        and state.scheduler_backend != StorageBackends.MEMORY
    ):
        scheduler_index = state.components.index(ComponentNames.SCHEDULER)
        state.components[scheduler_index] = (
            f"{ComponentNames.SCHEDULER}[{state.scheduler_backend}]"
        )

    # Service selection
    if SERVICES:  # Only show services if any are available
        ui.section(t("interactive.service_selection"), newline_before=True)
        ui.echo(t("interactive.services_intro") + "\n")
        _step_auth_services(state, ui)
        _step_ai_services(state, ui)
        _step_content_services(state, ui)

    return state


def _step_auth_services(state: ProjectSelection, ui: SelectionUI) -> None:
    """Auth prompts: level configuration plus the database confirmation."""
    auth_services = get_services_by_type(ServiceType.AUTH)
    if not auth_services:
        return

    ui.echo(t("interactive.auth_header"))
    for service_name, service_spec in auth_services.items():
        desc = _translated_desc(service_name, service_spec.description)
        if not ui.confirm(f"  {t('interactive.add_prompt', description=desc)}"):
            continue

        # Prompt for auth level first
        level = ui.configure_auth(service_name)

        # Auth service requires database - provide explicit confirmation
        ui.echo(f"\n{t('interactive.auth_db_required')}")
        ui.echo(f"  {t('interactive.auth_db_reason')}")
        ui.echo(f"  {t('interactive.auth_db_details')}")

        # Substring check on purpose: catches "database[postgres]" too.
        database_already_selected = any(
            ComponentNames.DATABASE in comp for comp in state.components
        )
        if database_already_selected:
            ui.success(t("interactive.auth_db_already"))
        elif not ui.confirm(f"  {t('interactive.auth_db_confirm')}"):
            ui.echo(t("interactive.auth_cancelled"))
            continue

        state.services.append(f"{service_name}[{level}]")

        # Note: Database will be auto-added by service resolution in init.py
        if not database_already_selected:
            ui.success(t("interactive.auth_db_configured"))


def _step_ai_services(state: ProjectSelection, ui: SelectionUI) -> None:
    """AI prompts: full configuration plus database auto-add for db backends."""
    ai_services = get_services_by_type(ServiceType.AI)
    if not ai_services:
        return

    ui.echo(f"\n{t('interactive.ai_header')}")
    for service_name, service_spec in ai_services.items():
        desc = _translated_desc(service_name, service_spec.description)
        if not ui.confirm(f"  {t('interactive.add_prompt', description=desc)}"):
            continue

        backend, framework, providers, rag_enabled, voice_enabled = ui.configure_ai(
            service_name
        )

        # Handle database auto-add for database backends
        if backend in (StorageBackends.SQLITE, StorageBackends.POSTGRES):
            database_already_selected = any(
                ComponentNames.DATABASE in comp for comp in state.components
            )
            if database_already_selected:
                ui.success(f"  {t('interactive.ai_db_already')}")
            else:
                state.components.append(f"{ComponentNames.DATABASE}[{backend}]")
                ui.success(f"  {t('interactive.ai_db_added', backend=backend)}")

        # Bracket syntax for TemplateGenerator:
        # ai[backend,framework,provider1,...,rag,voice]
        options = [backend, framework] + providers
        if rag_enabled:
            options.append("rag")
        if voice_enabled:
            options.append("voice")
        state.services.append(f"{service_name}[{','.join(options)}]")
        ui.success(t("interactive.ai_configured"))


def _step_content_services(state: ProjectSelection, ui: SelectionUI) -> None:
    """Plain confirm-and-add for content services."""
    content_services = get_services_by_type(ServiceType.CONTENT)
    if not content_services:
        return

    ui.echo(f"\n{t('services.type_content')}")
    for service_name, service_spec in content_services.items():
        desc = _translated_desc(service_name, service_spec.description)
        if ui.confirm(f"  {t('interactive.add_prompt', description=desc)}"):
            state.services.append(service_name)


def interactive_project_selection() -> tuple[list[str], str, list[str], bool]:
    """
    Interactive project selection with component and service options.

    Thin Typer-rendered wrapper over ``run_project_selection`` — the
    selection rules live in the step functions, shared with any other
    ``SelectionUI`` renderer.

    Returns:
        Tuple of (selected_components, scheduler_backend, selected_services, skip_llm_sync)
    """
    state = run_project_selection(TyperSelectionUI())
    # skip_llm_sync is recorded in module state during AI configuration.
    return (
        state.components,
        state.scheduler_backend,
        state.services,
        get_skip_llm_sync_selection(),
    )


def get_ai_provider_selection(service_name: str = "ai") -> list[str]:
    """
    Get AI provider selection from interactive session.

    Args:
        service_name: Name of the AI service (defaults to "ai")

    Returns:
        List of selected provider names, or default providers if none selected
    """
    return _ai_provider_selection.get(service_name, [AIProviders.OPENAI])


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


def get_ai_voice_selection(service_name: str = "ai") -> bool:
    """
    Get AI voice selection from interactive session.

    Args:
        service_name: Name of the AI service (defaults to "ai")

    Returns:
        True if voice is enabled, False otherwise
    """
    return _ai_voice_selection.get(service_name, False)


def clear_ai_voice_selection() -> None:
    """Clear stored AI voice selection (useful for testing)."""
    global _ai_voice_selection
    _ai_voice_selection.clear()


def get_skip_llm_sync_selection(service_name: str = "ai") -> bool:
    """
    Get skip LLM sync selection from interactive session.

    Args:
        service_name: Name of the AI service (defaults to "ai")

    Returns:
        True if LLM sync should be skipped, False otherwise
    """
    return _skip_llm_sync_selection.get(service_name, False)


def clear_skip_llm_sync_selection() -> None:
    """Clear stored skip LLM sync selection (useful for testing)."""
    global _skip_llm_sync_selection
    _skip_llm_sync_selection.clear()


def get_ollama_mode_selection(service_name: str = "ai") -> str:
    """
    Get Ollama mode selection from interactive session.

    Args:
        service_name: Name of the AI service (defaults to "ai")

    Returns:
        Selected Ollama mode (host, docker, or none)
    """
    return _ollama_mode_selection.get(service_name, OllamaMode.NONE)


def set_ollama_mode_selection(service_name: str, mode: str) -> None:
    """
    Set Ollama mode selection.

    Args:
        service_name: Name of the AI service (defaults to "ai")
        mode: Ollama mode (host, docker, or none)
    """
    global _ollama_mode_selection
    _ollama_mode_selection[service_name] = mode


def clear_ollama_mode_selection() -> None:
    """Clear stored Ollama mode selection (useful for testing)."""
    global _ollama_mode_selection
    _ollama_mode_selection.clear()


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
    global _ollama_mode_selection

    if framework is not None:
        _ai_framework_selection[service_name] = framework
    if backend is not None:
        _ai_backend_selection[service_name] = backend
    if providers is not None:
        _ai_provider_selection[service_name] = providers
        # Auto-set ollama_mode to "host" when ollama is a provider (non-interactive default)
        if AIProviders.OLLAMA in providers:
            _ollama_mode_selection[service_name] = OllamaMode.HOST


def clear_all_ai_selections() -> None:
    """Clear all AI selections (useful for testing)."""
    clear_ai_provider_selection()
    clear_ai_framework_selection()
    clear_ai_backend_selection()
    clear_ai_rag_selection()
    clear_ai_voice_selection()
    clear_skip_llm_sync_selection()
    clear_ollama_mode_selection()
    clear_database_engine_selection()
    clear_auth_level_selection()


def get_auth_level_selection(service_name: str = "auth") -> str:
    """
    Get auth level selection from interactive session.

    Args:
        service_name: Name of the auth service (defaults to "auth")

    Returns:
        Selected auth level, or default (basic) if none selected
    """
    return _auth_level_selection.get(service_name, AuthLevels.BASIC)


def set_auth_level_selection(
    service_name: str = "auth", level: str | None = None
) -> None:
    """
    Set auth level selection from CLI arguments or bracket syntax.

    Args:
        service_name: Name of the auth service (defaults to "auth")
        level: Auth level (basic or rbac) or None to skip
    """
    global _auth_level_selection
    if level is not None:
        _auth_level_selection[service_name] = level


def clear_auth_level_selection() -> None:
    """Clear stored auth level selection (useful for testing)."""
    global _auth_level_selection
    _auth_level_selection.clear()


def interactive_auth_service_config(
    service_name: str = AnswerKeys.SERVICE_AUTH,
) -> str:
    """
    Interactive auth service configuration prompts.

    Prompts user for auth level selection.
    Stores selection in global state for template generation.

    Args:
        service_name: Name of the auth service (defaults to "auth")

    Returns:
        Selected auth level string
    """
    global _auth_level_selection

    typer.echo(f"\n{t('interactive.auth_level_label')}")

    choices = [
        questionary.Choice(
            title=t("interactive.auth_basic"),
            value=AuthLevels.BASIC,
        ),
        questionary.Choice(
            title=t("interactive.auth_rbac"),
            value=AuthLevels.RBAC,
        ),
        questionary.Choice(
            title=t("interactive.auth_org"),
            value=AuthLevels.ORG,
        ),
    ]

    result = questionary.select(
        t("interactive.auth_select"),
        choices=choices,
        default=AuthLevels.BASIC,
    ).ask()

    if result is None:
        raise typer.Abort()

    _auth_level_selection[service_name] = result
    typer.secho(f"  {t('interactive.auth_selected', level=result)}", fg="green")

    return result


def interactive_ai_service_config(
    service_name: str = AnswerKeys.SERVICE_AI,
) -> tuple[str, str, list[str], bool, bool]:
    """
    Interactive AI service configuration prompts.

    Prompts user for framework, backend, provider, RAG, and voice selection.
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
    typer.echo(f"\n{t('interactive.ai_framework_label')}")
    typer.echo(f"  {t('interactive.ai_framework_intro')}")
    typer.echo(f"    1. {t('interactive.ai_pydanticai')}")
    typer.echo(f"    2. {t('interactive.ai_langchain')}")

    use_pydanticai = typer.confirm(
        f"  {t('interactive.ai_use_pydanticai')}", default=True
    )
    framework = AIFrameworks.PYDANTIC_AI if use_pydanticai else AIFrameworks.LANGCHAIN
    _ai_framework_selection[service_name] = framework
    typer.secho(
        f"  {t('interactive.ai_selected_framework', framework=framework)}",
        fg="green",
    )

    # AI Backend Selection
    typer.echo(f"\n{t('interactive.ai_tracking_label')}")
    enable_tracking = typer.confirm(
        f"  {t('interactive.ai_tracking_prompt')}",
        default=True,
    )

    if enable_tracking:
        # Database engine selection with arrow keys (reuses previous selection)
        backend = select_database_engine(context=t("interactive.ai_tracking_context"))
    else:
        backend = StorageBackends.MEMORY

    _ai_backend_selection[service_name] = backend

    # LLM catalog sync prompt (only for database backends)
    if backend in (StorageBackends.SQLITE, StorageBackends.POSTGRES):
        typer.echo(f"\n{t('interactive.ai_sync_label')}")
        typer.echo(f"  {t('interactive.ai_sync_desc')}")
        typer.echo(f"  {t('interactive.ai_sync_time')}")
        skip_sync = not typer.confirm(
            f"  {t('interactive.ai_sync_prompt')}",
            default=True,  # Default to sync
        )
        _skip_llm_sync_selection[service_name] = skip_sync
        if not skip_sync:
            typer.secho(f"  {t('interactive.ai_sync_will')}", fg="green")
        else:
            typer.echo(f"  {t('interactive.ai_sync_skipped')}")

    # Provider selection
    typer.echo(f"\n{t('interactive.ai_provider_label')}")
    typer.echo(f"  {t('interactive.ai_provider_intro')}")
    typer.echo(f"  {t('interactive.ai_provider_options')}")

    providers: list[str] = []

    # Ask about each provider
    for (
        provider_id,
        _name,
        _description,
        _pricing,
        recommended,
    ) in AIProviders.PROVIDER_INFO:
        provider_label = t(f"interactive.ai_provider.{provider_id}")
        recommend_text = (
            f" {t('interactive.ai_provider_recommended')}" if recommended else ""
        )
        if typer.confirm(
            f"    \u2610 {provider_label}{recommend_text}?",
            default=True,
        ):
            providers.append(provider_id)

    # Handle no providers selected
    if not providers:
        typer.secho(
            f"  {t('interactive.ai_no_providers')}",
            fg="yellow",
        )
        providers = list(AIProviders.INTERACTIVE_DEFAULTS)

    # Show selected providers
    typer.secho(
        f"\n  {t('interactive.ai_selected_providers', providers=', '.join(providers))}",
        fg="green",
    )
    typer.echo(f"  {t('interactive.ai_deps_optimized')}")

    # Store provider selection in global context for template generation
    _ai_provider_selection[service_name] = providers

    # Ollama deployment mode selection (only if Ollama was selected)
    if AIProviders.OLLAMA in providers:
        typer.echo(f"\n{t('interactive.ai_ollama_label')}")
        typer.echo(f"  {t('interactive.ai_ollama_intro')}")
        typer.echo(f"    1. {t('interactive.ai_ollama_host')}")
        typer.echo(f"    2. {t('interactive.ai_ollama_docker')}")

        use_host = typer.confirm(
            f"  {t('interactive.ai_ollama_host_prompt')}",
            default=True,
        )
        ollama_mode = OllamaMode.HOST if use_host else OllamaMode.DOCKER
        _ollama_mode_selection[service_name] = ollama_mode

        if ollama_mode == OllamaMode.HOST:
            typer.secho(f"  {t('interactive.ai_ollama_host_ok')}", fg="green")
            typer.echo(f"  {t('interactive.ai_ollama_host_hint')}")
        else:
            typer.secho(f"  {t('interactive.ai_ollama_docker_ok')}", fg="green")
            typer.echo(f"  {t('interactive.ai_ollama_docker_hint')}")
    else:
        # No Ollama selected - set mode to none
        _ollama_mode_selection[service_name] = OllamaMode.NONE

    # RAG selection with Python 3.14 compatibility check
    typer.echo(f"\n{t('interactive.ai_rag_label')}")
    if sys.version_info >= (3, 14):
        typer.secho(
            f"  {t('interactive.ai_rag_warning')}",
            fg="yellow",
        )
        typer.echo(f"  {t('interactive.ai_rag_compat_note')}")
        rag_enabled = typer.confirm(
            f"  {t('interactive.ai_rag_compat_prompt')}",
            default=True,
        )
    else:
        rag_enabled = typer.confirm(
            f"  {t('interactive.ai_rag_prompt')}",
            default=True,
        )
    _ai_rag_selection[service_name] = rag_enabled
    if rag_enabled:
        typer.secho(f"  {t('interactive.ai_rag_enabled')}", fg="green")

    # Voice (TTS/STT) selection
    typer.echo(f"\n{t('interactive.ai_voice_label')}")
    voice_enabled = typer.confirm(
        f"  {t('interactive.ai_voice_prompt')}",
        default=True,
    )
    _ai_voice_selection[service_name] = voice_enabled
    if voice_enabled:
        typer.secho(f"  {t('interactive.ai_voice_enabled')}", fg="green")

    return backend, framework, providers, rag_enabled, voice_enabled


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
                if typer.confirm(prompt, default=True):
                    backend = select_worker_backend()
                    if backend == WorkerBackends.ARQ:
                        selected.append(ComponentNames.WORKER)
                    else:
                        selected.append(f"{ComponentNames.WORKER}[{backend}]")
                    typer.secho(f"Worker with {backend} backend configured", fg="green")
            else:
                # Need to add redis too
                prompt = (
                    f"  Add {component_spec.description.lower()}? (will auto-add Redis)"
                )
                if typer.confirm(prompt, default=True):
                    backend = select_worker_backend()
                    if backend == WorkerBackends.ARQ:
                        selected.extend([ComponentNames.REDIS, ComponentNames.WORKER])
                    else:
                        selected.extend(
                            [
                                ComponentNames.REDIS,
                                f"{ComponentNames.WORKER}[{backend}]",
                            ]
                        )
                    typer.secho(f"Worker with {backend} backend configured", fg="green")

        elif component_name == ComponentNames.SCHEDULER:
            prompt = f"  Add {component_spec.description}?"
            if typer.confirm(prompt, default=True):
                selected.append(ComponentNames.SCHEDULER)

                # Check if database is available or will be added
                database_available = (
                    ComponentNames.DATABASE in enabled_components
                    or ComponentNames.DATABASE in selected
                )

                if database_available:
                    # Database already available - offer persistence
                    typer.echo("\nScheduler Persistence:")
                    if typer.confirm(
                        "  Enable job persistence with SQLite?", default=True
                    ):
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
                    if typer.confirm(
                        "  Add database component for job persistence?", default=True
                    ):
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
                if typer.confirm(prompt, default=True):
                    selected.append(ComponentNames.REDIS)

        else:
            # Standard prompt for other components
            prompt = f"  Add {component_spec.description}?"
            if typer.confirm(prompt, default=True):
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


def _configure_auth_service_add(service_name: str) -> str:
    """Prompt for auth level and return the ``auth[<level>]`` string."""
    level = interactive_auth_service_config(service_name)
    return f"{service_name}[{level}]"


# Per-service interactive configurators for the add flow. A service listed
# here gets its options prompted on acceptance and contributes the returned
# bracket string; unlisted services are added by plain name.
_SERVICE_ADD_CONFIGURATORS: dict[str, Callable[[str], str]] = {
    AnswerKeys.SERVICE_AUTH: _configure_auth_service_add,
}


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

    # Show available services grouped by type, in ServiceType declaration
    # order. Derived from the registry: a new service (or service type) is
    # offered here automatically instead of needing another copy-pasted
    # branch — the hand-written branches this replaced covered only
    # AUTH/AI/PAYMENT/CONTENT, so comms and insights were never offered.
    selected_services: list[str] = []
    first_header = True

    for service_type in ServiceType:
        type_services = get_services_by_type(service_type)
        if not type_services:
            continue

        if not first_header:
            typer.echo()
        typer.echo(f"{t(SERVICE_TYPE_I18N_KEYS[service_type])}:")
        first_header = False

        for service_name, service_spec in type_services.items():
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
            requirement_text = (
                f" (will auto-add: {', '.join(missing_components)})"
                if missing_components
                else ""
            )

            prompt = f"  Add {service_spec.description.lower()}{requirement_text}?"
            if not typer.confirm(prompt, default=True):
                continue

            # Services with an interactive configurator (auth's level prompt)
            # contribute a bracket string; everything else its plain name.
            configure = _SERVICE_ADD_CONFIGURATORS.get(service_name)
            selected_services.append(
                configure(service_name) if configure else service_name
            )

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
        typer.secho(f"  \u2022 {service_name}: {service_spec.description}", fg="cyan")
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
