"""
Pytest configuration for CLI integration tests.
"""

from collections.abc import Generator
from pathlib import Path
import tempfile
from typing import Any

import pytest

from .test_stack_generation import STACK_COMBINATIONS, StackCombination
from .test_utils import CLITestResult, run_aegis_init


@pytest.fixture(scope="session")
def cli_test_timeout() -> int:
    """Default timeout for CLI commands."""
    return 60  # seconds


@pytest.fixture
def temp_output_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test project generation."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture(scope="session")
def session_temp_dir() -> Generator[Path, None, None]:
    """Create a session-scoped temporary directory for shared stack generation."""
    with tempfile.TemporaryDirectory(prefix="aegis-test-session-") as temp_dir:
        yield Path(temp_dir)


@pytest.fixture(scope="session")
def generated_stacks(
    session_temp_dir: Path,
) -> dict[str, tuple[StackCombination, CLITestResult]]:
    """
    Generate all stack combinations once per test session.

    This dramatically reduces test time by avoiding duplicate stack generation.
    Returns a dict mapping stack names to (combination, result) tuples.
    """
    stacks = {}

    print(f"\n🏗️  Generating {len(STACK_COMBINATIONS)} stacks for session...")

    for combination in STACK_COMBINATIONS:
        print(f"   - Generating {combination.name} stack...")

        result = run_aegis_init(
            combination.project_name,
            combination.components,
            session_temp_dir,
            timeout=60,
        )

        if not result.success:
            raise RuntimeError(
                f"Failed to generate {combination.name} stack for test session:\n"
                f"STDOUT: {result.stdout}\n"
                f"STDERR: {result.stderr}"
            )

        stacks[combination.name] = (combination, result)

    print(f"✅ All {len(stacks)} stacks generated successfully!")
    return stacks


@pytest.fixture
def get_generated_stack(
    generated_stacks: dict[str, tuple[StackCombination, CLITestResult]],
) -> Any:
    """Helper to get a specific generated stack by name."""

    def _get_stack(name: str) -> tuple[StackCombination, CLITestResult]:
        if name not in generated_stacks:
            raise KeyError(
                f"Stack '{name}' not found. Available: {list(generated_stacks.keys())}"
            )
        return generated_stacks[name]

    return _get_stack


# Database Runtime Testing Fixtures
# Following ee-toolset pattern for proper fixture-based testing


@pytest.fixture(scope="session")
def generated_db_project(session_temp_dir: Path) -> CLITestResult:
    """
    Generate a project with database component once per session.

    This fixture generates a project and installs its dependencies
    so we can import and test the generated db.py module.
    """
    print("🗄️  Generating database project for runtime testing...")

    result = run_aegis_init(
        "test-database-runtime",
        ["database"],
        session_temp_dir,
        timeout=60,
    )

    if not result.success:
        raise RuntimeError(f"Failed to generate database project: {result.stderr}")

    # Install dependencies in the generated project
    print("📦 Installing dependencies in generated project...")
    from .test_utils import run_project_command

    assert result.project_path is not None, "Project path should not be None"
    install_result = run_project_command(
        ["uv", "sync", "--extra", "dev"],
        result.project_path,
        timeout=120,
        step_name="Install Dependencies",
        env_overrides={"VIRTUAL_ENV": ""},  # Ensure clean environment
    )

    if not install_result.success:
        raise RuntimeError(f"Failed to install dependencies: {install_result.stderr}")

    print("✅ Database project ready for runtime testing!")
    return result


@pytest.fixture(scope="session")
def db_module(generated_db_project: CLITestResult) -> dict[str, Any]:
    """
    Import the generated database module.

    This allows us to test the actual generated code,
    not just check that files exist.
    """
    import sys

    # Add generated project to Python path
    project_path = str(generated_db_project.project_path)
    if project_path not in sys.path:
        sys.path.insert(0, project_path)

    # Add generated project's site-packages to access its dependencies
    # This is safe because we control version pinning in both environments
    import glob

    site_packages_paths = glob.glob(f"{project_path}/.venv/lib/python*/site-packages")
    if site_packages_paths:
        sys.path.insert(0, site_packages_paths[0])

    # Import the generated db module
    # NOTE: These imports are from the dynamically generated project, not aegis-stack
    # MyPy can't see them during static analysis, hence the type: ignore comments
    from sqlalchemy.exc import IntegrityError  # type: ignore[import-not-found]

    # Also import SQLModel classes from the generated project
    from sqlmodel import Field, SQLModel  # type: ignore[import-not-found]

    from app.core.db import (  # type: ignore[import-not-found]
        SessionLocal,
        db_session,
        engine,
    )

    # Create model factory function
    def create_test_models() -> dict[str, Any]:
        """Create test model classes using the generated project's SQLModel."""

        class TestUser(SQLModel, table=True):  # type: ignore[misc,call-arg]
            """Simple test model for database tests."""

            __tablename__ = "test_users"
            id: int | None = Field(default=None, primary_key=True)
            name: str
            email: str | None = None

        class Parent(SQLModel, table=True):  # type: ignore[misc,call-arg]
            """Parent model for foreign key testing."""

            __tablename__ = "parents"
            id: int | None = Field(default=None, primary_key=True)
            name: str

        class Child(SQLModel, table=True):  # type: ignore[misc,call-arg]
            """Child model for foreign key testing."""

            __tablename__ = "children"
            id: int | None = Field(default=None, primary_key=True)
            name: str
            parent_id: int = Field(foreign_key="parents.id")

        return {
            "TestUser": TestUser,
            "Parent": Parent,
            "Child": Child,
        }

    return {
        "db_session": db_session,
        "engine": engine,
        "SessionLocal": SessionLocal,
        "SQLModel": SQLModel,
        "Field": Field,
        "IntegrityError": IntegrityError,
        "create_test_models": create_test_models,
    }
