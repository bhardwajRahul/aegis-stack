"""
Tests for copier_updater module functions.

These tests validate the backup, rollback, and version management functions.
"""

import subprocess
from pathlib import Path

import pytest

from aegis.core.copier_updater import (
    analyze_conflict_files,
    cleanup_backup_tag,
    create_backup_point,
    format_conflict_report,
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


class TestAnalyzeConflictFiles:
    """Tests for analyze_conflict_files function."""

    def test_finds_rej_files(self, tmp_path: Path) -> None:
        """Test that .rej files are detected and analyzed."""
        # Create some .rej files
        rej_file = tmp_path / "test.txt.rej"
        rej_file.write_text("rejected content\nline 2\nline 3")

        conflicts = analyze_conflict_files(tmp_path)

        assert len(conflicts) == 1
        assert conflicts[0]["original"] == "test.txt"
        assert conflicts[0]["path"] == "test.txt.rej"
        assert "3 lines in conflict file" in conflicts[0]["summary"]

    def test_handles_nested_rej_files(self, tmp_path: Path) -> None:
        """Test that nested .rej files are found."""
        # Create nested directory structure
        nested_dir = tmp_path / "app" / "core"
        nested_dir.mkdir(parents=True)
        rej_file = nested_dir / "config.py.rej"
        rej_file.write_text("rejected changes")

        conflicts = analyze_conflict_files(tmp_path)

        assert len(conflicts) == 1
        assert "app/core/config.py" in conflicts[0]["original"]

    def test_handles_no_conflicts(self, tmp_path: Path) -> None:
        """Test that empty list is returned when no .rej files exist."""
        # Create some regular files
        (tmp_path / "test.txt").write_text("normal content")

        conflicts = analyze_conflict_files(tmp_path)

        assert conflicts == []

    def test_handles_multiple_conflicts(self, tmp_path: Path) -> None:
        """Test handling of multiple .rej files."""
        # Create multiple .rej files
        (tmp_path / "file1.txt.rej").write_text("conflict 1")
        (tmp_path / "file2.py.rej").write_text("conflict 2\nmore")
        (tmp_path / "file3.md.rej").write_text("conflict 3\na\nb")

        conflicts = analyze_conflict_files(tmp_path)

        assert len(conflicts) == 3


class TestFormatConflictReport:
    """Tests for format_conflict_report function."""

    def test_formats_single_conflict(self) -> None:
        """Test formatting of a single conflict."""
        conflicts = [
            {
                "path": "test.txt.rej",
                "original": "test.txt",
                "size": "100 bytes",
                "summary": "5 rejected change(s)",
            }
        ]

        report = format_conflict_report(conflicts)

        assert "Conflicts detected" in report
        assert "test.txt" in report
        assert "test.txt.rej" in report
        assert "5 rejected change(s)" in report
        assert "Resolution steps" in report

    def test_formats_multiple_conflicts(self) -> None:
        """Test formatting of multiple conflicts."""
        conflicts = [
            {
                "path": "file1.rej",
                "original": "file1",
                "size": "50 bytes",
                "summary": "2 rejected change(s)",
            },
            {
                "path": "file2.rej",
                "original": "file2",
                "size": "100 bytes",
                "summary": "3 rejected change(s)",
            },
        ]

        report = format_conflict_report(conflicts)

        assert "file1" in report
        assert "file2" in report
        assert "git diff" in report

    def test_returns_empty_for_no_conflicts(self) -> None:
        """Test that empty string is returned for no conflicts."""
        report = format_conflict_report([])

        assert report == ""
