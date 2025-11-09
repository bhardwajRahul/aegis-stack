"""
Tests for shared post-generation tasks module.

These tests validate the post-generation task functions that are used
by both Cookiecutter hooks and Copier updaters.
"""

import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from aegis.core.post_gen_tasks import (
    format_code,
    install_dependencies,
    run_migrations,
    run_post_generation_tasks,
    setup_env_file,
)


class TestInstallDependencies:
    """Test dependency installation task."""

    def test_successful_installation(self, tmp_path: Path) -> None:
        """Test successful dependency installation."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stderr="")

            result = install_dependencies(tmp_path)

            assert result is True
            mock_run.assert_called_once()
            args = mock_run.call_args
            assert args[0][0] == ["uv", "sync"]
            assert args[1]["cwd"] == tmp_path
            assert "VIRTUAL_ENV" not in args[1]["env"]

    def test_installation_failure(self, tmp_path: Path) -> None:
        """Test failed dependency installation."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1, stderr="Installation error")

            result = install_dependencies(tmp_path)

            assert result is False

    def test_installation_timeout(self, tmp_path: Path) -> None:
        """Test dependency installation timeout."""
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("uv", 300)):
            result = install_dependencies(tmp_path)

            assert result is False

    def test_uv_not_found(self, tmp_path: Path) -> None:
        """Test when uv command is not found."""
        with patch("subprocess.run", side_effect=FileNotFoundError()):
            result = install_dependencies(tmp_path)

            assert result is False

    def test_virtual_env_unset(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that VIRTUAL_ENV is properly unset."""
        monkeypatch.setenv("VIRTUAL_ENV", "/some/venv")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stderr="")

            install_dependencies(tmp_path)

            args = mock_run.call_args
            assert "VIRTUAL_ENV" not in args[1]["env"]


class TestSetupEnvFile:
    """Test environment file setup task."""

    def test_creates_env_from_example(self, tmp_path: Path) -> None:
        """Test creating .env from .env.example."""
        env_example = tmp_path / ".env.example"
        env_example.write_text("DATABASE_URL=sqlite:///./data/app.db\n")

        result = setup_env_file(tmp_path)

        assert result is True
        env_file = tmp_path / ".env"
        assert env_file.exists()
        assert env_file.read_text() == "DATABASE_URL=sqlite:///./data/app.db\n"

    def test_env_already_exists(self, tmp_path: Path) -> None:
        """Test when .env already exists (should skip)."""
        env_example = tmp_path / ".env.example"
        env_example.write_text("EXAMPLE=value\n")
        env_file = tmp_path / ".env"
        env_file.write_text("EXISTING=value\n")

        result = setup_env_file(tmp_path)

        assert result is True
        # Should not overwrite existing .env
        assert env_file.read_text() == "EXISTING=value\n"

    def test_no_example_file(self, tmp_path: Path) -> None:
        """Test when .env.example doesn't exist."""
        result = setup_env_file(tmp_path)

        assert result is False
        env_file = tmp_path / ".env"
        assert not env_file.exists()


class TestRunMigrations:
    """Test database migration task."""

    def test_skips_when_auth_disabled(self, tmp_path: Path) -> None:
        """Test migrations are skipped when auth not enabled."""
        result = run_migrations(tmp_path, include_auth=False)

        assert result is True  # Success (no-op)

    def test_successful_migration(self, tmp_path: Path) -> None:
        """Test successful database migration."""
        # Create alembic config
        alembic_dir = tmp_path / "alembic"
        alembic_dir.mkdir()
        alembic_ini = alembic_dir / "alembic.ini"
        alembic_ini.write_text("[alembic]\n")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stderr="")

            result = run_migrations(tmp_path, include_auth=True)

            assert result is True
            mock_run.assert_called_once()
            args = mock_run.call_args
            assert args[0][0][0:3] == ["uv", "run", "alembic"]
            assert "VIRTUAL_ENV" not in args[1]["env"]

    def test_missing_alembic_config(self, tmp_path: Path) -> None:
        """Test when alembic config doesn't exist."""
        result = run_migrations(tmp_path, include_auth=True)

        assert result is False

    def test_migration_failure(self, tmp_path: Path) -> None:
        """Test failed migration."""
        alembic_dir = tmp_path / "alembic"
        alembic_dir.mkdir()
        alembic_ini = alembic_dir / "alembic.ini"
        alembic_ini.write_text("[alembic]\n")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1, stderr="Migration error")

            result = run_migrations(tmp_path, include_auth=True)

            assert result is False

    def test_creates_data_directory(self, tmp_path: Path) -> None:
        """Test that data directory is created."""
        alembic_dir = tmp_path / "alembic"
        alembic_dir.mkdir()
        alembic_ini = alembic_dir / "alembic.ini"
        alembic_ini.write_text("[alembic]\n")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stderr="")

            run_migrations(tmp_path, include_auth=True)

            data_dir = tmp_path / "data"
            assert data_dir.exists()
            assert data_dir.is_dir()


