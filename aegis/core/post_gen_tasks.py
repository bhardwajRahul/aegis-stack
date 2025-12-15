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

from aegis.constants import AnswerKeys, ComponentNames, StorageBackends, WorkerBackends

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
        ComponentNames.SCHEDULER: [
            "app/entrypoints/scheduler.py",
            "app/components/scheduler",
            "tests/components/test_scheduler.py",
            "docs/components/scheduler.md",
            "app/components/backend/api/scheduler.py",
            "tests/api/test_scheduler_endpoints.py",
            "app/components/frontend/dashboard/cards/scheduler_card.py",
            "tests/services/test_scheduled_task_manager.py",
        ],
        f"{ComponentNames.SCHEDULER}_persistence": [  # Only for sqlite backend
            "app/services/scheduler",
            "app/cli/tasks.py",
            "app/components/backend/api/scheduler.py",
            "tests/api/test_scheduler_endpoints.py",
            "tests/services/test_scheduled_task_manager.py",
        ],
        ComponentNames.WORKER: [
            "app/components/worker",
            "app/cli/load_test.py",
            "app/services/load_test.py",
            "app/services/load_test_models.py",
            "app/services/load_test_workloads.py",
            "tests/services/test_load_test_models.py",
            "tests/services/test_load_test_service.py",
            "tests/services/test_worker_health_registration.py",
            "app/components/backend/api/worker.py",
            "tests/api/test_worker_endpoints.py",
            "app/components/frontend/dashboard/cards/worker_card.py",
        ],
        ComponentNames.DATABASE: [
            "app/core/db.py",
            "app/components/frontend/dashboard/cards/database_card.py",
            "app/components/frontend/dashboard/modals/database_modal.py",
        ],
        ComponentNames.REDIS: [
            "app/components/frontend/dashboard/cards/redis_card.py",
            "app/components/frontend/dashboard/modals/redis_modal.py",
        ],
        AnswerKeys.SERVICE_AUTH: [
            "app/components/backend/api/auth",
            "app/models/user.py",
            "app/services/auth",
            "app/core/security.py",
            "app/cli/auth.py",
            "tests/api/test_auth_endpoints.py",
            "tests/services/test_auth_service.py",
            "tests/services/test_auth_integration.py",
            "tests/models/test_user.py",
            # Note: alembic is now shared between auth and AI services
            # Frontend dashboard files
            "app/components/frontend/dashboard/cards/auth_card.py",
            "app/components/frontend/dashboard/cards/services_card.py",
            "app/components/frontend/dashboard/modals/auth_modal.py",
        ],
        AnswerKeys.SERVICE_AI: [
            "app/components/backend/api/ai",
            "app/services/ai",
            "app/cli/ai.py",
            "app/cli/ai_rendering.py",
            "app/cli/marko_terminal_renderer.py",
            "app/models/conversation.py",
            "tests/api/test_ai_endpoints.py",
            "tests/services/test_conversation_persistence.py",
            "tests/cli/test_ai_rendering.py",
            "tests/cli/test_conversation_memory.py",
            "tests/services/ai",
            # Frontend dashboard files
            "app/components/frontend/dashboard/cards/ai_card.py",
            "app/components/frontend/dashboard/modals/ai_modal.py",
        ],
        AnswerKeys.SERVICE_COMMS: [
            "app/components/backend/api/comms",
            "app/services/comms",
            "app/cli/comms.py",
            "tests/api/test_comms_endpoints.py",
            "tests/services/comms",
            "docs/services/comms",
            # Frontend dashboard files
            "app/components/frontend/dashboard/cards/comms_card.py",
            "app/components/frontend/dashboard/modals/comms_modal.py",
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
    if not is_enabled(AnswerKeys.SCHEDULER):
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
    scheduler_backend = context.get(
        AnswerKeys.SCHEDULER_BACKEND, StorageBackends.MEMORY
    )
    if scheduler_backend == StorageBackends.MEMORY:
        remove_dir(project_path, "app/services/scheduler")
        remove_file(project_path, "app/cli/tasks.py")
        remove_file(project_path, "app/components/backend/api/scheduler.py")
        remove_file(project_path, "tests/api/test_scheduler_endpoints.py")
        remove_file(project_path, "tests/services/test_scheduled_task_manager.py")

    # Remove worker component if not selected
    if not is_enabled(AnswerKeys.WORKER):
        remove_dir(project_path, "app/components/worker")
        remove_file(project_path, "app/cli/load_test.py")
        remove_file(project_path, "app/services/load_test.py")
        remove_file(project_path, "app/services/load_test_models.py")
        remove_file(project_path, "app/services/load_test_workloads.py")
        remove_file(project_path, "tests/services/test_load_test_models.py")
        remove_file(project_path, "tests/services/test_load_test_service.py")
        remove_file(project_path, "tests/services/test_worker_health_registration.py")
        remove_file(project_path, "app/components/backend/api/worker.py")
        remove_file(project_path, "app/components/backend/api/worker_taskiq.py")
        remove_file(project_path, "tests/api/test_worker_endpoints.py")
        remove_file(
            project_path, "app/components/frontend/dashboard/cards/worker_card.py"
        )
        remove_file(
            project_path, "app/components/frontend/dashboard/modals/worker_modal.py"
        )
    else:
        # Worker is included - clean up backend-specific files
        worker_backend = context.get(AnswerKeys.WORKER_BACKEND, WorkerBackends.ARQ)
        queues_dir = project_path / "app/components/worker/queues"
        worker_dir = project_path / "app/components/worker"
        api_dir = project_path / "app/components/backend/api"

        if queues_dir.exists():
            if worker_backend == WorkerBackends.TASKIQ:
                # Using TaskIQ: rename _taskiq.py files and remove ALL arq files
                # Track which files we rename so we know what to keep
                taskiq_final_names = {"__init__.py"}  # Always keep __init__.py

                for taskiq_file in queues_dir.glob("*_taskiq.py"):
                    final_name = taskiq_file.name.replace("_taskiq.py", ".py")
                    arq_file = taskiq_file.with_name(final_name)
                    if arq_file.exists():
                        arq_file.unlink()
                    taskiq_file.rename(queues_dir / final_name)
                    taskiq_final_names.add(final_name)

                # Remove arq-only files (those without taskiq counterparts)
                for py_file in queues_dir.glob("*.py"):
                    if py_file.name not in taskiq_final_names:
                        py_file.unlink()

                # TaskIQ: Keep pools_taskiq.py, remove pools.py (arq version)
                pools_arq = worker_dir / "pools.py"
                pools_taskiq = worker_dir / "pools_taskiq.py"
                if pools_arq.exists():
                    pools_arq.unlink()
                if pools_taskiq.exists():
                    pools_taskiq.rename(worker_dir / "pools.py")

                # TaskIQ: Keep worker_taskiq.py, remove worker.py (arq version)
                worker_api_arq = api_dir / "worker.py"
                worker_api_taskiq = api_dir / "worker_taskiq.py"
                if worker_api_arq.exists():
                    worker_api_arq.unlink()
                if worker_api_taskiq.exists():
                    worker_api_taskiq.rename(api_dir / "worker.py")

                # TaskIQ: Keep registry_taskiq.py, remove registry.py (arq version)
                registry_arq = worker_dir / "registry.py"
                registry_taskiq = worker_dir / "registry_taskiq.py"
                if registry_arq.exists():
                    registry_arq.unlink()
                if registry_taskiq.exists():
                    registry_taskiq.rename(worker_dir / "registry.py")

                # TaskIQ: Keep load_test_taskiq.py, remove load_test.py (arq version)
                services_dir = project_path / "app/services"
                load_test_arq = services_dir / "load_test.py"
                load_test_taskiq = services_dir / "load_test_taskiq.py"
                if load_test_arq.exists():
                    load_test_arq.unlink()
                if load_test_taskiq.exists():
                    load_test_taskiq.rename(services_dir / "load_test.py")
            else:
                # Using arq (default): remove taskiq versions
                for taskiq_file in queues_dir.glob("*_taskiq.py"):
                    taskiq_file.unlink()

                # arq: Remove TaskIQ pool, API, and registry files
                pools_taskiq = worker_dir / "pools_taskiq.py"
                if pools_taskiq.exists():
                    pools_taskiq.unlink()

                worker_api_taskiq = api_dir / "worker_taskiq.py"
                if worker_api_taskiq.exists():
                    worker_api_taskiq.unlink()

                # arq: Remove TaskIQ registry file
                registry_taskiq = worker_dir / "registry_taskiq.py"
                if registry_taskiq.exists():
                    registry_taskiq.unlink()

                # arq: Remove TaskIQ load_test service
                services_dir = project_path / "app/services"
                load_test_taskiq = services_dir / "load_test_taskiq.py"
                if load_test_taskiq.exists():
                    load_test_taskiq.unlink()

    # Remove shared component integration tests only when BOTH scheduler AND worker disabled
    if not is_enabled(AnswerKeys.SCHEDULER) and not is_enabled(AnswerKeys.WORKER):
        remove_file(project_path, "tests/services/test_component_integration.py")
        remove_file(project_path, "tests/services/test_health_logic.py")

    # Remove database component if not selected
    if not is_enabled(AnswerKeys.DATABASE):
        remove_file(project_path, "app/core/db.py")
        remove_file(
            project_path, "app/components/frontend/dashboard/cards/database_card.py"
        )
        remove_file(
            project_path, "app/components/frontend/dashboard/modals/database_modal.py"
        )

    # Remove redis component dashboard files if not selected
    if not is_enabled(AnswerKeys.REDIS):
        remove_file(
            project_path, "app/components/frontend/dashboard/cards/redis_card.py"
        )
        remove_file(
            project_path, "app/components/frontend/dashboard/modals/redis_modal.py"
        )

    # Remove cache component if not selected
    if not is_enabled(AnswerKeys.CACHE):
        pass  # Placeholder - cache component doesn't exist yet

    # Remove auth service if not selected
    if not is_enabled(AnswerKeys.AUTH):
        remove_dir(project_path, "app/components/backend/api/auth")
        remove_file(project_path, "app/models/user.py")
        remove_dir(project_path, "app/services/auth")
        remove_file(project_path, "app/core/security.py")
        remove_file(project_path, "app/cli/auth.py")
        remove_file(project_path, "tests/api/test_auth_endpoints.py")
        remove_file(project_path, "tests/services/test_auth_service.py")
        remove_file(project_path, "tests/services/test_auth_integration.py")
        remove_file(project_path, "tests/models/test_user.py")
        # Note: alembic removal is handled below based on whether ANY service needs migrations

    # Remove AI service if not selected
    if not is_enabled(AnswerKeys.AI):
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
        # Remove AI conversation SQLModel tables
        remove_file(project_path, "app/models/conversation.py")

    # AI conversation persistence handling
    # When AI backend is memory (or not specified), remove SQLModel tables
    ai_backend = context.get(AnswerKeys.AI_BACKEND, StorageBackends.MEMORY)
    if ai_backend == StorageBackends.MEMORY:
        remove_file(project_path, "app/models/conversation.py")
        # Remove LLM tracking models (only needed with persistence)
        remove_dir(project_path, "app/services/ai/models/llm")
        # Remove LLM fixtures (only needed with persistence)
        remove_file(project_path, "app/services/ai/fixtures/llm_fixtures.py")
        # Remove usage tracking tests (only relevant with persistence)
        remove_file(project_path, "tests/services/ai/test_usage_tracking.py")

    # Remove comms service if not selected
    if not is_enabled(AnswerKeys.COMMS):
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
    if not is_enabled(AnswerKeys.AUTH):
        remove_file(
            project_path, "app/components/frontend/dashboard/cards/auth_card.py"
        )
        remove_file(
            project_path, "app/components/frontend/dashboard/cards/services_card.py"
        )
        remove_file(
            project_path, "app/components/frontend/dashboard/modals/auth_modal.py"
        )

    # Remove Alembic directory only if NO service needs migrations
    # Alembic is needed when: auth is enabled OR (AI is enabled AND backend is NOT memory)
    include_auth = is_enabled(AnswerKeys.AUTH)
    include_ai = is_enabled(AnswerKeys.AI)
    ai_backend = context.get(AnswerKeys.AI_BACKEND, StorageBackends.MEMORY)
    ai_needs_migrations = include_ai and ai_backend != StorageBackends.MEMORY
    needs_migrations = include_auth or ai_needs_migrations

    if not needs_migrations:
        remove_dir(project_path, "alembic")

    # Clean up empty docs/components directory if no components selected
    if (
        not is_enabled(AnswerKeys.SCHEDULER)
        and not is_enabled(AnswerKeys.WORKER)
        and not is_enabled(AnswerKeys.DATABASE)
        and not is_enabled(AnswerKeys.CACHE)
    ):
        remove_dir(project_path, "docs/components")


def _render_jinja_template(src: Path, dst: Path, project_path: Path) -> None:
    """
    Render a Jinja2 template file and write to destination.

    Args:
        src: Path to the .jinja template file
        dst: Path to write the rendered output (without .jinja extension)
        project_path: Path to the project (used to derive template variables)
    """
    from jinja2 import Environment, FileSystemLoader

    # Get project name from project path
    project_slug = project_path.name

    # Set up Jinja2 environment
    env = Environment(
        loader=FileSystemLoader(src.parent),
        keep_trailing_newline=True,
    )

    # Load and render template
    template = env.get_template(src.name)

    # Build context with common variables
    # These match the variables used in copier.yml
    context = {
        "project_slug": project_slug,
        "project_name": project_slug.replace("-", " ").title(),
        # Service flags - assume true since we're copying service files
        "include_auth": True,
        "include_ai": True,
        "include_comms": True,
        # Component flags - check what exists in project
        "include_scheduler": (project_path / "app/components/scheduler").exists(),
        "include_worker": (project_path / "app/components/worker").exists(),
        "include_database": (project_path / "app/core/db.py").exists(),
        "include_cache": (project_path / "app/components/cache").exists(),
        # AI-specific settings (defaults)
        "ai_framework": "anthropic",
        "ai_backend": "sqlite",
        "ai_provider_anthropic": True,
        "ai_provider_openai": False,
    }

    rendered = template.render(**context)

    # Write to destination
    dst.write_text(rendered)


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

        # Check for .jinja version if plain file doesn't exist
        jinja_src = template_content / (rel_path + ".jinja")
        is_jinja_template = False
        if not src.exists() and jinja_src.exists():
            src = jinja_src
            is_jinja_template = True

        # Skip if source doesn't exist (might be conditional on other settings)
        if not src.exists():
            continue

        # Skip if destination already exists (don't overwrite existing customizations)
        if dst.exists():
            continue

        # Create parent directory if needed
        dst.parent.mkdir(parents=True, exist_ok=True)

        # Copy file or directory
        if src.is_dir():
            shutil.copytree(src, dst)
            copied_count += 1
        elif is_jinja_template or src.suffix == ".jinja":
            # Render Jinja2 template
            _render_jinja_template(src, dst, project_path)
            copied_count += 1
        else:
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


def run_migrations(project_path: Path, include_migrations: bool = False) -> bool:
    """
    Run Alembic database migrations if any service requiring migrations is enabled.

    Migrations are needed when:
    - Auth service is enabled
    - AI service is enabled with a persistence backend (not memory)

    Args:
        project_path: Path to the project directory
        include_migrations: Whether any service requiring migrations is enabled

    Returns:
        True if migrations succeeded or not needed, False on error
    """
    if not include_migrations:
        return True  # No migrations needed

    try:
        typer.secho("Setting up database schema...", fg=typer.colors.CYAN)

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


class DependencyInstallationError(Exception):
    """Raised when dependency installation fails during project generation."""

    pass


def seed_llm_fixtures(project_path: Path) -> bool:
    """
    Seed LLM fixtures (vendors, models, pricing) into the database.

    This runs the load_all_llm_fixtures function from the generated project
    to populate the database with initial LLM data.

    Args:
        project_path: Path to the project directory

    Returns:
        True if seeding succeeded, False otherwise
    """
    try:
        typer.secho("Seeding LLM fixtures...", fg=typer.colors.CYAN)

        # Run the seeding script using uv run
        # Unset VIRTUAL_ENV to avoid conflicts with parent project's venv
        env = os.environ.copy()
        env.pop("VIRTUAL_ENV", None)

        # Call the fixture loading function in the generated project
        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                "-c",
                "from app.core.db import SessionLocal; "
                "from app.services.ai.fixtures import load_all_llm_fixtures; "
                "load_all_llm_fixtures(SessionLocal())",
            ],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=POST_GEN_TIMEOUT_MIGRATION,
            env=env,
        )

        if result.returncode == 0:
            typer.secho("LLM fixtures seeded successfully", fg=typer.colors.GREEN)
            return True
        else:
            typer.secho(
                "Warning: LLM fixture seeding failed",
                fg=typer.colors.YELLOW,
            )
            if result.stderr:
                # Show truncated error output
                truncated = result.stderr[:500]
                for line in truncated.split("\n"):
                    typer.echo(f"   {line}")
            typer.secho(
                "You can seed fixtures manually by running the fixture loader",
                dim=True,
            )
            return False

    except subprocess.TimeoutExpired:
        typer.secho(
            "Warning: LLM fixture seeding timeout",
            fg=typer.colors.YELLOW,
        )
        return False
    except Exception as e:
        typer.secho(f"Warning: LLM fixture seeding failed: {e}", fg=typer.colors.YELLOW)
        return False


