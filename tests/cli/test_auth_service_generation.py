"""
Tests for auth service generation behavior.

This module tests that auth service properly includes database dependencies,
migration infrastructure, and generates correct project structure.
"""

import tempfile
from typing import TYPE_CHECKING

import pytest

from tests.cli.test_utils import run_aegis_command

if TYPE_CHECKING:
    from tests.cli.conftest import ProjectFactory


class TestAuthServiceGeneration:
    """Test auth service file generation and dependency resolution."""

    def test_auth_service_includes_alembic_directory(
        self, project_factory: "ProjectFactory"
    ):
        """Test that auth service generates alembic directory and migration files."""
        # Use cached auth service project
        project_path = project_factory("base_with_auth_service")

        # Check alembic directory and files exist
        alembic_dir = project_path / "alembic"
        assert alembic_dir.exists(), "Alembic directory should exist with auth service"
        assert (alembic_dir / "alembic.ini").exists()
        assert (alembic_dir / "env.py").exists()
        assert (alembic_dir / "script.py.mako").exists()

        # Check versions directory with initial migration
        versions_dir = alembic_dir / "versions"
        assert versions_dir.exists()

        # Check for auth migration file (should start with 001_auth)
        migration_files = list(versions_dir.glob("001_auth.py"))
        assert len(migration_files) == 1, "Should have initial auth migration"

    def test_database_only_excludes_alembic_directory(
        self, project_factory: "ProjectFactory"
    ):
        """Test that database component without auth does NOT include alembic."""
        # Use cached database project
        project_path = project_factory("base_with_database")

        # Database component should exist
        assert (project_path / "app" / "core" / "db.py").exists()

        # But alembic directory should NOT exist
        alembic_dir = project_path / "alembic"
        assert not alembic_dir.exists(), "Database-only should not include alembic"

    def test_basic_project_excludes_alembic_directory(
        self, project_factory: "ProjectFactory"
    ):
        """Test that basic project without auth or database does NOT include alembic."""
        # Use cached base project
        project_path = project_factory("base")

        # Basic project structure should exist
        assert (project_path / "app" / "components" / "backend").exists()
        assert (project_path / "app" / "components" / "frontend").exists()

        # But alembic directory should NOT exist
        alembic_dir = project_path / "alembic"
        assert not alembic_dir.exists(), "Basic project should not include alembic"

        # And no database files
        assert not (project_path / "app" / "core" / "db.py").exists()

    def test_auth_service_auto_includes_database_component(
        self, project_factory: "ProjectFactory"
    ):
        """Test that auth service automatically includes database component."""
        # Use cached auth service project
        project_path = project_factory("base_with_auth_service")

        # Check database files are generated
        assert (project_path / "app" / "core" / "db.py").exists()

        # Check auth files are generated
        auth_dir = project_path / "app" / "components" / "backend" / "api" / "auth"
        assert auth_dir.exists()
        assert (project_path / "app" / "models" / "user.py").exists()
        assert (project_path / "app" / "core" / "security.py").exists()

    def test_auth_service_generates_complete_file_structure(
        self, project_factory: "ProjectFactory"
    ):
        """Test that auth service generates all expected files."""
        # Use cached auth service project
        project_path = project_factory("base_with_auth_service")

        # Core auth files
        assert (project_path / "app" / "models" / "user.py").exists()
        assert (project_path / "app" / "core" / "security.py").exists()

        # Auth API components
        auth_api_dir = project_path / "app" / "components" / "backend" / "api" / "auth"
        assert auth_api_dir.exists()

        # Auth services
        auth_services_dir = project_path / "app" / "services" / "auth"
        assert auth_services_dir.exists()

        # Database infrastructure
        assert (project_path / "app" / "core" / "db.py").exists()

        # Migration infrastructure
        alembic_dir = project_path / "alembic"
        assert alembic_dir.exists()
        assert (alembic_dir / "alembic.ini").exists()
        assert (alembic_dir / "env.py").exists()

        # Test files
        assert (project_path / "tests" / "api" / "test_auth_endpoints.py").exists()
        assert (
            project_path / "tests" / "services" / "test_auth_integration.py"
        ).exists()

    def test_auth_service_includes_correct_dependencies(
        self, project_factory: "ProjectFactory"
    ):
        """Test that auth service includes correct Python dependencies."""
        # Use cached auth service project
        project_path = project_factory("base_with_auth_service")

        # Check pyproject.toml has the dependencies
        pyproject_path = project_path / "pyproject.toml"
        pyproject_content = pyproject_path.read_text()

        # Core auth dependencies
        assert "python-jose[cryptography]==3.3.0" in pyproject_content
        assert "passlib[bcrypt]==1.7.4" in pyproject_content
        assert "python-multipart==0.0.9" in pyproject_content

        # Database dependencies (auto-included)
        assert "sqlmodel>=0.0.14" in pyproject_content
        assert "sqlalchemy>=2.0.0" in pyproject_content
        assert "aiosqlite>=0.19.0" in pyproject_content

    def test_auth_service_with_explicit_database_component(
        self, project_factory: "ProjectFactory"
    ):
        """Test auth service works when database component is explicitly provided."""
        # Use cached auth service project (already has database)
        project_path = project_factory("base_with_auth_service")

        # All files should be generated
        assert (project_path / "app" / "core" / "db.py").exists()
        assert (project_path / "alembic").exists()
        assert (project_path / "app" / "models" / "user.py").exists()


