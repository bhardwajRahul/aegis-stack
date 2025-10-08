"""
Experimental Copier-based updater using git-aware template at repo root.

This module provides an alternative to the manual updater by using Copier's
native update mechanism with a copier.yml at the repository root.
"""

from pathlib import Path

from copier import run_update
from pydantic import BaseModel, Field

from aegis.core.copier_manager import load_copier_answers
from aegis.core.post_gen_tasks import run_post_generation_tasks


class CopierUpdateResult(BaseModel):
    """Result of a Copier update operation."""

    success: bool = Field(description="Whether the operation succeeded")
    method: str = Field(default="copier-native", description="Update method used")
    error_message: str | None = Field(
        default=None, description="Error message if operation failed"
    )
    files_modified: list[str] = Field(
        default_factory=list, description="Files that were modified"
    )


def get_template_root() -> Path:
    """
    Get path to aegis-stack repository root (where copier.yml lives).

    Returns:
        Path to aegis-stack root directory
    """
    # This file is at: aegis-stack/aegis/core/copier_updater.py
    # We want: aegis-stack/ (2 levels up)
    return Path(__file__).parents[2]


def update_with_copier_native(
    project_path: Path,
    components_to_add: list[str],
    scheduler_backend: str = "memory",
) -> CopierUpdateResult:
    """
    EXPERIMENTAL: Use Copier's native update with git root template.

    This approach uses the copier.yml at aegis-stack repo root which
    includes _subdirectory setting. This allows Copier to recognize the
    template as git-tracked and use proper merge conflict handling.

    Args:
        project_path: Path to the existing project directory
        components_to_add: List of component names to add
        scheduler_backend: Backend to use for scheduler ("memory" or "sqlite")

    Returns:
        CopierUpdateResult with success status

    Note:
        This is experimental. Falls back to manual updater if it fails.
    """
    try:
        # Get template root (aegis-stack/, not aegis/templates/...)
        template_root = get_template_root()

        # Build update data for Copier
        update_data: dict[str, bool | str] = {}

        for component in components_to_add:
            include_key = f"include_{component}"
            update_data[include_key] = True

        # Add scheduler backend configuration if adding scheduler
        if "scheduler" in components_to_add:
            update_data["scheduler_backend"] = scheduler_backend
            update_data["scheduler_with_persistence"] = scheduler_backend == "sqlite"

        # CRITICAL: Manually update .copier-answers.yml BEFORE running copier update
        # The `data` parameter in run_update() doesn't actually update existing answers
        # We must edit the file directly, then Copier detects the change and regenerates
        answers = load_copier_answers(project_path)
        answers.update(update_data)

        # Save updated answers
        import yaml

        answers_file = project_path / ".copier-answers.yml"
        with open(answers_file, "w") as f:
            yaml.safe_dump(answers, f, default_flow_style=False, sort_keys=False)

        # Commit the updated answers (Copier requires clean repo)
        import subprocess

        try:
            subprocess.run(
                ["git", "add", ".copier-answers.yml"],
                cwd=project_path,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                [
                    "git",
                    "commit",
                    "-m",
                    f"Enable components: {', '.join(components_to_add)}",
                ],
                cwd=project_path,
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to commit .copier-answers.yml changes: {e}")

        # Run Copier update
        # Copier will detect the changed answers and regenerate files accordingly
        # Copier will:
        # 1. Use repo root as template (where .git exists)
        # 2. _subdirectory setting in copier.yml points to actual template content
        # 3. Detect template is git-tracked (finds .git at aegis-stack/)
        # 4. Detect changed answers in .copier-answers.yml (we just committed them)
        # 5. Use git diff to merge changes
        # 6. Handle conflicts with .rej files or inline markers
        # NOTE: _tasks removed from copier.yml - we run them ourselves below
        run_update(
            dst_path=str(project_path),
            src_path=str(template_root),  # Point to repo root, not subdirectory
            defaults=True,  # Use existing answers as defaults
            overwrite=True,  # Allow overwriting files
            conflict="rej",  # Create .rej files for conflicts
            unsafe=False,  # No tasks in copier.yml anymore - we run them ourselves
            vcs_ref="HEAD",  # Use latest template version
        )

        # Run post-generation tasks with explicit working directory control
        # This ensures consistent behavior with initial generation
        answers = load_copier_answers(project_path)
        include_auth = answers.get("include_auth", False)

        # Run shared post-generation tasks
        run_post_generation_tasks(project_path, include_auth=include_auth)

        return CopierUpdateResult(
            success=True,
            method="copier-native",
            files_modified=[],  # Copier doesn't provide this info easily
        )

    except Exception as e:
        return CopierUpdateResult(
            success=False, method="copier-native", error_message=str(e)
        )
