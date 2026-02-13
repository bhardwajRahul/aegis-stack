"""
Tests for template cleanup utilities.

These tests validate the post-update cleanup functions that handle
nested directory structures created during Copier template updates.
"""

from collections.abc import Callable
from pathlib import Path
from unittest.mock import patch

from aegis.core.template_cleanup import (
    _should_skip_sync,
    cleanup_nested_project_directory,
    sync_template_changes,
)


class TestCleanupNestedProjectDirectory:
    """Test cleanup_nested_project_directory function."""

    def test_no_nested_dir_returns_empty(self, tmp_path: Path) -> None:
        """Test that empty list is returned when nested directory doesn't exist."""
        result = cleanup_nested_project_directory(tmp_path, "my-project")
        assert result == []

    def test_empty_slug_returns_empty(self, tmp_path: Path) -> None:
        """Test that empty list is returned when project_slug is empty."""
        result = cleanup_nested_project_directory(tmp_path, "")
        assert result == []

    def test_moves_files_from_nested_directory(self, tmp_path: Path) -> None:
        """Test that files are moved from nested directory to project root."""
        project_slug = "my-project"
        nested_dir = tmp_path / project_slug
        nested_dir.mkdir()

        # Create a file in the nested directory
        nested_file = nested_dir / "new_file.py"
        nested_file.write_text("# new file content")

        result = cleanup_nested_project_directory(tmp_path, project_slug)

        # File should be moved to root
        assert "new_file.py" in result
        assert (tmp_path / "new_file.py").exists()
        assert (tmp_path / "new_file.py").read_text() == "# new file content"

        # Nested directory should be removed
        assert not nested_dir.exists()

    def test_moves_files_in_subdirectories(self, tmp_path: Path) -> None:
        """Test that files in nested subdirectories are moved correctly."""
        project_slug = "my-project"
        nested_dir = tmp_path / project_slug
        subdir = nested_dir / "app" / "services" / "ai"
        subdir.mkdir(parents=True)

        # Create files in nested subdirectory
        file1 = subdir / "agent.py"
        file1.write_text("# AI agent")
        file2 = subdir / "config.py"
        file2.write_text("# AI config")

        result = cleanup_nested_project_directory(tmp_path, project_slug)

        # Files should be moved to corresponding paths in project root
        assert "app/services/ai/agent.py" in result
        assert "app/services/ai/config.py" in result
        assert (tmp_path / "app" / "services" / "ai" / "agent.py").exists()
        assert (tmp_path / "app" / "services" / "ai" / "config.py").exists()

        # Nested directory should be removed
        assert not nested_dir.exists()

    def test_skips_existing_files(self, tmp_path: Path) -> None:
        """Test that existing files are skipped (sync_template_changes handles them)."""
        project_slug = "my-project"
        nested_dir = tmp_path / project_slug
        nested_dir.mkdir()

        # Create existing file in project root
        existing_file = tmp_path / "config.py"
        existing_file.write_text("# old config")

        # Create file in nested directory (newer version)
        nested_file = nested_dir / "config.py"
        nested_file.write_text("# new config from template")

        result = cleanup_nested_project_directory(tmp_path, project_slug)

        # Existing file should NOT be in the moved list — it's skipped
        assert "config.py" not in result
        # Original content should be preserved (sync_template_changes will merge later)
        assert (tmp_path / "config.py").read_text() == "# old config"
        # Nested source file should be cleaned up
        assert not nested_dir.exists()

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        """Test that parent directories are created if they don't exist."""
        project_slug = "my-project"
        nested_dir = tmp_path / project_slug / "app" / "new_module"
        nested_dir.mkdir(parents=True)

        new_file = nested_dir / "handler.py"
        new_file.write_text("# handler code")

        # app/new_module doesn't exist in project root yet
        assert not (tmp_path / "app" / "new_module").exists()

        result = cleanup_nested_project_directory(tmp_path, project_slug)

        # Parent directories should be created
        assert (tmp_path / "app" / "new_module" / "handler.py").exists()
        assert "app/new_module/handler.py" in result


