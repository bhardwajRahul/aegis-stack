"""
Service registry and specifications for Aegis Stack.

This module defines all available services (auth, payment, AI, etc.), their dependencies,
and metadata used for project generation and validation.
"""

from dataclasses import dataclass, field
from enum import Enum


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


# Service registry - single source of truth for all available services
SERVICES: dict[str, ServiceSpec] = {
    "auth": ServiceSpec(
        name="auth",
        type=ServiceType.AUTH,
        description="User authentication and authorization with JWT tokens",
        required_components=["backend", "database"],
        pyproject_deps=[
            "python-jose[cryptography]==3.3.0",
            "passlib[bcrypt]==1.7.4",
            "python-multipart==0.0.9",  # For form data parsing
        ],
        template_files=[
            "app/components/backend/api/auth/",
            "app/models/user.py",
            "app/services/auth/",
            "app/core/security.py",
        ],
    ),
    # Future services will be added here:
    # "payment_stripe": ServiceSpec(...),
    # "notification_email": ServiceSpec(...),
    # "ai_openai": ServiceSpec(...),
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
            errors.append(f"Unknown service: {service_name}")
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
