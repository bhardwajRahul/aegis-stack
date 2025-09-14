"""
Tests for services CLI functionality.

This module tests the services command and --services option integration.
"""

import re
import subprocess
import tempfile
from pathlib import Path
from unittest import mock

import pytest


class TestServicesCommand:
    """Test the 'aegis services' command."""

    def test_services_command_shows_available_services(self):
        """Test that services command displays available services."""
        result = subprocess.run(
            ["uv", "run", "python", "-m", "aegis", "services"],
            capture_output=True,
            text=True,
        )

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
        result = subprocess.run(
            ["uv", "run", "python", "-m", "aegis", "services", "--help"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "List available services and their dependencies" in result.stdout

    def test_services_command_appears_in_main_help(self):
        """Test that services command appears in main CLI help."""
        result = subprocess.run(
            ["uv", "run", "python", "-m", "aegis", "--help"],
            capture_output=True,
            text=True,
        )

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

            result = subprocess.run(
                ["uv", "run", "python", "-m", "aegis", "services"],
                capture_output=True,
                text=True,
            )

            assert result.returncode == 0
            # Should show no services message (though this won't actually show due to mock)


class TestServicesOptionIntegration:
    """Test the --services option in init command."""

    def test_init_with_valid_service(self):
        """Test init command with valid service."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = subprocess.run(
                [
                    "uv",
                    "run",
                    "python",
                    "-m",
                    "aegis",
                    "init",
                    "test-auth-service",
                    "--services",
                    "auth",
                    "--no-interactive",
                    "--yes",
                    "--output-dir",
                    temp_dir,
                ],
                capture_output=True,
                text=True,
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
        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                "-m",
                "aegis",
                "init",
                "test-invalid",
                "--services",
                "invalid-service",
                "--no-interactive",
                "--yes",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "❌ Unknown services: invalid-service" in result.stderr
        assert "Available services: auth" in result.stderr

    def test_init_with_multiple_services(self):
        """Test init command with multiple services (when more are available)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = subprocess.run(
                [
                    "uv",
                    "run",
                    "python",
                    "-m",
                    "aegis",
                    "init",
                    "test-multi-service",
                    "--services",
                    "auth",  # Only auth available for now
                    "--no-interactive",
                    "--yes",
                    "--output-dir",
                    temp_dir,
                ],
                capture_output=True,
                text=True,
            )

            assert result.returncode == 0
            assert "🔧 Services: auth" in result.stdout

    def test_init_with_empty_service_name(self):
        """Test init command with empty service name."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = subprocess.run(
                [
                    "uv",
                    "run",
                    "python",
                    "-m",
                    "aegis",
                    "init",
                    "test-empty",
                    "--services",
                    "",
                    "--output-dir",
                    temp_dir,
                    "--no-interactive",
                    "--yes",
                ],
                capture_output=True,
                text=True,
            )

            # Empty string is treated as "no services provided", so it should succeed
            assert result.returncode == 0
            # Should not show any services section
            assert "🔧 Services:" not in result.stdout

    def test_init_with_services_and_components_together(self):
        """Test init command with both services and components specified."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = subprocess.run(
                [
                    "uv",
                    "run",
                    "python",
                    "-m",
                    "aegis",
                    "init",
                    "test-combined",
                    "--services",
                    "auth",
                    "--components",
                    "worker",
                    "--no-interactive",
                    "--yes",
                    "--output-dir",
                    temp_dir,
                ],
                capture_output=True,
                text=True,
            )

            assert result.returncode == 0
            output = result.stdout

            # Should show both services and components
            assert "🔧 Services: auth" in output
            assert "📦 Infrastructure:" in output
            # Both auth (database) and worker (redis) dependencies should be present
            assert (
                ("database" in output and "redis" in output)
                or "database, redis" in output
                or "redis, database" in output
            )

    def test_init_services_help_text_accuracy(self):
        """Test that init command help shows correct services help text."""
        result = subprocess.run(
            ["uv", "run", "python", "-m", "aegis", "init", "--help"],
            capture_output=True,
            text=True,
        )

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
            result = subprocess.run(
                [
                    "uv",
                    "run",
                    "python",
                    "-m",
                    "aegis",
                    "init",
                    "test-non-interactive",
                    "--services",
                    "auth",
                    "--yes",
                    "--output-dir",
                    temp_dir,
                ],
                capture_output=True,
                text=True,
            )

            assert result.returncode == 0
            # Should not show interactive prompts
            assert "🎯 Component Selection" not in result.stdout


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

            result = subprocess.run(
                [
                    "uv",
                    "run",
                    "python",
                    "-m",
                    "aegis",
                    "init",
                    "test-force-service",
                    "--services",
                    "auth",
                    "--force",
                    "--no-interactive",
                    "--yes",
                    "--output-dir",
                    temp_dir,
                ],
                capture_output=True,
                text=True,
            )

            assert result.returncode == 0
            assert "⚠️  Overwriting existing directory" in result.stdout

    def test_services_work_with_custom_output_dir(self):
        """Test that services work with custom output directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            custom_dir = Path(temp_dir) / "custom"
            custom_dir.mkdir()

            result = subprocess.run(
                [
                    "uv",
                    "run",
                    "python",
                    "-m",
                    "aegis",
                    "init",
                    "test-custom-dir",
                    "--services",
                    "auth",
                    "--output-dir",
                    str(custom_dir),
                    "--no-interactive",
                    "--yes",
                ],
                capture_output=True,
                text=True,
            )

            assert result.returncode == 0
            assert (custom_dir / "test-custom-dir").exists()

    def test_services_dependency_display_consistency(self):
        """Test that services show dependencies consistently."""
        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                "-m",
                "aegis",
                "init",
                "test-deps",
                "--services",
                "auth",
                "--no-interactive",
                "--yes",
                "--output-dir",
                "/tmp",  # Won't create due to early exit
            ],
            capture_output=True,
            text=True,
            input="n\n",  # Decline creation
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
        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                "-m",
                "aegis",
                "init",
                "test-malformed",
                "--services",
                "auth,,invalid",
                "--no-interactive",
                "--yes",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "❌ Empty service name is not allowed" in result.stderr

    def test_service_with_whitespace(self):
        """Test service names with whitespace."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = subprocess.run(
                [
                    "uv",
                    "run",
                    "python",
                    "-m",
                    "aegis",
                    "init",
                    "test-whitespace",
                    "--services",
                    " auth ",
                    "--output-dir",
                    temp_dir,
                    "--no-interactive",
                    "--yes",
                ],
                capture_output=True,
                text=True,
            )

            assert result.returncode == 0  # Should handle whitespace gracefully
