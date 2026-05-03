"""
Service registry and specifications for Aegis Stack.

This module defines all available services (auth, payment, AI, etc.), their dependencies,
and metadata used for project generation and validation.
"""

from dataclasses import dataclass
from enum import Enum

from ..constants import (
    AIFrameworks,
    AIProviders,
    AuthLevels,
    ComponentNames,
    StorageBackends,
)
from ..i18n import t
from .file_manifest import FileManifest
from .migration_generator import (
    AI_MIGRATION,
    AUTH_MIGRATION,
    AUTH_RBAC_MIGRATION,
    AUTH_TOKENS_MIGRATION,
    INSIGHTS_MIGRATION,
    ORG_MIGRATION,
    PAYMENT_AUTH_LINK_MIGRATION,
    PAYMENT_MIGRATION,
    VOICE_MIGRATION,
)
from .option_spec import OptionMode, OptionSpec
from .plugin_spec import (
    FrontendWidgetWiring,
    PluginKind,
    PluginSpec,
    PluginWiring,
    RouterWiring,
    SymbolWiring,
)


class ServiceType(Enum):
    """Service type classifications."""

    AUTH = "auth"  # Authentication and authorization
    PAYMENT = "payment"  # Payment processing
    AI = "ai"  # AI and ML integrations
    NOTIFICATION = "notification"  # Email, SMS, push notifications
    ANALYTICS = "analytics"  # Usage analytics and metrics
    STORAGE = "storage"  # File storage and CDN


@dataclass(kw_only=True)
class ServiceSpec(PluginSpec):
    """Service-flavoured PluginSpec — back-compat alias for pre-R2 callers.

    Subclasses ``PluginSpec`` and pins ``kind`` to ``SERVICE`` by default, so
    ``ServiceSpec(name=..., type=..., description=...)`` still works without
    naming the kind. R2 of the plugin system refactor; see
    ``aegis/core/plugin_spec.py`` for the unified type.

    ``kw_only=True`` is required: ``PluginSpec`` has a required ``kind`` field
    followed by defaulted fields, and overriding ``kind`` with a default in
    this subclass would otherwise violate the "required field after default"
    dataclass rule. Pre-R2 callers all used keyword construction (verified
    by AST scan), so no real call sites are affected.
    """

    kind: PluginKind = PluginKind.SERVICE


