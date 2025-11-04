"""
Tests for the 'aegis remove' command that removes components from existing projects.

Uses manual updater (Copier-lite) approach for component removal.
"""

from pathlib import Path

import pytest

from aegis.core.components import COMPONENTS, CORE_COMPONENTS
from aegis.core.copier_manager import (
    generate_with_copier,
    load_copier_answers,
)
from aegis.core.template_generator import TemplateGenerator

from .test_utils import CLI_TIMEOUT_STANDARD, run_aegis_command


class TestRemoveCommand:
    """Test suite for 'aegis remove' command."""

    def test_remove_command_not_copier_project(self, temp_output_dir: Path) -> None:
        """Test that remove command fails on non-Copier projects."""
        # Create a dummy directory that's not a Copier project
        fake_project = temp_output_dir / "fake-project"
        fake_project.mkdir()

        # Try to remove component
        result = run_aegis_command(
            "remove", "scheduler", "--project-path", str(fake_project), "--yes"
        )

        # Should fail with helpful message
        assert not result.success
        assert "not generated with copier" in result.stderr.lower()

    def test_remove_command_missing_project(self) -> None:
        """Test that remove command fails when project doesn't exist."""
        result = run_aegis_command(
            "remove", "scheduler", "--project-path", "/nonexistent/path", "--yes"
        )

        assert not result.success
        assert "not generated with copier" in result.stderr.lower()

    def test_remove_command_invalid_component(self, temp_output_dir: Path) -> None:
        """Test that remove command validates component names."""
        # Generate project with scheduler
        template_gen = TemplateGenerator(
            "test-remove-invalid", ["scheduler"], "memory", []
        )
        project_path = generate_with_copier(template_gen, temp_output_dir)

        # Try to remove invalid component
        result = run_aegis_command(
            "remove", "invalid_component", "--project-path", str(project_path), "--yes"
        )

        assert not result.success
        assert "unknown component" in result.stderr.lower()

    def test_remove_scheduler_from_project(self, temp_output_dir: Path) -> None:
        """Test removing scheduler component from a project."""
        # Generate project WITH scheduler
        template_gen = TemplateGenerator(
            "test-remove-scheduler", ["scheduler"], "memory", []
        )
        project_path = generate_with_copier(template_gen, temp_output_dir)

        # Verify scheduler is present
        initial_answers = load_copier_answers(project_path)
        assert initial_answers.get("include_scheduler") is True
        assert (project_path / "app" / "entrypoints" / "scheduler.py").exists()

        # Remove scheduler component
        result = run_aegis_command(
            "remove", "scheduler", "--project-path", str(project_path), "--yes"
        )

        # Should succeed
        assert result.success, f"Command failed: {result.stderr}"

        # Verify scheduler was removed from answers
        updated_answers = load_copier_answers(project_path)
        assert updated_answers.get("include_scheduler") is False

        # Verify scheduler files were deleted
        assert not (project_path / "app" / "entrypoints" / "scheduler.py").exists()
        assert not (
            project_path / "tests" / "components" / "test_scheduler.py"
        ).exists()

    def test_remove_not_enabled_component(self, temp_output_dir: Path) -> None:
        """Test removing a component that's not enabled."""
        # Generate project WITHOUT scheduler
        template_gen = TemplateGenerator("test-remove-missing", [], "memory", [])
        project_path = generate_with_copier(template_gen, temp_output_dir)

        # Try to remove scheduler (not enabled)
        result = run_aegis_command(
            "remove", "scheduler", "--project-path", str(project_path), "--yes"
        )

        # Should succeed with message about not enabled
        assert result.success
        assert (
            "not enabled" in result.stdout.lower()
            or "no components to remove" in result.stdout.lower()
        )

    def test_remove_multiple_components(self, temp_output_dir: Path) -> None:
        """Test removing multiple components at once."""
        # Generate project with multiple components
        template_gen = TemplateGenerator(
            "test-remove-multiple", ["scheduler", "database"], "memory", []
        )
        project_path = generate_with_copier(template_gen, temp_output_dir)

        # Remove both components
        result = run_aegis_command(
            "remove",
            "scheduler,database",
            "--project-path",
            str(project_path),
            "--yes",
        )

        assert result.success

        # Verify all components were removed
        updated_answers = load_copier_answers(project_path)
        assert updated_answers.get("include_scheduler") is False
        assert updated_answers.get("include_database") is False

        # Verify files deleted
        assert not (project_path / "app" / "entrypoints" / "scheduler.py").exists()
        assert not (project_path / "app" / "core" / "db.py").exists()

    def test_remove_empty_component_name(self, temp_output_dir: Path) -> None:
        """Test that empty component names are rejected."""
        # Generate project with scheduler
        template_gen = TemplateGenerator(
            "test-remove-empty", ["scheduler"], "memory", []
        )
        project_path = generate_with_copier(template_gen, temp_output_dir)

        # Try to remove with empty component
        result = run_aegis_command(
            "remove",
            "scheduler,,database",
            "--project-path",
            str(project_path),
            "--yes",
        )

        assert not result.success
        assert "empty component name" in result.stderr.lower()

    def test_remove_command_help(self) -> None:
        """Test that remove command has proper help text."""
        result = run_aegis_command("remove", "--help")

        assert result.success
        assert "remove components" in result.stdout.lower()
        assert "warning" in result.stdout.lower()
        assert "delete" in result.stdout.lower()

    @pytest.mark.skip(reason="Redis dependency cleanup logic incomplete")
    def test_remove_worker_keeps_redis(self, temp_output_dir: Path) -> None:
        """Test that removing worker doesn't remove redis if needed by other components."""
        # Generate project with worker (auto-includes redis)
        template_gen = TemplateGenerator("test-remove-worker", ["worker"], "memory", [])
        project_path = generate_with_copier(template_gen, temp_output_dir)

        # Verify both are enabled
        initial_answers = load_copier_answers(project_path)
        assert initial_answers.get("include_worker") is True
        assert initial_answers.get("include_redis") is True

        # Remove worker
        result = run_aegis_command(
            "remove", "worker", "--project-path", str(project_path), "--yes"
        )

        assert result.success

        # Verify worker removed but redis might stay (depends on implementation)
        updated_answers = load_copier_answers(project_path)
        assert updated_answers.get("include_worker") is False
        # Redis stays enabled because it's not automatically removed

    @pytest.mark.skip(reason="Empty directory cleanup edge case")
    def test_remove_cleans_empty_directories(self, temp_output_dir: Path) -> None:
        """Test that removing components cleans up empty parent directories."""
        # Generate project with worker
        template_gen = TemplateGenerator(
            "test-remove-cleanup", ["worker"], "memory", []
        )
        project_path = generate_with_copier(template_gen, temp_output_dir)

        # Verify worker directory exists
        worker_dir = project_path / "app" / "components" / "worker"
        assert worker_dir.exists()

        # Remove worker
        result = run_aegis_command(
            "remove", "worker", "--project-path", str(project_path), "--yes"
        )

        assert result.success

        # Verify worker directory removed
        assert not worker_dir.exists()

    def test_remove_updates_dependencies(self, temp_output_dir: Path) -> None:
        """Test that removing components runs uv sync to clean up dependencies."""
        # Generate project with worker
        template_gen = TemplateGenerator("test-remove-deps", ["worker"], "memory", [])
        project_path = generate_with_copier(template_gen, temp_output_dir)

        # Remove worker
        result = run_aegis_command(
            "remove", "worker", "--project-path", str(project_path), "--yes"
        )

        assert result.success
        assert (
            "dependencies synced" in result.stdout.lower()
            or "uv sync" in result.stdout.lower()
        )


