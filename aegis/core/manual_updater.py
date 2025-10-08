"""
Manual project update mechanism (Copier-lite).

This module provides manual component addition/removal without relying on
Copier's git-dependent update mechanism. It directly renders Jinja2 templates
and copies files to the target project.
"""

import shutil
import subprocess
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from pydantic import BaseModel, Field

from aegis.config.shared_files import SHARED_TEMPLATE_FILES

from .component_files import get_component_files, get_template_path
from .copier_manager import is_copier_project, load_copier_answers

# Constants
COPIER_ANSWERS_FILE = ".copier-answers.yml"
COPIER_ANSWERS_HEADER = (
    "# Changes here will be overwritten by Copier; NEVER EDIT MANUALLY\n"
)
PROJECT_SLUG_PLACEHOLDER = "{{ project_slug }}"
JINJA_EXTENSION = ".jinja"


class UpdateResult(BaseModel):
    """Result of a component update operation."""

    component: str = Field(description="Component that was updated")
    files_modified: list[str] = Field(
        default_factory=list, description="Files that were created/modified"
    )
    files_deleted: list[str] = Field(
        default_factory=list, description="Files that were deleted"
    )
    files_skipped: list[str] = Field(
        default_factory=list, description="Files that already existed and were skipped"
    )
    shared_files_updated: list[str] = Field(
        default_factory=list, description="Shared template files that were regenerated"
    )
    shared_files_backed_up: list[str] = Field(
        default_factory=list,
        description="Shared files that were backed up before update",
    )
    shared_files_need_manual_merge: list[str] = Field(
        default_factory=list, description="Shared files that need manual merging"
    )
    success: bool = Field(description="Whether the operation succeeded")
    error_message: str | None = Field(
        default=None, description="Error message if operation failed"
    )


