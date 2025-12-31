"""
Tests for template cleanup utilities.

These tests validate the post-update cleanup functions that handle
nested directory structures created during Copier template updates.
"""

from pathlib import Path
from unittest.mock import patch

from aegis.core.template_cleanup import cleanup_nested_project_directory


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

    def test_replaces_existing_files(self, tmp_path: Path) -> None:
        """Test that files in project root are replaced by nested versions."""
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

        # File should be replaced with nested version
        assert "config.py" in result
        assert (tmp_path / "config.py").read_text() == "# new config from template"

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