# Service registry - single source of truth for all available services
SERVICES: dict[str, ServiceSpec] = {
    "auth": ServiceSpec(
        name="auth",
        type=ServiceType.AUTH,
        description="User authentication and authorization with JWT tokens",
        required_components=[ComponentNames.BACKEND, ComponentNames.DATABASE],
        # Round 7 wiring: routers + dashboard card/modal. Mirrors what
        # ``app/components/backend/api/routing.py.jinja`` and the
        # ``cards/__init__.py.jinja`` / ``modals/__init__.py.jinja``
        # currently inject via Jinja conditionals on include_auth /
        # include_oauth / include_auth_org. Predicates here read those
        # same flags from the merged options dict (see PluginWiring docs).
        wiring=PluginWiring(
            routers=[
                RouterWiring(
                    module="app.components.backend.api.auth.router",
                    symbol="router",
                    alias="auth_router",
                    prefix="/api/v1",
                ),
                RouterWiring(
                    module="app.components.backend.api.auth.oauth",
                    symbol="router",
                    alias="oauth_router",
                    prefix="/api/v1",
                    when=lambda opts: bool(opts.get("include_oauth")),
                ),
                RouterWiring(
                    module="app.components.backend.api.orgs.router",
                    symbol="router",
                    alias="org_router",
                    prefix="/api/v1",
                    when=lambda opts: bool(opts.get("include_auth_org")),
                ),
            ],
            dashboard_cards=[
                FrontendWidgetWiring(
                    module="app.components.frontend.dashboard.cards.auth_card",
                    symbol="AuthCard",
                    modal_id="auth",
                ),
            ],
            dashboard_modals=[
                FrontendWidgetWiring(
                    module="app.components.frontend.dashboard.modals.auth_modal",
                    symbol="AuthDetailDialog",
                    modal_id="auth",
                ),
            ],
            # FastAPI dependency providers — service-facade deps that
            # take an AsyncSession and return a service instance. These
            # used to live inline in the shared deps.py.jinja behind
            # ``{% if include_auth %}`` blocks. Round 7.x moves them
            # into ``app/services/auth/deps.py.jinja`` (Option-1 refactor),
            # and the shared template just imports them via this list.
            #
            # Org-scoped providers gate on ``include_auth_org`` because
            # the org/membership/invite tables only exist at that auth
            # level.
            deps_providers=[
                SymbolWiring(
                    module="app.services.auth.deps",
                    symbol="get_user_service",
                ),
                SymbolWiring(
                    module="app.services.auth.deps",
                    symbol="get_org_service",
                    when=lambda opts: bool(opts.get("include_auth_org")),
                ),
                SymbolWiring(
                    module="app.services.auth.deps",
                    symbol="get_membership_service",
                    when=lambda opts: bool(opts.get("include_auth_org")),
                ),
                SymbolWiring(
                    module="app.services.auth.deps",
                    symbol="get_invite_service",
                    when=lambda opts: bool(opts.get("include_auth_org")),
                ),
            ],
        ),
        # R4-A: migrations declared on the spec. Pre-R4 these lived in a
        # MIGRATION_SPECS dict literal in migration_generator.py; that dict
        # is now derived from this list (and from the migrations field on
        # the AI / payment / insights specs).
        migrations=[
            AUTH_MIGRATION,
            AUTH_RBAC_MIGRATION,
            ORG_MIGRATION,
            AUTH_TOKENS_MIGRATION,
        ],
        # Bracket-syntax options: auth[level, engine, oauth]
        # e.g. auth[rbac], auth[org,postgres], auth[basic,oauth]
        options=[
            OptionSpec(
                name="level",
                mode=OptionMode.SINGLE,
                choices=list(AuthLevels.ALL),
                default=AuthLevels.BASIC,
            ),
            OptionSpec(
                name="engine",
                mode=OptionMode.SINGLE,
                choices=[StorageBackends.SQLITE, StorageBackends.POSTGRES],
                default=None,
                # Auto-add engine-specific database; service_resolver
                # normalisation drops the plain `database` already in
                # required_components when a bracket variant is added.
                auto_requires=lambda v: [f"{ComponentNames.DATABASE}[{v}]"]
                if v
                else [],
            ),
            OptionSpec(
                name="oauth",
                mode=OptionMode.FLAG,
                choices=["oauth"],
                default=False,
            ),
        ],
        # Mirrors the ``{%- if include_auth %}`` + cross-service blocks in
        # pyproject.toml.jinja. Auth contributes ``alembic`` (auth has
        # migrations) and ``email-validator`` (User.email is EmailStr).
        # Order matches the legacy render for byte-parity.
        pyproject_deps=[
            "python-jose[cryptography]==3.3.0",
            "bcrypt>=4.0.0",
            "python-multipart==0.0.9",
            "alembic==1.16.5",
            "email-validator==2.2.0",
        ],
        template_files=[
            "app/components/backend/api/auth/",
            "app/models/user.py",
            "app/models/org.py",
            "app/services/auth/",
            "app/core/security.py",
        ],
        files=FileManifest(
            # Mirrors cleanup_components() lines 486-499 (auth NOT enabled)
            # PLUS lines 685-692 (auth dashboard cleanup, same condition).
            # alembic removal is cross-spec (line 707-720), stays inline.
            primary=[
                "app/components/backend/api/auth",
                "app/models/user.py",
                "app/services/auth",
                "app/core/security.py",
                "app/cli/auth.py",
                "tests/api/test_auth_endpoints.py",
                "tests/services/test_auth_service.py",
                "tests/services/test_auth_integration.py",
                "tests/models/test_user.py",
                # Goal service is auth-coupled (Goal.user_id FK to user table);
                # cleanup_components removes it on the auth-off path. Note: it
                # is also removed on the insights-off path (kept consistent
                # there too), so duplicate removal is fine — apply_cleanup_path
                # is idempotent on missing files.
                "tests/services/test_goal_service.py",
                # Frontend dashboard files
                "app/components/frontend/dashboard/cards/auth_card.py",
                "app/components/frontend/dashboard/modals/auth_modal.py",
            ],
            # Auth org-level cleanup (cleanup_components lines 503-514) is
            # inline because it gates on "auth enabled AND auth_org off",
            # not just on a single AnswerKey. Move into extras under R2.
        ),
    ),
    "ai": ServiceSpec(
        name="ai",
        type=ServiceType.AI,
        description="AI chatbot service with multi-framework support",
        required_components=[ComponentNames.BACKEND],
        # Round 7 wiring: 4 conditional routers + dashboard card/modal.
        # Predicates read both this plugin's options ("voice", "rag")
        # and broader project state ("ai_backend", "ollama_mode") from
        # the merged opts dict. Mirrors routing.py.jinja lines 21-29 +
        # 65-73.
        wiring=PluginWiring(
            routers=[
                RouterWiring(
                    module="app.components.backend.api.ai.router",
                    symbol="router",
                    alias="ai_router",
                ),
                RouterWiring(
                    module="app.components.backend.api.voice.router",
                    symbol="router",
                    alias="voice_router",
                    prefix="/api/v1",
                    when=lambda opts: bool(opts.get("ai_voice")),
                ),
                RouterWiring(
                    module="app.components.backend.api.llm.router",
                    symbol="router",
                    alias="llm_router",
                    prefix="/api/v1",
                    when=lambda opts: (
                        opts.get("ai_backend") != "memory"
                        and opts.get("ollama_mode") != "none"
                    ),
                ),
                RouterWiring(
                    module="app.components.backend.api.rag.router",
                    symbol="router",
                    alias="rag_router",
                    prefix="/api/v1",
                    when=lambda opts: bool(opts.get("ai_rag")),
                ),
            ],
            dashboard_cards=[
                FrontendWidgetWiring(
                    module="app.components.frontend.dashboard.cards.ai_card",
                    symbol="AICard",
                    modal_id="ai",
                ),
            ],
            dashboard_modals=[
                FrontendWidgetWiring(
                    module="app.components.frontend.dashboard.modals.ai_modal",
                    symbol="AIDetailDialog",
                    modal_id="ai",
                ),
            ],
        ),
        # R4-A: migrations declared on the spec.
        migrations=[AI_MIGRATION, VOICE_MIGRATION],
        # Bracket-syntax options: ai[framework, backend, providers..., flags...]
        # e.g. ai[langchain,sqlite,openai], ai[pydantic-ai,postgres,rag,voice]
        options=[
            OptionSpec(
                name="framework",
                mode=OptionMode.SINGLE,
                choices=list(AIFrameworks.ALL),
                default=AIFrameworks.PYDANTIC_AI,
            ),
            OptionSpec(
                name="backend",
                mode=OptionMode.SINGLE,
                choices=[
                    StorageBackends.MEMORY,
                    StorageBackends.SQLITE,
                    StorageBackends.POSTGRES,
                ],
                default=StorageBackends.MEMORY,
                # Persistence backends auto-add the matching database engine.
                auto_requires=lambda v: [f"{ComponentNames.DATABASE}[{v}]"]
                if v != StorageBackends.MEMORY
                else [],
            ),
            OptionSpec(
                name="providers",
                mode=OptionMode.MULTI,
                choices=sorted(AIProviders.ALL),
                default=list(AIProviders.DEFAULT),
            ),
            OptionSpec(
                name="rag",
                mode=OptionMode.FLAG,
                choices=["rag"],
                default=False,
            ),
            OptionSpec(
                name="voice",
                mode=OptionMode.FLAG,
                choices=["voice"],
                default=False,
            ),
        ],
        pyproject_deps=[
            "{AI_FRAMEWORK_DEPS}",  # Dynamic framework + provider deps
        ],
        template_files=[
            "app/services/ai/",
            "app/cli/ai.py",
            "app/components/backend/api/ai/",
        ],
        files=FileManifest(
            # Mirrors cleanup_components() lines 517-542 (AI NOT enabled).
            # NOTE: the analytics tab, llm catalog tab, and rag tab are NOT
            # in this list — cleanup_components() does not remove them on
            # AI-off (they are removed in other paths: AI memory backend,
            # ollama=none, AI_RAG off respectively). R1 preserves that.
            primary=[
                "app/components/backend/api/ai",
                "app/services/ai",
                "app/cli/ai.py",
                "app/cli/ai_rendering.py",
                "app/cli/marko_terminal_renderer.py",
                "app/cli/chat_completer.py",
                "app/cli/slash_commands.py",
                "app/cli/llm.py",
                "app/cli/status_line.py",
                "app/core/formatting.py",
                "tests/api/test_ai_endpoints.py",
                "tests/services/test_conversation_persistence.py",
                "tests/cli/test_ai_rendering.py",
                "tests/cli/test_conversation_memory.py",
                "tests/cli/test_chat_completer.py",
                "tests/cli/test_llm_cli.py",
                "tests/cli/test_slash_commands.py",
                "tests/cli/test_status_line.py",
                "tests/services/ai",
                "app/components/frontend/dashboard/cards/ai_card.py",
                "app/components/frontend/dashboard/modals/ai_modal.py",
                "app/models/conversation.py",
            ],
            # AI sub-features (ai_rag, ai_voice, AI memory backend, ollama
            # mode) are gated by various AnswerKeys / option values; their
            # cleanup remains inline in cleanup_components for R1.
        ),
    ),
    "comms": ServiceSpec(
        name="comms",
        type=ServiceType.NOTIFICATION,
        description="Communications service with email (Resend), SMS and voice (Twilio)",
        required_components=[ComponentNames.BACKEND],
        # Round 7 wiring: single router + dashboard card/modal.
        wiring=PluginWiring(
            routers=[
                RouterWiring(
                    module="app.components.backend.api.comms.router",
                    symbol="router",
                    alias="comms_router",
                    prefix="/api/v1",
                ),
            ],
            dashboard_cards=[
                FrontendWidgetWiring(
                    module="app.components.frontend.dashboard.cards.comms_card",
                    symbol="CommsCard",
                    modal_id="comms",
                ),
            ],
            dashboard_modals=[
                FrontendWidgetWiring(
                    module="app.components.frontend.dashboard.modals.comms_modal",
                    symbol="CommsDetailDialog",
                    modal_id="comms",
                ),
            ],
        ),
        pyproject_deps=[
            "resend>=2.4.0",
            "twilio>=9.3.7",
            "email-validator==2.2.0",
        ],
        template_files=[
            "app/services/comms/",
            "app/cli/comms.py",
            "app/components/backend/api/comms/",
        ],
        files=FileManifest(
            primary=[
                "app/components/backend/api/comms",
                "app/services/comms",
                "app/cli/comms.py",
                "tests/api/test_comms_endpoints.py",
                "tests/services/comms",
                "docs/services/comms",
                # Frontend dashboard files
                "app/components/frontend/dashboard/cards/comms_card.py",
                "app/components/frontend/dashboard/modals/comms_modal.py",
            ],
        ),
    ),
    "insights": ServiceSpec(
        name="insights",
        type=ServiceType.ANALYTICS,
        description="Adoption metrics and analytics with automated data collection",
        required_components=[
            ComponentNames.BACKEND,
            ComponentNames.DATABASE,
            ComponentNames.SCHEDULER,
        ],
        recommended_components=[ComponentNames.WORKER],
        # Round 7 wiring: insights router lives in api/insights.py (not
        # api/insights/router.py); see routing.py.jinja:34.
        wiring=PluginWiring(
            routers=[
                RouterWiring(
                    module="app.components.backend.api.insights",
                    symbol="router",
                    alias="insights_router",
                    prefix="/api/v1",
                    tags=["insights"],
                ),
            ],
            dashboard_cards=[
                FrontendWidgetWiring(
                    module="app.components.frontend.dashboard.cards.insights_card",
                    symbol="InsightsCard",
                    modal_id="service_insights",
                ),
            ],
            dashboard_modals=[
                FrontendWidgetWiring(
                    module="app.components.frontend.dashboard.modals.insights_modal",
                    symbol="InsightsDetailDialog",
                    modal_id="service_insights",
                ),
            ],
            # FastAPI dependency providers — moved from inline definitions
            # in shared deps.py.jinja into ``app/services/insights/deps.py``.
            deps_providers=[
                SymbolWiring(
                    module="app.services.insights.deps",
                    symbol="get_insight_service",
                ),
                SymbolWiring(
                    module="app.services.insights.deps",
                    symbol="get_collector_service",
                ),
                SymbolWiring(
                    module="app.services.insights.deps",
                    symbol="get_query_service",
                ),
            ],
        ),
        # R4-A: migrations declared on the spec. The insights spec is
        # context-aware — at generation time it rebuilds itself with the
        # per-user variant if ``insights_per_user`` is on.
        migrations=[INSIGHTS_MIGRATION],
        # Bracket-syntax options: insights[sources..., per_user]
        # e.g. insights[github,pypi,plausible,reddit,per_user]
        options=[
            OptionSpec(
                name="sources",
                mode=OptionMode.MULTI,
                choices=["github", "pypi", "plausible", "reddit"],
                default=["github", "pypi"],
            ),
            OptionSpec(
                name="per_user",
                mode=OptionMode.FLAG,
                choices=["per_user"],
                default=False,
            ),
        ],
        pyproject_deps=[
            "httpx>=0.27.0",  # HTTP client for API collectors
        ],
        template_files=[
            "app/services/insights/",
            "app/cli/insights.py",
            "app/components/backend/api/insights/",
        ],
        files=FileManifest(
            # Mirrors cleanup_components() lines 654-683 (insights NOT enabled).
            primary=[
                "app/components/backend/api/insights",
                "app/services/insights",
                "app/components/backend/api/insights.py",
                "app/cli/insights.py",
                "tests/services/test_insights_service.py",
                "tests/services/test_insights_collectors.py",
                "tests/services/test_insight_service.py",
                "tests/services/test_query_service.py",
                "tests/services/test_collector_service.py",
                "tests/services/test_collector_github_traffic.py",
                "tests/services/test_collector_github_events.py",
                "tests/services/test_collector_github_stars.py",
                "tests/services/test_collector_pypi.py",
                "tests/services/test_collector_plausible.py",
                "tests/services/test_collector_reddit.py",
                # Goal service tests — also removed on the auth-off path;
                # double-removal is fine (apply_cleanup_path is idempotent).
                "tests/services/test_goal_service.py",
                "tests/api/test_insights_endpoints.py",
                "tests/test_bulk_response.py",
                "tests/test_cache_integration.py",
                "app/components/frontend/dashboard/cards/insights_card.py",
                "app/components/frontend/dashboard/modals/insights_modal.py",
            ],
        ),
    ),
    "payment": ServiceSpec(
        name="payment",
        type=ServiceType.PAYMENT,
        description="Payment processing with Stripe (checkout, subscriptions, webhooks)",
        required_components=[
            ComponentNames.BACKEND,
            ComponentNames.DATABASE,
        ],
        recommended_components=[ComponentNames.WORKER],
        # Round 7 wiring: 2 routers (API + pages) + dashboard card/modal.
        # Mirrors routing.py.jinja:36-38 + 80-83.
        wiring=PluginWiring(
            routers=[
                RouterWiring(
                    module="app.components.backend.api.payment.router",
                    symbol="router",
                    alias="payment_router",
                    prefix="/api/v1",
                ),
                RouterWiring(
                    module="app.components.backend.api.payment.pages",
                    symbol="router",
                    alias="payment_pages_router",
                ),
            ],
            dashboard_cards=[
                FrontendWidgetWiring(
                    module="app.components.frontend.dashboard.cards.payment_card",
                    symbol="PaymentCard",
                    modal_id="service_payment",
                ),
            ],
            dashboard_modals=[
                FrontendWidgetWiring(
                    module="app.components.frontend.dashboard.modals.payment_modal",
                    symbol="PaymentDetailDialog",
                    modal_id="service_payment",
                ),
            ],
            # FastAPI dependency providers — moved from inline definitions
            # in shared deps.py.jinja into ``app/services/payment/deps.py``.
            deps_providers=[
                SymbolWiring(
                    module="app.services.payment.deps",
                    symbol="get_payment_service",
                ),
            ],
        ),
        # R4-A: migrations declared on the spec.
        migrations=[PAYMENT_MIGRATION, PAYMENT_AUTH_LINK_MIGRATION],
        pyproject_deps=[
            "alembic==1.16.5",
            "stripe>=11.0.0",
        ],
        template_files=[
            "app/services/payment/",
            "app/cli/payment.py",
            "app/components/backend/api/payment/",
        ],
        files=FileManifest(
            primary=[
                "app/components/backend/api/payment",
                "app/services/payment",
                "app/cli/payment.py",
                "tests/services/test_payment_service.py",
                "tests/services/test_payment_models.py",
                "tests/services/test_payment_catalog.py",
                "tests/services/test_payment_webhook_forwarder.py",
                "tests/cli/test_payment_trigger.py",
                "tests/api/test_payment_endpoints.py",
                # Backend lifecycle hooks (auto-forward stripe-cli webhooks in dev)
                "app/components/backend/startup/payment_webhook_forwarder.py",
                "app/components/backend/shutdown/payment_webhook_forwarder.py",
                # Frontend dashboard files
                "app/components/frontend/dashboard/cards/payment_card.py",
                "app/components/frontend/dashboard/modals/payment_modal.py",
            ],
        ),
    ),
}


