"""Integration tests for aegis update command with version management."""

import subprocess
from pathlib import Path

import pytest


class TestUpdateIntegration:
    """Test update command functionality with version management."""

    @pytest.fixture
    def template_path(self) -> Path:
        """Get path to aegis-stack repository root."""
        return Path(__file__).parents[2]

    @pytest.fixture
    def old_commit_hash(self, template_path: Path) -> str:
        """Get commit hash from an older commit for testing upgrades."""
        # Try progressively fewer commits back to handle shallow clones in CI
        for commits_back in [10, 5, 1]:
            result = subprocess.run(
                ["git", "rev-parse", f"HEAD~{commits_back}"],
                cwd=template_path,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                return result.stdout.strip()

        # If no history available, skip tests that need old commits
        # Note: pytest.skip() raises an exception, so this never actually returns None
        pytest.skip("Insufficient git history (shallow clone)")
        return ""  # Unreachable, but satisfies type checker

    def test_init_with_to_version(
        self, tmp_path: Path, template_path: Path, old_commit_hash: str
    ) -> None:
        """Test generating project from specific version."""
        # Generate project from old commit
        # Use --python-version 3.11 to ensure compatibility with old template versions
        result = subprocess.run(
            [
                "aegis",
                "init",
                "test-project",
                "--to-version",
                old_commit_hash,
                "--python-version",
                "3.11",
                "--no-interactive",
                "--yes",
            ],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"Init failed: {result.stderr}"
        assert "Template Version:" in result.stdout
        project_path = tmp_path / "test-project"
        assert project_path.exists()

        # Verify .copier-answers.yml has the old commit
        answers_file = project_path / ".copier-answers.yml"
        assert answers_file.exists()
        content = answers_file.read_text()
        assert old_commit_hash[:8] in content

    def test_update_from_old_to_head(
        self, tmp_path: Path, template_path: Path, old_commit_hash: str
    ) -> None:
        """Test updating from old commit to HEAD."""
        # Generate project from old commit
        # Use --python-version 3.11 to ensure compatibility with old template versions
        subprocess.run(
            [
                "aegis",
                "init",
                "test-project",
                "--to-version",
                old_commit_hash,
                "--python-version",
                "3.11",
                "--no-interactive",
                "--yes",
            ],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=True,
        )

        project_dir = tmp_path / "test-project"

        # Get current HEAD commit
        result_head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=template_path,
            capture_output=True,
            text=True,
            check=True,
        )
        head_commit = result_head.stdout.strip()

        # Update to HEAD explicitly
        result = subprocess.run(
            [
                "aegis",
                "update",
                "--to-version",
                head_commit,
                "--template-path",
                str(template_path),
                "--yes",
            ],
            cwd=project_dir,
            capture_output=True,
            text=True,
        )

        # Should succeed
        assert result.returncode == 0, f"Update failed: {result.stderr}"
        assert "✅" in result.stdout or "completed" in result.stdout.lower()

    def test_downgrade_without_flag_fails(
        self, tmp_path: Path, template_path: Path, old_commit_hash: str
    ) -> None:
        """Test that downgrade without --allow-downgrade fails."""
        # Generate project from HEAD
        subprocess.run(
            ["aegis", "init", "test-project", "--no-interactive", "--yes"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=True,
        )

        project_dir = tmp_path / "test-project"

        # Try to downgrade without flag (should fail)
        result = subprocess.run(
            [
                "aegis",
                "update",
                "--to-version",
                old_commit_hash,
                "--template-path",
                str(template_path),
                "--yes",
            ],
            cwd=project_dir,
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0, "Expected downgrade to fail without flag"
        assert (
            "downgrade" in result.stderr.lower() or "downgrade" in result.stdout.lower()
        )

    def test_downgrade_with_flag_shows_warning(
        self, tmp_path: Path, template_path: Path, old_commit_hash: str
    ) -> None:
        """Test that downgrade with --allow-downgrade shows warning."""
        # Generate project from HEAD
        subprocess.run(
            ["aegis", "init", "test-project", "--no-interactive", "--yes"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=True,
        )

        project_dir = tmp_path / "test-project"

        # Try to downgrade with flag
        # NOTE: Copier itself may still block downgrades due to PEP 440 version checking
        # This test verifies our downgrade detection works, even if Copier blocks it
        result = subprocess.run(
            [
                "aegis",
                "update",
                "--to-version",
                old_commit_hash,
                "--allow-downgrade",
                "--template-path",
                str(template_path),
                "--yes",
            ],
            cwd=project_dir,
            capture_output=True,
            text=True,
        )

        # Should show warning about downgrade (whether it succeeds or not)
        output = result.stdout + result.stderr
        assert (
            "warning" in output.lower() or "⚠️" in output or "downgrad" in output.lower()
        )

    def test_update_with_dirty_git_tree(
        self, tmp_path: Path, template_path: Path
    ) -> None:
        """Test that update fails with dirty git tree."""
        # Generate initial project
        subprocess.run(
            ["aegis", "init", "test-project", "--no-interactive", "--yes"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=True,
        )

        project_dir = tmp_path / "test-project"

        # Make a change without committing
        readme = project_dir / "README.md"
        readme.write_text(readme.read_text() + "\nTest change")

        # Try to update (should fail)
        result = subprocess.run(
            [
                "aegis",
                "update",
                "--template-path",
                str(template_path),
                "--yes",
            ],
            cwd=project_dir,
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "clean" in result.stdout.lower() or "clean" in result.stderr.lower()

    def test_update_shows_version_info(
        self, tmp_path: Path, template_path: Path, old_commit_hash: str
    ) -> None:
        """Test that update displays version information."""
        # Generate from old version
        # Use --python-version 3.11 to ensure compatibility with old template versions
        subprocess.run(
            [
                "aegis",
                "init",
                "test-project",
                "--to-version",
                old_commit_hash,
                "--python-version",
                "3.11",
                "--no-interactive",
                "--yes",
            ],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=True,
        )

        project_dir = tmp_path / "test-project"

        # Run update
        result = subprocess.run(
            [
                "aegis",
                "update",
                "--template-path",
                str(template_path),
                "--yes",
            ],
            cwd=project_dir,
            capture_output=True,
            text=True,
        )

        # Should display version info
        assert "Version Information:" in result.stdout
        assert "Current Template:" in result.stdout
        assert "Target Template:" in result.stdout

    def test_update_not_copier_project(
        self, tmp_path: Path, template_path: Path
    ) -> None:
        """Test that update fails on non-Copier projects."""
        # Create a directory that's not a Copier project
        project_dir = tmp_path / "not-a-project"
        project_dir.mkdir()

        result = subprocess.run(
            [
                "aegis",
                "update",
                "--project-path",
                str(project_dir),
                "--template-path",
                str(template_path),
            ],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "copier" in result.stderr.lower()
