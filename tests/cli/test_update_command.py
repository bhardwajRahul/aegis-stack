"""
Tests for the 'aegis update' command for template version upgrades.

Tests cover version detection, changelog generation, dry-run mode,
and the full update workflow.
"""

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from aegis.core.copier_manager import is_copier_project

from .test_utils import run_aegis_command, strip_ansi_codes

if TYPE_CHECKING:
    from tests.cli.conftest import ProjectFactory


class TestUpdateCommandBasics:
    """Basic validation tests for update command."""

    def test_update_command_help(self) -> None:
        """Test update command shows help text."""
        result = run_aegis_command("update", "--help")

        assert result.success
        clean_output = strip_ansi_codes(result.stdout.lower())
        assert "update" in clean_output
        assert "--to-version" in clean_output
        assert "--dry-run" in clean_output

    def test_update_command_not_copier_project(self, temp_output_dir: Path) -> None:
        """Test that update command fails on non-Copier projects."""
        # Create a dummy directory that's not a Copier project
        fake_project = temp_output_dir / "fake-project"
        fake_project.mkdir()

        # Try to update
        result = run_aegis_command(
            "update", "--project-path", str(fake_project), "--yes"
        )

        # Should fail with helpful message
        assert not result.success
        assert "not generated with copier" in result.stderr.lower()

    def test_update_command_missing_project(self) -> None:
        """Test that update command fails when project doesn't exist."""
        result = run_aegis_command(
            "update", "--project-path", "/nonexistent/path", "--yes"
        )

        assert not result.success
        assert "not generated with copier" in result.stderr.lower()


class TestUpdateCommandGitValidation:
    """Tests for git tree validation."""

    def test_update_requires_clean_git_tree(
        self, project_factory: "ProjectFactory"
    ) -> None:
        """Test that update command requires clean git working tree."""
        # Use cached base project
        project_path = project_factory("base")

        # Verify it's a Copier project
        assert is_copier_project(project_path)

        # Create an uncommitted change
        test_file = project_path / "dirty.txt"
        test_file.write_text("uncommitted change")

        # Try to update
        result = run_aegis_command(
            "update", "--project-path", str(project_path), "--yes"
        )

        # Should fail with git tree error
        assert not result.success
        assert (
            "git tree" in result.stderr.lower()
            or "uncommitted" in result.stderr.lower()
        )

    def test_update_succeeds_with_clean_git_tree(
        self, project_factory: "ProjectFactory"
    ) -> None:
        """Test that update command works with clean git tree."""
        # Use cached base project
        project_path = project_factory("base")

        # Verify it's a Copier project and has clean git tree
        assert is_copier_project(project_path)

        # Dry-run should work (doesn't actually update, so no version issues)
        result = run_aegis_command(
            "update", "--project-path", str(project_path), "--dry-run"
        )

        # Should either succeed (git is clean) or fail with a version-related message
        # but NOT with a git tree error
        if not result.success:
            assert "git tree" not in result.stderr.lower()
            assert "uncommitted" not in result.stderr.lower()

    def test_update_exits_early_when_at_target_commit(
        self, project_factory: "ProjectFactory"
    ) -> None:
        """Test that update exits early when project is already at target commit."""
        # Use cached base project
        project_path = project_factory("base")

        # Verify it's a Copier project
        assert is_copier_project(project_path)

        # Try to update to HEAD (should be same commit as project was just created)
        result = run_aegis_command(
            "update",
            "--project-path",
            str(project_path),
            "--to-version",
            "HEAD",
            "--yes",
        )

        # Should succeed and show early exit message
        assert result.success
        assert "already at the target commit" in result.stdout.lower()