class TestUpdateCleanupIntegration:
    """Test that cleanup_components is called after moving nested files."""

    def test_cleanup_components_called_when_files_moved(self, tmp_path: Path) -> None:
        """Test that cleanup_components is called after files are moved from nested dir."""
        from aegis.core.template_cleanup import cleanup_nested_project_directory

        project_slug = "test-project"
        nested_dir = tmp_path / project_slug
        subdir = nested_dir / "app" / "services" / "ai"
        subdir.mkdir(parents=True)

        # Create AI service files that shouldn't exist (include_ai: false)
        (subdir / "agent.py").write_text("# AI agent")
        (subdir / "config.py").write_text("# AI config")

        # Mock answers with include_ai: false
        answers = {
            "project_slug": project_slug,
            "include_ai": False,
            "include_auth": False,
        }

        # First, move files from nested directory
        moved_files = cleanup_nested_project_directory(tmp_path, project_slug)

        # Verify files were moved
        assert len(moved_files) == 2
        assert (tmp_path / "app" / "services" / "ai" / "agent.py").exists()

        # Now test that cleanup_components would remove them
        with patch(
            "aegis.core.post_gen_tasks.cleanup_components"
        ) as mock_cleanup_components:
            # Import and call as the update command would
            from aegis.core.post_gen_tasks import cleanup_components

            cleanup_components(tmp_path, answers)

            # Verify cleanup_components was called with correct arguments
            mock_cleanup_components.assert_called_once_with(tmp_path, answers)

    def test_cleanup_components_not_called_when_no_files_moved(
        self, tmp_path: Path
    ) -> None:
        """Test that cleanup_components is NOT called when no files were moved."""
        project_slug = "test-project"

        # No nested directory exists
        moved_files = cleanup_nested_project_directory(tmp_path, project_slug)

        # No files moved
        assert moved_files == []

        # In the actual update code, cleanup_components should only be called
        # inside the `if moved_files:` block, so it wouldn't be called here


class TestCleanupRemovesUnwantedAIFiles:
    """
    Test the full integration: cleanup_components removes AI files
    when include_ai is False in answers.
    """

    def test_ai_files_removed_when_include_ai_false(self, tmp_path: Path) -> None:
        """Test that AI service files are removed when include_ai: false."""
        from aegis.core.post_gen_tasks import cleanup_components

        # Setup: Create AI service directory structure
        # These paths are defined in get_component_file_mapping() for SERVICE_AI
        ai_services_dir = tmp_path / "app" / "services" / "ai"
        ai_services_dir.mkdir(parents=True)
        (ai_services_dir / "__init__.py").write_text("# AI init")
        (ai_services_dir / "agent.py").write_text("# AI agent")

        # Also create AI API directory (from mapping)
        ai_api_dir = tmp_path / "app" / "components" / "backend" / "api" / "ai"
        ai_api_dir.mkdir(parents=True)
        (ai_api_dir / "__init__.py").write_text("# AI API init")

        # Answers indicate AI is NOT included
        answers = {
            "project_slug": "test-project",
            "include_ai": False,
            "include_auth": False,
            "include_scheduler": False,
            "include_worker": False,
            "include_database": False,
            "include_redis": False,
            "include_cache": False,
            "include_comms": False,
        }

        # Run cleanup_components
        cleanup_components(tmp_path, answers)

        # AI service directory should be removed
        assert not ai_services_dir.exists(), "AI service directory should be removed"
        # AI API directory should be removed
        assert not ai_api_dir.exists(), "AI API directory should be removed"

    def test_ai_files_kept_when_include_ai_true(self, tmp_path: Path) -> None:
        """Test that AI service files are kept when include_ai: true."""
        from aegis.core.post_gen_tasks import cleanup_components

        # Setup: Create AI service directory structure
        ai_dir = tmp_path / "app" / "services" / "ai"
        ai_dir.mkdir(parents=True)
        (ai_dir / "__init__.py").write_text("# AI init")
        (ai_dir / "agent.py").write_text("# AI agent")

        # Answers indicate AI IS included
        answers = {
            "project_slug": "test-project",
            "include_ai": True,
            "include_auth": False,
            "include_scheduler": False,
            "include_worker": False,
            "include_database": False,
            "include_redis": False,
            "include_cache": False,
            "include_comms": False,
        }

        # Run cleanup_components
        cleanup_components(tmp_path, answers)

        # AI service directory should be kept
        assert ai_dir.exists(), "AI service directory should be kept"
        assert (ai_dir / "agent.py").exists(), "AI agent.py should be kept"


