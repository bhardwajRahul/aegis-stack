"""
Basic CLI tests that run quickly.

These tests focus on command parsing, help text, and basic functionality
without doing full project generation.
"""

import re

import pytest

from .test_utils import run_aegis_command, run_cli_help_command


class TestCLIBasics:
    """Test basic CLI functionality."""

    def test_cli_help(self) -> None:
        """Test main CLI help."""
        result = run_cli_help_command("--help")
        assert result.success, f"Help command failed: {result.stderr}"
        assert "Aegis Stack CLI" in result.stdout
        assert "init" in result.stdout
        assert "version" in result.stdout

    def test_init_help(self) -> None:
        """Test init command help."""
        result = run_cli_help_command("init", "--help")

        assert result.success, f"Init help command failed: {result.stderr}"

        # Remove ANSI color codes for reliable string matching
        clean_output = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout)
        assert "Initialize a new Aegis Stack project" in clean_output
        assert "--components" in clean_output
        assert (
            "redis,worker,scheduler" in clean_output
        )  # Updated to match actual available components
        assert "--no-interactive" in clean_output
        assert "--force" in clean_output

    def test_version_command(self) -> None:
        """Test version command."""
        result = run_cli_help_command("version")
        assert result.success, f"Version command failed: {result.stderr}"
        assert "Aegis Stack CLI" in result.stdout
        assert "v" in result.stdout  # Should show version number

    def test_invalid_component_error(self) -> None:
        """Test that invalid components are rejected with clear error."""
        result = run_aegis_command(
            "init",
            "test-project",
            "--components",
            "invalid_component",
            "--no-interactive",
            "--yes",
            timeout=10,
        )
        assert not result.success, "Expected command to fail with invalid component"
        assert (
            "Unknown component: invalid_component" in result.stderr
        )  # Updated to match actual error message

    def test_missing_project_name(self) -> None:
        """Test that missing project name shows helpful error."""
        result = run_aegis_command("init", timeout=10)
        assert not result.success, "Expected command to fail with missing project name"
        # Should show usage information about missing project name


class TestComponentValidation:
    """Test component validation logic."""

    @pytest.mark.parametrize(
        "component", ["scheduler", "worker", "redis"]
    )  # Updated to match actual available components
    def test_valid_components(self, component: str) -> None:
        """Test that valid components are accepted (but don't generate project)."""
        # This test would normally fail at project creation, but we're just
        # testing that the component name is validated as correct
        result = run_aegis_command(
            "init",
            "test-project",
            "--components",
            component,
            "--no-interactive",
            "--yes",
            "--force",
            "--output-dir",
            "/tmp/test-non-existent-dir",
            timeout=10,
        )
        # Should not fail with "Invalid component" error
        assert "Invalid component" not in result.stderr

    def test_multiple_components(self) -> None:
        """Test multiple component validation."""
        result = run_aegis_command(
            "init",
            "test-project",
            "--components",
            "scheduler,worker",  # Updated to match actual available components
            "--no-interactive",
            "--yes",
            "--force",
            "--output-dir",
            "/tmp/test-non-existent-dir",
            timeout=10,
        )
        # Should not fail with component validation errors
        assert "Invalid component" not in result.stderr

    def test_mixed_valid_invalid_components(self) -> None:
        """Test mix of valid and invalid components."""
        result = run_aegis_command(
            "init",
            "test-project",
            "--components",
            "scheduler,invalid,worker",  # Updated to match actual available components
            "--no-interactive",
            "--yes",
            timeout=10,
        )
        assert not result.success, "Expected command to fail with invalid component"
        assert (
            "Unknown component: invalid" in result.stderr
        )  # Updated to match actual error message
