#!/usr/bin/env python
import os
import shutil
import sys
from pathlib import Path

from jinja2 import Environment

# Add aegis-stack to path to import shared post-generation tasks
# This hook runs from within the generated project, so we need to go up to aegis-stack root
AEGIS_STACK_ROOT = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(AEGIS_STACK_ROOT))

from aegis.core.migration_generator import (  # noqa: E402
    generate_migrations_for_services,
    get_services_needing_migrations,
)
from aegis.core.post_gen_tasks import run_post_generation_tasks  # noqa: E402

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
            "include_comms": "{{ cookiecutter.include_comms }}",
            "worker_backend": "{{ cookiecutter.worker_backend }}",
            "ai_framework": "{{ cookiecutter.ai_framework }}",
            "ai_backend": "{{ cookiecutter.ai_backend }}",
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
        # Remove scheduler dashboard card and modal
        remove_file("app/components/frontend/dashboard/cards/scheduler_card.py")
        remove_file("app/components/frontend/dashboard/modals/scheduler_modal.py")
        # Remove scheduler-specific test file
        remove_file("tests/services/test_scheduled_task_manager.py")

    # Remove scheduler service if scheduler backend is memory
    # The service is only useful when we can persist to a database
    if "{{ cookiecutter.scheduler_backend }}" == "memory":
        remove_dir("app/services/scheduler")
        remove_file("app/cli/tasks.py")
        # Remove scheduler API endpoints (empty when using memory backend)
        remove_file("app/components/backend/api/scheduler.py")
        remove_file("tests/api/test_scheduler_endpoints.py")
        # Remove task manager test (only exists with persistence)
        remove_file("tests/services/test_scheduled_task_manager.py")

    if "{{ cookiecutter.include_worker }}" != "yes":
        # Remove worker-specific files
        remove_dir("app/components/worker")
        remove_file("app/cli/load_test.py")
        remove_file("app/services/load_test.py")
        remove_file("app/services/load_test_models.py")
        remove_file("app/services/load_test_workloads.py")
        remove_file("tests/services/test_load_test_models.py")
        remove_file("tests/services/test_load_test_service.py")
        remove_file("tests/services/test_worker_health_registration.py")
        # Remove worker API endpoints (empty when worker not included)
        remove_file("app/components/backend/api/worker.py")
        remove_file("app/components/backend/api/worker_taskiq.py")
        remove_file("tests/api/test_worker_endpoints.py")
        # Remove worker dashboard card and modal
        remove_file("app/components/frontend/dashboard/cards/worker_card.py")
        remove_file("app/components/frontend/dashboard/modals/worker_modal.py")
    else:
        # Worker is included - select correct backend files
        queues_dir = os.path.join(PROJECT_DIRECTORY, "app/components/worker/queues")
        worker_dir = os.path.join(PROJECT_DIRECTORY, "app/components/worker")
        api_dir = os.path.join(PROJECT_DIRECTORY, "app/components/backend/api")

        if "{{ cookiecutter.worker_backend }}" == "taskiq":
            # Use taskiq files: rename _taskiq.py and remove ALL arq files
            if os.path.exists(queues_dir):
                # Track which files we rename so we know what to keep
                taskiq_final_names = {"__init__.py"}  # Always keep __init__.py

                # Rename taskiq files to replace arq versions
                for taskiq_file in Path(queues_dir).glob("*_taskiq.py"):
                    final_name = taskiq_file.name.replace("_taskiq.py", ".py")
                    arq_file = taskiq_file.with_name(final_name)
                    # Remove arq version if it exists
                    if arq_file.exists():
                        arq_file.unlink()
                    # Rename taskiq version
                    taskiq_file.rename(Path(queues_dir) / final_name)
                    taskiq_final_names.add(final_name)

                # Remove arq-only files (those without taskiq counterparts)
                for py_file in Path(queues_dir).glob("*.py"):
                    if py_file.name not in taskiq_final_names:
                        py_file.unlink()

            # TaskIQ: Rename pools_taskiq.py -> pools.py, remove arq version
            pools_arq = Path(worker_dir) / "pools.py"
            pools_taskiq = Path(worker_dir) / "pools_taskiq.py"
            if pools_arq.exists():
                pools_arq.unlink()
            if pools_taskiq.exists():
                pools_taskiq.rename(Path(worker_dir) / "pools.py")

            # TaskIQ: Rename worker_taskiq.py -> worker.py, remove arq version
            worker_api_arq = Path(api_dir) / "worker.py"
            worker_api_taskiq = Path(api_dir) / "worker_taskiq.py"
            if worker_api_arq.exists():
                worker_api_arq.unlink()
            if worker_api_taskiq.exists():
                worker_api_taskiq.rename(Path(api_dir) / "worker.py")

            # TaskIQ: Rename registry_taskiq.py -> registry.py, remove arq version
            registry_arq = Path(worker_dir) / "registry.py"
            registry_taskiq = Path(worker_dir) / "registry_taskiq.py"
            if registry_arq.exists():
                registry_arq.unlink()
            if registry_taskiq.exists():
                registry_taskiq.rename(Path(worker_dir) / "registry.py")

            # TaskIQ: Rename load_test_taskiq.py -> load_test.py, remove arq version
            services_dir = os.path.join(PROJECT_DIRECTORY, "app/services")
            load_test_arq = Path(services_dir) / "load_test.py"
            load_test_taskiq = Path(services_dir) / "load_test_taskiq.py"
            if load_test_arq.exists():
                load_test_arq.unlink()
            if load_test_taskiq.exists():
                load_test_taskiq.rename(Path(services_dir) / "load_test.py")
        else:
            # Use arq files (default): remove taskiq versions
            if os.path.exists(queues_dir):
                for taskiq_file in Path(queues_dir).glob("*_taskiq.py"):
                    taskiq_file.unlink()

            # arq: Remove TaskIQ pool and API files
            pools_taskiq = Path(worker_dir) / "pools_taskiq.py"
            if pools_taskiq.exists():
                pools_taskiq.unlink()

            worker_api_taskiq = Path(api_dir) / "worker_taskiq.py"
            if worker_api_taskiq.exists():
                worker_api_taskiq.unlink()

            # arq: Remove TaskIQ registry file
            registry_taskiq = Path(worker_dir) / "registry_taskiq.py"
            if registry_taskiq.exists():
                registry_taskiq.unlink()

            # arq: Remove TaskIQ load_test service
            services_dir = os.path.join(PROJECT_DIRECTORY, "app/services")
            load_test_taskiq = Path(services_dir) / "load_test_taskiq.py"
            if load_test_taskiq.exists():
                load_test_taskiq.unlink()

    # Remove shared component integration tests only when BOTH scheduler AND worker disabled
    if (
        "{{ cookiecutter.include_scheduler }}" != "yes"
        and "{{ cookiecutter.include_worker }}" != "yes"
    ):
        remove_file("tests/services/test_component_integration.py")
        remove_file("tests/services/test_health_logic.py")

    if "{{ cookiecutter.include_database }}" != "yes":
        remove_file("app/core/db.py")
        # Remove database dashboard card and modal
        remove_file("app/components/frontend/dashboard/cards/database_card.py")
        remove_file("app/components/frontend/dashboard/modals/database_modal.py")

    # Remove redis component dashboard files if not selected
    if "{{ cookiecutter.include_redis }}" != "yes":
        remove_file("app/components/frontend/dashboard/cards/redis_card.py")
        remove_file("app/components/frontend/dashboard/modals/redis_modal.py")

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
        # Remove auth dashboard card and modal
        remove_file("app/components/frontend/dashboard/cards/auth_card.py")
        remove_file("app/components/frontend/dashboard/cards/services_card.py")
        remove_file("app/components/frontend/dashboard/modals/auth_modal.py")
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
        # Remove AI dashboard card and modal
        remove_file("app/components/frontend/dashboard/cards/ai_card.py")
        remove_file("app/components/frontend/dashboard/modals/ai_modal.py")
        # Remove AI-related tests if they exist
        remove_file("tests/api/test_ai_endpoints.py")
        remove_file("tests/services/test_conversation_persistence.py")
        remove_file("tests/cli/test_ai_rendering.py")
        remove_file("tests/cli/test_conversation_memory.py")
        # Remove AI test directory (contains test_service.py, test_health.py, etc.)
        remove_dir("tests/services/ai")
        # Remove AI conversation SQLModel tables (only exists for AI service)
        remove_file("app/models/conversation.py")

    # AI conversation persistence handling
    # When AI backend is memory, remove SQLModel tables (not needed)
    if "{{ cookiecutter.ai_backend }}" == "memory":
        remove_file("app/models/conversation.py")
        # Remove LLM tracking models (only needed with persistence)
        remove_dir("app/services/ai/models/llm")
        # Remove LLM fixtures (only needed with persistence)
        remove_file("app/services/ai/fixtures/llm_fixtures.py")
        # Remove usage tracking tests (only relevant with persistence)
        remove_file("tests/services/ai/test_usage_tracking.py")

    if "{{ cookiecutter.include_comms }}" != "yes":
        # Remove comms service files
        remove_dir("app/components/backend/api/comms")
        remove_dir("app/services/comms")
        # Remove comms CLI
        remove_file("app/cli/comms.py")
        # Remove comms dashboard card and modal
        remove_file("app/components/frontend/dashboard/cards/comms_card.py")
        remove_file("app/components/frontend/dashboard/modals/comms_modal.py")
        # Remove comms-related tests if they exist
        remove_file("tests/api/test_comms_endpoints.py")
        remove_dir("tests/services/comms")
        # Remove comms documentation
        remove_dir("docs/services/comms")

    # Clean up empty docs/components directory if no components selected
    if (
        "{{ cookiecutter.include_scheduler }}" != "yes"
        and "{{ cookiecutter.include_worker }}" != "yes"
        and "{{ cookiecutter.include_database }}" != "yes"
        and "{{ cookiecutter.include_cache }}" != "yes"
    ):
        remove_dir("docs/components")

    # Remove Alembic directory only if NO service needs migrations
    # Alembic is needed when: auth is included OR (AI is included AND backend is NOT memory)
    include_auth = "{{ cookiecutter.include_auth }}" == "yes"
    include_ai = "{{ cookiecutter.include_ai }}" == "yes"
    ai_needs_migrations = include_ai and "{{ cookiecutter.ai_backend }}" != "memory"
    needs_migrations = include_auth or ai_needs_migrations
    # AI needs seeding when using persistence backend (same condition as migrations)
    ai_needs_seeding = ai_needs_migrations

    if not needs_migrations:
        remove_dir("alembic")
    else:
        # Generate migrations for services that need them
        context = {
            "include_auth": include_auth,
            "include_ai": include_ai,
            "ai_backend": "{{ cookiecutter.ai_backend }}",
        }
        services = get_services_needing_migrations(context)
        if services:
            project_path = Path(PROJECT_DIRECTORY)
            generated = generate_migrations_for_services(project_path, services)
            for migration_path in generated:
                print(f"Generated migration: {migration_path.name}")

    # Print only templates that survived cleanup
    for file_path in processed_files:
        if file_path.exists():
            print(f"Processed template: {file_path.name}")

    # Complete project setup: dependencies, env file, migrations, formatting, seeding
    # Use shared post-generation tasks module (also used by Copier)
    python_version = "{{ cookiecutter.python_version }}"
    run_post_generation_tasks(
        Path(PROJECT_DIRECTORY),
        include_migrations=needs_migrations,
        python_version=python_version,
        seed_ai=ai_needs_seeding,
    )


if __name__ == "__main__":
    main()