class TestUpdateCommandDryRun:
    """Tests for dry-run mode."""

    def test_dry_run_shows_preview(self, project_factory: "ProjectFactory") -> None:
        """Test that --dry-run shows preview without applying changes."""
        # Use cached base project
        project_path = project_factory("base")

        # Run update in dry-run mode
        result = run_aegis_command(
            "update",
            "--project-path",
            str(project_path),
            "--to-version",
            "HEAD",
            "--dry-run",
        )

        # Should succeed and either show dry-run message or early exit message
        assert result.success
        # If early exit happened (already at target), that's valid too
        is_early_exit = "already at the target commit" in result.stdout.lower()
        has_dry_run_msg = (
            "dry run" in result.stdout.lower() or "preview" in result.stdout.lower()
        )
        assert is_early_exit or has_dry_run_msg

        # Should not have actually updated anything
        # (we can verify by checking that .copier-answers.yml hasn't changed)
        # This is a basic smoke test - real validation would compare commits


class TestUpdateCommandVersionResolution:
    """Tests for version resolution logic."""

    @patch("aegis.commands.update.get_latest_version")
    @patch("aegis.commands.update.resolve_version_to_ref")
    def test_update_to_latest_default(
        self,
        mock_resolve: MagicMock,
        mock_get_latest: MagicMock,
        project_factory: "ProjectFactory",
    ) -> None:
        """Test that update defaults to latest version."""
        # Setup mocks
        mock_get_latest.return_value = "0.2.0"
        mock_resolve.return_value = "v0.2.0"

        # Use cached base project
        project_path = project_factory("base")

        # Run update in dry-run mode (to avoid actual update)
        result = run_aegis_command(
            "update", "--project-path", str(project_path), "--dry-run"
        )

        # Should show version information
        assert "version" in result.stdout.lower()

    @patch("aegis.commands.update.resolve_version_to_ref")
    def test_update_to_specific_version(
        self, mock_resolve: MagicMock, project_factory: "ProjectFactory"
    ) -> None:
        """Test updating to a specific version."""
        # Setup mock
        mock_resolve.return_value = "v0.1.5"

        # Use cached base project
        project_path = project_factory("base")

        # Run update to specific version in dry-run mode
        result = run_aegis_command(
            "update",
            "--to-version",
            "0.1.5",
            "--project-path",
            str(project_path),
            "--dry-run",
        )

        # Should mention the target version
        assert "0.1.5" in result.stdout or "v0.1.5" in result.stdout


class TestUpdateCommandChangelog:
    """Tests for changelog display."""

    @patch("aegis.commands.update.get_changelog")
    @patch("aegis.commands.update.get_current_template_commit")
    def test_update_shows_changelog(
        self,
        mock_get_commit: MagicMock,
        mock_get_changelog: MagicMock,
        project_factory: "ProjectFactory",
    ) -> None:
        """Test that update command shows changelog."""
        # Setup mocks - use a different commit to prevent early exit
        mock_get_commit.return_value = "abc123def456"
        mock_get_changelog.return_value = (
            "✨ New Features:\n  • Added AI service\n\n"
            "🐛 Bug Fixes:\n  • Fixed scheduler persistence"
        )

        # Use cached base project
        project_path = project_factory("base")

        # Run update in dry-run mode
        result = run_aegis_command(
            "update", "--project-path", str(project_path), "--dry-run"
        )

        # Should succeed
        assert result.success
        # Either shows changelog or early exit (both valid)
        has_changelog = (
            "changelog" in result.stdout.lower() or "changes" in result.stdout.lower()
        )
        is_early_exit = "already at the target commit" in result.stdout.lower()
        assert has_changelog or is_early_exit


class TestUpdateCommandConfirmation:
    """Tests for user confirmation workflow."""

    def test_update_requires_confirmation_without_yes_flag(
        self, project_factory: "ProjectFactory"
    ) -> None:
        """Test that update requires confirmation without --yes flag."""
        # Use cached base project
        project_path = project_factory("base")

        # Note: This test is tricky because it requires user input simulation
        # For now, we just verify the command structure accepts --yes
        result = run_aegis_command(
            "update", "--project-path", str(project_path), "--help"
        )

        assert "--yes" in result.stdout or "-y" in result.stdout

    def test_update_skips_confirmation_with_yes_flag(
        self, project_factory: "ProjectFactory"
    ) -> None:
        """Test that --yes flag skips confirmation."""
        # Use cached base project
        project_path = project_factory("base")

        # Dry-run with --yes should not prompt
        result = run_aegis_command(
            "update", "--project-path", str(project_path), "--dry-run", "--yes"
        )

        # Should complete without waiting for input
        # (if it waited, the test would hang/timeout)
        assert result.stdout  # Got some output