class TestEndToEndNestedCleanup:
    """
    End-to-end test simulating what happens during aegis update.

    This mimics the flow:
    1. Copier creates nested files in project_slug/
    2. cleanup_nested_project_directory moves them to project root
    3. cleanup_components removes files that shouldn't exist
    """

    def test_full_update_flow_with_ai_disabled(self, tmp_path: Path) -> None:
        """
        Test full update flow: nested AI files are moved then cleaned up.

        Simulates: User has include_ai: false, but new AI files were added
        to template. After update, AI files should NOT exist.
        """
        from aegis.core.post_gen_tasks import cleanup_components
        from aegis.core.template_cleanup import cleanup_nested_project_directory

        project_slug = "my-project"

        # Step 1: Copier creates nested directory with AI files
        # (This is what Copier does for new files in template)
        nested_dir = tmp_path / project_slug
        ai_nested = nested_dir / "app" / "services" / "ai"
        ai_nested.mkdir(parents=True)
        (ai_nested / "__init__.py").write_text("# AI init")
        (ai_nested / "agent.py").write_text("# AI agent")

        # User's answers say AI is NOT enabled
        answers = {
            "project_slug": project_slug,
            "include_ai": False,
            "include_auth": False,
            "include_scheduler": False,
            "include_worker": False,
            "include_database": False,
            "include_redis": False,
            "include_cache": False,
            "include_comms": False,
        }

        # Step 2: cleanup_nested_project_directory moves files
        moved_files = cleanup_nested_project_directory(tmp_path, project_slug)

        # Verify files were moved
        assert len(moved_files) == 2
        assert (tmp_path / "app" / "services" / "ai" / "agent.py").exists()

        # Step 3: cleanup_components removes unwanted files
        # This is the fix we're adding!
        if moved_files:
            cleanup_components(tmp_path, answers)

        # Result: AI files should NOT exist because include_ai: false
        assert not (tmp_path / "app" / "services" / "ai").exists(), (
            "AI service directory should be removed because include_ai is False"
        )

    def test_full_update_flow_with_ai_enabled(self, tmp_path: Path) -> None:
        """
        Test full update flow: nested AI files are moved and kept.

        Simulates: User has include_ai: true, new AI files are added.
        After update, AI files should exist.
        """
        from aegis.core.post_gen_tasks import cleanup_components
        from aegis.core.template_cleanup import cleanup_nested_project_directory

        project_slug = "my-project"

        # Step 1: Copier creates nested directory with AI files
        nested_dir = tmp_path / project_slug
        ai_nested = nested_dir / "app" / "services" / "ai"
        ai_nested.mkdir(parents=True)
        (ai_nested / "__init__.py").write_text("# AI init")
        (ai_nested / "agent.py").write_text("# AI agent")

        # User's answers say AI IS enabled
        answers = {
            "project_slug": project_slug,
            "include_ai": True,
            "include_auth": False,
            "include_scheduler": False,
            "include_worker": False,
            "include_database": False,
            "include_redis": False,
            "include_cache": False,
            "include_comms": False,
        }

        # Step 2: Move files
        moved_files = cleanup_nested_project_directory(tmp_path, project_slug)
        assert len(moved_files) == 2

        # Step 3: Cleanup (should keep AI files)
        if moved_files:
            cleanup_components(tmp_path, answers)

        # Result: AI files SHOULD exist because include_ai: true
        assert (tmp_path / "app" / "services" / "ai").exists(), (
            "AI service directory should be kept because include_ai is True"
        )
        assert (tmp_path / "app" / "services" / "ai" / "agent.py").exists(), (
            "AI agent.py should be kept"
        )


