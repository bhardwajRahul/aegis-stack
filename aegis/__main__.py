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
    deploy_backup_command,
    deploy_backups_command,
    deploy_command,
    deploy_init_command,
    deploy_logs_command,
    deploy_restart_command,
    deploy_rollback_command,
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
from .i18n import detect_locale, set_locale
from .i18n.locales import AVAILABLE_LOCALES

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
    lang: str | None = typer.Option(
        None,
        "--lang",
        help="Output language (de, en, fr, ja, ko, ru, zh, zh_Hant). Default: auto-detect from AEGIS_LANG or system locale",
        envvar="AEGIS_LANG",
    ),
) -> None:
    """Aegis Stack CLI - Global options and configuration."""
    set_verbose(verbose)
    if lang:
        from .i18n.registry import _normalize_locale

        resolved = _normalize_locale(lang)
        # _normalize_locale falls back to "en" for unknown inputs,
        # so check if the input actually maps to a real locale
        base = lang.lower().replace("-", "_").split(".")[0].split("@")[0]
        if resolved == "en" and not base.startswith("en"):
            typer.secho(
                f"Unsupported language '{lang}'. Available: {', '.join(sorted(AVAILABLE_LOCALES))}",
                fg="red",
                err=True,
            )
            raise typer.Exit(1)
    set_locale(lang if lang else detect_locale())


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
app.command(name="deploy-backup")(deploy_backup_command)
app.command(name="deploy-backups")(deploy_backups_command)
app.command(name="deploy-rollback")(deploy_rollback_command)
app.command(name="deploy-logs")(deploy_logs_command)
app.command(name="deploy-status")(deploy_status_command)
app.command(name="deploy-stop")(deploy_stop_command)
app.command(name="deploy-restart")(deploy_restart_command)
app.command(name="deploy-shell")(deploy_shell_command)


# This is what runs when you do: aegis
if __name__ == "__main__":
    app()
