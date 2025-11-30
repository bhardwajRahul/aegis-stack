"""
Shared post-generation tasks for Cookiecutter and Copier.

This module provides common post-generation functionality used by both
template engines to avoid code duplication and ensure consistent behavior.
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import typer

# Task configuration constants (following tests/cli/test_utils.py pattern)
POST_GEN_TIMEOUT_INSTALL = 300  # 5 minutes for dependency installation
POST_GEN_TIMEOUT_FORMAT = 60  # 1 minute for code formatting
POST_GEN_TIMEOUT_MIGRATION = 30  # 30 seconds for database migration
POST_GEN_STDERR_MAX_LINES = 15  # Maximum stderr lines to display


def _truncate_stderr(stderr: str, max_lines: int = POST_GEN_STDERR_MAX_LINES) -> str:
    """
    Truncate stderr output to a reasonable number of lines.

    Args:
        stderr: The stderr output to truncate
        max_lines: Maximum number of lines to show

    Returns:
        Truncated stderr with indication if lines were omitted
    """
    lines = stderr.strip().split("\n")
    if len(lines) <= max_lines:
        return stderr.strip()

    # Show first and last portions
    head_lines = max_lines // 2
    tail_lines = max_lines - head_lines
    omitted = len(lines) - max_lines

    result = lines[:head_lines]
    result.append(f"   ... ({omitted} lines omitted) ...")
    result.extend(lines[-tail_lines:])
    return "\n".join(result)


def get_component_file_mapping() -> dict[str, list[str]]:
    """
    Get mapping of components to their files.

    Returns a dictionary mapping component names to lists of files/directories
    that belong to that component. This is used by both cleanup_components()
    and component_files.py for consistency.

    Returns:
        Dict mapping component names to file paths (relative to project root)
    """
    return {
        "scheduler": [
            "app/entrypoints/scheduler.py",
            "app/components/scheduler",
            "tests/components/test_scheduler.py",
            "docs/components/scheduler.md",
            "app/components/backend/api/scheduler.py",
            "tests/api/test_scheduler_endpoints.py",
            "app/components/frontend/dashboard/cards/scheduler_card.py",
            "tests/services/test_scheduled_task_manager.py",
        ],
        "scheduler_persistence": [  # Only for sqlite backend
            "app/services/scheduler",
            "app/cli/tasks.py",
            "app/components/backend/api/scheduler.py",
            "tests/api/test_scheduler_endpoints.py",
            "tests/services/test_scheduled_task_manager.py",
        ],
        "worker": [
            "app/components/worker",
            "app/cli/load_test.py",
            "app/services/load_test.py",
            "app/services/load_test_models.py",
            "tests/services/test_load_test_models.py",
            "tests/services/test_load_test_service.py",
            "tests/services/test_worker_health_registration.py",
            "app/components/backend/api/worker.py",
            "tests/api/test_worker_endpoints.py",
            "app/components/frontend/dashboard/cards/worker_card.py",
        ],
        "database": [
            "app/core/db.py",
        ],
        "auth": [
            "app/components/backend/api/auth",
            "app/models/user.py",
            "app/services/auth",
            "app/core/security.py",
            "app/cli/auth.py",
            "tests/api/test_auth_endpoints.py",
            "tests/services/test_auth_service.py",
            "tests/services/test_auth_integration.py",
            "tests/models/test_user.py",
            "alembic",
        ],
        "ai": [
            "app/components/backend/api/ai",
            "app/services/ai",
            "app/cli/ai.py",
            "app/cli/ai_rendering.py",
            "app/cli/marko_terminal_renderer.py",
            "tests/api/test_ai_endpoints.py",
            "tests/services/test_conversation_persistence.py",
            "tests/cli/test_ai_rendering.py",
            "tests/cli/test_conversation_memory.py",
            "tests/services/ai",
        ],
    }


def remove_file(project_path: Path, filepath: str) -> None:
    """
    Remove a file from the generated project.

    Args:
        project_path: Path to the project directory
        filepath: Relative path to the file to remove
    """
    full_path = project_path / filepath
    if full_path.exists():
        full_path.unlink()


def remove_dir(project_path: Path, dirpath: str) -> None:
    """
    Remove a directory from the generated project.

    Args:
        project_path: Path to the project directory
        dirpath: Relative path to the directory to remove
    """
    full_path = project_path / dirpath
    if full_path.exists():
        shutil.rmtree(full_path)


def cleanup_components(project_path: Path, context: dict[str, Any]) -> None:
    """
    Remove component files based on component selection.

    This function handles component cleanup for both Cookiecutter and Copier
    template engines, ensuring identical behavior.

    Args:
        project_path: Path to the generated project
        context: Dictionary with component/service flags

    Note:
        Handles both Cookiecutter (string "yes"/"no") and Copier (boolean true/false)
        context values for maximum compatibility.
    """

    # Helper to handle both bool and string values from different template engines
    def is_enabled(key: str) -> bool:
        value = context.get(key)
        return value is True or value == "yes"

    # Remove scheduler component if not selected
    if not is_enabled("include_scheduler"):
        remove_file(project_path, "app/entrypoints/scheduler.py")
        remove_dir(project_path, "app/components/scheduler")
        remove_file(project_path, "tests/components/test_scheduler.py")
        remove_file(project_path, "docs/components/scheduler.md")
        remove_file(project_path, "app/components/backend/api/scheduler.py")
        remove_file(project_path, "tests/api/test_scheduler_endpoints.py")
        remove_file(
            project_path, "app/components/frontend/dashboard/cards/scheduler_card.py"
        )
        remove_file(
            project_path, "app/components/frontend/dashboard/modals/scheduler_modal.py"
        )
        remove_file(project_path, "tests/services/test_scheduled_task_manager.py")

    # Remove scheduler service if using memory backend
    # The service is only useful when we can persist to a database
    scheduler_backend = context.get("scheduler_backend", "memory")
    if scheduler_backend == "memory":
        remove_dir(project_path, "app/services/scheduler")
        remove_file(project_path, "app/cli/tasks.py")
        remove_file(project_path, "app/components/backend/api/scheduler.py")
        remove_file(project_path, "tests/api/test_scheduler_endpoints.py")
        remove_file(project_path, "tests/services/test_scheduled_task_manager.py")

    # Remove worker component if not selected
    if not is_enabled("include_worker"):
        remove_dir(project_path, "app/components/worker")
        remove_file(project_path, "app/cli/load_test.py")
        remove_file(project_path, "app/services/load_test.py")
        remove_file(project_path, "app/services/load_test_models.py")
        remove_file(project_path, "tests/services/test_load_test_models.py")
        remove_file(project_path, "tests/services/test_load_test_service.py")
        remove_file(project_path, "tests/services/test_worker_health_registration.py")
        remove_file(project_path, "app/components/backend/api/worker.py")
        remove_file(project_path, "tests/api/test_worker_endpoints.py")
        remove_file(
            project_path, "app/components/frontend/dashboard/cards/worker_card.py"
        )
        remove_file(
            project_path, "app/components/frontend/dashboard/modals/worker_modal.py"
        )

    # Remove shared component integration tests only when BOTH scheduler AND worker disabled
    if not is_enabled("include_scheduler") and not is_enabled("include_worker"):
        remove_file(project_path, "tests/services/test_component_integration.py")
        remove_file(project_path, "tests/services/test_health_logic.py")

    # Remove database component if not selected
    if not is_enabled("include_database"):
        remove_file(project_path, "app/core/db.py")
        remove_file(
            project_path, "app/components/frontend/dashboard/cards/database_card.py"
        )
        remove_file(
            project_path, "app/components/frontend/dashboard/modals/database_modal.py"
        )

    # Remove redis component dashboard files if not selected
    if not is_enabled("include_redis"):
        remove_file(
            project_path, "app/components/frontend/dashboard/cards/redis_card.py"
        )
        remove_file(
            project_path, "app/components/frontend/dashboard/modals/redis_modal.py"
        )

    # Remove cache component if not selected
    if not is_enabled("include_cache"):
        pass  # Placeholder - cache component doesn't exist yet

    # Remove auth service if not selected
    if not is_enabled("include_auth"):
        remove_dir(project_path, "app/components/backend/api/auth")
        remove_file(project_path, "app/models/user.py")
        remove_dir(project_path, "app/services/auth")
        remove_file(project_path, "app/core/security.py")
        remove_file(project_path, "app/cli/auth.py")
        remove_file(project_path, "tests/api/test_auth_endpoints.py")
        remove_file(project_path, "tests/services/test_auth_service.py")
        remove_file(project_path, "tests/services/test_auth_integration.py")
        remove_file(project_path, "tests/models/test_user.py")
        remove_dir(project_path, "alembic")

    # Remove AI service if not selected
    if not is_enabled("include_ai"):
        remove_dir(project_path, "app/components/backend/api/ai")
        remove_dir(project_path, "app/services/ai")
        remove_file(project_path, "app/cli/ai.py")
        remove_file(project_path, "app/cli/ai_rendering.py")
        remove_file(project_path, "app/cli/marko_terminal_renderer.py")
        remove_file(project_path, "tests/api/test_ai_endpoints.py")
        remove_file(project_path, "tests/services/test_conversation_persistence.py")
        remove_file(project_path, "tests/cli/test_ai_rendering.py")
        remove_file(project_path, "tests/cli/test_conversation_memory.py")
        remove_dir(project_path, "tests/services/ai")
        remove_file(project_path, "app/components/frontend/dashboard/cards/ai_card.py")
        remove_file(
            project_path, "app/components/frontend/dashboard/modals/ai_modal.py"
        )

    # Remove comms service if not selected
    if not is_enabled("include_comms"):
        remove_dir(project_path, "app/components/backend/api/comms")
        remove_dir(project_path, "app/services/comms")
        remove_file(project_path, "app/cli/comms.py")
        remove_file(project_path, "tests/api/test_comms_endpoints.py")
        remove_dir(project_path, "tests/services/comms")
        remove_dir(project_path, "docs/services/comms")
        remove_file(
            project_path, "app/components/frontend/dashboard/cards/comms_card.py"
        )
        remove_file(
            project_path, "app/components/frontend/dashboard/modals/comms_modal.py"
        )

    # Remove auth service dashboard files if not selected
    if not is_enabled("include_auth"):
        remove_file(
            project_path, "app/components/frontend/dashboard/cards/auth_card.py"
        )
        remove_file(
            project_path, "app/components/frontend/dashboard/cards/services_card.py"
        )
        remove_file(
            project_path, "app/components/frontend/dashboard/modals/auth_modal.py"
        )

    # Clean up empty docs/components directory if no components selected
    if (
        not is_enabled("include_scheduler")
        and not is_enabled("include_worker")
        and not is_enabled("include_database")
        and not is_enabled("include_cache")
    ):
        remove_dir(project_path, "docs/components")


def copy_service_files(
    project_path: Path, service_name: str, template_path: Path
) -> None:
    """
    Copy service-specific files from template to project.

    This is needed when services are added post-generation via Copier update.
    Copier can only re-render existing files - it cannot copy new directories
    that were excluded during initial generation.

    Args:
        project_path: Path to the project directory
        service_name: Name of the service ('auth', 'ai', etc.)
        template_path: Path to the Copier template directory

    Note:
        Uses get_component_file_mapping() to know which files belong to each service.
    """
    # Get the file mapping for this service
    file_mapping = get_component_file_mapping()
    if service_name not in file_mapping:
        typer.secho(
            f"Unknown service '{service_name}' - skipping file copy",
            fg=typer.colors.YELLOW,
        )
        return

    service_files = file_mapping[service_name]
    typer.secho(
        f"Copying {service_name} service files from template...", fg=typer.colors.CYAN
    )

    # The template is at: aegis-stack/aegis/templates/copier-aegis-project/{{ project_slug }}/
    # We need to find the template content directory
    template_content = template_path / "{{ project_slug }}"
    if not template_content.exists():
        typer.secho(
            f"Warning: Template content directory not found: {template_content}",
            fg=typer.colors.YELLOW,
        )
        return

    copied_count = 0
    for rel_path in service_files:
        src = template_content / rel_path
        dst = project_path / rel_path

        # Skip if source doesn't exist (might be conditional on other settings)
        if not src.exists():
            continue

        # Create parent directory if needed
        dst.parent.mkdir(parents=True, exist_ok=True)

        # Copy file or directory
        if src.is_dir():
            if dst.exists():
                # Skip if already exists (don't overwrite existing customizations)
                continue
            shutil.copytree(src, dst)
            copied_count += 1
        else:
            # For files, check if .jinja extension (template file)
            if src.suffix == ".jinja":
                # This is a Jinja2 template - we need to render it
                # For now, skip template files (they'll be handled by Copier update)
                continue
            # Copy regular file
            shutil.copy2(src, dst)
            copied_count += 1

    if copied_count > 0:
        typer.secho(
            f"Copied {copied_count} {service_name} service files", fg=typer.colors.GREEN
        )
    else:
        typer.echo(
            f"No {service_name} files copied (may already exist or be templates)"
        )


def install_dependencies(project_path: Path, python_version: str | None = None) -> bool:
    """
    Install project dependencies using uv.

    Args:
        project_path: Path to the project directory
        python_version: Python version for project (currently unused in implementation
                        but required for test mocking and future extensibility)

    Returns:
        True if installation succeeded, False otherwise

    Note:
        We pass --python to uv sync when python_version is specified to ensure
        uv uses the correct Python version and respects the requires-python
        constraint in pyproject.toml. This prevents uv from selecting incompatible
        Python versions (e.g., 3.14 when requires-python = ">=3.11,<3.14").

        When python_version is None, uv sync runs without version constraint,
        allowing uv to auto-detect a compatible Python version.
    """
    try:
        typer.secho("Installing dependencies with uv...", fg=typer.colors.CYAN)

        # Unset VIRTUAL_ENV to avoid conflicts with parent project's venv
        env = os.environ.copy()
        env.pop("VIRTUAL_ENV", None)

        # Build command with optional --python flag to enforce version constraint
        cmd = ["uv", "sync"]
        if python_version:
            cmd.extend(["--python", python_version])

        result = subprocess.run(
            cmd,
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=POST_GEN_TIMEOUT_INSTALL,
            env=env,
        )

        if result.returncode == 0:
            typer.secho("Dependencies installed successfully", fg=typer.colors.GREEN)
            return True
        else:
            typer.secho(
                "Warning: Dependency installation failed", fg=typer.colors.YELLOW
            )
            if result.stderr:
                truncated = _truncate_stderr(result.stderr)
                for line in truncated.split("\n"):
                    typer.echo(f"   {line}")
            typer.secho("Run 'uv sync' manually after project creation", dim=True)
            return False

    except subprocess.TimeoutExpired:
        typer.secho(
            "Warning: Dependency installation timeout - run 'uv sync' manually",
            fg=typer.colors.YELLOW,
        )
        return False
    except FileNotFoundError:
        typer.secho("Warning: uv not found in PATH", fg=typer.colors.YELLOW)
        typer.secho("Install uv first: https://github.com/astral-sh/uv", dim=True)
        return False
    except Exception as e:
        typer.secho(
            f"Warning: Dependency installation failed: {e}", fg=typer.colors.YELLOW
        )
        typer.secho("Run 'uv sync' manually after project creation", dim=True)
        return False


def setup_env_file(project_path: Path) -> bool:
    """
    Copy .env.example to .env if .env doesn't exist.

    Args:
        project_path: Path to the project directory

    Returns:
        True if setup succeeded or .env already exists, False on error
    """
    try:
        typer.secho("Setting up environment configuration...", fg=typer.colors.CYAN)
        env_example = project_path / ".env.example"
        env_file = project_path / ".env"

        if env_example.exists() and not env_file.exists():
            shutil.copy(env_example, env_file)
            typer.secho(
                "Environment file created from .env.example", fg=typer.colors.GREEN
            )
            return True
        elif env_file.exists():
            typer.echo("Environment file already exists")
            return True
        else:
            typer.secho("Warning: No .env.example file found", fg=typer.colors.YELLOW)
            return False

    except Exception as e:
        typer.secho(f"Warning: Environment setup failed: {e}", fg=typer.colors.YELLOW)
        typer.secho("Copy .env.example to .env manually", dim=True)
        return False


def run_migrations(project_path: Path, include_auth: bool = False) -> bool:
    """
    Run Alembic database migrations if auth service is enabled.

    Args:
        project_path: Path to the project directory
        include_auth: Whether auth service is enabled

    Returns:
        True if migrations succeeded or not needed, False on error
    """
    if not include_auth:
        return True  # No migrations needed

    try:
        typer.secho("Setting up database with auth schema...", fg=typer.colors.CYAN)

        # Ensure data directory exists
        data_dir = project_path / "data"
        data_dir.mkdir(exist_ok=True)

        # Verify alembic config exists before running migration
        alembic_ini_path = project_path / "alembic" / "alembic.ini"
        if not alembic_ini_path.exists():
            typer.secho(
                f"Warning: Alembic config file not found at {alembic_ini_path}",
                fg=typer.colors.YELLOW,
            )
            typer.secho(
                "Skipping database migration. Please ensure the config file exists "
                "and run 'alembic upgrade head' manually.",
                dim=True,
            )
            return False

        # Run alembic migrations using uv run (ensures correct environment)
        # Unset VIRTUAL_ENV to avoid conflicts with parent project's venv
        env = os.environ.copy()
        env.pop("VIRTUAL_ENV", None)

        result = subprocess.run(
            [
                "uv",
                "run",
                "alembic",
                "-c",
                str(alembic_ini_path),
                "upgrade",
                "head",
            ],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=POST_GEN_TIMEOUT_MIGRATION,
            env=env,
        )

        if result.returncode == 0:
            typer.secho("Database tables created successfully", fg=typer.colors.GREEN)
            return True
        else:
            typer.secho(
                "Warning: Database migration setup failed", fg=typer.colors.YELLOW
            )
            if result.stderr:
                truncated = _truncate_stderr(result.stderr)
                for line in truncated.split("\n"):
                    typer.echo(f"   {line}")
            typer.secho(
                "Run 'alembic upgrade head' manually after project creation", dim=True
            )
            return False

    except subprocess.TimeoutExpired:
        typer.secho(
            "Warning: Migration setup timeout - run 'alembic upgrade head' manually",
            fg=typer.colors.YELLOW,
        )
        return False
    except Exception as e:
        typer.secho(f"Warning: Migration setup failed: {e}", fg=typer.colors.YELLOW)
        typer.secho(
            "Run 'alembic upgrade head' manually after project creation", dim=True
        )
        return False


def format_code(project_path: Path) -> bool:
    """
    Auto-format generated code using make fix.

    Args:
        project_path: Path to the project directory

    Returns:
        True if formatting succeeded, False otherwise
    """
    try:
        typer.secho("Auto-formatting generated code...", fg=typer.colors.CYAN)

        # Call make fix to auto-format the generated project
        # Unset VIRTUAL_ENV to avoid conflicts with parent project's venv
        env = os.environ.copy()
        env.pop("VIRTUAL_ENV", None)

        result = subprocess.run(
            ["make", "fix"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=POST_GEN_TIMEOUT_FORMAT,
            env=env,
        )

        if result.returncode == 0:
            typer.secho("Code formatting completed successfully", fg=typer.colors.GREEN)
            return True
        else:
            typer.secho(
                "Some formatting issues detected, but project created successfully",
                fg=typer.colors.YELLOW,
            )
            typer.secho("Run 'make fix' manually to resolve remaining issues", dim=True)
            return False

    except FileNotFoundError:
        typer.secho("Run 'make fix' to format code when ready", dim=True)
        return False
    except subprocess.TimeoutExpired:
        typer.secho(
            "Warning: Formatting timeout - run 'make fix' manually when ready",
            fg=typer.colors.YELLOW,
        )
        return False
    except Exception as e:
        typer.secho(f"Warning: Auto-formatting skipped: {e}", fg=typer.colors.YELLOW)
        typer.secho("Run 'make fix' manually to format code", dim=True)
        return False


def run_post_generation_tasks(
    project_path: Path, include_auth: bool = False, python_version: str | None = None
) -> bool:
    """
    Run all post-generation tasks for a project.

    This is the main entry point called by both Cookiecutter hooks
    and Copier updaters.

    Args:
        project_path: Path to the generated/updated project
        include_auth: Whether auth service is enabled (triggers migrations)
        python_version: Python version to use (e.g., "3.13")

    Returns:
        True if all critical tasks succeeded, False otherwise

    Note:
        Individual task failures don't stop execution - we try to complete
        as many tasks as possible and report what needs manual intervention.
    """
    typer.echo()
    typer.secho(
        "Setting up your project environment...", fg=typer.colors.BLUE, bold=True
    )

    # Task 1: Install dependencies (critical)
    deps_success = install_dependencies(project_path, python_version)

    # Task 2: Setup .env file (non-critical)
    setup_env_file(project_path)

    # Task 3: Run migrations if auth enabled (non-critical)
    run_migrations(project_path, include_auth)

    # Task 4: Format code (non-critical)
    format_code(project_path)

    # Print final status
    typer.echo()
    if deps_success:
        typer.secho("Project ready to run!", fg=typer.colors.GREEN, bold=True)
        typer.echo()
        typer.secho("Next steps:", fg=typer.colors.CYAN, bold=True)
        typer.echo(f"   cd {project_path.name}")
        typer.echo("   make serve")
        typer.echo()
        typer.secho("Your application is fully configured and ready to use!", dim=True)
    else:
        typer.secho(
            "Project created with some setup issues", fg=typer.colors.YELLOW, bold=True
        )
        typer.echo()
        typer.secho("Manual setup required:", fg=typer.colors.CYAN, bold=True)
        typer.echo(f"   cd {project_path.name}")
        typer.echo("   uv sync")
        typer.echo("   cp .env.example .env")
        if include_auth:
            typer.echo("   alembic upgrade head")
        typer.echo("   make serve")

    return deps_success