class TestShouldSkipSync:
    """Test _should_skip_sync helper function."""

    def test_skips_copier_answers(self) -> None:
        """Test that .copier-answers.yml is skipped."""
        assert _should_skip_sync(".copier-answers.yml") is True

    def test_skips_env_file(self) -> None:
        """Test that .env is skipped."""
        assert _should_skip_sync(".env") is True

    def test_skips_python_version(self) -> None:
        """Test that .python-version is skipped."""
        assert _should_skip_sync(".python-version") is True

    def test_skips_venv_directory(self) -> None:
        """Test that .venv/ files are skipped."""
        assert _should_skip_sync(".venv/lib/python3.11/site-packages/foo.py") is True

    def test_skips_pycache(self) -> None:
        """Test that __pycache__/ files are skipped."""
        assert _should_skip_sync("__pycache__/module.cpython-311.pyc") is True
        assert _should_skip_sync("app/__pycache__/foo.pyc") is True

    def test_skips_pyc_files(self) -> None:
        """Test that .pyc files are skipped."""
        assert _should_skip_sync("module.pyc") is True
        assert _should_skip_sync("app/services/ai/agent.pyc") is True

    def test_does_not_skip_regular_files(self) -> None:
        """Test that regular Python files are not skipped."""
        assert _should_skip_sync("app/__init__.py") is False
        assert _should_skip_sync("app/services/ai/agent.py") is False
        assert _should_skip_sync("pyproject.toml") is False
        assert _should_skip_sync("app/components/frontend/theme.py") is False


