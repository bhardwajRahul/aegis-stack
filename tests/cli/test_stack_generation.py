"""
Stack Generation Matrix Tests for Aegis Stack CLI.

This module tests all valid component combinations to ensure every possible
stack configuration generates successfully and produces valid project structures.

Test Matrix:
1. base                    (backend + frontend only)
2. base + redis           (adds Redis infrastructure)
3. base + scheduler       (includes Redis + APScheduler)
4. base + worker          (includes Redis + arq workers)
5. base + worker + scheduler (full processing stack)

Each combination must:
- Generate without errors
- Create correct file structure
- Include proper dependencies
- Generate valid Docker configuration
- Pass basic validation checks
"""

from typing import Any

import pytest

from .test_utils import (
    validate_docker_compose,
    validate_project_structure,
    validate_pyproject_dependencies,
)


class StackCombination:
    """Represents a stack component combination for testing."""

    def __init__(
        self,
        name: str,
        components: list[str],
        description: str,
        expected_files: list[str],
        expected_docker_services: list[str],
        expected_pyproject_deps: list[str],
    ):
        self.name = name
        self.components = components
        self.description = description
        self.expected_files = expected_files
        self.expected_docker_services = expected_docker_services
        self.expected_pyproject_deps = expected_pyproject_deps

    @property
    def components_str(self) -> str:
        """Get components as comma-separated string for CLI."""
        return ",".join(self.components) if self.components else ""

    @property
    def project_name(self) -> str:
        """Get project name for this combination."""
        return f"test-{self.name}"


# Define all valid stack combinations
STACK_COMBINATIONS = [
    StackCombination(
        name="base",
        components=[],
        description="Base stack with backend and frontend only",
        expected_files=[
            "app/components/backend/",
            "app/components/frontend/",
            "app/entrypoints/webserver.py",
            "docker-compose.yml",
            "pyproject.toml",
            "Makefile",
        ],
        expected_docker_services=["webserver"],
        expected_pyproject_deps=["fastapi", "flet", "uvicorn"],
    ),
    StackCombination(
        name="redis",
        components=["redis"],
        description="Base stack with Redis infrastructure",
        expected_files=[
            "app/components/backend/",
            "app/components/frontend/",
            "app/entrypoints/webserver.py",
            "docker-compose.yml",
        ],
        expected_docker_services=["webserver", "redis"],
        expected_pyproject_deps=["fastapi", "flet", "redis"],
    ),
    StackCombination(
        name="scheduler",
        components=["scheduler"],
        description="Base stack with scheduler (APScheduler only, no Redis)",
        expected_files=[
            "app/components/backend/",
            "app/components/frontend/",
            "app/components/scheduler/",
            "app/entrypoints/webserver.py",
            "app/entrypoints/scheduler.py",
            "docker-compose.yml",
        ],
        expected_docker_services=["webserver", "scheduler"],
        expected_pyproject_deps=["fastapi", "flet", "apscheduler"],
    ),
    StackCombination(
        name="worker",
        components=["worker"],
        description="Base stack with worker queues (includes Redis)",
        expected_files=[
            "app/components/backend/",
            "app/components/frontend/",
            "app/components/worker/",
            "app/entrypoints/webserver.py",
            "docker-compose.yml",
        ],
        expected_docker_services=[
            "webserver",
            "redis",
            "worker-system",
            "worker-load-test",
        ],
        expected_pyproject_deps=["fastapi", "flet", "arq", "redis"],
    ),
    StackCombination(
        name="full",
        components=["worker", "scheduler"],
        description="Full processing stack with both worker and scheduler",
        expected_files=[
            "app/components/backend/",
            "app/components/frontend/",
            "app/components/worker/",
            "app/components/scheduler/",
            "app/entrypoints/webserver.py",
            "app/entrypoints/scheduler.py",
            "docker-compose.yml",
        ],
        expected_docker_services=[
            "webserver",
            "redis",
            "scheduler",
            "worker-system",
            "worker-load-test",
        ],
        expected_pyproject_deps=["fastapi", "flet", "arq", "apscheduler", "redis"],
    ),
    StackCombination(
        name="database",
        components=["database"],
        description="Base stack with SQLite database",
        expected_files=[
            "app/components/backend/",
            "app/components/frontend/",
            "app/core/db.py",  # Database-specific file
            "app/entrypoints/webserver.py",
            "docker-compose.yml",
            "pyproject.toml",
            "Makefile",
        ],
        expected_docker_services=["webserver"],  # No database service for SQLite
        expected_pyproject_deps=[
            "fastapi",
            "flet",
            "sqlmodel",
            "sqlalchemy",
            "aiosqlite",
        ],
    ),
]


