"""
Components command implementation.
"""

import typer

from ..core.components import CORE_COMPONENTS, ComponentType, get_components_by_type


def components_command() -> None:
    """List available components and their dependencies."""

    typer.echo("\n📦 CORE COMPONENTS")
    typer.echo("=" * 40)
    for component in CORE_COMPONENTS:
        if component == "backend":
            typer.echo("  backend      - FastAPI backend server (always included)")
        elif component == "frontend":
            typer.echo("  frontend     - Flet frontend interface (always included)")

    typer.echo("\n🏗️  INFRASTRUCTURE COMPONENTS")
    typer.echo("=" * 40)

    infra_components = get_components_by_type(ComponentType.INFRASTRUCTURE)
    for name, spec in infra_components.items():
        typer.echo(f"  {name:12} - {spec.description}")
        if spec.requires:
            typer.echo(f"               Requires: {', '.join(spec.requires)}")
        if spec.recommends:
            typer.echo(f"               Recommends: {', '.join(spec.recommends)}")

    typer.echo(
        "\n💡 Use 'aegis init PROJECT_NAME --components redis,worker' "
        "to select components"
    )