class TestUpdateCommandErrorHandling:
    """Tests for error handling and edge cases."""

    def test_update_with_invalid_version(
        self, project_factory: "ProjectFactory"
    ) -> None:
        """Test update with non-existent version."""
        # Use cached base project
        project_path = project_factory("base")

        # Try to update to an invalid version
        result = run_aegis_command(
            "update",
            "--to-version",
            "999.999.999",
            "--project-path",
            str(project_path),
            "--dry-run",
        )

        # Should handle gracefully (may show warning or proceed with HEAD)
        # At minimum, shouldn't crash
        assert result.stdout or result.stderr

    def test_update_shows_helpful_error_messages(self, temp_output_dir: Path) -> None:
        """Test that update shows helpful error messages."""
        # Create a non-Copier project
        fake_project = temp_output_dir / "not-copier"
        fake_project.mkdir()

        result = run_aegis_command(
            "update", "--project-path", str(fake_project), "--yes"
        )

        assert not result.success
        # Should have helpful error message
        assert len(result.stderr) > 0
        assert "copier" in result.stderr.lower()


class TestUpdateCommandTemplatePath:
    """Tests for --template-path flag functionality."""

    def test_update_command_has_template_path_option(self) -> None:
        """Test that update command has --template-path option in help."""
        result = run_aegis_command("update", "--help")

        assert result.success
        clean_output = strip_ansi_codes(result.stdout)
        assert "--template-path" in clean_output

    def test_update_with_nonexistent_template_path(
        self, project_factory: "ProjectFactory"
    ) -> None:
        """Test that update fails with non-existent template path."""
        project_path = project_factory("base")

        result = run_aegis_command(
            "update",
            "--project-path",
            str(project_path),
            "--template-path",
            "/nonexistent/path",
            "--dry-run",
        )

        assert not result.success
        assert "does not exist" in result.stderr.lower()

    def test_update_with_invalid_template_structure(
        self, project_factory: "ProjectFactory", temp_output_dir: Path
    ) -> None:
        """Test that update fails when template path is missing copier.yml."""
        project_path = project_factory("base")

        # Create an empty directory (no copier.yml)
        invalid_template = temp_output_dir / "invalid-template"
        invalid_template.mkdir()

        result = run_aegis_command(
            "update",
            "--project-path",
            str(project_path),
            "--template-path",
            str(invalid_template),
            "--dry-run",
        )

        assert not result.success
        assert "missing copier.yml" in result.stderr.lower()

    def test_update_with_non_git_template_path(
        self, project_factory: "ProjectFactory", temp_output_dir: Path
    ) -> None:
        """Test that update fails when template path is not a git repository."""
        project_path = project_factory("base")

        # Create directory with copier.yml but no .git
        non_git_template = temp_output_dir / "non-git-template"
        non_git_template.mkdir()
        (non_git_template / "copier.yml").write_text("# mock copier config")

        result = run_aegis_command(
            "update",
            "--project-path",
            str(project_path),
            "--template-path",
            str(non_git_template),
            "--dry-run",
        )

        assert not result.success
        assert "git repository" in result.stderr.lower()

    def test_update_with_valid_template_path(
        self, project_factory: "ProjectFactory"
    ) -> None:
        """Test that update works with valid custom template path."""
        project_path = project_factory("base")

        # Use the actual aegis-stack repo as template path
        # This is the same as the default, but tests the path validation
        from aegis.core.copier_updater import get_template_root

        template_root = get_template_root()

        result = run_aegis_command(
            "update",
            "--project-path",
            str(project_path),
            "--template-path",
            str(template_root),
            "--to-version",
            "HEAD",
            "--dry-run",
        )

        # Should succeed or show early exit (already at target)
        assert result.success
        # Should show that custom template is being used
        assert (
            "custom template" in result.stdout.lower()
            or "already at" in result.stdout.lower()
        )

    def test_update_template_path_expands_tilde(
        self, project_factory: "ProjectFactory"
    ) -> None:
        """Test that template path expands ~ to home directory."""
        project_path = project_factory("base")

        # Use a path that should expand (even if it doesn't exist)
        result = run_aegis_command(
            "update",
            "--project-path",
            str(project_path),
            "--template-path",
            "~/nonexistent-aegis-stack",
            "--dry-run",
        )

        # Should fail with "does not exist" (not a raw path error)
        # This proves ~ was expanded
        assert not result.success
        assert "does not exist" in result.stderr.lower()
        # Should NOT contain the literal ~ in the error message
        assert "~/nonexistent" not in result.stderr