@pytest.mark.parametrize("combination", STACK_COMBINATIONS, ids=lambda x: x.name)
def test_stack_generation_matrix(
    combination: StackCombination, get_generated_stack: Any
) -> None:
    """Test generation of each valid stack combination."""
    # Get the pre-generated stack
    _, result = get_generated_stack(combination.name)

    # Assert generation succeeded (this was already validated during session setup)
    assert result.success, (
        f"Failed to generate {combination.description}\n"
        f"Return code: {result.returncode}\n"
        f"STDOUT: {result.stdout}\n"
        f"STDERR: {result.stderr}"
    )

    # Assert project directory was created
    assert result.project_path.exists(), (
        f"Project directory not created: {result.project_path}"
    )
    assert result.project_path.is_dir(), (
        f"Project path is not a directory: {result.project_path}"
    )


@pytest.mark.parametrize("combination", STACK_COMBINATIONS, ids=lambda x: x.name)
def test_stack_file_structure(
    combination: StackCombination, get_generated_stack: Any
) -> None:
    """Test that each stack has the correct file structure."""
    # Get the pre-generated stack
    _, result = get_generated_stack(combination.name)

    assert result.success, f"Failed to generate {combination.description}"

    # Validate file structure
    missing_files = validate_project_structure(
        result.project_path, combination.expected_files
    )
    assert not missing_files, (
        f"Missing expected files in {combination.description}:\n"
        + "\n".join(f"  - {file}" for file in missing_files)
    )


@pytest.mark.parametrize("combination", STACK_COMBINATIONS, ids=lambda x: x.name)
def test_stack_docker_configuration(
    combination: StackCombination, get_generated_stack: Any
) -> None:
    """Test that each stack has correct Docker Compose configuration."""
    # Get the pre-generated stack
    _, result = get_generated_stack(combination.name)

    assert result.success, f"Failed to generate {combination.description}"

    # Validate Docker Compose services
    missing_services = validate_docker_compose(
        result.project_path, combination.expected_docker_services
    )
    assert not missing_services, (
        f"Docker Compose issues in {combination.description}:\n"
        + "\n".join(f"  - {issue}" for issue in missing_services)
    )


@pytest.mark.parametrize("combination", STACK_COMBINATIONS, ids=lambda x: x.name)
def test_stack_dependencies(
    combination: StackCombination, get_generated_stack: Any
) -> None:
    """Test that each stack has correct Python dependencies."""
    # Get the pre-generated stack
    _, result = get_generated_stack(combination.name)

    assert result.success, f"Failed to generate {combination.description}"

    # Validate dependencies
    missing_deps = validate_pyproject_dependencies(
        result.project_path, combination.expected_pyproject_deps
    )
    assert not missing_deps, (
        f"Missing dependencies in {combination.description}:\n"
        + "\n".join(f"  - {dep}" for dep in missing_deps)
    )


def test_stack_combinations_comprehensive() -> None:
    """Test that we're covering all expected component combinations."""
    # Verify we have tests for basic patterns
    combination_names = {combo.name for combo in STACK_COMBINATIONS}

    expected_combinations = {"base", "redis", "scheduler", "worker", "full", "database"}
    assert combination_names == expected_combinations, (
        f"Missing expected combinations. "
        f"Expected: {expected_combinations}, "
        f"Got: {combination_names}"
    )


def test_component_dependency_resolution() -> None:
    """Test that component dependencies are properly resolved."""
    # Worker should automatically include Redis
    worker_combo = next(c for c in STACK_COMBINATIONS if c.name == "worker")
    assert "redis" in worker_combo.expected_docker_services
    assert "redis" in worker_combo.expected_pyproject_deps

    # Scheduler should run standalone
    scheduler_combo = next(c for c in STACK_COMBINATIONS if c.name == "scheduler")
    assert "redis" not in scheduler_combo.expected_docker_services
    assert "redis" not in scheduler_combo.expected_pyproject_deps
    assert "apscheduler" in scheduler_combo.expected_pyproject_deps

    # Full stack should have both worker and scheduler capabilities
    full_combo = next(c for c in STACK_COMBINATIONS if c.name == "full")
    assert "worker-system" in full_combo.expected_docker_services
    assert "scheduler" in full_combo.expected_docker_services
    assert "arq" in full_combo.expected_pyproject_deps
    assert "apscheduler" in full_combo.expected_pyproject_deps


@pytest.mark.integration
def test_stack_generation_output_messages(get_generated_stack: Any) -> None:
    """Test that CLI provides helpful output messages during generation."""
    # Get the worker stack to check output messages
    _, result = get_generated_stack("worker")

    assert result.success

    # Should mention component inclusion
    assert "worker" in result.stdout.lower() or "worker" in result.stderr.lower()

    # Should indicate success
    success_indicators = ["✅", "success", "complete", "created"]
    output_text = (result.stdout + result.stderr).lower()
    assert any(indicator in output_text for indicator in success_indicators)
