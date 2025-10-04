#!/usr/bin/env python
import os
import shutil
import subprocess
from pathlib import Path

from jinja2 import Environment

PROJECT_DIRECTORY = os.path.realpath(os.path.curdir)


def remove_file(filepath):
    """Removes a file from the generated project."""
    full_path = os.path.join(PROJECT_DIRECTORY, filepath)
    if os.path.exists(full_path):
        os.remove(full_path)


def remove_dir(dirpath):
    """Removes a directory from the generated project."""
    full_path = os.path.join(PROJECT_DIRECTORY, dirpath)
    if os.path.exists(full_path):
        shutil.rmtree(full_path)


def process_j2_templates():
    """
    Process all .j2 template files in the generated project.
    Renders them with cookiecutter context and removes the .j2 originals.
    Returns list of output files that were created.
    """
    # Cookiecutter context variables - these template strings are processed
    # by cookiecutter before this hook runs, so they contain actual values
    context = {
        "cookiecutter": {
            "project_name": "{{ cookiecutter.project_name }}",
            "project_slug": "{{ cookiecutter.project_slug }}",
            "project_description": "{{ cookiecutter.project_description }}",
            "author_name": "{{ cookiecutter.author_name }}",
            "author_email": "{{ cookiecutter.author_email }}",
            "version": "{{ cookiecutter.version }}",
            "python_version": "{{ cookiecutter.python_version }}",
            "include_redis": "{{ cookiecutter.include_redis }}",
            "include_scheduler": "{{ cookiecutter.include_scheduler }}",
            "include_worker": "{{ cookiecutter.include_worker }}",
            "include_database": "{{ cookiecutter.include_database }}",
            "include_cache": "{{ cookiecutter.include_cache }}",
            "include_auth": "{{ cookiecutter.include_auth }}",
            "include_ai": "{{ cookiecutter.include_ai }}",
        }
    }

    # Find all .j2 files in the project
    project_path = Path(PROJECT_DIRECTORY)
    j2_files = list(project_path.rglob("*.j2"))
    processed_files = []

    for j2_file in j2_files:
        # Read the template content
        with open(j2_file, encoding="utf-8") as f:
            template_content = f.read()

        # Create Jinja2 environment and render the template
        env = Environment()
        template = env.from_string(template_content)
        rendered_content = template.render(context)

        # Write the rendered content to the final file (without .j2 extension)
        output_file = j2_file.with_suffix("")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(rendered_content)

        # Remove the original .j2 file
        j2_file.unlink()

        # Track processed files for later reporting
        processed_files.append(output_file)

        # Ensure file ends with newline
        if not rendered_content.endswith("\n"):
            with open(output_file, "a", encoding="utf-8") as f:
                f.write("\n")

    return processed_files


