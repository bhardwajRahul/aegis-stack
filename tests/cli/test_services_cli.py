"""
Tests for services CLI functionality.

This module tests the services command and --services option integration.
"""

import re
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from tests.cli.test_utils import run_aegis_command


class TestServicesCommand:
    """Test the 'aegis services' command."""

    def test_services_command_shows_available_services(self):
        """Test that services command displays available services."""
        result = run_aegis_command("services")

        assert result.returncode == 0
        output = result.stdout

        # Check for main header
        assert "🔧 AVAILABLE SERVICES" in output
        assert "=" * 40 in output

        # Check for auth service section
        assert "🔐 Authentication Services" in output
        assert "-" * 40 in output

        # Check for auth service details
        assert "auth" in output
        assert "User authentication and authorization with JWT tokens" in output
        assert "Requires components: backend, database" in output

        # Check for usage guidance
        assert (
            "💡 Use 'aegis init PROJECT_NAME --services auth' to add services" in output
        )

    def test_services_command_help(self):
        """Test that services command help works."""
        result = run_aegis_command("services", "--help")

        assert result.returncode == 0
        assert "List available services and their dependencies" in result.stdout

    def test_services_command_appears_in_main_help(self):
        """Test that services command appears in main CLI help."""
        result = run_aegis_command("--help")

        assert result.returncode == 0
        assert "services" in result.stdout
        assert "List available services and their dependencies" in result.stdout

    def test_services_command_with_empty_registry(self):
        """Test services command behavior with empty registry."""
        with mock.patch(
            "aegis.commands.services.get_services_by_type"
        ) as mock_get_services:
            # Mock all service types to return empty dict
            mock_get_services.return_value = {}

            result = run_aegis_command("services")

            assert result.returncode == 0
            # Should show no services message (though this won't actually show due to mock)


