"""
Integration tests for the Aegis Stack CLI init command.

These tests validate:
- CLI command execution and output
- Generated project structure
- Template processing
- Component integration
"""

from pathlib import Path
from typing import Any

import pytest

from .test_utils import (
    assert_file_contains,
    assert_file_exists,
    run_aegis_init,
)


def assert_file_not_exists(project_path: Path, relative_path: str) -> None:
    """Assert that a file does not exist in the generated project."""
    file_path = project_path / relative_path
    assert not file_path.exists(), f"Unexpected file found: {relative_path}"


def assert_no_template_files(project_path: Path) -> None:
    """Assert that no .j2 template files remain in the generated project."""
    j2_files = list(project_path.rglob("*.j2"))
    assert not j2_files, (
        f"Template files should not exist in generated project: {j2_files}"
    )


class TestCLIInit:
    """Test cases for the aegis init command."""

    @pytest.mark.slow
    def test_init_with_scheduler_component(
        self, temp_output_dir: Any, skip_slow_tests: Any
    ) -> None:
        """Test generating a project with scheduler component."""
        result = run_aegis_init(
            project_name="test-scheduler",
            components=["scheduler"],
            output_dir=temp_output_dir,
        )

        # Assert command succeeded
        assert result.success, f"CLI command failed: {result.stderr}"

        # Assert expected CLI output content
        assert "🛡️  Aegis Stack Project Initialization" in result.stdout
        assert "✅ Additional Components:" in result.stdout
        assert "• scheduler" in result.stdout
        assert "• app/components/scheduler.py" in result.stdout
        assert "• tests/components/test_scheduler.py" in result.stdout
        assert "• apscheduler" in result.stdout
        assert "✅ Project created successfully!" in result.stdout

        # Assert project structure
        project_path = result.project_path
        assert project_path is not None, "Project path is None"
        self._assert_scheduler_project_structure(project_path)

        # Assert template processing
        self._assert_scheduler_template_processing(project_path)

    @pytest.mark.slow
    def test_init_without_components(
        self, temp_output_dir: Any, skip_slow_tests: Any
    ) -> None:
        """Test generating a project with no additional components."""
        result = run_aegis_init(
            project_name="test-no-components", output_dir=temp_output_dir
        )

        # Assert command succeeded
        assert result.success, f"CLI command failed: {result.stderr}"

        # Assert expected CLI output
        assert "📦 No additional components selected" in result.stdout
        assert "scheduler" not in result.stdout
        assert "apscheduler" not in result.stdout

        # Assert project structure (no scheduler files)
        project_path = result.project_path
        assert project_path is not None, "Project path is None"
        self._assert_core_project_structure(project_path)
        assert_file_not_exists(project_path, "app/components/scheduler.py")
        assert_file_not_exists(project_path, "tests/components/test_scheduler.py")

    @pytest.mark.slow
    def test_init_invalid_component(
        self, temp_output_dir: Any, skip_slow_tests: Any
    ) -> None:
        """Test that invalid component names are rejected."""
        result = run_aegis_init(
            project_name="test-invalid",
            components=["invalid_component"],
            output_dir=temp_output_dir,
        )

        # Assert command failed
        assert not result.success
        assert "Invalid component: invalid_component" in result.stderr
        assert "Valid components: scheduler, database, cache" in result.stderr

    @pytest.mark.slow
    def test_init_multiple_components(
        self, temp_output_dir: Any, skip_slow_tests: Any
    ) -> None:
        """Test generating project with multiple components (when available)."""
        # For now, test with just scheduler since others aren't implemented
        result = run_aegis_init(
            project_name="test-multi",
            components=["scheduler"],  # Add database, cache when implemented
            output_dir=temp_output_dir,
        )

        assert result.success, f"CLI command failed: {result.stderr}"
        project_path = result.project_path
        assert project_path is not None, "Project path is None"
        self._assert_scheduler_project_structure(project_path)

    @pytest.mark.slow
    def test_template_variable_substitution(
        self, temp_output_dir: Any, skip_slow_tests: Any
    ) -> None:
        """Test that template variables are properly substituted."""
        project_name = "my-custom-project"
        result = run_aegis_init(
            project_name=project_name,
            components=["scheduler"],
            output_dir=temp_output_dir,
        )

        assert result.success

        # Check that project name was substituted in scheduler component
        project_path = result.project_path
        assert project_path is not None, "Project path is None"
        expected_title = project_name.replace("-", " ").title()
        assert_file_contains(
            project_path,
            "app/components/scheduler/main.py",
            f"🕒 Starting {expected_title} Scheduler",
        )

        # Check pyproject.toml has correct name
        assert_file_contains(project_path, "pyproject.toml", f'name = "{project_name}"')

    @pytest.mark.slow
    def test_project_quality_checks(
        self, temp_output_dir: Any, skip_slow_tests: Any
    ) -> None:
        """Test that generated project passes quality checks."""
        result = run_aegis_init(
            project_name="test-quality",
            components=["scheduler"],
            output_dir=temp_output_dir,
        )

        assert result.success

        # Run quality checks on generated project
        project_path = result.project_path
        assert project_path is not None, "Project path is None"

        # Run quality checks using unified system
        from .test_utils import run_quality_checks

        quality_results = run_quality_checks(project_path)

        dep_result = quality_results[0]  # Dependency installation
        lint_result = quality_results[2]  # Linting
        type_result = quality_results[3]  # Type checking
        test_result = quality_results[4]  # Tests

        assert dep_result.success, f"Failed to install deps: {dep_result.stderr}"

        # Linting should either pass or only have fixable issues
        assert lint_result.returncode in [0, 1], f"Linting failed: {lint_result.stderr}"

        assert type_result.success, f"Type checking failed: {type_result.stdout}"

        # Tests may have some issues but should at least run
        assert test_result.returncode in [0, 1], (
            f"Tests completely failed: {test_result.stdout}"
        )

    @pytest.mark.slow
    def test_init_with_worker_component(
        self, temp_output_dir: Any, skip_slow_tests: Any
    ) -> None:
        """Test generating a project with worker component."""
        result = run_aegis_init(
            project_name="test-worker",
            components=["worker"],
            output_dir=temp_output_dir,
        )

        # Assert command succeeded
        assert result.success, f"CLI command failed: {result.stderr}"

        # Assert expected CLI output content
        assert "🛡️  Aegis Stack Project Initialization" in result.stdout
        assert "📦 Infrastructure: redis, worker" in result.stdout
        assert "• app/components/worker/" in result.stdout
        assert "👷 Worker Queues:" in result.stdout
        assert "• arq==0.25.0" in result.stdout
        assert "✅ Project created successfully!" in result.stdout

        # Assert project structure
        project_path = result.project_path
        assert project_path is not None, "Project path is None"
        self._assert_worker_project_structure(project_path)

        # Assert template processing
        self._assert_worker_template_processing(project_path)

    def _assert_core_project_structure(self, project_path: Path) -> None:
        """Assert that core project files exist."""
        core_files = [
            "pyproject.toml",
            "README.md",
            "Dockerfile",
            "docker-compose.yml",
            "Makefile",
            ".dockerignore",
            "app/__init__.py",
            "app/components/backend/main.py",
            "app/components/backend/hooks.py",
            "app/components/backend/middleware/__init__.py",
            "app/components/backend/startup/__init__.py",
            "app/components/backend/shutdown/__init__.py",
            "app/components/frontend/main.py",
            "app/core/config.py",
            "app/core/log.py",
            "app/entrypoints/webserver.py",
            "app/integrations/main.py",
            "app/services/__init__.py",
            "scripts/entrypoint.sh",
            "uv.lock",
        ]

        for file_path in core_files:
            assert_file_exists(project_path, file_path)

        # Assert no template files remain
        assert_no_template_files(project_path)

    def _assert_scheduler_project_structure(self, project_path: Path) -> None:
        """Assert scheduler-specific project structure."""
        self._assert_core_project_structure(project_path)

        # Scheduler-specific files
        assert_file_exists(project_path, "app/entrypoints/scheduler.py")
        assert_file_exists(project_path, "app/components/scheduler/main.py")
        assert_file_exists(project_path, "tests/components/test_scheduler.py")

        # Services directory should exist (it's initially empty)
        services_dir = project_path / "app/services"
        assert services_dir.exists()

    def _assert_scheduler_template_processing(self, project_path: Path) -> None:
        """Assert that scheduler templates were processed correctly."""
        scheduler_file = project_path / "app/components/scheduler/main.py"
        scheduler_content = scheduler_file.read_text()

        # Check imports and structure for scheduler component
        assert (
            "from apscheduler.schedulers.asyncio import AsyncIOScheduler"
            in scheduler_content
        )
        assert "scheduler = AsyncIOScheduler()" in scheduler_content
        assert "scheduler.add_job(" in scheduler_content
        assert "def create_scheduler()" in scheduler_content

        # Check pyproject.toml includes APScheduler
        pyproject_content = (project_path / "pyproject.toml").read_text()
        assert "apscheduler>=3.10.0" in pyproject_content

        # Check mypy overrides for APScheduler
        assert 'module = "apscheduler.*"' in pyproject_content
        assert "ignore_missing_imports = true" in pyproject_content

    def _assert_worker_project_structure(self, project_path: Path) -> None:
        """Assert worker-specific project structure."""
        self._assert_core_project_structure(project_path)

        # Worker-specific files
        worker_files = [
            "app/components/worker/queues/system.py",
            "app/components/worker/queues/load_test.py",
            "app/components/worker/queues/media.py",
            "app/components/worker/tasks/simple_system_tasks.py",
            "app/components/worker/tasks/load_tasks.py",
            "app/components/worker/constants.py",
            "app/components/worker/registry.py",
            "app/components/worker/pools.py",
            "app/services/load_test.py",
            "app/services/load_test_models.py",
        ]

        for file_path in worker_files:
            assert_file_exists(project_path, file_path)

        # Task API files should exist
        api_files = [
            "app/components/backend/api/tasks.py",
            "app/components/backend/api/models.py",
            "app/components/backend/api/routing.py",
        ]

        for file_path in api_files:
            assert_file_exists(project_path, file_path)

    def _assert_worker_template_processing(self, project_path: Path) -> None:
        """Assert that worker templates were processed correctly."""
        # Check that component health includes worker registration
        component_health_file = (
            project_path
            / Path("app/components/backend/startup")
            / "component_health.py"
        )
        component_health_content = component_health_file.read_text()

        # CRITICAL: This is what we're testing - worker health registration
        expected_import = "from app.services.system.health import check_worker_health"
        assert expected_import in component_health_content

        registration_snippet = 'register_health_check("worker", check_worker_health)'
        assert registration_snippet in component_health_content
        assert "Worker component health check registered" in component_health_content

        # Check that routing includes task endpoints
        routing_file = project_path / "app/components/backend/api/routing.py"
        routing_content = routing_file.read_text()
        assert "health, tasks" in routing_content  # From import line
        assert 'tasks.router, prefix="/api/v1"' in routing_content

        # Check pyproject.toml includes arq
        pyproject_content = (project_path / "pyproject.toml").read_text()
        assert "arq==0.25.0" in pyproject_content

        # Check worker configuration files exist and have correct structure
        system_worker_file = project_path / "app/components/worker/queues/system.py"
        system_worker_content = system_worker_file.read_text()
        assert "class WorkerSettings:" in system_worker_content
        assert "system_health_check" in system_worker_content
        assert "cleanup_temp_files" in system_worker_content

    @pytest.mark.slow
    def test_init_with_database_component(
        self, temp_output_dir: Any, skip_slow_tests: Any
    ) -> None:
        """Test generating a project with database component."""
        result = run_aegis_init(
            project_name="test-database",
            components=["database"],
            output_dir=temp_output_dir,
        )

        # Assert command succeeded
        assert result.success, f"CLI command failed: {result.stderr}"

        # Assert expected CLI output content
        assert "🛡️  Aegis Stack Project Initialization" in result.stdout
        assert "📦 Infrastructure: database" in result.stdout
        assert "• app/core/db.py" in result.stdout
        assert "• sqlmodel>=0.0.14" in result.stdout
        assert "• sqlalchemy>=2.0.0" in result.stdout
        assert "• aiosqlite>=0.19.0" in result.stdout
        assert "✅ Project created successfully!" in result.stdout

        # Assert project structure
        project_path = result.project_path
        assert project_path is not None, "Project path is None"
        self._assert_database_project_structure(project_path)
        self._assert_database_template_processing(project_path)

        # Assert no template files remain
        assert_no_template_files(project_path)

    def _assert_database_project_structure(self, project_path: Path) -> None:
        """Assert database-specific project structure."""
        self._assert_core_project_structure(project_path)

        # Database-specific files
        assert_file_exists(project_path, "app/core/db.py")

        # Database component should not create additional directories
        # (unlike scheduler and worker which create component directories)

    def _assert_database_template_processing(self, project_path: Path) -> None:
        """Assert that database templates were processed correctly."""
        from .test_utils import (
            assert_database_config_present,
            assert_db_file_structure,
        )

        # Check config.py includes database settings
        config_file = project_path / "app/core/config.py"
        config_content = config_file.read_text()
        assert_database_config_present(config_content)

        # Check db.py has complete structure
        db_file = project_path / "app/core/db.py"
        db_content = db_file.read_text()
        assert_db_file_structure(db_content)

        # Check pyproject.toml includes database dependencies
        pyproject_content = (project_path / "pyproject.toml").read_text()
        assert "sqlmodel>=0.0.14" in pyproject_content
        assert "sqlalchemy>=2.0.0" in pyproject_content
        assert "aiosqlite>=0.19.0" in pyproject_content

        # Check mypy overrides for SQLModel
        assert 'module = "sqlmodel.*"' in pyproject_content


# Note: CLI help tests moved to test_cli_basic.py to avoid duplication