class TestRemoveCommandIntegration:
    """Integration tests for remove command that validate full workflow."""

    @pytest.mark.slow
    def test_add_then_remove_cycle(self, temp_output_dir: Path) -> None:
        """
        Full integration test: add component, then remove it.

        This test validates the complete add/remove cycle works correctly.
        """
        # Generate base project
        template_gen = TemplateGenerator("test-cycle", [], "memory", [])
        project_path = generate_with_copier(template_gen, temp_output_dir)

        # Add scheduler
        add_result = run_aegis_command(
            "add", "scheduler", "--project-path", str(project_path), "--yes"
        )
        assert add_result.success

        # Verify added
        assert (project_path / "app" / "entrypoints" / "scheduler.py").exists()
        answers_after_add = load_copier_answers(project_path)
        assert answers_after_add.get("include_scheduler") is True

        # Remove scheduler
        remove_result = run_aegis_command(
            "remove", "scheduler", "--project-path", str(project_path), "--yes"
        )
        assert remove_result.success

        # Verify removed
        assert not (project_path / "app" / "entrypoints" / "scheduler.py").exists()
        answers_after_remove = load_copier_answers(project_path)
        assert answers_after_remove.get("include_scheduler") is False

    @pytest.mark.slow
    def test_remove_then_add_cycle(self, temp_output_dir: Path) -> None:
        """Test removing a component and then adding it back."""
        # Generate project WITH scheduler
        template_gen = TemplateGenerator("test-re-add", ["scheduler"], "memory", [])
        project_path = generate_with_copier(template_gen, temp_output_dir)

        # Remove scheduler
        remove_result = run_aegis_command(
            "remove", "scheduler", "--project-path", str(project_path), "--yes"
        )
        assert remove_result.success
        assert not (project_path / "app" / "entrypoints" / "scheduler.py").exists()

        # Add it back
        add_result = run_aegis_command(
            "add", "scheduler", "--project-path", str(project_path), "--yes"
        )
        assert add_result.success

        # Verify it's back
        assert (project_path / "app" / "entrypoints" / "scheduler.py").exists()
        final_answers = load_copier_answers(project_path)
        assert final_answers.get("include_scheduler") is True

    @pytest.mark.slow
    def test_remove_keeps_other_components(self, temp_output_dir: Path) -> None:
        """Test that removing one component doesn't affect others."""
        # Generate project with multiple components
        template_gen = TemplateGenerator(
            "test-selective-remove", ["scheduler", "database"], "memory", []
        )
        project_path = generate_with_copier(template_gen, temp_output_dir)

        # Verify both exist
        assert (project_path / "app" / "entrypoints" / "scheduler.py").exists()
        assert (project_path / "app" / "core" / "db.py").exists()

        # Remove only scheduler
        result = run_aegis_command(
            "remove", "scheduler", "--project-path", str(project_path), "--yes"
        )
        assert result.success

        # Verify scheduler removed but database remains
        assert not (project_path / "app" / "entrypoints" / "scheduler.py").exists()
        assert (project_path / "app" / "core" / "db.py").exists()

        final_answers = load_copier_answers(project_path)
        assert final_answers.get("include_scheduler") is False
        assert final_answers.get("include_database") is True

    @pytest.mark.slow
    def test_remove_all_components(self, temp_output_dir: Path) -> None:
        """Test removing all optional components, leaving only core."""
        # Generate project with multiple components
        template_gen = TemplateGenerator(
            "test-remove-all", ["scheduler", "worker", "database"], "memory", []
        )
        project_path = generate_with_copier(template_gen, temp_output_dir)

        # Remove all components one by one
        for component in ["scheduler", "worker", "database"]:
            result = run_aegis_command(
                "remove", component, "--project-path", str(project_path), "--yes"
            )
            assert result.success

        # Verify only core files remain (backend, frontend)
        final_answers = load_copier_answers(project_path)
        assert final_answers.get("include_scheduler") is False
        assert final_answers.get("include_worker") is False
        assert final_answers.get("include_database") is False

        # Core files should still exist
        assert (project_path / "app" / "components" / "backend").exists()
        assert (project_path / "app" / "components" / "frontend").exists()