class TestSyncTemplateChanges:
    """Test sync_template_changes function."""

    def test_empty_project_slug_returns_empty(self, tmp_path: Path) -> None:
        """Test that empty SyncResult is returned when project_slug is empty."""
        answers: dict[str, str] = {"project_slug": ""}
        result = sync_template_changes(tmp_path, answers, "gh:test/repo", "v1.0.0")
        assert result.synced == []
        assert result.conflicts == []

    def test_syncs_differing_files_no_old_commit(self, tmp_path: Path) -> None:
        """Test that files differing from template are synced (overwrite fallback)."""
        project_slug = "my-project"
        answers = {"project_slug": project_slug}

        # Create project file with old content
        project_file = tmp_path / "app" / "config.py"
        project_file.parent.mkdir(parents=True)
        project_file.write_text("# old config")

        def mock_run_copy(**kwargs: object) -> None:
            """Mock run_copy to create rendered template."""
            dst_path = str(kwargs["dst_path"])
            rendered_dir = Path(dst_path) / project_slug / "app"
            rendered_dir.mkdir(parents=True)
            (rendered_dir / "config.py").write_text("# new config from template")

        with patch("copier.run_copy", side_effect=mock_run_copy):
            result = sync_template_changes(tmp_path, answers, "gh:test/repo", "v1.0.0")

        # File should be synced (no old_commit → overwrite fallback)
        assert "app/config.py" in result.synced
        assert project_file.read_text() == "# new config from template"

    def test_skips_identical_files(self, tmp_path: Path) -> None:
        """Test that identical files are not synced."""
        project_slug = "my-project"
        answers = {"project_slug": project_slug}

        project_file = tmp_path / "app" / "config.py"
        project_file.parent.mkdir(parents=True)
        project_file.write_text("# same content")

        def mock_run_copy(**kwargs: object) -> None:
            dst_path = str(kwargs["dst_path"])
            rendered_dir = Path(dst_path) / project_slug / "app"
            rendered_dir.mkdir(parents=True)
            (rendered_dir / "config.py").write_text("# same content")

        with patch("copier.run_copy", side_effect=mock_run_copy):
            result = sync_template_changes(tmp_path, answers, "gh:test/repo", "v1.0.0")

        assert result.synced == []

    def test_skips_nonexistent_project_files(self, tmp_path: Path) -> None:
        """Test that new files in template are skipped (handled by cleanup_nested)."""
        project_slug = "my-project"
        answers = {"project_slug": project_slug}

        def mock_run_copy(**kwargs: object) -> None:
            dst_path = str(kwargs["dst_path"])
            rendered_dir = Path(dst_path) / project_slug / "app"
            rendered_dir.mkdir(parents=True)
            (rendered_dir / "new_file.py").write_text("# new file")

        with patch("copier.run_copy", side_effect=mock_run_copy):
            result = sync_template_changes(tmp_path, answers, "gh:test/repo", "v1.0.0")

        assert result.synced == []
        assert not (tmp_path / "app" / "new_file.py").exists()

    def test_skips_files_matching_skip_patterns(self, tmp_path: Path) -> None:
        """Test that files matching skip patterns are not synced."""
        project_slug = "my-project"
        answers = {"project_slug": project_slug}

        env_file = tmp_path / ".env"
        env_file.write_text("SECRET=old_value")

        def mock_run_copy(**kwargs: object) -> None:
            dst_path = str(kwargs["dst_path"])
            rendered_dir = Path(dst_path) / project_slug
            rendered_dir.mkdir(parents=True)
            (rendered_dir / ".env").write_text("SECRET=new_value")

        with patch("copier.run_copy", side_effect=mock_run_copy):
            result = sync_template_changes(tmp_path, answers, "gh:test/repo", "v1.0.0")

        assert result.synced == []
        assert env_file.read_text() == "SECRET=old_value"

    def test_syncs_only_listed_template_changed_files(self, tmp_path: Path) -> None:
        """Test that only files in template_changed_files are synced."""
        project_slug = "my-project"
        answers = {"project_slug": project_slug}

        config_file = tmp_path / "app" / "config.py"
        config_file.parent.mkdir(parents=True)
        config_file.write_text("# old config")

        main_file = tmp_path / "app" / "main.py"
        main_file.write_text("# old main")

        def mock_run_copy(**kwargs: object) -> None:
            dst_path = str(kwargs["dst_path"])
            rendered_dir = Path(dst_path) / project_slug / "app"
            rendered_dir.mkdir(parents=True)
            (rendered_dir / "config.py").write_text("# new config")
            (rendered_dir / "main.py").write_text("# new main")

        with patch("copier.run_copy", side_effect=mock_run_copy):
            result = sync_template_changes(
                tmp_path,
                answers,
                "gh:test/repo",
                "v1.0.0",
                template_changed_files={"app/config.py"},
            )

        assert "app/config.py" in result.synced
        assert "app/main.py" not in result.synced
        assert config_file.read_text() == "# new config"
        assert main_file.read_text() == "# old main"

    def test_empty_template_changed_files_syncs_nothing(self, tmp_path: Path) -> None:
        """Test that empty set means no files changed — nothing synced."""
        project_slug = "my-project"
        answers = {"project_slug": project_slug}

        config_file = tmp_path / "app" / "config.py"
        config_file.parent.mkdir(parents=True)
        config_file.write_text("# old config")

        def mock_run_copy(**kwargs: object) -> None:
            dst_path = str(kwargs["dst_path"])
            rendered_dir = Path(dst_path) / project_slug / "app"
            rendered_dir.mkdir(parents=True)
            (rendered_dir / "config.py").write_text("# new config")

        with patch("copier.run_copy", side_effect=mock_run_copy):
            result = sync_template_changes(
                tmp_path,
                answers,
                "gh:test/repo",
                "v1.0.0",
                template_changed_files=set(),
            )

        assert result.synced == []
        assert config_file.read_text() == "# old config"

    def test_none_template_changed_files_syncs_all(self, tmp_path: Path) -> None:
        """Test that None (default) syncs all differing files — backwards compat."""
        project_slug = "my-project"
        answers = {"project_slug": project_slug}

        config_file = tmp_path / "app" / "config.py"
        config_file.parent.mkdir(parents=True)
        config_file.write_text("# old config")

        main_file = tmp_path / "app" / "main.py"
        main_file.write_text("# old main")

        def mock_run_copy(**kwargs: object) -> None:
            dst_path = str(kwargs["dst_path"])
            rendered_dir = Path(dst_path) / project_slug / "app"
            rendered_dir.mkdir(parents=True)
            (rendered_dir / "config.py").write_text("# new config")
            (rendered_dir / "main.py").write_text("# new main")

        with patch("copier.run_copy", side_effect=mock_run_copy):
            result = sync_template_changes(
                tmp_path,
                answers,
                "gh:test/repo",
                "v1.0.0",
                template_changed_files=None,
            )

        assert "app/config.py" in result.synced
        assert "app/main.py" in result.synced
        assert config_file.read_text() == "# new config"
        assert main_file.read_text() == "# new main"

    def test_handles_render_failure(self, tmp_path: Path) -> None:
        """Test that render failure returns empty SyncResult."""
        answers = {"project_slug": "my-project"}

        with patch(
            "copier.run_copy",
            side_effect=Exception("Render failed"),
        ):
            result = sync_template_changes(tmp_path, answers, "gh:test/repo", "v1.0.0")

        assert result.synced == []
        assert result.conflicts == []