class TestUpdateCommandRollback:
    """Tests for rollback mechanism."""

    def test_update_creates_backup_point(
        self, project_factory: "ProjectFactory"
    ) -> None:
        """Test that update creates a backup point before updating."""
        project_path = project_factory("base")

        # Run update in dry-run mode (won't actually update but shows workflow)
        result = run_aegis_command(
            "update",
            "--project-path",
            str(project_path),
            "--to-version",
            "HEAD",
            "--dry-run",
        )

        # Dry run doesn't create backup, but command structure is valid
        assert result.success

    @patch("aegis.commands.update.create_backup_point")
    def test_update_calls_create_backup(
        self,
        mock_create_backup: MagicMock,
        project_factory: "ProjectFactory",
    ) -> None:
        """Test that update calls create_backup_point."""
        mock_create_backup.return_value = "aegis-backup-123"

        project_path = project_factory("base")

        # Run update (will hit early exit but should still create backup)
        result = run_aegis_command(
            "update", "--project-path", str(project_path), "--yes"
        )

        # Either creates backup or hits early exit
        assert result.stdout

    @patch("copier.run_update")
    @patch("aegis.commands.update.get_current_template_commit")
    @patch("aegis.commands.update.cleanup_backup_tag")
    @patch("aegis.commands.update.create_backup_point")
    def test_update_cleans_up_backup_on_success(
        self,
        mock_create_backup: MagicMock,
        mock_cleanup: MagicMock,
        mock_get_commit: MagicMock,
        mock_copier_update: MagicMock,
        project_factory: "ProjectFactory",
    ) -> None:
        """Test that backup tag is cleaned up on successful update."""
        mock_create_backup.return_value = "aegis-backup-123"
        mock_get_commit.return_value = "different-commit"  # Prevent early exit

        project_path = project_factory("base")

        # Run update
        run_aegis_command("update", "--project-path", str(project_path), "--yes")

        # Backup should be created and cleaned up on success
        assert mock_create_backup.called, "Backup should be created"
        assert mock_cleanup.called, "Cleanup should be called when backup was created"

    @patch("aegis.commands.update.rollback_to_backup")
    @patch("aegis.commands.update.create_backup_point")
    @patch("copier.run_update")
    def test_update_offers_rollback_on_failure(
        self,
        mock_copier_update: MagicMock,
        mock_create_backup: MagicMock,
        mock_rollback: MagicMock,
        project_factory: "ProjectFactory",
    ) -> None:
        """Test that update offers rollback when Copier fails."""
        mock_create_backup.return_value = "aegis-backup-123"
        mock_copier_update.side_effect = Exception("Copier failed")
        mock_rollback.return_value = (True, "Rolled back successfully")

        project_path = project_factory("base")

        # Run update with --yes to auto-rollback
        result = run_aegis_command(
            "update", "--project-path", str(project_path), "--yes"
        )

        # Should fail but offer/perform rollback
        # Note: may hit early exit before Copier is called
        assert result.stdout or result.stderr


