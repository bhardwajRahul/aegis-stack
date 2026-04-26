"""
Components command implementation.
"""

import typer

from ..constants import ComponentNames
from ..core.components import CORE_COMPONENTS, ComponentType, get_components_by_type
from ..i18n import t


def _translated_desc(name: str, fallback: str) -> str:
    """Get translated description for a component, with fallback."""
    comp_key = f"component.{name}"
    result = t(comp_key)
    return result if result != comp_key else fallback


def components_command() -> None:
    """List available components and their dependencies."""

    typer.echo(f"\n{t('components.core_title')}")
    typer.echo("=" * 40)
    for component in CORE_COMPONENTS:
        if component == ComponentNames.BACKEND:
            typer.echo(t("components.backend_desc"))
        elif component == ComponentNames.FRONTEND:
            typer.echo(t("components.frontend_desc"))

    typer.echo(f"\n{t('components.infra_title')}")
    typer.echo("=" * 40)

    infra_components = get_components_by_type(ComponentType.INFRASTRUCTURE)
    for name, spec in infra_components.items():
        desc = _translated_desc(name, spec.description)
        typer.echo(f"  {name:12} - {desc}")
        if spec.requires:
            typer.echo(
                f"               {t('components.requires', deps=', '.join(spec.requires))}"
            )
        if spec.recommends:
            typer.echo(
                f"               {t('components.recommends', deps=', '.join(spec.recommends))}"
            )

    typer.echo(f"\n{t('components.usage_hint')}")
