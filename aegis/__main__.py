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
from .commands.deploy import (
    deploy_command,
    deploy_init_command,
    deploy_logs_command,
    deploy_restart_command,
    deploy_setup_command,
    deploy_shell_command,
    deploy_status_command,
    deploy_stop_command,
)
from .commands.ingress import ingress_enable_command
from .commands.init import init_command
from .commands.remove import remove_command
from .commands.remove_service import remove_service_command
from .commands.services import services_command
from .commands.update import update_command
from .commands.version import version_command
from .core.verbosity import set_verbose

# Create the main Typer application
app = typer.Typer(
    name="aegis",
    help=(
        "Aegis Stack - Production-ready Python foundation\n\n"
        "Quick start: uvx aegis-stack init my-project\n\n"
        "Available components: redis, worker, scheduler, scheduler[sqlite], database\n"
        "Backend selection: Use --backend flag or bracket syntax (sqlite only)"
    ),
    epilog=(
        "Try it instantly: uvx aegis-stack init my-project\n"
        "More info: https://lbedner.github.io/aegis-stack/"
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
app.command(name="remove-service")(remove_service_command)
app.command(name="update")(update_command)

# Ingress commands
app.command(name="ingress-enable")(ingress_enable_command)

# Deploy commands
app.command(name="deploy-init")(deploy_init_command)
app.command(name="deploy-setup")(deploy_setup_command)
app.command(name="deploy")(deploy_command)
app.command(name="deploy-logs")(deploy_logs_command)
app.command(name="deploy-status")(deploy_status_command)
app.command(name="deploy-stop")(deploy_stop_command)
app.command(name="deploy-restart")(deploy_restart_command)
app.command(name="deploy-shell")(deploy_shell_command)


# This is what runs when you do: aegis
if __name__ == "__main__":
    app()