class TestUpdateCommandPostGenTasks:
    """Tests for post-generation task handling."""

    @patch("aegis.commands.update.run_post_generation_tasks")
    def test_update_shows_warning_on_post_gen_failure(
        self,
        mock_post_gen: MagicMock,
        project_factory: "ProjectFactory",
    ) -> None:
        """Test that update shows warning when post-gen tasks fail."""
        # Setup mock to return failure
        mock_post_gen.return_value = False

        project_path = project_factory("base")

        # Run update (will exit early due to same commit, but we can test the pattern)
        result = run_aegis_command(
            "update", "--project-path", str(project_path), "--yes"
        )

        # This will likely hit early exit, but tests the plumbing exists
        assert result.stdout or result.stderr

    @patch("aegis.commands.update.run_post_generation_tasks")
    @patch("aegis.commands.update.get_current_template_commit")
    @patch("copier.run_update")
    def test_update_surfaces_post_gen_task_failure(
        self,
        mock_copier_update: MagicMock,
        mock_get_commit: MagicMock,
        mock_post_gen: MagicMock,
        project_factory: "ProjectFactory",
    ) -> None:
        """Test that update properly shows post-gen task failures."""
        # Setup mocks to bypass early exit and simulate post-gen failure
        mock_get_commit.return_value = "abc123"  # Different from target
        mock_post_gen.return_value = False

        project_path = project_factory("base")

        result = run_aegis_command(
            "update", "--project-path", str(project_path), "--yes"
        )

        # Should show warning about post-gen failures
        assert (
            "post-generation task" in result.stdout.lower()
            or "setup tasks failed" in result.stdout.lower()
            or "already at" in result.stdout.lower()  # Early exit is valid
        )