def run_post_generation_tasks(
    project_path: Path,
    include_migrations: bool = False,
    python_version: str | None = None,
    seed_ai: bool = False,
) -> bool:
    """
    Run all post-generation tasks for a project.

    This is the main entry point called by both Cookiecutter hooks
    and Copier updaters.

    Args:
        project_path: Path to the generated/updated project
        include_migrations: Whether to run Alembic migrations (auth or AI with persistence)
        python_version: Python version to use (e.g., "3.13")
        seed_ai: Whether to seed LLM fixtures (AI service with persistence backend)

    Returns:
        True if all critical tasks succeeded

    Raises:
        DependencyInstallationError: If dependency installation fails.
            This is a hard failure that aborts project generation.

    Note:
        Dependency installation is critical - if it fails, the entire project
        generation fails. Other tasks (env setup, migrations, formatting, seeding) are
        non-critical and won't cause hard failures.
    """
    typer.echo()
    typer.secho(
        "Setting up your project environment...", fg=typer.colors.BLUE, bold=True
    )

    # Task 1: Install dependencies (CRITICAL - fails entire generation if this fails)
    deps_success = install_dependencies(project_path, python_version)

    if not deps_success:
        typer.echo()
        typer.secho(
            "Project generation failed: dependency installation failed",
            fg=typer.colors.RED,
            bold=True,
        )
        typer.echo()
        typer.secho(
            "The generated project files remain in place, but the project is not usable.",
            dim=True,
        )
        typer.secho(
            "Fix the dependency issue (check Python version compatibility) and try again.",
            dim=True,
        )
        raise DependencyInstallationError(
            f"Failed to install dependencies for project at {project_path}"
        )

    # Task 2: Setup .env file (non-critical)
    setup_env_file(project_path)

    # Task 3: Run migrations if needed (non-critical)
    run_migrations(project_path, include_migrations)

    # Task 4: Seed LLM fixtures if AI service with persistence (non-critical)
    if seed_ai:
        seed_llm_fixtures(project_path)

    # Task 5: Format code (non-critical)
    format_code(project_path)

    # Print final status (only reached if deps succeeded)
    typer.echo()
    typer.secho("Project ready to run!", fg=typer.colors.GREEN, bold=True)
    typer.echo()
    typer.secho("Next steps:", fg=typer.colors.CYAN, bold=True)
    typer.echo(f"   cd {project_path.name}")
    typer.echo("   make serve")
    typer.echo()
    typer.secho("Your application is fully configured and ready to use!", dim=True)

    return True