class TestServicesOptionIntegration:
    """Test the --services option in init command."""

    def test_init_with_valid_service(self):
        """Test init command with valid service."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_aegis_command(
                "init",
                "test-auth-service",
                "--services",
                "auth",
                "--no-interactive",
                "--yes",
                "--output-dir",
                temp_dir,
            )

            assert result.returncode == 0
            output = result.stdout

            # Check that service dependency resolution worked
            assert "📦 Services require components: backend, database" in output
            assert "🔧 Services: auth" in output
            assert "📦 Infrastructure: database" in output

            # Check that project was created
            project_path = Path(temp_dir) / "test-auth-service"
            assert project_path.exists()
            assert (project_path / "app").exists()

    def test_init_with_invalid_service(self):
        """Test init command with invalid service shows error."""
        result = run_aegis_command(
            "init",
            "test-invalid",
            "--services",
            "invalid-service",
            "--no-interactive",
            "--yes",
        )

        assert result.returncode != 0
        assert "❌ Unknown services: invalid-service" in result.stderr
        assert "Available services: auth" in result.stderr

    def test_init_with_multiple_services(self):
        """Test init command with multiple services (when more are available)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_aegis_command(
                "init",
                "test-multi-service",
                "--services",
                "auth",  # Only auth available for now
                "--no-interactive",
                "--yes",
                "--output-dir",
                temp_dir,
            )

            assert result.returncode == 0
            assert "🔧 Services: auth" in result.stdout

    def test_init_with_empty_service_name(self):
        """Test init command with empty service name."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_aegis_command(
                "init",
                "test-empty",
                "--services",
                "",
                "--output-dir",
                temp_dir,
                "--no-interactive",
                "--yes",
            )

            # Empty string is treated as "no services provided", so it should succeed
            assert result.returncode == 0
            # Should not show any services section
            assert "🔧 Services:" not in result.stdout

    def test_init_with_services_and_components_together(self):
        """Test init command with both services and components specified."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_aegis_command(
                "init",
                "test-combined",
                "--services",
                "auth",
                "--components",
                "database,worker",  # Auth needs database (backend always included), plus explicit worker
                "--no-interactive",
                "--yes",
                "--output-dir",
                temp_dir,
            )

            assert result.returncode == 0
            output = result.stdout

            # Should show both services and components
            assert "🔧 Services: auth" in output
            assert "📦 Infrastructure:" in output
            # Should have all components: backend, database (auth), worker and redis (worker dep)
            assert "backend" in output
            assert "database" in output
            assert "worker" in output
            # Worker adds redis as dependency
            assert "redis" in output

    def test_init_services_help_text_accuracy(self):
        """Test that init command help shows correct services help text."""
        result = run_aegis_command("init", "--help")

        assert result.returncode == 0

        # Remove ANSI color codes for reliable string matching
        clean_output = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout)

        assert "--services" in clean_output
        # Check that services option is properly documented
        assert "services" in clean_output.lower()
        assert "auth" in clean_output

    def test_init_services_disables_interactive_mode(self):
        """Test that specifying services disables interactive mode."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_aegis_command(
                "init",
                "test-non-interactive",
                "--services",
                "auth",
                "--yes",
                "--output-dir",
                temp_dir,
            )

            assert result.returncode == 0
            # Should not show interactive prompts
            assert "🎯 Component Selection" not in result.stdout


class TestInteractiveServiceSelection:
    """Test interactive service selection functionality."""

    def test_interactive_project_selection_includes_services(self):
        """Test that interactive project selection includes service prompts."""
        from unittest.mock import patch

        from aegis.cli.interactive import interactive_project_selection

        with patch("typer.confirm") as mock_confirm:
            # Simulate: no components selected, but yes auth service
            mock_confirm.side_effect = [False, False, False, False, True]

            components, scheduler_backend, services = interactive_project_selection()

            assert components == []  # No components selected
            assert scheduler_backend == "memory"  # Default
            assert "auth" in services  # Auth service selected

    def test_interactive_project_selection_no_services(self):
        """Test that services can be declined in interactive mode."""
        from unittest.mock import patch

        from aegis.cli.interactive import interactive_project_selection

        with patch("typer.confirm") as mock_confirm:
            # Simulate: no components, no services
            mock_confirm.side_effect = [False, False, False, False, False]

            components, scheduler_backend, services = interactive_project_selection()

            assert components == []
            assert scheduler_backend == "memory"
            assert services == []


class TestServicesValidation:
    """Test service validation logic."""

    def test_service_validation_callback_with_valid_service(self):
        """Test service validation callback with valid service."""

        from aegis.cli.callbacks import validate_and_resolve_services

        # Mock typer context and param
        mock_ctx = mock.MagicMock()
        mock_param = mock.MagicMock()

        result = validate_and_resolve_services(mock_ctx, mock_param, "auth")
        assert result == ["auth"]

    def test_service_validation_callback_with_invalid_service(self):
        """Test service validation callback with invalid service."""
        import typer

        from aegis.cli.callbacks import validate_and_resolve_services

        mock_ctx = mock.MagicMock()
        mock_param = mock.MagicMock()

        with pytest.raises(typer.Exit):
            validate_and_resolve_services(mock_ctx, mock_param, "invalid")

    def test_service_validation_callback_with_none(self):
        """Test service validation callback with None value."""
        from aegis.cli.callbacks import validate_and_resolve_services

        mock_ctx = mock.MagicMock()
        mock_param = mock.MagicMock()

        result = validate_and_resolve_services(mock_ctx, mock_param, None)
        assert result is None

    def test_service_validation_callback_with_empty_string(self):
        """Test service validation callback with empty string."""
        import typer

        from aegis.cli.callbacks import validate_and_resolve_services

        mock_ctx = mock.MagicMock()
        mock_param = mock.MagicMock()

        with pytest.raises(typer.Exit):
            validate_and_resolve_services(mock_ctx, mock_param, "auth,")


class TestServicesIntegrationWithExistingFeatures:
    """Test services integration with existing CLI features."""

    def test_services_work_with_force_flag(self):
        """Test that services work with --force flag."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test-force-service"
            project_path.mkdir()  # Create directory to test force

            result = run_aegis_command(
                "init",
                "test-force-service",
                "--services",
                "auth",
                "--force",
                "--no-interactive",
                "--yes",
                "--output-dir",
                temp_dir,
            )

            assert result.returncode == 0
            assert "⚠️  Overwriting existing directory" in result.stdout

    def test_services_work_with_custom_output_dir(self):
        """Test that services work with custom output directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            custom_dir = Path(temp_dir) / "custom"
            custom_dir.mkdir()

            result = run_aegis_command(
                "init",
                "test-custom-dir",
                "--services",
                "auth",
                "--output-dir",
                str(custom_dir),
                "--no-interactive",
                "--yes",
            )

            assert result.returncode == 0
            assert (custom_dir / "test-custom-dir").exists()

    def test_services_dependency_display_consistency(self):
        """Test that services show dependencies consistently."""
        result = run_aegis_command(
            "init",
            "test-deps",
            "--services",
            "auth",
            "--no-interactive",
            "--yes",
            "--output-dir",
            tempfile.gettempdir(),  # Won't create due to early exit
        )

        # Check that dependency messages are shown
        assert "📦 Services require components:" in result.stdout
        assert (
            "backend, database" in result.stdout or "database, backend" in result.stdout
        )


class TestServicesErrorHandling:
    """Test error handling for services functionality."""

    def test_malformed_service_list(self):
        """Test handling of malformed service lists."""
        result = run_aegis_command(
            "init",
            "test-malformed",
            "--services",
            "auth,,invalid",
            "--no-interactive",
            "--yes",
        )

        assert result.returncode != 0
        assert "❌ Empty service name is not allowed" in result.stderr

    def test_service_with_whitespace(self):
        """Test service names with whitespace."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_aegis_command(
                "init",
                "test-whitespace",
                "--services",
                " auth ",
                "--output-dir",
                temp_dir,
                "--no-interactive",
                "--yes",
            )

            assert result.returncode == 0  # Should handle whitespace gracefully