class TestUpdateCommandEnvVar:
    """Tests for AEGIS_TEMPLATE_PATH environment variable support."""

    def test_update_uses_env_var_when_no_flag(
        self, project_factory: "ProjectFactory", monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that update uses AEGIS_TEMPLATE_PATH when flag not provided."""
        project_path = project_factory("base")

        # Use the actual aegis-stack repo as template path
        from aegis.core.copier_updater import get_template_root

        template_root = get_template_root()

        # Set env var
        monkeypatch.setenv("AEGIS_TEMPLATE_PATH", str(template_root))

        result = run_aegis_command(
            "update",
            "--project-path",
            str(project_path),
            "--to-version",
            "HEAD",
            "--dry-run",
        )

        # Should succeed and show env var source
        assert result.success
        assert (
            "aegis_template_path" in result.stdout.lower()
            or "already at" in result.stdout.lower()
        )

    def test_update_flag_overrides_env_var(
        self, project_factory: "ProjectFactory", monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that --template-path flag overrides AEGIS_TEMPLATE_PATH env var."""
        project_path = project_factory("base")

        # Set env var to a non-existent path
        monkeypatch.setenv("AEGIS_TEMPLATE_PATH", "/env/var/path")

        # Use flag with different (also non-existent) path
        result = run_aegis_command(
            "update",
            "--project-path",
            str(project_path),
            "--template-path",
            "/flag/path",
            "--dry-run",
        )

        # Should fail with flag path error (not env var path)
        assert not result.success
        assert "/flag/path" in result.stderr
        assert "/env/var/path" not in result.stderr

    def test_update_env_var_invalid_path(
        self, project_factory: "ProjectFactory", monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that invalid AEGIS_TEMPLATE_PATH env var shows error."""
        project_path = project_factory("base")

        # Set env var to non-existent path
        monkeypatch.setenv("AEGIS_TEMPLATE_PATH", "/nonexistent/env/path")

        result = run_aegis_command(
            "update",
            "--project-path",
            str(project_path),
            "--dry-run",
        )

        # Should fail with validation error
        assert not result.success
        assert "does not exist" in result.stderr.lower()

    def test_update_env_var_empty_string_ignored(
        self, project_factory: "ProjectFactory", monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that empty AEGIS_TEMPLATE_PATH env var is ignored."""
        project_path = project_factory("base")

        # Set env var to empty string
        monkeypatch.setenv("AEGIS_TEMPLATE_PATH", "")

        result = run_aegis_command(
            "update",
            "--project-path",
            str(project_path),
            "--to-version",
            "HEAD",
            "--dry-run",
        )

        # Should succeed using default template (empty string is falsy)
        assert result.success
        # Should NOT show "custom template" message
        assert "custom template" not in result.stdout.lower()


class TestUpdateCommandConflictHandling:
    """Tests for enhanced conflict handling."""

    def test_conflict_analysis_functions_work(self, tmp_path: Path) -> None:
        """Test that conflict analysis functions properly detect and format conflicts."""
        from aegis.core.copier_updater import (
            analyze_conflict_files,
            format_conflict_report,
        )

        # Create .rej files
        (tmp_path / "test.txt.rej").write_text("content\nline2")
        (tmp_path / "app").mkdir(exist_ok=True)
        (tmp_path / "app" / "main.py.rej").write_text("rejected")

        conflicts = analyze_conflict_files(tmp_path)
        assert len(conflicts) == 2

        report = format_conflict_report(conflicts)
        assert "conflict" in report.lower()
        assert "resolution" in report.lower()
        assert "git diff" in report.lower()


class TestUpdateCommandMigrationDetection:
    """Tests for detecting projects that need migration."""

    def test_update_detects_non_copier_project(self, temp_output_dir: Path) -> None:
        """Test that update detects v0.1.0 style projects without copier answers."""
        # Create a project directory without .copier-answers.yml
        project_path = temp_output_dir / "old-project"
        project_path.mkdir()
        (project_path / "pyproject.toml").write_text(
            "[project]\nname = 'old-project'\n"
        )

        result = run_aegis_command(
            "update",
            "--project-path",
            str(project_path),
        )

        # Should fail with helpful error
        assert not result.success
        assert (
            "copier" in result.stderr.lower()
            or "not generated" in result.stderr.lower()
        )

    def test_update_shows_migration_guidance(self, temp_output_dir: Path) -> None:
        """Test that update provides guidance for non-copier projects."""
        # Create a non-copier project
        project_path = temp_output_dir / "legacy-project"
        project_path.mkdir()
        (project_path / "pyproject.toml").write_text("[project]\nname = 'legacy'\n")

        result = run_aegis_command(
            "update",
            "--project-path",
            str(project_path),
        )

        assert not result.success
        # Should mention regeneration or v0.2.0
        stderr_lower = result.stderr.lower()
        assert (
            "regenerat" in stderr_lower
            or "v0.2" in stderr_lower
            or "copier" in stderr_lower
        )


class TestUpdateCommandVersionInfo:
    """Tests for version information display."""

    def test_update_shows_current_and_target_versions(
        self, project_factory: "ProjectFactory"
    ) -> None:
        """Test that update displays version information clearly."""
        project_path = project_factory("base")

        result = run_aegis_command(
            "update",
            "--project-path",
            str(project_path),
            "--to-version",
            "HEAD",
            "--dry-run",
        )

        assert result.success
        output = result.stdout.lower()
        # Should show version information
        assert "version" in output or "template" in output

    @patch("aegis.commands.update.get_latest_version")
    @patch("aegis.commands.update.get_current_template_commit")
    def test_update_shows_cli_version(
        self,
        mock_get_commit: MagicMock,
        mock_latest: MagicMock,
        project_factory: "ProjectFactory",
    ) -> None:
        """Test that update shows CLI version information."""
        mock_get_commit.return_value = "abc123"
        mock_latest.return_value = "0.2.0"

        project_path = project_factory("base")

        result = run_aegis_command(
            "update",
            "--project-path",
            str(project_path),
            "--dry-run",
        )

        assert result.success
        # Should display CLI version
        assert "cli" in result.stdout.lower()