def setup_project_environment():
    """
    Complete project setup: dependencies, env file, migrations.

    This function automates the entire setup process so users can
    immediately start using their project after generation.
    """
    print("\n🚀 Setting up your project environment...")

    # Step 1: Install dependencies with uv
    try:
        print("📦 Installing dependencies with uv...")
        result = subprocess.run(
            ["uv", "sync"],
            cwd=PROJECT_DIRECTORY,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutes for dependency installation
        )

        if result.returncode == 0:
            print("✅ Dependencies installed successfully")
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

    # Step 2: Copy .env file
    try:
        print("📄 Setting up environment configuration...")
        env_example = Path(PROJECT_DIRECTORY) / ".env.example"
        env_file = Path(PROJECT_DIRECTORY) / ".env"

        if env_example.exists() and not env_file.exists():
            shutil.copy(env_example, env_file)
            print("✅ Environment file created from .env.example")
        elif env_file.exists():
            print("✅ Environment file already exists")
        else:
            print("⚠️  No .env.example file found")

    except Exception as e:
        print(f"⚠️  Environment setup failed: {e}")
        print("💡 Copy .env.example to .env manually")

    # Step 3: Run migrations (if auth service included)
    if "{{ cookiecutter.include_auth }}" == "yes":
        try:
            print("🗃️  Setting up database with auth schema...")

            # Ensure data directory exists
            data_dir = Path(PROJECT_DIRECTORY) / "data"
            data_dir.mkdir(exist_ok=True)

            # Verify alembic config exists before running migration
            alembic_ini_path = Path(PROJECT_DIRECTORY) / "alembic" / "alembic.ini"
            if not alembic_ini_path.exists():
                print(f"⚠️  Alembic config file not found at {alembic_ini_path}")
                print(
                    "💡 Skipping database migration. Please ensure the config file exists and run 'alembic upgrade head' manually."
                )
                return

            # Run alembic migrations using uv run (ensures correct environment)
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
                cwd=PROJECT_DIRECTORY,
                capture_output=True,
                text=True,
                timeout=30,  # Reasonable timeout for initial migration
            )

            if result.returncode == 0:
                print("✅ Database tables created successfully")
            else:
                print("⚠️  Database migration setup failed")
                if result.stderr:
                    print(f"   Error: {result.stderr.strip()}")
                print("💡 Run 'alembic upgrade head' manually after project creation")

        except subprocess.TimeoutExpired:
            print("⚠️  Migration setup timeout - run 'alembic upgrade head' manually")
        except Exception as e:
            print(f"⚠️  Migration setup failed: {e}")
            print("💡 Run 'alembic upgrade head' manually after project creation")

    return True


def run_auto_formatting():
    """
    Auto-format generated code by calling make fix.
    Fixes linting issues and formats code for consistency.
    """
    try:
        print("🎨 Auto-formatting generated code...")

        # Call make fix to auto-format the generated project
        result = subprocess.run(
            ["make", "fix"],
            cwd=PROJECT_DIRECTORY,
            capture_output=True,
            text=True,
            timeout=60,  # Don't hang forever
        )

        if result.returncode == 0:
            print("✅ Code formatting completed successfully")
        else:
            print(
                "⚠️  Some formatting issues detected, but project created successfully"
            )
            print("💡 Run 'make fix' manually to resolve remaining issues")

    except FileNotFoundError:
        print("💡 Run 'make fix' to format code when ready")
    except subprocess.TimeoutExpired:
        print("⚠️  Formatting timeout - run 'make fix' manually when ready")
    except Exception as e:
        print(f"⚠️  Auto-formatting skipped: {e}")
        print("💡 Run 'make fix' manually to format code")
        # Don't fail project generation due to formatting issues


