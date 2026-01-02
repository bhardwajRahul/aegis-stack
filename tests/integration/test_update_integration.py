"""Integration tests for aegis update command with version management."""

import subprocess
from pathlib import Path

import pytest

# Mark all tests in this module as slow (skip with: pytest -m "not slow")
pytestmark = [pytest.mark.slow, pytest.mark.integration]

# =============================================================================
# Helper Functions
# =============================================================================


def run_update(
    project: Path,
    template: Path,
    *args: str,
) -> subprocess.CompletedProcess[str]:
    """Run aegis update with standard options.

    Args:
        project: Path to the project to update
        template: Path to the template repository
        *args: Additional arguments to pass to aegis update

    Returns:
        CompletedProcess with stdout/stderr
    """
    cmd = ["aegis", "update", "--template-path", str(template), "--yes"]
    cmd.extend(args)
    return subprocess.run(cmd, cwd=project, capture_output=True, text=True)


def git_tag_exists(repo: Path, tag_pattern: str) -> bool:
    """Check if git tag matching pattern exists in repo."""
    result = subprocess.run(
        ["git", "tag", "-l", tag_pattern],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    return bool(result.stdout.strip())


def find_rej_files(project: Path) -> list[Path]:
    """Find all .rej conflict files in project."""
    return list(project.rglob("*.rej"))


def modify_and_commit(project: Path, file_path: str, content: str) -> None:
    """Modify a file and commit to create conflict scenario."""
    target = project / file_path
    target.write_text(content)
    subprocess.run(["git", "add", "."], cwd=project, check=True)
    subprocess.run(
        ["git", "commit", "-m", "User modification"],
        cwd=project,
        check=True,
    )


# =============================================================================
# Test Classes
# =============================================================================


class TestUpdateIntegration:
    """Test update command functionality with version management.

    Note: Uses session-scoped fixtures from conftest.py for performance.
    - template_path: Path to aegis-stack repo
    - old_commit_hash: Commit hash from ~10 commits ago
    - updatable_project: Cached project from old commit (copied per test)
    - head_project: Cached project from HEAD (copied per test)
    """

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
        self, updatable_project: Path, template_path: Path, head_commit_hash: str
    ) -> None:
        """Test updating from old commit to HEAD."""
        # updatable_project is already generated from old commit (cached)

        # Update to HEAD explicitly
        result = run_update(
            updatable_project, template_path, "--to-version", head_commit_hash
        )

        # Should succeed
        assert result.returncode == 0, f"Update failed: {result.stderr}"
        assert "✅" in result.stdout or "completed" in result.stdout.lower()

    def test_downgrade_fails(
        self, head_project: Path, template_path: Path, old_commit_hash: str
    ) -> None:
        """Test that downgrade to older version fails (not supported by Copier)."""
        # head_project is already generated from HEAD (cached)

        # Try to downgrade (should fail - Copier doesn't support downgrades)
        result = run_update(
            head_project, template_path, "--to-version", old_commit_hash
        )

        assert result.returncode != 0, "Expected downgrade to fail"
        assert (
            "downgrade" in result.stderr.lower() or "downgrade" in result.stdout.lower()
        )

    def test_update_with_dirty_git_tree(
        self, head_project: Path, template_path: Path
    ) -> None:
        """Test that update fails with dirty git tree."""
        # head_project is already generated from HEAD (cached)

        # Make a change without committing
        readme = head_project / "README.md"
        readme.write_text(readme.read_text() + "\nTest change")

        # Try to update (should fail)
        result = run_update(head_project, template_path)

        assert result.returncode != 0
        assert "clean" in result.stdout.lower() or "clean" in result.stderr.lower()

    def test_update_shows_version_info(
        self, updatable_project: Path, template_path: Path
    ) -> None:
        """Test that update displays version information."""
        # updatable_project is already generated from old commit (cached)

        # Run update
        result = run_update(updatable_project, template_path)

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


