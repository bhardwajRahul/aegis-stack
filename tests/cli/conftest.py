"""
Pytest configuration for CLI integration tests.
"""

import hashlib
import shutil
import tempfile
from collections.abc import Callable, Generator, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from aegis.core.copier_manager import generate_with_copier
from aegis.core.template_generator import TemplateGenerator

from .test_stack_generation import STACK_COMBINATIONS, StackCombination
from .test_utils import CLITestResult, run_aegis_init

# Type alias for project_factory fixture
ProjectFactory = Callable[..., Path]


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


@dataclass(frozen=True)
class ProjectTemplateSpec:
    """Normalized spec used for caching generated projects."""

    components: tuple[str, ...] = ()
    scheduler_backend: str = "memory"
    services: tuple[str, ...] = ()


NAMED_PROJECT_SPECS: dict[str, ProjectTemplateSpec] = {
    "base": ProjectTemplateSpec(),
    "base_with_database": ProjectTemplateSpec(components=("database",)),
    "base_with_scheduler": ProjectTemplateSpec(components=("scheduler",)),
    "base_with_scheduler_sqlite": ProjectTemplateSpec(
        components=("database", "scheduler"), scheduler_backend="sqlite"
    ),
    "base_with_worker": ProjectTemplateSpec(components=("worker",)),
    "base_with_redis": ProjectTemplateSpec(components=("redis",)),
    "scheduler_and_database": ProjectTemplateSpec(components=("database", "scheduler")),
    "base_with_auth_service": ProjectTemplateSpec(services=("auth",)),
}


@pytest.fixture(scope="session")
def project_template_cache(
    tmp_path_factory: pytest.TempPathFactory,
) -> Callable[[ProjectTemplateSpec], Path]:
    """
    Generate reusable project skeletons once per test session.

    Returns:
        Callable that returns the cached project path for a given spec.
    """
    cache_root = tmp_path_factory.mktemp("aegis-project-cache")
    cache: dict[ProjectTemplateSpec, Path] = {}

    def build_project(spec: ProjectTemplateSpec) -> Path:
        spec_hash = hashlib.sha1(repr(spec).encode("utf-8")).hexdigest()[:10]
        project_name = f"cached-{spec_hash}"
        template_gen = TemplateGenerator(
            project_name=project_name,
            selected_components=list(spec.components),
            scheduler_backend=spec.scheduler_backend,
            selected_services=list(spec.services),
        )
        return generate_with_copier(template_gen, cache_root)

    def get_project(spec: ProjectTemplateSpec) -> Path:
        if spec not in cache:
            cache[spec] = build_project(spec)
        return cache[spec]

    return get_project


@pytest.fixture
def project_factory(
    project_template_cache: Callable[[ProjectTemplateSpec], Path],
    temp_output_dir: Path,
) -> Callable[..., Path]:
    """
    Provide a helper that copies cached skeletons into the per-test temp directory.

    Supports either named specs (e.g., "base") or explicit component lists.
    """

    def _factory(
        name: str | None = None,
        *,
        components: Iterable[str] | None = None,
        scheduler_backend: str = "memory",
        services: Iterable[str] | None = None,
    ) -> Path:
        if name is not None:
            if name not in NAMED_PROJECT_SPECS:
                raise KeyError(
                    f"Project template '{name}' is not cached. "
                    f"Available templates: {list(NAMED_PROJECT_SPECS.keys())}"
                )
            spec = NAMED_PROJECT_SPECS[name]
        else:
            spec = ProjectTemplateSpec(
                components=tuple(components or ()),
                scheduler_backend=scheduler_backend,
                services=tuple(services or ()),
            )

        source = project_template_cache(spec)
        destination = temp_output_dir / source.name
        shutil.copytree(source, destination)
        return destination

    return _factory


@pytest.fixture(scope="session")
def generated_stacks(
    session_temp_dir: Path,
) -> dict[str, tuple[StackCombination, CLITestResult]]:
    """
    Generate all stack combinations once per test session.

    This dramatically reduces test time by avoiding duplicate stack generation.
    Returns a dict mapping stack names to (combination, result) tuples.

    Note: Always uses Cookiecutter engine for session-scoped generation.
    Engine-parameterized tests will skip Copier tests via skip_copier_tests fixture.
    """
    # Always use Cookiecutter for session-scoped fixture
    engine = "cookiecutter"

    stacks = {}

    print(
        f"\n🏗️  Generating {len(STACK_COMBINATIONS)} stacks for session (engine={engine})..."
    )

    for combination in STACK_COMBINATIONS:
        print(f"   - Generating {combination.name} stack...")

        result = run_aegis_init(
            combination.project_name,
            combination.components,
            session_temp_dir,
            engine=engine,
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
    from app.core.db import (  # type: ignore[import-not-found]
        SessionLocal,
        db_session,
        engine,
    )
    from sqlalchemy.exc import IntegrityError  # type: ignore[import-not-found]

    # Also import SQLModel classes from the generated project
    from sqlmodel import Field, SQLModel  # type: ignore[import-not-found]

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