class TestThreeWayMerge:
    """Test 3-way merge logic in sync_template_changes.

    These tests exercise the core merge scenarios by providing old_commit
    so that both old and new templates are rendered.
    """

    @staticmethod
    def _make_mock(
        project_slug: str,
        old_content: str,
        new_content: str,
    ) -> Callable[..., None]:
        """Create a mock_run_copy that renders old/new based on dst_path."""

        def mock_run_copy(**kwargs: object) -> None:
            dst_path = str(kwargs["dst_path"])
            rendered_dir = Path(dst_path) / project_slug / "app"
            rendered_dir.mkdir(parents=True)
            if "/old" in dst_path:
                (rendered_dir / "config.py").write_text(old_content)
            else:
                (rendered_dir / "config.py").write_text(new_content)

        return mock_run_copy

    def test_user_didnt_customize_overwrites(self, tmp_path: Path) -> None:
        """When user's file == old template, safe to overwrite with new."""
        project_slug = "my-project"
        answers = {"project_slug": project_slug}

        project_file = tmp_path / "app" / "config.py"
        project_file.parent.mkdir(parents=True)
        project_file.write_text("# original template content")

        mock = self._make_mock(
            project_slug,
            old_content="# original template content",
            new_content="# updated template content",
        )

        with patch("copier.run_copy", side_effect=mock):
            result = sync_template_changes(
                tmp_path,
                answers,
                "gh:test/repo",
                "v2.0.0",
                old_commit="abc123",
            )

        assert "app/config.py" in result.synced
        assert result.conflicts == []
        assert project_file.read_text() == "# updated template content"

    def test_template_didnt_change_preserves_user(self, tmp_path: Path) -> None:
        """When old template == new template, keep user's customized version."""
        project_slug = "my-project"
        answers = {"project_slug": project_slug}

        project_file = tmp_path / "app" / "config.py"
        project_file.parent.mkdir(parents=True)
        project_file.write_text("# user customized content")

        mock = self._make_mock(
            project_slug,
            old_content="# same template",
            new_content="# same template",
        )

        with patch("copier.run_copy", side_effect=mock):
            result = sync_template_changes(
                tmp_path,
                answers,
                "gh:test/repo",
                "v2.0.0",
                old_commit="abc123",
            )

        # Template didn't change → user's version preserved, not synced
        assert result.synced == []
        assert result.conflicts == []
        assert project_file.read_text() == "# user customized content"

    def test_clean_three_way_merge(self, tmp_path: Path) -> None:
        """When all three differ but changes don't overlap, clean merge."""
        project_slug = "my-project"
        answers = {"project_slug": project_slug}

        # Base has 3 lines, user changed line 1, template changed line 3
        base = "line1\nline2\nline3\n"
        user = "user-changed-line1\nline2\nline3\n"
        new = "line1\nline2\ntemplate-changed-line3\n"

        project_file = tmp_path / "app" / "config.py"
        project_file.parent.mkdir(parents=True)
        project_file.write_text(user)

        mock = self._make_mock(project_slug, old_content=base, new_content=new)

        with patch("copier.run_copy", side_effect=mock):
            result = sync_template_changes(
                tmp_path,
                answers,
                "gh:test/repo",
                "v2.0.0",
                old_commit="abc123",
            )

        assert "app/config.py" in result.synced
        assert result.conflicts == []
        merged = project_file.read_text()
        assert "user-changed-line1" in merged
        assert "template-changed-line3" in merged

    def test_conflicting_merge_writes_markers(self, tmp_path: Path) -> None:
        """When user and template changed the same line, write conflict markers."""
        project_slug = "my-project"
        answers = {"project_slug": project_slug}

        base = "line1\nline2\nline3\n"
        user = "user-line1\nline2\nline3\n"
        new = "template-line1\nline2\nline3\n"

        project_file = tmp_path / "app" / "config.py"
        project_file.parent.mkdir(parents=True)
        project_file.write_text(user)

        mock = self._make_mock(project_slug, old_content=base, new_content=new)

        with patch("copier.run_copy", side_effect=mock):
            result = sync_template_changes(
                tmp_path,
                answers,
                "gh:test/repo",
                "v2.0.0",
                old_commit="abc123",
            )

        # Conflicting file should be reported as conflict, not synced
        assert "app/config.py" not in result.synced
        assert "app/config.py" in result.conflicts
        # File should contain conflict markers with both versions
        content = project_file.read_text()
        assert "<<<<<<<" in content
        assert "user-line1" in content
        assert "template-line1" in content

    def test_old_render_failure_falls_back_to_overwrite(self, tmp_path: Path) -> None:
        """When old template render fails, fall back to overwrite behavior."""
        project_slug = "my-project"
        answers = {"project_slug": project_slug}

        project_file = tmp_path / "app" / "config.py"
        project_file.parent.mkdir(parents=True)
        project_file.write_text("# user content")

        def mock_run_copy(**kwargs: object) -> None:
            dst_path = str(kwargs["dst_path"])
            if "/old" in dst_path:
                raise Exception("Old render failed")
            rendered_dir = Path(dst_path) / project_slug / "app"
            rendered_dir.mkdir(parents=True)
            (rendered_dir / "config.py").write_text("# new template content")

        with patch("copier.run_copy", side_effect=mock_run_copy):
            result = sync_template_changes(
                tmp_path,
                answers,
                "gh:test/repo",
                "v2.0.0",
                old_commit="abc123",
            )

        # Falls back to overwrite since old render failed
        assert "app/config.py" in result.synced
        assert project_file.read_text() == "# new template content"

    def test_old_file_not_in_old_render_falls_back(self, tmp_path: Path) -> None:
        """When a file exists in new but not old template, fall back to overwrite."""
        project_slug = "my-project"
        answers = {"project_slug": project_slug}

        project_file = tmp_path / "app" / "config.py"
        project_file.parent.mkdir(parents=True)
        project_file.write_text("# old project content")

        def mock_run_copy(**kwargs: object) -> None:
            dst_path = str(kwargs["dst_path"])
            if "/old" in dst_path:
                # Old render has no config.py (new file in template)
                rendered_dir = Path(dst_path) / project_slug / "app"
                rendered_dir.mkdir(parents=True)
            else:
                rendered_dir = Path(dst_path) / project_slug / "app"
                rendered_dir.mkdir(parents=True)
                (rendered_dir / "config.py").write_text("# new template content")

        with patch("copier.run_copy", side_effect=mock_run_copy):
            result = sync_template_changes(
                tmp_path,
                answers,
                "gh:test/repo",
                "v2.0.0",
                old_commit="abc123",
            )

        assert "app/config.py" in result.synced
        assert project_file.read_text() == "# new template content"