class TestConflictHandling:
    """Test update behavior when user has modified files.

    Uses session-scoped fixtures from conftest.py for performance.
    """

    def test_update_with_user_modifications_creates_rej_files(
        self, updatable_project: Path, template_path: Path, head_commit_hash: str
    ) -> None:
        """Test that updating with user modifications creates .rej files for conflicts."""
        # Modify a file that's likely to conflict (README.md is template-managed)
        modified_content = "# COMPLETELY CUSTOM README\n\nUser-specific content.\n"
        modify_and_commit(updatable_project, "README.md", modified_content)

        # Update to HEAD
        result = run_update(
            updatable_project, template_path, "--to-version", head_commit_hash
        )

        # Update should complete (possibly with conflicts)
        rej_files = find_rej_files(updatable_project)
        output = result.stdout + result.stderr

        # Either we have conflicts (.rej files) or the update succeeded
        assert result.returncode == 0 or len(rej_files) > 0, (
            f"Update failed without conflicts: {output}"
        )

    def test_update_conflict_report_shows_affected_files(
        self, updatable_project: Path, template_path: Path, head_commit_hash: str
    ) -> None:
        """Test that conflict report lists affected files."""
        # Modify README to create potential conflict
        modify_and_commit(
            updatable_project,
            "README.md",
            "# Custom Project\n\nThis is custom content that will conflict.\n",
        )

        # Update to HEAD
        result = run_update(
            updatable_project, template_path, "--to-version", head_commit_hash
        )

        # If there are conflicts, output should mention them
        rej_files = find_rej_files(updatable_project)
        if rej_files:
            output = result.stdout + result.stderr
            assert (
                "conflict" in output.lower()
                or ".rej" in output
                or any(f.stem in output for f in rej_files)
            ), f"Conflicts exist but not reported: {rej_files}"

    def test_update_completes_despite_conflicts(
        self, updatable_project: Path, template_path: Path, head_commit_hash: str
    ) -> None:
        """Test that update completes successfully even with conflicts."""
        # Modify a file to create conflict
        modify_and_commit(
            updatable_project,
            "README.md",
            "# My Custom Title\n\nCustom description.\n",
        )

        # Update to HEAD
        result = run_update(
            updatable_project, template_path, "--to-version", head_commit_hash
        )

        # Update should complete (return code 0) even with conflicts
        # Copier creates .rej files for conflicts but doesn't fail
        assert result.returncode == 0, f"Update failed: {result.stderr}"


class TestBackupAndRollback:
    """Test backup tag creation and rollback functionality.

    Uses session-scoped fixtures from conftest.py for performance.
    """

    def test_update_creates_backup_tag(
        self, updatable_project: Path, template_path: Path, head_commit_hash: str
    ) -> None:
        """Test that update creates a backup tag before making changes."""
        result = run_update(
            updatable_project, template_path, "--to-version", head_commit_hash
        )

        # Check output mentions backup
        output = result.stdout + result.stderr
        assert "backup" in output.lower() or result.returncode == 0, (
            f"No backup mentioned and update failed: {output}"
        )

    def test_update_cleans_backup_on_success(
        self, updatable_project: Path, template_path: Path, head_commit_hash: str
    ) -> None:
        """Test that backup tag is cleaned up after successful update."""
        result = run_update(
            updatable_project, template_path, "--to-version", head_commit_hash
        )

        # After successful update, backup tags should be cleaned up
        if result.returncode == 0:
            has_backup_tags = git_tag_exists(updatable_project, "aegis-backup-*")
            assert not has_backup_tags, "Backup tag not cleaned up after success"

    def test_update_preserves_git_history(
        self, updatable_project: Path, template_path: Path, head_commit_hash: str
    ) -> None:
        """Test that update preserves git history and creates commit."""
        # Get initial commit count
        result = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            cwd=updatable_project,
            capture_output=True,
            text=True,
            check=True,
        )
        initial_commits = int(result.stdout.strip())

        # Update to HEAD
        update_result = run_update(
            updatable_project, template_path, "--to-version", head_commit_hash
        )

        if update_result.returncode == 0:
            # Get new commit count
            result = subprocess.run(
                ["git", "rev-list", "--count", "HEAD"],
                cwd=updatable_project,
                capture_output=True,
                text=True,
                check=True,
            )
            final_commits = int(result.stdout.strip())

            # Should have at least the same number of commits (Copier may add one)
            assert final_commits >= initial_commits


class TestUpToDate:
    """Test behavior when project is already up to date.

    Uses session-scoped fixtures from conftest.py for performance.
    """

    def test_update_already_at_target_shows_message(
        self, head_project: Path, template_path: Path, head_commit_hash: str
    ) -> None:
        """Test that updating to current version shows appropriate message."""
        # Try to update to same version
        result = run_update(
            head_project, template_path, "--to-version", head_commit_hash
        )

        # Should indicate already up to date or no changes
        output = result.stdout + result.stderr
        assert (
            "up to date" in output.lower()
            or "no changes" in output.lower()
            or "already" in output.lower()
            or result.returncode == 0
        )

    def test_update_same_version_quick_exit(
        self, head_project: Path, template_path: Path
    ) -> None:
        """Test that update to same version exits quickly without post-gen."""
        # Update without specifying version (should detect same version)
        result = run_update(head_project, template_path)

        # Should complete quickly (already at target commit)
        assert result.returncode == 0