class ManualUpdater:
    """
    Manual project updater that bypasses Copier's update mechanism.

    This class provides component addition/removal by:
    1. Reading current state from .copier-answers.yml
    2. Rendering Jinja2 templates with updated context
    3. Copying rendered files to project
    4. Updating .copier-answers.yml
    5. Running post-generation tasks
    """

    def __init__(self, project_path: Path):
        """
        Initialize updater for a project.

        Args:
            project_path: Path to the Aegis Stack project

        Raises:
            FileNotFoundError: If project is not a Copier-generated project
        """
        if not is_copier_project(project_path):
            raise FileNotFoundError(
                f"Project at {project_path} was not generated with Copier"
            )

        self.project_path = project_path
        self.template_path = get_template_path()
        self.answers = load_copier_answers(project_path)

        # Setup Jinja2 environment
        # Template files are at: template/{{ project_slug }}/...
        # We need to point to the template root
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.template_path)),
            trim_blocks=False,  # Preserve newlines after blocks (matches Copier default)
            lstrip_blocks=False,  # Preserve whitespace for parity
        )

    def add_component(
        self,
        component: str,
        additional_data: dict[str, Any] | None = None,
    ) -> UpdateResult:
        """
        Add a component to the project.

        Args:
            component: Component name (e.g., "scheduler", "worker")
            additional_data: Additional configuration data (e.g., scheduler_backend)

        Returns:
            UpdateResult with files modified/skipped

        Raises:
            ValueError: If component is already enabled or no files found
        """
        files_modified: list[str] = []
        files_skipped: list[str] = []
        shared_files_updated: list[str] = []
        shared_files_backed_up: list[str] = []
        shared_files_need_manual_merge: list[str] = []

        try:
            # Check if already enabled
            include_key = f"include_{component}"
            if self.answers.get(include_key) is True:
                raise ValueError(f"Component '{component}' is already enabled")

            # Merge additional data
            update_data = additional_data or {}
            update_data[include_key] = True

            # Update answers with new component
            updated_answers = {**self.answers, **update_data}

            # Get files for this component
            backend_variant = (
                update_data.get("scheduler_backend")
                if component == "scheduler"
                else None
            )
            component_files = get_component_files(component, backend_variant)

            if not component_files:
                raise ValueError(f"No files found for component '{component}'")

            # Render and copy each file
            rendered_files: dict[Path, str] = {}

            for file_path in component_files:
                # Convert relative path to template path
                # copier_files: "app/components/scheduler"
                # template_file: "{{ project_slug }}/app/components/scheduler.jinja"
                template_file = f"{PROJECT_SLUG_PLACEHOLDER}/{file_path}"

                # Try with .jinja extension first, then without
                content = self._render_template_file(template_file, updated_answers)

                if content is not None:
                    # Output path in project
                    output_path = self.project_path / file_path
                    rendered_files[output_path] = content

            # Copy files to project
            for output_path, content in rendered_files.items():
                # Create parent directories
                output_path.parent.mkdir(parents=True, exist_ok=True)

                relative_path = str(output_path.relative_to(self.project_path))

                # Check for conflicts
                if output_path.exists():
                    # For now, skip existing files
                    # TODO: Implement conflict resolution
                    print(f"   ⚠️  Skipping existing file: {relative_path}")
                    files_skipped.append(relative_path)
                    continue

                # Write file
                output_path.write_text(content)
                print(f"   ✅ Created: {relative_path}")
                files_modified.append(relative_path)

            # Handle shared template files (docker-compose.yml, pyproject.toml, etc.)
            # These files always exist and need to be regenerated with updated answers
            print("\n📦 Updating shared template files...")
            for shared_file, policy in SHARED_TEMPLATE_FILES.items():
                template_file = f"{PROJECT_SLUG_PLACEHOLDER}/{shared_file}"
                output_path = self.project_path / shared_file

                # Skip if file doesn't exist (shouldn't happen for shared files)
                if not output_path.exists():
                    continue

                # Render template with updated answers
                content = self._render_template_file(template_file, updated_answers)

                if content is None:
                    continue  # Template not found

                if policy.get("backup"):
                    # Create backup before overwriting
                    backup_path = output_path.with_suffix(
                        output_path.suffix + ".backup"
                    )
                    shutil.copy(output_path, backup_path)
                    print(f"   💾 Backed up: {shared_file}")
                    shared_files_backed_up.append(shared_file)

                if policy.get("overwrite"):
                    # Regenerate with updated answers
                    output_path.write_text(content)
                    print(f"   ♻️  Updated: {shared_file}")
                    shared_files_updated.append(shared_file)
                elif policy.get("warn"):
                    # Warn user manual merge needed
                    print(f"   ⚠️  Manual merge required: {shared_file}")
                    shared_files_need_manual_merge.append(shared_file)

            # Update .copier-answers.yml
            self._save_answers(updated_answers)

            # Run post-generation tasks
            self._run_post_generation_tasks()

            return UpdateResult(
                component=component,
                files_modified=files_modified,
                files_skipped=files_skipped,
                shared_files_updated=shared_files_updated,
                shared_files_backed_up=shared_files_backed_up,
                shared_files_need_manual_merge=shared_files_need_manual_merge,
                success=True,
            )

        except Exception as e:
            return UpdateResult(
                component=component,
                files_modified=files_modified,
                files_skipped=files_skipped,
                success=False,
                error_message=str(e),
            )

    def remove_component(self, component: str) -> UpdateResult:
        """
        Remove a component from the project.

        Args:
            component: Component name to remove

        Returns:
            UpdateResult with files deleted

        Raises:
            ValueError: If component is not enabled
        """
        files_deleted: list[str] = []

        try:
            # Check if enabled
            include_key = f"include_{component}"
            if not self.answers.get(include_key):
                raise ValueError(f"Component '{component}' is not enabled")

            # Get files for this component
            backend_variant = (
                self.answers.get("scheduler_backend")
                if component == "scheduler"
                else None
            )
            component_files = get_component_files(component, backend_variant)

            # Delete each file
            deleted_paths: list[Path] = []

            for file_path in component_files:
                full_path = self.project_path / file_path

                if full_path.exists():
                    relative_path = str(full_path.relative_to(self.project_path))

                    if full_path.is_dir():
                        shutil.rmtree(full_path)
                        print(f"   🗑️  Removed directory: {relative_path}")
                    else:
                        full_path.unlink()
                        print(f"   🗑️  Removed file: {relative_path}")

                    files_deleted.append(relative_path)
                    deleted_paths.append(full_path)

            # Clean up empty parent directories
            for file_path in deleted_paths:
                parent = file_path.parent
                try:
                    if parent.exists() and not any(parent.iterdir()):
                        parent.rmdir()
                        relative_parent = str(parent.relative_to(self.project_path))
                        print(f"   🗑️  Removed empty directory: {relative_parent}")
                except OSError:
                    # Directory not empty or other error, skip
                    pass

            # Update answers
            updated_answers = {**self.answers, include_key: False}

            # Also reset backend variant if removing scheduler
            if component == "scheduler":
                updated_answers["scheduler_backend"] = "memory"
                updated_answers["scheduler_with_persistence"] = False

            self._save_answers(updated_answers)

            # Run post-generation tasks to clean up dependencies
            self._run_post_generation_tasks()

            return UpdateResult(
                component=component,
                files_deleted=files_deleted,
                success=True,
            )

        except Exception as e:
            return UpdateResult(
                component=component,
                files_deleted=files_deleted,
                success=False,
                error_message=str(e),
            )

    def _render_template_file(
        self, template_file: str, context: dict[str, Any]
    ) -> str | None:
        """
        Render a Jinja2 template file.

        Args:
            template_file: Template file path (relative to template root)
            context: Jinja2 context variables

        Returns:
            Rendered content, or None if template not found
        """
        # Try with .jinja extension
        try:
            template = self.jinja_env.get_template(f"{template_file}{JINJA_EXTENSION}")
            return template.render(context)
        except TemplateNotFound:
            pass

        # Try without extension
        try:
            template = self.jinja_env.get_template(template_file)
            return template.render(context)
        except TemplateNotFound:
            return None

    def _save_answers(self, answers: dict[str, Any]) -> None:
        """
        Save updated answers to .copier-answers.yml.

        Args:
            answers: Updated answers dictionary
        """
        import yaml

        answers_file = self.project_path / COPIER_ANSWERS_FILE

        # Preserve metadata
        answers_with_meta = {
            **answers,
            "_commit": answers.get("_commit", "None"),
            "_src_path": answers.get("_src_path", str(self.template_path)),
        }

        with open(answers_file, "w") as f:
            f.write(COPIER_ANSWERS_HEADER)
            yaml.safe_dump(
                answers_with_meta, f, default_flow_style=False, sort_keys=False
            )

        self.answers = answers

    def _run_post_generation_tasks(self) -> None:
        """
        Run post-generation tasks (uv sync, make fix).

        This ensures:
        - Dependencies are updated
        - Code is auto-formatted
        - Imports are organized
        """
        print("\n🔧 Running post-generation tasks...")

        # Run uv sync to update dependencies
        try:
            subprocess.run(
                ["uv", "sync", "--all-extras"],
                cwd=self.project_path,
                check=True,
                capture_output=True,
            )
            print("   ✅ Dependencies synced (uv sync)")
        except subprocess.CalledProcessError as e:
            print(f"   ⚠️  Failed to sync dependencies: {e}")

        # Run make fix to auto-format code
        try:
            subprocess.run(
                ["make", "fix"],
                cwd=self.project_path,
                check=True,
                capture_output=True,
            )
            print("   ✅ Code formatted (make fix)")
        except subprocess.CalledProcessError as e:
            print(f"   ⚠️  Failed to format code: {e}")


def add_component_manual(
    project_path: Path,
    component: str,
    additional_data: dict[str, Any] | None = None,
) -> None:
    """
    Convenience function to add a component to a project.

    Args:
        project_path: Path to the Aegis Stack project
        component: Component name
        additional_data: Additional configuration data
    """
    updater = ManualUpdater(project_path)
    updater.add_component(component, additional_data)


def remove_component_manual(project_path: Path, component: str) -> None:
    """
    Convenience function to remove a component from a project.

    Args:
        project_path: Path to the Aegis Stack project
        component: Component name
    """
    updater = ManualUpdater(project_path)
    updater.remove_component(component)
