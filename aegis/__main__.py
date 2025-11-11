#!/usr/bin/env python3
"""
Aegis Stack CLI - Main entry point

Usage:
    aegis init PROJECT_NAME
    aegis components
    aegis --help
"""

import typer

from .commands.add import add_command
from .commands.add_service import add_service_command
from .commands.components import components_command
from .commands.init import init_command
from .commands.remove import remove_command
from .commands.services import services_command
from .commands.update import update_command
from .commands.version import version_command
from .core.verbosity import set_verbose

# Create the main Typer application
app = typer.Typer(
    name="aegis",
    help=(
        "🛡️ Aegis Stack - Production-ready Python foundation\n\n"
        "Quick start: uvx aegis-stack init my-project\n\n"
        "Available components: redis, worker, scheduler, scheduler[sqlite], database\n"
        "Backend selection: Use --backend flag or bracket syntax (sqlite only)"
    ),
    epilog=(
        "💡 Try it instantly: uvx aegis-stack init my-project\n"
        "📚 More info: https://lbedner.github.io/aegis-stack/"
    ),
    add_completion=False,
)


@app.callback()
def main(
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose output (show detailed file operations)",
    ),
) -> None:
    """Aegis Stack CLI - Global options and configuration."""
    set_verbose(verbose)


# Register commands
app.command(name="version")(version_command)
app.command(name="components")(components_command)
app.command(name="services")(services_command)
app.command(name="init")(init_command)
app.command(name="add")(add_command)
app.command(name="add-service")(add_service_command)
app.command(name="remove")(remove_command)
app.command(name="update")(update_command)


# This is what runs when you do: aegis
if __name__ == "__main__":
    app()
