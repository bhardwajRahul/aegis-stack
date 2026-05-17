"""
Pytest configuration for CLI integration tests.
"""

import hashlib
import os
import shutil
import tempfile
from collections.abc import Callable, Generator, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from filelock import FileLock

from aegis.core.copier_manager import generate_with_copier
from aegis.core.template_generator import TemplateGenerator

from .test_stack_generation import STACK_COMBINATIONS, StackCombination
from .test_utils import CLITestResult, run_aegis_init

# Type alias for project_factory fixture
ProjectFactory = Callable[..., Path]

# PostgreSQL test configuration (password can be overridden via environment)
POSTGRES_TEST_PASSWORD = os.environ.get("POSTGRES_TEST_PASSWORD", "postgres")


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
    "base_with_database_postgres": ProjectTemplateSpec(
        components=("database[postgres]",)
    ),
    "base_with_scheduler": ProjectTemplateSpec(components=("scheduler",)),
    "base_with_scheduler_sqlite": ProjectTemplateSpec(
        components=("database", "scheduler"), scheduler_backend="sqlite"
    ),
    "base_with_worker": ProjectTemplateSpec(components=("worker",)),
    "base_with_worker_taskiq": ProjectTemplateSpec(components=("worker[taskiq]",)),
    "base_with_worker_dramatiq": ProjectTemplateSpec(components=("worker[dramatiq]",)),
    "base_with_redis": ProjectTemplateSpec(components=("redis",)),
    "scheduler_and_database": ProjectTemplateSpec(components=("database", "scheduler")),
    "base_with_auth_service": ProjectTemplateSpec(services=("auth",)),
    "base_with_ai_service": ProjectTemplateSpec(services=("ai",)),
    "base_with_ai_sqlite_service": ProjectTemplateSpec(services=("ai[sqlite]",)),
    "base_with_auth_and_ai_services": ProjectTemplateSpec(services=("auth", "ai")),
    # Full-stack matrix entries (mirror STACK_COMBINATIONS service rows so
    # ``make test-stacks-build`` doesn't pay a 30-40s regeneration cost
    # per slow test — per ``tests/CLAUDE.md``, every new stack MUST have
    # a cache entry or the matrix explodes past 10 minutes.
    "auth_basic": ProjectTemplateSpec(services=("auth",)),
    "auth_org_with_database": ProjectTemplateSpec(
        components=("database",), services=("auth[org]",)
    ),
    "ai_with_database": ProjectTemplateSpec(
        components=("database",), services=("ai[sqlite]",)
    ),
    "insights_full": ProjectTemplateSpec(
        components=("database", "scheduler"), services=("insights",)
    ),
    "insights_per_user": ProjectTemplateSpec(
        components=("database", "scheduler"),
        services=("auth[org]", "insights[per_user]"),
    ),
    "payment_with_database": ProjectTemplateSpec(
        components=("database",), services=("payment",)
    ),
    "blog_with_database": ProjectTemplateSpec(
        components=("database",), services=("blog",)
    ),
    "comms_only": ProjectTemplateSpec(services=("comms",)),
    "everything": ProjectTemplateSpec(
        components=("database", "scheduler", "worker", "redis"),
        services=("auth[org]", "ai[sqlite]", "insights", "payment", "blog", "comms"),
    ),
}


