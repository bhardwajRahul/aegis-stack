"""
Validation functions for CLI inputs.

This module contains all validation logic for project names, components,
and other CLI inputs.
"""

import typer


def validate_project_name(project_name: str) -> None:
    """Validate project name and raise typer.Exit if invalid."""
    import re

    # Check for invalid characters (only allow letters, numbers, hyphens,
    # underscores)
    if not re.match(r"^[a-zA-Z0-9_-]+$", project_name):
        typer.secho(
            "Invalid project name. Only letters, numbers, hyphens, and "
            "underscores are allowed.",
            fg="red",
            err=True,
        )
        raise typer.Exit(1)

    # Check for reserved names
    reserved_names = {"aegis", "aegis-stack"}
    if project_name.lower() in reserved_names:
        typer.secho(f"'{project_name}' is a reserved name.", fg="red", err=True)
        raise typer.Exit(1)

    # Check length limit
    if len(project_name) > 50:
        typer.secho(
            "Project name too long. Maximum 50 characters allowed.", fg="red", err=True
        )
        raise typer.Exit(1)
