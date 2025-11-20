"""
Tests for copier_updater module functions.

These tests validate the backup, rollback, and version management functions.
"""

import subprocess
from pathlib import Path

import pytest

from aegis.core.copier_updater import (
    cleanup_backup_tag,
    create_backup_point,
    rollback_to_backup,
)


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Initialize a git repository with an initial commit."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=tmp_path,
        capture_output=True,
    )

    # Create initial commit
    (tmp_path / "test.txt").write_text("test")
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial"],
        cwd=tmp_path,
        capture_output=True,
    )

    return tmp_path


class TestCreateBackupPoint:
    """Tests for create_backup_point function."""

    def test_creates_backup_tag(self, git_repo: Path) -> None:
        """Test successful backup tag creation."""
        backup_tag = create_backup_point(git_repo)

        assert backup_tag is not None
        assert backup_tag.startswith("aegis-backup-")

        # Verify tag exists
        result = subprocess.run(
            ["git", "tag", "-l", backup_tag],
            cwd=git_repo,
            capture_output=True,
            text=True,
        )
        assert backup_tag in result.stdout

    def test_returns_none_on_failure(self, tmp_path: Path) -> None:
        """Test returns None when not in git repo."""
        # Don't initialize git - should fail
        backup_tag = create_backup_point(tmp_path)

        assert backup_tag is None


class TestRollbackToBackup:
    """Tests for rollback_to_backup function."""

    def test_successful_rollback(self, git_repo: Path) -> None:
        """Test successful rollback to backup point."""
        # Modify the test file to have original content
        test_file = git_repo / "test.txt"
        test_file.write_text("original")
        subprocess.run(["git", "add", "."], cwd=git_repo, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Set original"],
            cwd=git_repo,
            capture_output=True,
        )

        # Create backup
        backup_tag = create_backup_point(git_repo)
        assert backup_tag is not None

        # Make changes
        test_file.write_text("modified")
        subprocess.run(["git", "add", "."], cwd=git_repo, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Modified"],
            cwd=git_repo,
            capture_output=True,
        )

        # Verify file is modified
        assert test_file.read_text() == "modified"

        # Rollback
        success, message = rollback_to_backup(git_repo, backup_tag)

        assert success is True
        assert backup_tag in message
        assert test_file.read_text() == "original"

    def test_rollback_failure(self, git_repo: Path) -> None:
        """Test rollback failure with invalid tag."""
        # Try to rollback to non-existent tag
        success, message = rollback_to_backup(git_repo, "nonexistent-tag")

        assert success is False
        assert "failed" in message.lower()


class TestCleanupBackupTag:
    """Tests for cleanup_backup_tag function."""

    def test_removes_existing_tag(self, git_repo: Path) -> None:
        """Test that cleanup removes an existing tag."""
        # Create backup
        backup_tag = create_backup_point(git_repo)
        assert backup_tag is not None

        # Verify tag exists
        result = subprocess.run(
            ["git", "tag", "-l", backup_tag],
            cwd=git_repo,
            capture_output=True,
            text=True,
        )
        assert backup_tag in result.stdout

        # Cleanup
        cleanup_backup_tag(git_repo, backup_tag)

        # Verify tag is gone
        result = subprocess.run(
            ["git", "tag", "-l", backup_tag],
            cwd=git_repo,
            capture_output=True,
            text=True,
        )
        assert backup_tag not in result.stdout

    def test_handles_nonexistent_tag(self, tmp_path: Path) -> None:
        """Test that cleanup handles non-existent tag gracefully."""
        # Initialize git repo (minimal, just needs to be a git repo)
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)

        # Should not raise exception
        cleanup_backup_tag(tmp_path, "nonexistent-tag")
