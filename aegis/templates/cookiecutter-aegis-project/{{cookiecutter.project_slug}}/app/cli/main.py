"""
Main CLI application entry point.

Command-line interface for full-stack management tasks.
"""

import importlib
from typing import TYPE_CHECKING

import typer

from app.cli import health

if TYPE_CHECKING:
    from app.cli import load_test

app = typer.Typer(
    name="full-stack",
    help="full-stack management CLI",
    no_args_is_help=True,
)

# Register sub-commands
app.add_typer(health.app, name="health")

# Conditionally register load-test command if worker components are available
try:
    load_test_module = importlib.import_module("app.cli.load_test")
    app.add_typer(load_test_module.app, name="load-test")
except ImportError:
    # Worker components not available, skip load-test commands
    pass


def main() -> None:
    """Entry point for the CLI application."""
    app()


if __name__ == "__main__":
    main()
