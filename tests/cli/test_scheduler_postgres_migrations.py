"""Regression guard: a Postgres-backed scheduler must ship runnable migrations.

The stack matrix is all-SQLite (which uses ``SQLModel.metadata.create_all`` and
never calls the startup ``_run_migrations`` path), so it never exercises a
Postgres scheduler stack actually running its schema-qualified migration. These
tests assert the three pieces that path needs at runtime, each of which was
missing at some point because "needs migrations" was computed from services
only, never the scheduler:

1. ``alembic`` as a runtime dependency (otherwise ``from alembic import
   command`` resolves to the project's local ``alembic/`` directory and the
   migration runner crashes).
2. the alembic environment (``env.py`` + ``alembic.ini``) surviving the
   post-generation cleanup that removes ``alembic/`` when nothing needs it.
3. the generated, schema-qualified scheduler migration itself.
"""

from pathlib import Path

from .test_utils import run_aegis_command


def test_postgres_scheduler_ships_runnable_migrations(
    temp_output_dir: Path,
) -> None:
    result = run_aegis_command(
        "init",
        "schedpg",
        "--components",
        "scheduler[postgres]",
        "--output-dir",
        str(temp_output_dir),
        "--no-interactive",
        "--yes",
    )
    assert result.returncode == 0, f"init failed: {result.stderr}"

    project = temp_output_dir / "schedpg"
    answers = (project / ".copier-answers.yml").read_text()
    assert "scheduler_backend: postgres" in answers

    # 1. alembic must be a runtime dependency.
    assert "alembic==" in (project / "pyproject.toml").read_text(), (
        "Postgres scheduler stack must depend on alembic to run migrations"
    )

    # 2. the alembic environment must survive post-generation cleanup.
    assert (project / "alembic" / "env.py").exists(), "alembic/env.py missing"
    assert (project / "alembic" / "alembic.ini").exists(), "alembic.ini missing"

    # 3. the schema-qualified scheduler migration must be generated.
    migrations = list((project / "alembic" / "versions").glob("*_scheduler.py"))
    assert len(migrations) == 1, "expected exactly one scheduler migration"
    content = migrations[0].read_text()
    assert 'CREATE SCHEMA IF NOT EXISTS "scheduler"' in content
    # post-generation `ruff --fix` may normalise quote style
    assert ('schema="scheduler"' in content) or ("schema='scheduler'" in content)


def test_sqlite_scheduler_has_no_alembic(temp_output_dir: Path) -> None:
    """A SQLite scheduler uses create_all, so it must NOT carry alembic or a
    scheduler migration (the schema'd migration can't run on SQLite)."""
    result = run_aegis_command(
        "init",
        "schedlite",
        "--components",
        "scheduler[sqlite]",
        "--output-dir",
        str(temp_output_dir),
        "--no-interactive",
        "--yes",
    )
    assert result.returncode == 0, f"init failed: {result.stderr}"

    project = temp_output_dir / "schedlite"
    assert "alembic==" not in (project / "pyproject.toml").read_text()
    assert not (project / "alembic").exists()