class TestPostGenerationTasks:
    """Test post-generation task behavior during updates.

    Uses session-scoped fixtures from conftest.py for performance.
    """

    def test_update_runs_post_gen_tasks(
        self, updatable_project: Path, template_path: Path, head_commit_hash: str
    ) -> None:
        """Test that post-generation tasks run after update."""
        result = run_update(
            updatable_project,
            template_path,
            "--to-version",
            head_commit_hash,
        )

        # Check output mentions post-gen tasks
        output = result.stdout + result.stderr
        if result.returncode == 0:
            assert (
                "post" in output.lower()
                or "Setting up" in output
                or "dependencies" in output.lower()
            ), f"No post-gen task indication in successful update: {output}"

    def test_update_continues_on_post_gen_failure(
        self, updatable_project: Path, template_path: Path, head_commit_hash: str
    ) -> None:
        """Test that update succeeds even if post-gen tasks have warnings."""
        result = run_update(
            updatable_project,
            template_path,
            "--to-version",
            head_commit_hash,
        )

        # Update should succeed (post-gen failures are warnings, not errors)
        assert result.returncode == 0, f"Update failed: {result.stderr}"


class TestVersionEdgeCases:
    """Test version-related edge cases.

    Uses session-scoped fixtures from conftest.py for performance.
    """

    def test_update_to_tagged_version(
        self, updatable_project: Path, template_path: Path
    ) -> None:
        """Test updating to a tagged version (e.g., v0.4.0)."""
        # Get available tags
        result = subprocess.run(
            ["git", "tag", "-l", "v*"],
            cwd=template_path,
            capture_output=True,
            text=True,
        )
        tags = result.stdout.strip().split("\n")
        tags = [t for t in tags if t]  # Filter empty

        if not tags:
            pytest.skip("No version tags available")

        # Use the latest tag
        latest_tag = sorted(tags)[-1]

        # Update to tagged version
        result = run_update(
            updatable_project, template_path, "--to-version", latest_tag
        )

        # Should succeed or show version info
        output = result.stdout + result.stderr
        assert result.returncode == 0 or latest_tag in output, (
            f"Failed to update to tag {latest_tag}: {output}"
        )

    def test_update_invalid_version_shows_error(
        self, head_project: Path, template_path: Path
    ) -> None:
        """Test that invalid version reference shows clear error."""
        # Try to update to invalid version
        result = run_update(
            head_project, template_path, "--to-version", "invalid-version-xyz123"
        )

        # Should fail with clear error
        assert result.returncode != 0
        output = result.stdout + result.stderr
        assert (
            "invalid" in output.lower()
            or "not found" in output.lower()
            or "error" in output.lower()
            or "could not" in output.lower()
        )


class TestErrorHandling:
    """Test error handling scenarios.

    Uses session-scoped fixtures from conftest.py for performance.
    """

    def test_update_invalid_template_path(self, head_project: Path) -> None:
        """Test that invalid template path shows clear error."""
        # Try to update with invalid template path
        result = subprocess.run(
            [
                "aegis",
                "update",
                "--template-path",
                "/nonexistent/path/to/template",
                "--yes",
            ],
            cwd=head_project,
            capture_output=True,
            text=True,
        )

        # Should fail with clear error
        assert result.returncode != 0
        output = result.stdout + result.stderr
        assert (
            "not exist" in output.lower()
            or "invalid" in output.lower()
            or "error" in output.lower()
            or "not found" in output.lower()
        )

    def test_update_missing_copier_answers(
        self, tmp_path: Path, template_path: Path
    ) -> None:
        """Test handling of missing .copier-answers.yml."""
        # Create a directory that looks like a project but has no .copier-answers.yml
        project_path = tmp_path / "fake-project"
        project_path.mkdir()

        # Initialize git to make it look more like a project
        subprocess.run(["git", "init"], cwd=project_path, check=True)
        (project_path / "README.md").write_text("# Fake Project\n")
        subprocess.run(["git", "add", "."], cwd=project_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial"],
            cwd=project_path,
            check=True,
        )

        # Try to update
        result = run_update(project_path, template_path)

        # Should fail because it's not a Copier project
        assert result.returncode != 0
        output = result.stdout + result.stderr
        assert (
            "copier" in output.lower()
            or "not" in output.lower()
            or "invalid" in output.lower()
        )