class TestAuthServiceErrorHandling:
    """Test auth service error handling and edge cases."""

    def test_auth_service_with_insufficient_explicit_components_fails(self):
        """Test that auth service fails when explicitly given insufficient components."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Try to use auth service with redis component only (missing database)
            result = run_aegis_command(
                "init",
                "test-auth-insufficient",
                "--services",
                "auth",
                "--components",
                "redis",  # Missing database
                "--no-interactive",
                "--yes",
                "--output-dir",
                temp_dir,
            )

            assert result.returncode != 0
            error_output = result.stderr

            # Should show specific error about missing database
            assert "Service 'auth' requires component 'database'" in error_output
            # Should suggest fix
            assert "Add missing components --components database,redis" in error_output

    def test_auth_service_error_suggests_alternatives(self):
        """Test that auth service errors provide helpful suggestions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_aegis_command(
                "init",
                "test-auth-suggestions",
                "--services",
                "auth",
                "--components",
                "worker",  # Wrong component
                "--no-interactive",
                "--yes",
                "--output-dir",
                temp_dir,
            )

            assert result.returncode != 0
            error_output = result.stderr

            # Should suggest removing --components to let services auto-add
            assert (
                "Or remove --components to let services auto-add dependencies"
                in error_output
            )
            assert (
                "use interactive mode to auto-add service dependencies" in error_output
            )


class TestAuthServiceInteractiveMode:
    """Test auth service behavior in interactive mode."""

    @pytest.mark.slow
    def test_auth_service_interactive_messaging(self):
        """Test that interactive mode shows proper messaging for auth service."""
        # Note: This would require mocking interactive input
        # For now, we focus on non-interactive mode testing
        # Future enhancement could add proper interactive testing
        pass


class TestAuthServiceMigrationConfiguration:
    """Test auth service migration-specific configuration."""

    def test_auth_migration_has_correct_revision_id(
        self, project_factory: "ProjectFactory"
    ):
        """Test that auth migration has correct revision ID and structure."""
        # Use cached auth service project
        project_path = project_factory("base_with_auth_service")

        # Read migration file
        migration_file = project_path / "alembic" / "versions" / "001_auth.py"
        assert migration_file.exists()

        migration_content = migration_file.read_text()

        # Check migration structure (handle both quote styles across Python versions)
        assert (
            "revision = '001'" in migration_content
            or 'revision = "001"' in migration_content
        )
        assert "down_revision = None" in migration_content
        assert "def upgrade() -> None:" in migration_content
        assert "def downgrade() -> None:" in migration_content

        # Check user table creation (handle both quote styles)
        assert "op.create_table(" in migration_content
        assert "'user'" in migration_content or '"user"' in migration_content
        assert "email" in migration_content
        assert "hashed_password" in migration_content

    def test_alembic_config_has_correct_settings(
        self, project_factory: "ProjectFactory"
    ):
        """Test that alembic.ini has correct configuration."""
        # Use cached auth service project
        project_path = project_factory("base_with_auth_service")

        # Read alembic config
        alembic_ini = project_path / "alembic" / "alembic.ini"
        assert alembic_ini.exists()

        config_content = alembic_ini.read_text()

        # Check key configuration
        assert "script_location = alembic" in config_content
        assert "prepend_sys_path = ." in config_content
        assert "version_path_separator = os" in config_content
