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

# Task configuration constants (following tests/cli/test_utils.py pattern)
POST_GEN_TIMEOUT_INSTALL = 300  # 5 minutes for dependency installation
POST_GEN_TIMEOUT_FORMAT = 60  # 1 minute for code formatting
POST_GEN_TIMEOUT_MIGRATION = 30  # 30 seconds for database migration


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

    # Remove shared component integration tests only when BOTH scheduler AND worker disabled
    if not is_enabled("include_scheduler") and not is_enabled("include_worker"):
        remove_file(project_path, "tests/services/test_component_integration.py")
        remove_file(project_path, "tests/services/test_health_logic.py")

    # Remove database component if not selected
    if not is_enabled("include_database"):
        remove_file(project_path, "app/core/db.py")

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
        print(f"⚠️  Unknown service '{service_name}' - skipping file copy")
        return

    service_files = file_mapping[service_name]
    print(f"📁 Copying {service_name} service files from template...")

    # The template is at: aegis-stack/aegis/templates/copier-aegis-project/{{ project_slug }}/
    # We need to find the template content directory
    template_content = template_path / "{{ project_slug }}"
    if not template_content.exists():
        print(f"⚠️  Template content directory not found: {template_content}")
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
        print(f"✅ Copied {copied_count} {service_name} service files")
    else:
        print(f"⚠️  No {service_name} files copied (may already exist or be templates)")


def install_dependencies(project_path: Path) -> bool:
    """
    Install project dependencies using uv.

    Args:
        project_path: Path to the project directory

    Returns:
        True if installation succeeded, False otherwise
    """
    try:
        print("📦 Installing dependencies with uv...")

        # Unset VIRTUAL_ENV to avoid conflicts with parent project's venv
        env = os.environ.copy()
        env.pop("VIRTUAL_ENV", None)

        result = subprocess.run(
            ["uv", "sync"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=POST_GEN_TIMEOUT_INSTALL,
            env=env,
        )

        if result.returncode == 0:
            print("✅ Dependencies installed successfully")
            return True
        else:
            print("⚠️  Dependency installation failed")
            if result.stderr:
                print(f"   Error: {result.stderr.strip()}")
            print("💡 Run 'uv sync' manually after project creation")
            return False

    except subprocess.TimeoutExpired:
        print("⚠️  Dependency installation timeout - run 'uv sync' manually")
        return False
    except FileNotFoundError:
        print("⚠️  uv not found in PATH")
        print("💡 Install uv first: https://github.com/astral-sh/uv")
        return False
    except Exception as e:
        print(f"⚠️  Dependency installation failed: {e}")
        print("💡 Run 'uv sync' manually after project creation")
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
        print("📄 Setting up environment configuration...")
        env_example = project_path / ".env.example"
        env_file = project_path / ".env"

        if env_example.exists() and not env_file.exists():
            shutil.copy(env_example, env_file)
            print("✅ Environment file created from .env.example")
            return True
        elif env_file.exists():
            print("✅ Environment file already exists")
            return True
        else:
            print("⚠️  No .env.example file found")
            return False

    except Exception as e:
        print(f"⚠️  Environment setup failed: {e}")
        print("💡 Copy .env.example to .env manually")
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
        print("🗃️  Setting up database with auth schema...")

        # Ensure data directory exists
        data_dir = project_path / "data"
        data_dir.mkdir(exist_ok=True)

        # Verify alembic config exists before running migration
        alembic_ini_path = project_path / "alembic" / "alembic.ini"
        if not alembic_ini_path.exists():
            print(f"⚠️  Alembic config file not found at {alembic_ini_path}")
            print(
                "💡 Skipping database migration. Please ensure the config file exists "
                "and run 'alembic upgrade head' manually."
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
            print("✅ Database tables created successfully")
            return True
        else:
            print("⚠️  Database migration setup failed")
            if result.stderr:
                print(f"   Error: {result.stderr.strip()}")
            print("💡 Run 'alembic upgrade head' manually after project creation")
            return False

    except subprocess.TimeoutExpired:
        print("⚠️  Migration setup timeout - run 'alembic upgrade head' manually")
        return False
    except Exception as e:
        print(f"⚠️  Migration setup failed: {e}")
        print("💡 Run 'alembic upgrade head' manually after project creation")
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
        print("🎨 Auto-formatting generated code...")

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
            print("✅ Code formatting completed successfully")
            return True
        else:
            print(
                "⚠️  Some formatting issues detected, but project created successfully"
            )
            print("💡 Run 'make fix' manually to resolve remaining issues")
            return False

    except FileNotFoundError:
        print("💡 Run 'make fix' to format code when ready")
        return False
    except subprocess.TimeoutExpired:
        print("⚠️  Formatting timeout - run 'make fix' manually when ready")
        return False
    except Exception as e:
        print(f"⚠️  Auto-formatting skipped: {e}")
        print("💡 Run 'make fix' manually to format code")
        return False


def run_post_generation_tasks(project_path: Path, include_auth: bool = False) -> bool:
    """
    Run all post-generation tasks for a project.

    This is the main entry point called by both Cookiecutter hooks
    and Copier updaters.

    Args:
        project_path: Path to the generated/updated project
        include_auth: Whether auth service is enabled (triggers migrations)

    Returns:
        True if all critical tasks succeeded, False otherwise

    Note:
        Individual task failures don't stop execution - we try to complete
        as many tasks as possible and report what needs manual intervention.
    """
    print("\n🚀 Setting up your project environment...")

    # Task 1: Install dependencies (critical)
    deps_success = install_dependencies(project_path)

    # Task 2: Setup .env file (non-critical)
    setup_env_file(project_path)

    # Task 3: Run migrations if auth enabled (non-critical)
    run_migrations(project_path, include_auth)

    # Task 4: Format code (non-critical)
    format_code(project_path)

    # Print final status
    print("\n" + "=" * 60)
    if deps_success:
        print("✅ Project ready to run!")
        print("\n📋 Next steps:")
        print(f"   cd {project_path.name}")
        print("   make server")
        print("\n💡 Your application is fully configured and ready to use!")
    else:
        print("⚠️  Project created with some setup issues")
        print("\n📋 Manual setup required:")
        print(f"   cd {project_path.name}")
        print("   uv sync")
        print("   cp .env.example .env")
        if include_auth:
            print("   alembic upgrade head")
        print("   make server")
    print("=" * 60)

    return deps_success