def get_service(name: str) -> ServiceSpec:
    """Get service specification by name."""
    if name not in SERVICES:
        raise ValueError(f"Unknown service: {name}")
    return SERVICES[name]


def get_services_by_type(service_type: ServiceType) -> dict[str, ServiceSpec]:
    """Get all services of a specific type."""
    return {name: spec for name, spec in SERVICES.items() if spec.type == service_type}


def list_available_services() -> list[str]:
    """Get list of all available service names."""
    return list(SERVICES.keys())


def get_service_dependencies(service_name: str) -> list[str]:
    """
    Get all required components for a service.

    Args:
        service_name: Name of the service

    Returns:
        List of component names required by this service
    """
    if service_name not in SERVICES:
        return []

    service = SERVICES[service_name]
    return service.required_components.copy()


def validate_service_dependencies(
    selected_services: list[str], available_components: list[str]
) -> list[str]:
    """
    Validate that all required components are available for selected services.

    Args:
        selected_services: List of service names to validate
        available_components: List of available component names

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    for service_name in selected_services:
        if service_name not in SERVICES:
            errors.append(t("validation.unknown_service", name=service_name))
            continue

        service = SERVICES[service_name]

        # Check required components
        for required_comp in service.required_components:
            if required_comp not in available_components:
                errors.append(
                    f"Service '{service_name}' requires component '{required_comp}'"
                )

        # Check service conflicts
        if service.conflicts:
            for conflict in service.conflicts:
                if conflict in selected_services:
                    errors.append(
                        f"Service '{service_name}' conflicts with service '{conflict}'"
                    )

    return errors
