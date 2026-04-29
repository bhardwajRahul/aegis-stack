"""
Service registry and specifications for Aegis Stack.

This module defines all available services (auth, payment, AI, etc.), their dependencies,
and metadata used for project generation and validation.
"""

from dataclasses import dataclass, field
from enum import Enum

from ..constants import ComponentNames
from ..i18n import t
from .file_manifest import FileManifest


class ServiceType(Enum):
    """Service type classifications."""

    AUTH = "auth"  # Authentication and authorization
    PAYMENT = "payment"  # Payment processing
    AI = "ai"  # AI and ML integrations
    NOTIFICATION = "notification"  # Email, SMS, push notifications
    ANALYTICS = "analytics"  # Usage analytics and metrics
    STORAGE = "storage"  # File storage and CDN


@dataclass
class ServiceSpec:
    """Specification for a single service."""

    name: str
    type: ServiceType
    description: str
    required_components: list[str] = field(
        default_factory=list
    )  # Components this service needs
    recommended_components: list[str] = field(
        default_factory=list
    )  # Soft component dependencies
    required_services: list[str] = field(
        default_factory=list
    )  # Other services this service needs
    conflicts: list[str] = field(default_factory=list)  # Mutual exclusions
    pyproject_deps: list[str] = field(
        default_factory=list
    )  # Python packages for this service
    template_files: list[str] = field(default_factory=list)  # Template files to include
    # R1 file manifest used by cleanup_components(). The legacy
    # post_gen_tasks.get_component_file_mapping() dict is still maintained
    # separately, so this manifest must be kept aligned with it by hand
    # until R2 derives the mapping from manifests. See file_manifest.py.
    files: FileManifest = field(default_factory=FileManifest)


# Service registry - single source of truth for all available services
SERVICES: dict[str, ServiceSpec] = {
    "auth": ServiceSpec(
        name="auth",
        type=ServiceType.AUTH,
        description="User authentication and authorization with JWT tokens",
        required_components=[ComponentNames.BACKEND, ComponentNames.DATABASE],
        pyproject_deps=[
            "python-jose[cryptography]==3.3.0",
            "passlib[bcrypt]==1.7.4",
            "python-multipart==0.0.9",  # For form data parsing
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
        pyproject_deps=[
            "resend>=2.4.0",  # Email provider
            "twilio>=9.3.7",  # SMS/Voice provider
            # Note: email-validator is shared with auth service, handled in pyproject.toml.jinja
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
        pyproject_deps=[
            "stripe>=11.0.0",  # Stripe Python SDK
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