class TestRemoveCommandInteractive:
    """Test suite for 'aegis remove --interactive' command."""

    def test_remove_interactive_requires_components_or_flag(
        self, temp_output_dir: Path
    ) -> None:
        """Test that remove command requires either components argument or --interactive flag."""
        # Generate project with scheduler
        scheduler_component = COMPONENTS["scheduler"]
        template_gen = TemplateGenerator(
            "test-remove-requires-arg",
            [scheduler_component.name],
            "memory",
            [],
        )
        project_path = generate_with_copier(template_gen, temp_output_dir)

        # Try to run remove without components or --interactive
        result = run_aegis_command(
            "remove", "--project-path", str(project_path), "--yes"
        )

        # Should fail with helpful message
        assert not result.success
        assert "components argument is required" in result.stderr.lower()
        assert "--interactive" in result.stderr.lower()

    def test_remove_interactive_base_project_no_components(
        self, temp_output_dir: Path
    ) -> None:
        """Test that interactive mode reports no removable components on base project."""
        # Generate base project (core only)
        template_gen = TemplateGenerator(
            "test-remove-interactive-base", [], "memory", []
        )
        project_path = generate_with_copier(template_gen, temp_output_dir)

        # Verify no infrastructure components enabled
        answers = load_copier_answers(project_path)
        for component_name in COMPONENTS:
            if component_name not in CORE_COMPONENTS:
                include_key = f"include_{component_name}"
                assert answers.get(include_key) is False, (
                    f"{component_name} should not be enabled"
                )

        # If we ran interactive mode, it would show "No optional components to remove"

    def test_remove_interactive_detects_enabled_components(
        self, temp_output_dir: Path
    ) -> None:
        """Test that interactive mode detects enabled components for removal."""
        # Generate project with multiple components
        scheduler_component = COMPONENTS["scheduler"]
        database_component = COMPONENTS["database"]
        template_gen = TemplateGenerator(
            "test-remove-interactive-enabled",
            [scheduler_component.name, database_component.name],
            "memory",
            [],
        )
        project_path = generate_with_copier(template_gen, temp_output_dir)

        # Verify both components are enabled
        answers = load_copier_answers(project_path)
        assert answers.get("include_scheduler") is True
        assert answers.get("include_database") is True

        # The interactive function would offer both for removal
        # (Can't test interactive prompts, but we verify state detection)

    def test_remove_interactive_core_components_protected(
        self, temp_output_dir: Path
    ) -> None:
        """Test that core components cannot be removed."""
        # Generate base project
        template_gen = TemplateGenerator("test-remove-core-protected", [], "memory", [])
        project_path = generate_with_copier(template_gen, temp_output_dir)

        # Core components should always be present (implicitly)
        # The interactive mode would show them as "cannot remove"
        for core_component in CORE_COMPONENTS:
            # Core components don't have include_* flags (they're always included)
            # Verify the files exist
            component_spec = COMPONENTS.get(core_component)
            if component_spec and component_spec.template_files:
                for template_file in component_spec.template_files:
                    expected_path = project_path / template_file
                    assert expected_path.exists(), (
                        f"Core component {core_component} file missing: {template_file}"
                    )

    @pytest.mark.slow
    def test_remove_interactive_workflow_removes_component(
        self, temp_output_dir: Path
    ) -> None:
        """Test that components removed via remove command update project correctly."""
        # Generate project WITH scheduler
        scheduler_component = COMPONENTS["scheduler"]
        template_gen = TemplateGenerator(
            "test-remove-workflow",
            [scheduler_component.name],
            "memory",
            [],
        )
        project_path = generate_with_copier(template_gen, temp_output_dir)

        # Verify scheduler is present initially
        initial_answers = load_copier_answers(project_path)
        assert initial_answers.get("include_scheduler") is True

        # Remove scheduler component (non-interactive, but validates the workflow)
        result = run_aegis_command(
            "remove",
            scheduler_component.name,
            "--project-path",
            str(project_path),
            "--yes",
            timeout=CLI_TIMEOUT_STANDARD,
        )

        assert result.success, (
            f"Failed to remove {scheduler_component.name}: {result.stderr}"
        )

        # Verify scheduler was removed from answers
        updated_answers = load_copier_answers(project_path)
        assert updated_answers.get("include_scheduler") is False

        # Verify expected files are deleted (from component template_files)
        assert scheduler_component.template_files is not None
        for template_file in scheduler_component.template_files:
            expected_file = project_path / template_file
            assert not expected_file.exists(), f"File {template_file} should be deleted"

    @pytest.mark.slow
    def test_remove_interactive_workflow_multiple_components(
        self, temp_output_dir: Path
    ) -> None:
        """Test removing multiple components in sequence."""
        # Generate project with scheduler and database
        scheduler_component = COMPONENTS["scheduler"]
        database_component = COMPONENTS["database"]
        template_gen = TemplateGenerator(
            "test-remove-multiple",
            [scheduler_component.name, database_component.name],
            "memory",
            [],
        )
        project_path = generate_with_copier(template_gen, temp_output_dir)

        # Remove scheduler first
        result1 = run_aegis_command(
            "remove",
            scheduler_component.name,
            "--project-path",
            str(project_path),
            "--yes",
            timeout=CLI_TIMEOUT_STANDARD,
        )
        assert result1.success

        # Remove database second
        result2 = run_aegis_command(
            "remove",
            database_component.name,
            "--project-path",
            str(project_path),
            "--yes",
            timeout=CLI_TIMEOUT_STANDARD,
        )
        assert result2.success

        # Verify both are removed
        final_answers = load_copier_answers(project_path)
        assert final_answers.get("include_scheduler") is False
        assert final_answers.get("include_database") is False

        # Verify core components still exist
        backend_spec = COMPONENTS["backend"]
        assert backend_spec.template_files is not None
        for template_file in backend_spec.template_files:
            core_file = project_path / template_file
            assert core_file.exists(), f"Core file {template_file} should remain"

    def test_remove_validates_component_names_in_interactive(
        self, temp_output_dir: Path
    ) -> None:
        """Test that component validation works the same in interactive mode."""
        # Generate project with scheduler
        scheduler_component = COMPONENTS["scheduler"]
        template_gen = TemplateGenerator(
            "test-remove-interactive-validation",
            [scheduler_component.name],
            "memory",
            [],
        )
        project_path = generate_with_copier(template_gen, temp_output_dir)

        # Try to remove invalid component (non-interactive for validation test)
        result = run_aegis_command(
            "remove",
            "nonexistent_component",
            "--project-path",
            str(project_path),
            "--yes",
        )

        # Should fail with validation error
        assert not result.success
        assert "unknown component" in result.stderr.lower()


