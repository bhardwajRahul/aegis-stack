"""
Services command implementation.
"""

import typer

from ..core.services import ServiceType, get_services_by_type


def services_command() -> None:
    """List available services and their dependencies."""

    typer.echo("\nAVAILABLE SERVICES")
    typer.echo("=" * 40)

    # Group services by type
    service_types = [
        (ServiceType.AUTH, "Authentication Services"),
        (ServiceType.PAYMENT, "Payment Services"),
        (ServiceType.AI, "AI & Machine Learning Services"),
        (ServiceType.NOTIFICATION, "Notification Services"),
        (ServiceType.ANALYTICS, "Analytics Services"),
        (ServiceType.STORAGE, "Storage Services"),
    ]

    services_found = False
    for service_type, header in service_types:
        type_services = get_services_by_type(service_type)
        if type_services:
            services_found = True
            typer.echo(f"\n{header}")
            typer.echo("-" * 40)

            for name, spec in type_services.items():
                typer.echo(f"  {name:12} - {spec.description}")
                if spec.required_components:
                    typer.echo(
                        f"               Requires components: {', '.join(spec.required_components)}"
                    )
                if spec.recommended_components:
                    typer.echo(
                        f"               Recommends components: {', '.join(spec.recommended_components)}"
                    )
                if spec.required_services:
                    typer.echo(
                        f"               Requires services: {', '.join(spec.required_services)}"
                    )

    if not services_found:
        typer.echo("  No services available yet.")

    typer.echo("\nUse 'aegis init PROJECT_NAME --services auth' to add services")