@pytest.fixture(scope="session")
def project_template_cache(
    tmp_path_factory: pytest.TempPathFactory,
) -> Callable[[ProjectTemplateSpec], Path]:
    """
    Generate reusable project skeletons once per test session, shared across xdist workers.

    Cache root selection:
      - Under xdist, ``tmp_path_factory.getbasetemp()`` is per-worker
        (``.../pytest-N/popen-gw0``), so we climb to its parent
        (``.../pytest-N``) which is per-session and shared across workers.
        Result: 16 workers, 1 cache build per spec instead of 16.
      - Without xdist, ``getbasetemp()`` is already per-session and not
        shared with anyone, so we use it directly. We DO NOT use
        ``getbasetemp().parent`` outside xdist — that's
        ``/tmp/pytest-of-<user>/``, persisted across runs and branch
        checkouts, which would serve stale projects after template edits.

    Atomic generation: write to a sibling temp dir, then rename onto the
    final target only on success. A partial directory after a crash will
    never be mistaken for a valid cache entry.
    """
    if os.environ.get("PYTEST_XDIST_WORKER"):
        shared_root = tmp_path_factory.getbasetemp().parent / "aegis-shared-cache"
    else:
        shared_root = tmp_path_factory.getbasetemp() / "aegis-shared-cache"
    shared_root.mkdir(exist_ok=True)
    in_memory: dict[ProjectTemplateSpec, Path] = {}

    def get_project(spec: ProjectTemplateSpec) -> Path:
        if spec in in_memory:
            return in_memory[spec]
        spec_hash = hashlib.sha1(repr(spec).encode("utf-8")).hexdigest()[:10]
        project_name = f"cached-{spec_hash}"
        target = shared_root / project_name
        # Lock per-spec so concurrent workers don't both build the same project;
        # workers wanting different specs proceed in parallel.
        with FileLock(str(shared_root / f"{project_name}.lock")):
            if not target.exists():
                staging_parent = Path(
                    tempfile.mkdtemp(prefix=f"{project_name}.staging-", dir=shared_root)
                )
                try:
                    template_gen = TemplateGenerator(
                        project_name=project_name,
                        selected_components=list(spec.components),
                        scheduler_backend=spec.scheduler_backend,
                        selected_services=list(spec.services),
                    )
                    generate_with_copier(template_gen, staging_parent, dev_mode=True)
                    staged = staging_parent / project_name
                    if not staged.exists():
                        raise FileNotFoundError(
                            f"Generated project not found at expected staging path: {staged}"
                        )
                    # Atomic publish: rename only succeeds whole or not at all,
                    # so a partial project is never visible to other workers.
                    staged.rename(target)
                finally:
                    shutil.rmtree(staging_parent, ignore_errors=True)
        in_memory[spec] = target
        return target

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

    Runs serially — ``run_aegis_init`` invokes the aegis CLI in-process via
    Typer's ``CliRunner``, so it shares module state, cwd, and copier caches.
    A ThreadPoolExecutor here races on all of those. Parallelizing this lane
    would require a ProcessPoolExecutor (with subprocess isolation) or a
    refactor of ``run_aegis_init`` to shell out — both bigger changes.

    Returns a dict mapping stack names to (combination, result) tuples.
    """
    stacks = {}

    print(f"\nGenerating {len(STACK_COMBINATIONS)} stacks for session...")

    for combination in STACK_COMBINATIONS:
        print(f"   - Generating {combination.name} stack...")

        result = run_aegis_init(
            combination.project_name,
            combination.components,
            session_temp_dir,
            services=combination.services or None,
            dev=True,
        )

        if not result.success:
            raise RuntimeError(
                f"Failed to generate {combination.name} stack for test session:\n"
                f"STDOUT: {result.stdout}\n"
                f"STDERR: {result.stderr}"
            )

        stacks[combination.name] = (combination, result)

    print(f"All {len(stacks)} stacks generated successfully!")
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


# PostgreSQL Runtime Testing Fixtures


@pytest.fixture(scope="session")
def generated_db_project_postgres(
    project_template_cache: Callable[[ProjectTemplateSpec], Path],
    session_temp_dir: Path,
) -> CLITestResult | None:
    """
    Get a cached PostgreSQL database project for runtime testing.

    Uses the project_template_cache for fast project generation.
    Returns None if PostgreSQL is not available.
    """
    import os
    import socket
    import subprocess
    import sys

    from .test_utils import CLITestResult, run_project_command

    # Check if PostgreSQL is available
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(("localhost", 5432))
        sock.close()
        if result != 0:
            print("PostgreSQL not available on localhost:5432, skipping setup")
            return None
    except Exception:
        print("Could not check PostgreSQL availability, skipping setup")
        return None

    # Create the test database in PostgreSQL
    db_name = "test-database-postgres-runtime"
    print(f"Creating PostgreSQL database: {db_name}")
    try:
        subprocess.run(
            [
                "psql",
                "-h",
                "localhost",
                "-U",
                "postgres",
                "-c",
                f'DROP DATABASE IF EXISTS "{db_name}"',
            ],
            capture_output=True,
            env={**dict(os.environ), "PGPASSWORD": POSTGRES_TEST_PASSWORD},
        )
        create_result = subprocess.run(
            [
                "psql",
                "-h",
                "localhost",
                "-U",
                "postgres",
                "-c",
                f'CREATE DATABASE "{db_name}"',
            ],
            capture_output=True,
            env={**dict(os.environ), "PGPASSWORD": POSTGRES_TEST_PASSWORD},
        )
        if create_result.returncode != 0:
            print(f"Failed to create database: {create_result.stderr.decode()}")
            return None
    except Exception as e:
        print(f"Could not create PostgreSQL database: {e}")
        return None

    # Get cached project and copy to session temp dir (exclude .venv - wrong Python version)
    print("Using cached PostgreSQL project template...")
    spec = NAMED_PROJECT_SPECS["base_with_database_postgres"]
    cached_project = project_template_cache(spec)
    project_path = session_temp_dir / "db-postgres-runtime"
    shutil.copytree(
        cached_project, project_path, ignore=shutil.ignore_patterns(".venv")
    )

    # Patch pyproject.toml to use current Python version (cached may have different version)
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    pyproject_path = project_path / "pyproject.toml"
    content = pyproject_path.read_text()
    import re

    content = re.sub(
        r'requires-python\s*=\s*"[^"]+"',
        f'requires-python = ">={python_version}"',
        content,
    )
    pyproject_path.write_text(content)

    # Update .python-version to match current Python (cached may have different version)
    python_version_file = project_path / ".python-version"
    python_version_file.write_text(f"{python_version}\n")

    # Install dependencies
    print("Installing dependencies in PostgreSQL project...")
    install_result = run_project_command(
        ["uv", "sync", "--extra", "dev", "--python", python_version],
        project_path,
        step_name="Install Dependencies",
        env_overrides={"VIRTUAL_ENV": ""},
    )

    if not install_result.success:
        raise RuntimeError(f"Failed to install dependencies: {install_result.stderr}")

    print("PostgreSQL database project ready for runtime testing!")
    return CLITestResult(
        returncode=0,
        stdout="",
        stderr="",
        project_path=project_path,
    )


# SQLite Runtime Testing Fixtures


@pytest.fixture(scope="session")
def generated_db_project(
    project_template_cache: Callable[[ProjectTemplateSpec], Path],
    session_temp_dir: Path,
) -> CLITestResult:
    """
    Get a cached SQLite database project for runtime testing.

    Uses the project_template_cache for fast project generation.
    """
    from .test_utils import CLITestResult, run_project_command

    # Get cached project and copy to session temp dir (exclude .venv - wrong Python version)
    print("Using cached SQLite project template...")
    spec = NAMED_PROJECT_SPECS["base_with_database"]
    cached_project = project_template_cache(spec)
    project_path = session_temp_dir / "db-sqlite-runtime"
    shutil.copytree(
        cached_project, project_path, ignore=shutil.ignore_patterns(".venv")
    )

    # Patch pyproject.toml to use current Python version (cached may have different version)
    import re
    import sys

    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    pyproject_path = project_path / "pyproject.toml"
    content = pyproject_path.read_text()
    content = re.sub(
        r'requires-python\s*=\s*"[^"]+"',
        f'requires-python = ">={python_version}"',
        content,
    )
    pyproject_path.write_text(content)

    # Update .python-version to match current Python (cached may have different version)
    python_version_file = project_path / ".python-version"
    python_version_file.write_text(f"{python_version}\n")

    # Install dependencies
    print("Installing dependencies in SQLite project...")
    install_result = run_project_command(
        ["uv", "sync", "--extra", "dev"],
        project_path,
        step_name="Install Dependencies",
        env_overrides={"VIRTUAL_ENV": ""},
    )

    if not install_result.success:
        raise RuntimeError(f"Failed to install dependencies: {install_result.stderr}")

    print("SQLite database project ready for runtime testing!")
    return CLITestResult(
        returncode=0,
        stdout="",
        stderr="",
        project_path=project_path,
    )