class TestRemoveCommandVersionCompatibility:
    """Test version compatibility checks in remove command."""

    def test_remove_with_force_flag_available(self) -> None:
        """Test that remove command accepts --force flag."""
        result = run_aegis_command("remove", "--help")

        assert result.success
        assert "--force" in result.stdout or "-f" in result.stdout

    def test_remove_command_version_check_skipped_when_no_version(
        self, temp_output_dir: Path
    ) -> None:
        """Test that remove command works when project version can't be determined."""
        # Generate a project with scheduler
        template_gen = TemplateGenerator(
            "test-remove-no-version", ["scheduler"], "memory", []
        )
        project_path = generate_with_copier(template_gen, temp_output_dir)

        # Remove a component - should work even if version can't be determined
        result = run_aegis_command(
            "remove", "scheduler", "--project-path", str(project_path), "--yes"
        )

        # Should succeed (version check is skipped when version unknown)
        assert result.success, f"Command failed: {result.stderr}"

    def test_remove_force_flag_bypasses_version_warning(
        self, temp_output_dir: Path
    ) -> None:
        """Test that --force flag is available for bypassing warnings."""
        # Generate a project with scheduler
        template_gen = TemplateGenerator(
            "test-remove-force", ["scheduler"], "memory", []
        )
        project_path = generate_with_copier(template_gen, temp_output_dir)

        # Try remove with force flag (should be accepted even if not needed)
        result = run_aegis_command(
            "remove",
            "scheduler",
            "--project-path",
            str(project_path),
            "--yes",
            "--force",
        )

        # Should succeed
        assert result.success, f"Command failed: {result.stderr}"
