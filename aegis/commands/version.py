"""
Version command implementation.
"""

import typer

from .. import __version__


def version_command() -> None:
    """Show the Aegis Stack CLI version."""
    typer.echo(f"Aegis Stack CLI v{__version__}")
