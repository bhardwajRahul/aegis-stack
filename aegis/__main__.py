#!/usr/bin/env python3
"""
Aegis Stack CLI - Main entry point

Usage:
    aegis init PROJECT_NAME
    aegis components
    aegis --help
"""

import typer

from .commands.components import components_command
from .commands.init import init_command
from .commands.version import version_command

# Create the main Typer application
app = typer.Typer(
    name="aegis",
    help=(
        "🛡️ Aegis Stack - Production-ready Python foundation\n\n"
        "Quick start: uvx aegis-stack init my-project\n\n"
        "Available components: redis, worker, scheduler, scheduler[sqlite], database"
    ),
    epilog=(
        "💡 Try it instantly: uvx aegis-stack init my-project\n"
        "📚 More info: https://lbedner.github.io/aegis-stack/"
    ),
    add_completion=False,
)

# Register commands
app.command(name="version")(version_command)
app.command(name="components")(components_command)
app.command(name="init")(init_command)


# This is what runs when you do: aegis
if __name__ == "__main__":
    app()
