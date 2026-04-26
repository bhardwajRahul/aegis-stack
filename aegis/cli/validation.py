"""
Validation utilities for CLI commands.

This module provides reusable validation functions used across multiple
CLI commands to reduce code duplication.
"""

from pathlib import Path

import typer

from ..core.copier_manager import is_copier_project
from ..i18n import t


def validate_copier_project(target_path: Path, command_name: str) -> None:
    """
    Validate that a project was generated with Copier.

    Args:
        target_path: Path to the project directory
        command_name: Name of the command for error messages

    Raises:
        typer.Exit: If project is not a Copier project
    """
    if not is_copier_project(target_path):
        typer.secho(
            t("shared.not_copier_project", path=target_path),
            fg="red",
            err=True,
        )
        from ..constants import Messages

        typer.echo(
            f"   {Messages.copier_only_command(command_name)}",
            err=True,
        )
        typer.echo(
            f"   {t('shared.regenerate_hint')}",
            err=True,
        )
        raise typer.Exit(1)


def validate_git_repository(target_path: Path) -> None:
    """
    Validate that a project is in a git repository.

    Args:
        target_path: Path to the project directory

    Raises:
        typer.Exit: If project is not in a git repository
    """
    git_dir = target_path / ".git"
    if not git_dir.exists():
        typer.secho(f"\n{t('shared.git_not_initialized')}", fg="red", err=True)
        typer.echo(f"   {t('shared.git_required')}", err=True)
        typer.echo(f"   {t('shared.git_init_hint')}", err=True)
        typer.echo(f"   {t('shared.git_manual_init')}", err=True)
        raise typer.Exit(1)


def parse_comma_separated_list(value: str, item_type: str = "item") -> list[str]:
    """
    Parse and validate a comma-separated list.

    Args:
        value: Comma-separated string to parse
        item_type: Type name for error messages (e.g., "component", "service")

    Returns:
        List of parsed items

    Raises:
        typer.Exit: If empty item names are found
    """
    items = [item.strip() for item in value.split(",")]

    if any(not item for item in items):
        if item_type == "component":
            typer.secho(t("shared.empty_component"), fg="red", err=True)
        elif item_type == "service":
            typer.secho(t("shared.empty_service"), fg="red", err=True)
        else:
            typer.secho(f"Empty {item_type} name is not allowed", fg="red", err=True)
        raise typer.Exit(1)

    return [item for item in items if item]
