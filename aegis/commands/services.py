"""
Services command implementation.
"""

import typer

from ..core.services import ServiceType, get_services_by_type
from ..i18n import t


def _translated_service_desc(name: str, fallback: str) -> str:
    """Get translated description for a service, with fallback."""
    svc_key = f"service.{name}"
    result = t(svc_key)
    return result if result != svc_key else fallback


# Map ServiceType enum to translation keys
_SERVICE_TYPE_KEYS: dict[ServiceType, str] = {
    ServiceType.AUTH: "services.type_auth",
    ServiceType.PAYMENT: "services.type_payment",
    ServiceType.AI: "services.type_ai",
    ServiceType.NOTIFICATION: "services.type_notification",
    ServiceType.ANALYTICS: "services.type_analytics",
    ServiceType.STORAGE: "services.type_storage",
}


def services_command() -> None:
    """List available services and their dependencies."""

    typer.echo(f"\n{t('services.title')}")
    typer.echo("=" * 40)

    # Group services by type
    service_types = [
        ServiceType.AUTH,
        ServiceType.PAYMENT,
        ServiceType.AI,
        ServiceType.NOTIFICATION,
        ServiceType.ANALYTICS,
        ServiceType.STORAGE,
    ]

    services_found = False
    for service_type in service_types:
        type_services = get_services_by_type(service_type)
        if type_services:
            services_found = True
            header = t(_SERVICE_TYPE_KEYS[service_type])
            typer.echo(f"\n{header}")
            typer.echo("-" * 40)

            for name, spec in type_services.items():
                desc = _translated_service_desc(name, spec.description)
                typer.echo(f"  {name:12} - {desc}")
                if spec.required_components:
                    typer.echo(
                        f"               {t('services.requires_components', deps=', '.join(spec.required_components))}"
                    )
                if spec.recommended_components:
                    typer.echo(
                        f"               {t('services.recommends_components', deps=', '.join(spec.recommended_components))}"
                    )
                if spec.required_services:
                    typer.echo(
                        f"               {t('services.requires_services', deps=', '.join(spec.required_services))}"
                    )

    if not services_found:
        typer.echo(t("services.none_available"))

    typer.echo(f"\n{t('services.usage_hint')}")