class TestFormatCode:
    """Test code formatting task."""

    def test_successful_formatting(self, tmp_path: Path) -> None:
        """Test successful code formatting."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stderr="")

            result = format_code(tmp_path)

            assert result is True
            mock_run.assert_called_once()
            args = mock_run.call_args
            assert args[0][0] == ["make", "fix"]
            assert args[1]["cwd"] == tmp_path
            assert "VIRTUAL_ENV" not in args[1]["env"]

    def test_formatting_failure(self, tmp_path: Path) -> None:
        """Test formatting failure (non-critical)."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1, stderr="Format error")

            result = format_code(tmp_path)

            assert result is False  # Reports failure but doesn't crash

    def test_make_not_found(self, tmp_path: Path) -> None:
        """Test when make command is not found."""
        with patch("subprocess.run", side_effect=FileNotFoundError()):
            result = format_code(tmp_path)

            assert result is False

    def test_formatting_timeout(self, tmp_path: Path) -> None:
        """Test formatting timeout."""
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("make", 60)):
            result = format_code(tmp_path)

            assert result is False


class TestRunPostGenerationTasks:
    """Test main post-generation task orchestrator."""

    def test_all_tasks_succeed(self, tmp_path: Path) -> None:
        """Test when all tasks succeed."""
        # Create minimal project structure
        env_example = tmp_path / ".env.example"
        env_example.write_text("TEST=value\n")

        with (
            patch("aegis.core.post_gen_tasks.install_dependencies", return_value=True),
            patch("aegis.core.post_gen_tasks.setup_env_file", return_value=True),
            patch("aegis.core.post_gen_tasks.run_migrations", return_value=True),
            patch("aegis.core.post_gen_tasks.format_code", return_value=True),
        ):
            result = run_post_generation_tasks(tmp_path, include_auth=False)

            assert result is True

    def test_dependency_install_failure(self, tmp_path: Path) -> None:
        """Test when dependency installation fails (critical)."""
        with (
            patch("aegis.core.post_gen_tasks.install_dependencies", return_value=False),
            patch("aegis.core.post_gen_tasks.setup_env_file", return_value=True),
            patch("aegis.core.post_gen_tasks.run_migrations", return_value=True),
            patch("aegis.core.post_gen_tasks.format_code", return_value=True),
        ):
            result = run_post_generation_tasks(tmp_path, include_auth=False)

            assert result is False  # Critical failure

    def test_non_critical_failures_continue(self, tmp_path: Path) -> None:
        """Test that non-critical failures don't stop execution."""
        with (
            patch("aegis.core.post_gen_tasks.install_dependencies", return_value=True),
            patch("aegis.core.post_gen_tasks.setup_env_file", return_value=False),
            patch("aegis.core.post_gen_tasks.run_migrations", return_value=False),
            patch("aegis.core.post_gen_tasks.format_code", return_value=False),
        ):
            result = run_post_generation_tasks(tmp_path, include_auth=True)

            assert result is True  # Deps succeeded, so overall success

    def test_auth_migrations_triggered(self, tmp_path: Path) -> None:
        """Test that migrations run when auth is enabled."""
        with (
            patch("aegis.core.post_gen_tasks.install_dependencies", return_value=True),
            patch("aegis.core.post_gen_tasks.setup_env_file", return_value=True),
            patch("aegis.core.post_gen_tasks.run_migrations") as mock_migrations,
            patch("aegis.core.post_gen_tasks.format_code", return_value=True),
        ):
            mock_migrations.return_value = True

            run_post_generation_tasks(tmp_path, include_auth=True)

            mock_migrations.assert_called_once_with(tmp_path, True)

    def test_tasks_run_in_order(self, tmp_path: Path) -> None:
        """Test that tasks run in the correct order."""
        call_order = []

        def track_deps(path: Path, python_version: str | None = None) -> bool:
            call_order.append("deps")
            return True

        def track_env(path: Path) -> bool:
            call_order.append("env")
            return True

        def track_migrations(path: Path, auth: bool) -> bool:
            call_order.append("migrations")
            return True

        def track_format(path: Path) -> bool:
            call_order.append("format")
            return True

        with (
            patch(
                "aegis.core.post_gen_tasks.install_dependencies", side_effect=track_deps
            ),
            patch("aegis.core.post_gen_tasks.setup_env_file", side_effect=track_env),
            patch(
                "aegis.core.post_gen_tasks.run_migrations", side_effect=track_migrations
            ),
            patch("aegis.core.post_gen_tasks.format_code", side_effect=track_format),
        ):
            run_post_generation_tasks(tmp_path, include_auth=True)

            assert call_order == ["deps", "env", "migrations", "format"]
