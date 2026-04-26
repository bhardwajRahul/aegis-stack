"""
Version command implementation.
"""

import typer

from .. import __version__
from ..i18n import t


def version_command() -> None:
    """Show the Aegis Stack CLI version."""
    typer.echo(t("version.info", version=__version__))
