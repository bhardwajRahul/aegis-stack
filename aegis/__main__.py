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
    deploy_cd_setup_command,
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
from .commands.plugins import plugins_app
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
        help="Output language (de, en, es, fr, ja, ko, ru, zh, zh_Hant). Default: auto-detect from AEGIS_LANG or system locale",
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

# Plugin inspection commands (#769).
# Mounted before R5's plugin-defined sub-apps so its name is "reserved"
# from the perspective of plugin discovery (a plugin called "plugins"
# would collide with this surface). There is intentionally no
# ``plugins install``: putting bytes on disk is ``pip install``;
# project-configuration is ``aegis add`` (#771).
app.add_typer(plugins_app, name="plugins")

# Deploy commands
app.command(name="deploy-init")(deploy_init_command)
app.command(name="deploy-setup")(deploy_setup_command)
app.command(name="deploy-cd-setup")(deploy_cd_setup_command)
app.command(name="deploy")(deploy_command)
app.command(name="deploy-backup")(deploy_backup_command)
app.command(name="deploy-backups")(deploy_backups_command)
app.command(name="deploy-rollback")(deploy_rollback_command)
app.command(name="deploy-logs")(deploy_logs_command)
app.command(name="deploy-status")(deploy_status_command)
app.command(name="deploy-stop")(deploy_stop_command)
app.command(name="deploy-restart")(deploy_restart_command)
app.command(name="deploy-shell")(deploy_shell_command)


# R5: mount plugin-provided sub-apps under `aegis <plugin> ...`.
# Each plugin declares a typer.Typer via the `aegis.plugins.cli` entry
# point group; see aegis/core/plugin_discovery.py. Discovery is
# error-tolerant — a malformed plugin warns to stderr and is skipped,
# so a broken third-party install never breaks the core CLI.
def _mount_plugin_cli_apps(target_app: typer.Typer) -> None:
    """Discover plugin CLI sub-apps and mount them under ``target_app``.

    Pulled out as a function (taking ``target_app`` rather than reading the
    module-level ``app``) so tests can verify the mount path against a
    fresh Typer instance without re-running module import.
    """
    from .core.plugins.discovery import discover_plugin_cli_apps

    reserved = {cmd.name for cmd in target_app.registered_commands if cmd.name}
    reserved.update(grp.name for grp in target_app.registered_groups if grp.name)

    for plugin_name, sub_app in discover_plugin_cli_apps(reserved).items():
        target_app.add_typer(sub_app, name=plugin_name)


_mount_plugin_cli_apps(app)


# This is what runs when you do: aegis
if __name__ == "__main__":
    app()