def main():
    """
    Runs the post-generation cleanup to remove files for unselected
    components and process template files.
    """
    # Process .j2 template files first
    processed_files = process_j2_templates()

    # Remove components not selected
    if "{{ cookiecutter.include_scheduler }}" != "yes":
        # Remove scheduler-specific files
        remove_file("app/entrypoints/scheduler.py")
        remove_dir("app/components/scheduler")
        remove_file("tests/components/test_scheduler.py")
        remove_file("docs/components/scheduler.md")
        # Remove scheduler API endpoints (empty when scheduler not included)
        remove_file("app/components/backend/api/scheduler.py")
        remove_file("tests/api/test_scheduler_endpoints.py")
        # Remove scheduler card (should not display when scheduler not included)
        remove_file("app/components/frontend/dashboard/cards/scheduler_card.py")
        # Remove scheduler test files
        remove_file("tests/services/test_scheduled_task_manager.py")
        remove_file("tests/services/test_component_integration.py")
        remove_file("tests/services/test_health_logic.py")

    # Remove scheduler service if scheduler backend is memory
    # The service is only useful when we can persist to a database
    if "{{ cookiecutter.scheduler_backend }}" == "memory":
        remove_dir("app/services/scheduler")
        remove_file("app/cli/tasks.py")
        # Remove scheduler API endpoints (empty when using memory backend)
        remove_file("app/components/backend/api/scheduler.py")
        remove_file("tests/api/test_scheduler_endpoints.py")

    if "{{ cookiecutter.include_worker }}" != "yes":
        # Remove worker-specific files
        remove_dir("app/components/worker")
        remove_file("app/cli/load_test.py")
        remove_file("app/services/load_test.py")
        remove_file("app/services/load_test_models.py")
        remove_file("tests/services/test_load_test_models.py")
        remove_file("tests/services/test_load_test_service.py")
        remove_file("tests/services/test_worker_health_registration.py")
        # Remove worker API endpoints (empty when worker not included)
        remove_file("app/components/backend/api/worker.py")
        remove_file("tests/api/test_worker_endpoints.py")
        # Remove worker card (should not display when worker not included)
        remove_file("app/components/frontend/dashboard/cards/worker_card.py")

    if "{{ cookiecutter.include_database }}" != "yes":
        remove_file("app/core/db.py")

    if "{{ cookiecutter.include_cache }}" != "yes":
        # remove_file("app/services/cache_service.py")
        pass  # Placeholder for cache component

    # Remove services not selected
    if "{{ cookiecutter.include_auth }}" != "yes":
        # Remove auth service files
        remove_dir("app/components/backend/api/auth")
        remove_file("app/models/user.py")
        remove_dir("app/services/auth")
        remove_file("app/core/security.py")
        # Remove auth CLI
        remove_file("app/cli/auth.py")
        # Remove auth-related tests if they exist
        remove_file("tests/api/test_auth_endpoints.py")
        remove_file("tests/services/test_auth_service.py")
        remove_file("tests/services/test_auth_integration.py")
        remove_file("tests/models/test_user.py")

    if "{{ cookiecutter.include_ai }}" != "yes":
        # Remove AI service files
        remove_dir("app/components/backend/api/ai")
        remove_dir("app/services/ai")
        # Remove AI CLI and rendering
        remove_file("app/cli/ai.py")
        remove_file("app/cli/ai_rendering.py")
        remove_file("app/cli/marko_terminal_renderer.py")
        # Remove AI-related tests if they exist
        remove_file("tests/api/test_ai_endpoints.py")
        remove_file("tests/services/test_ai_service.py")
        remove_file("tests/services/test_ai_integration.py")
        remove_file("tests/services/test_conversation_persistence.py")
        remove_file("tests/cli/test_ai_rendering.py")
        remove_file("tests/cli/test_conversation_memory.py")

    # Clean up empty docs/components directory if no components selected
    if (
        "{{ cookiecutter.include_scheduler }}" != "yes"
        and "{{ cookiecutter.include_worker }}" != "yes"
        and "{{ cookiecutter.include_database }}" != "yes"
        and "{{ cookiecutter.include_cache }}" != "yes"
    ):
        remove_dir("docs/components")

    # Remove Alembic directory if auth service not included
    if "{{ cookiecutter.include_auth }}" != "yes":
        remove_dir("alembic")

    # Print only templates that survived cleanup
    for file_path in processed_files:
        if file_path.exists():
            print(f"Processed template: {file_path.name}")

    # Complete project setup: dependencies, env file, migrations
    setup_success = setup_project_environment()

    # Run auto-formatting after all processing is complete
    run_auto_formatting()

    # Print final status and next steps
    print("\n" + "=" * 60)
    if setup_success:
        print("✅ Project ready to run!")
        print("\n📋 Next steps:")
        print(f"   cd {Path(PROJECT_DIRECTORY).name}")
        print("   make server")
        print("\n💡 Your application is fully configured and ready to use!")
    else:
        print("⚠️  Project created with some setup issues")
        print("\n📋 Manual setup required:")
        print(f"   cd {Path(PROJECT_DIRECTORY).name}")
        print("   uv sync")
        print("   cp .env.example .env")
        if "{{ cookiecutter.include_auth }}" == "yes":
            print("   alembic upgrade head")
        print("   make server")
    print("=" * 60)


if __name__ == "__main__":
    main()