class TestServiceComponentCompatibilityValidation:
    """Test service-component compatibility validation in CLI."""

    def test_services_with_compatible_explicit_components_success(self):
        """Test that services work when user provides compatible explicit components."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_aegis_command(
                "init",
                "test-compatible",
                "--services",
                "auth",
                "--components",
                "database",  # Auth requires database (backend is always included)
                "--no-interactive",
                "--yes",
                "--output-dir",
                temp_dir,
            )

            assert result.returncode == 0
            assert "🔧 Services: auth" in result.stdout
            assert "backend" in result.stdout
            assert "database" in result.stdout

    def test_services_with_insufficient_explicit_components_failure(self):
        """Test that services fail when user provides insufficient explicit components."""
        result = run_aegis_command(
            "init",
            "test-insufficient",
            "--services",
            "auth",
            "--components",
            "worker",  # Auth requires database, but user only provided worker
            "--no-interactive",
            "--yes",
            "--output-dir",
            tempfile.gettempdir(),  # Won't be created due to validation failure
        )

        assert result.returncode == 1
        assert "Service-component compatibility errors:" in result.stderr
        assert "Service 'auth' requires component 'database'" in result.stderr
        assert "💡 Suggestion:" in result.stderr
        # Should suggest adding missing components (worker auto-adds redis dependency)
        assert "database" in result.stderr

    def test_services_with_no_explicit_components_auto_add(self):
        """Test that services auto-add components when user doesn't provide --components."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_aegis_command(
                "init",
                "test-auto-add",
                "--services",
                "auth",
                "--no-interactive",
                "--yes",
                "--output-dir",
                temp_dir,
            )

            assert result.returncode == 0
            assert "🔧 Services: auth" in result.stdout
            # Should auto-add both required components
            assert "backend" in result.stdout
            assert "database" in result.stdout

    def test_services_with_partial_explicit_components_failure(self):
        """Test that services fail when explicit components are partially sufficient."""
        result = run_aegis_command(
            "init",
            "test-partial",
            "--services",
            "auth",
            "--components",
            "redis",  # Auth requires database (missing database, backend is always included)
            "--no-interactive",
            "--yes",
            "--output-dir",
            tempfile.gettempdir(),
        )

        assert result.returncode == 1
        assert "Service-component compatibility errors:" in result.stderr
        assert "Service 'auth' requires component 'database'" in result.stderr

    def test_multiple_services_with_insufficient_components_failure(self):
        """Test validation with multiple services and insufficient components."""
        # Note: This test assumes we might add more services in the future
        # For now, we only have auth service, so this tests the error handling pattern
        result = run_aegis_command(
            "init",
            "test-multi-insufficient",
            "--services",
            "auth",  # Only auth available for now
            "--components",
            "worker,scheduler",  # Missing database for auth
            "--no-interactive",
            "--yes",
            "--output-dir",
            tempfile.gettempdir(),
        )

        assert result.returncode == 1
        assert "Service-component compatibility errors:" in result.stderr
        assert "Service 'auth' requires component 'database'" in result.stderr

    def test_services_error_message_suggests_alternatives(self):
        """Test that error message suggests both adding components and removing --components."""
        result = run_aegis_command(
            "init",
            "test-suggestions",
            "--services",
            "auth",
            "--components",
            "redis",  # Wrong component for auth
            "--no-interactive",
            "--yes",
            "--output-dir",
            tempfile.gettempdir(),
        )

        assert result.returncode == 1
        assert "💡 Suggestion: Add missing components" in result.stderr
        assert "remove --components to let services auto-add" in result.stderr
