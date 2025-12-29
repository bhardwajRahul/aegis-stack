"""
Project structure map rendering for post-generation output.
"""

from pathlib import Path

import typer


def _detect_worker_backend(project_path: Path) -> str:
    """Detect the worker backend (arq or taskiq) from project files."""
    worker_dir = project_path / "app" / "components" / "worker"
    if not worker_dir.exists():
        return "worker"

    # Check queues directory for backend-specific imports
    queues_dir = worker_dir / "queues"
    if queues_dir.exists():
        for queue_file in queues_dir.glob("*.py"):
            try:
                content = queue_file.read_text()
                if "from arq" in content or "import arq" in content:
                    return "arq"
                if "from taskiq" in content or "import taskiq" in content:
                    return "taskiq"
            except (OSError, UnicodeDecodeError):
                # Best-effort detection: ignore unreadable or malformed files
                pass

    return "worker"


def _is_highlighted(name: str, highlight: list[str] | None) -> bool:
    """Check if a component/service name should be highlighted as NEW."""
    if not highlight:
        return False
    # Normalize: remove trailing slash, lowercase
    name_clean = name.rstrip("/").lower()
    return any(h.lower() == name_clean for h in highlight)


def _get_uses_marker(name: str, uses: dict[str, list[str]] | None) -> str | None:
    """Get the uses marker for a component if it's used by added services."""
    if not uses:
        return None
    # Normalize name
    name_clean = name.rstrip("/").lower()
    for key, services in uses.items():
        if key.lower() == name_clean:
            return f"({', '.join(services)})"
    return None


def _render_line(
    prefix: str,
    name: str,
    desc: str,
    highlight: list[str] | None,
    uses: dict[str, list[str]] | None = None,
    check_name: str | None = None,
) -> None:
    """Render a tree line with optional NEW or (service) markers."""
    # Use check_name if provided (for mapping component names), otherwise use name
    check = check_name or name.rstrip("/")
    is_new = _is_highlighted(check, highlight)
    uses_marker = _get_uses_marker(check, uses)

    # Pad name for consistent column width
    padded_name = f"{name:<18}"

    # Build the line with consistent 18-char name column
    if is_new:
        typer.secho(f"{prefix}{padded_name}← NEW", fg=typer.colors.GREEN, bold=True)
    elif uses_marker:
        typer.echo(f"{prefix}{padded_name}", nl=False)
        typer.secho(f"← {uses_marker}", fg=typer.colors.CYAN)
    else:
        typer.echo(f"{prefix}{padded_name}← {desc}")


def render_project_map(
    project_path: Path,
    highlight: list[str] | None = None,
    uses: dict[str, list[str]] | None = None,
) -> None:
    """
    Render project structure tree to terminal by detecting what exists.

    Displays a visual tree of the generated project structure, with annotations
    explaining what each directory contains. Only shows directories that were
    actually generated based on component/service selections.

    Args:
        project_path: Path to the generated project root directory.
        highlight: Optional list of component/service names to highlight as NEW.
        uses: Optional dict mapping component names to services that use them.
              Shows "← (service)" for existing dependencies.
    """
    app = project_path / "app"

    # Detect what exists
    has_scheduler = (app / "components" / "scheduler").exists()
    has_worker = (app / "components" / "worker").exists()
    has_auth = (app / "services" / "auth").exists()
    has_ai = (app / "services" / "ai").exists()
    has_comms = (app / "services" / "comms").exists()
    has_models = (app / "models").exists()
    has_cli = (app / "cli").exists()
    has_alembic = (project_path / "alembic").exists()

    project_name = project_path.name

    typer.secho("Project Structure:", fg=typer.colors.CYAN, bold=True)
    typer.echo(f"{project_name}/")

    # app/ section
    typer.echo("├── app/")

    # components/
    typer.echo("│   ├── components/       ← Components")
    _render_line("│   │   ├── ", "backend/", "FastAPI", highlight, uses, "backend")

    # Build component children
    component_children: list[tuple[str, str, str]] = []  # (name, desc, check_name)
    component_children.append(("frontend/", "Flet UI", "frontend"))
    if has_scheduler:
        component_children.append(("scheduler/", "APScheduler", "scheduler"))
    if has_worker:
        worker_backend = _detect_worker_backend(project_path)
        component_children.append(("worker/", worker_backend, "worker"))

    # Render component children
    for i, (name, desc, check_name) in enumerate(component_children):
        is_last = i == len(component_children) - 1
        prefix = "│   │   └── " if is_last else "│   │   ├── "
        _render_line(prefix, name, desc, highlight, uses, check_name)

    # services/ - only show if any services exist
    service_children: list[tuple[str, str, str]] = []  # (name, desc, check_name)
    if has_auth:
        service_children.append(("auth/", "Authentication", "auth"))
    if has_ai:
        service_children.append(("ai/", "AI conversations", "ai"))
    if has_comms:
        service_children.append(("comms/", "Communications", "comms"))

    if service_children:
        typer.echo("│   ├── services/         ← Business logic")
        for i, (name, desc, check_name) in enumerate(service_children):
            is_last = i == len(service_children) - 1
            prefix = "│   │   └── " if is_last else "│   │   ├── "
            _render_line(prefix, name, desc, highlight, uses, check_name)

    # models/ - only show if database component
    if has_models:
        _render_line(
            "│   ├── ", "models/", "Database models", highlight, uses, "database"
        )

    # cli/ - only show if any CLI commands exist
    if has_cli:
        typer.echo("│   ├── cli/               ← CLI commands")

    # entrypoints/ - always present
    typer.echo("│   └── entrypoints/       ← Run targets")

    # Root level directories
    typer.echo("├── tests/                 ← Test suite")

    # alembic/ - only show if migrations
    if has_alembic:
        _render_line("├── ", "alembic/", "Migrations", highlight, uses, "database")

    # docs/ - always present (last item)
    typer.echo("└── docs/                  ← Documentation")
