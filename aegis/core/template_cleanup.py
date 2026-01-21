"""
Template cleanup utilities for post-update processing.

This module handles cleanup tasks after Copier updates, particularly
dealing with nested directory structures created during template updates.
"""

import shutil
import tempfile
from pathlib import Path

from .verbosity import verbose_print


def cleanup_nested_project_directory(
    project_path: Path,
    project_slug: str,
) -> list[str]:
    """
    Move files from nested project_slug directory up to project root.

    This handles Copier's behavior during updates where NEW files
    get created with {{ project_slug }}/ prefix. The template uses
    a {{ project_slug }}/ wrapper directory, which Copier renders
    during updates, creating nested paths like:

        project/project_slug/new_file.py

    This function moves such files to their correct location:

        project/new_file.py

    Args:
        project_path: Path to project root
        project_slug: The project slug (from .copier-answers.yml)

    Returns:
        List of relative file paths that were moved
    """
    if not project_slug:
        return []

    nested_dir = project_path / project_slug

    if not nested_dir.exists() or not nested_dir.is_dir():
        return []

    files_moved: list[str] = []

    # Collect all files first (avoid modifying while iterating)
    files_to_move: list[tuple[Path, Path]] = []

    for item in nested_dir.rglob("*"):
        if item.is_dir():
            continue

        # Calculate destination path
        relative = item.relative_to(nested_dir)
        dest = project_path / relative

        files_to_move.append((item, dest))

    # Move files
    for source, dest in files_to_move:
        try:
            # Create parent directories if needed
            dest.parent.mkdir(parents=True, exist_ok=True)

            # Handle case where file exists at both locations
            if dest.exists():
                # Keep the nested version (it's from newer template)
                # This handles edge cases where Copier created duplicates
                dest.unlink()
                verbose_print(f"   Replaced: {dest.relative_to(project_path)}")

            shutil.move(str(source), str(dest))

            relative_path = str(dest.relative_to(project_path))
            files_moved.append(relative_path)
            verbose_print(f"   Moved: {relative_path}")
        except (OSError, shutil.Error) as e:
            raise RuntimeError(f"Failed to move {source} to {dest}: {e}") from e

    # Remove the nested directory tree (non-critical cleanup)
    if nested_dir.exists():
        try:
            shutil.rmtree(nested_dir)
            verbose_print(f"   Removed nested directory: {project_slug}/")
        except (OSError, shutil.Error):
            # Non-critical: nested dir removal is just cleanup
            verbose_print(f"   Warning: Could not remove {project_slug}/")

    return files_moved


def sync_template_changes(
    project_path: Path,
    answers: dict,
    template_src: str,
    vcs_ref: str,
) -> list[str]:
    """
    Sync template changes that Copier's git apply may have missed.

    Copier's update mechanism uses `git apply` with exclusions based on
    `git status --ignored`. When the template uses a {{ project_slug }}/
    wrapper, and the nested directory contains only ignored files, the
    entire project slug directory gets excluded from the patch.

    This function works around that by:
    1. Rendering the new template to a temp directory
    2. Comparing files between project and rendered template
    3. Updating project files that differ from template

    Note: This function only syncs EXISTING files. New files are handled by
    cleanup_nested_project_directory() which must run BEFORE this function.
    The update command (aegis/commands/update.py) ensures this ordering.

    Args:
        project_path: Path to project root
        answers: Copier answers dict (from .copier-answers.yml)
        template_src: Template source (e.g., "gh:user/repo")
        vcs_ref: Git ref for template version (e.g., "v0.5.3-rc1")

    Returns:
        List of relative file paths that were updated
    """
    from copier import run_copy

    project_slug = answers.get("project_slug", "")
    if not project_slug:
        return []

    files_updated: list[str] = []

    # Create temp directory for rendered template
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Render the new template version
        try:
            run_copy(
                src_path=template_src,
                dst_path=str(temp_path),
                data=answers,
                defaults=True,
                overwrite=True,
                unsafe=False,
                vcs_ref=vcs_ref,
                quiet=True,
            )
        except Exception as e:
            verbose_print(f"   Warning: Could not render template for sync: {e}")
            return []

        # The rendered template is in temp_path/project_slug/
        rendered_dir = temp_path / project_slug
        if not rendered_dir.exists():
            return []

        # Compare and sync files
        for template_file in rendered_dir.rglob("*"):
            if template_file.is_dir():
                continue

            # Skip certain files that shouldn't be synced
            relative = template_file.relative_to(rendered_dir)
            if _should_skip_sync(str(relative)):
                continue

            project_file = project_path / relative

            # Only update existing files (new files handled by cleanup_nested)
            if not project_file.exists():
                continue

            # Compare file contents
            try:
                template_content = template_file.read_bytes()
                project_content = project_file.read_bytes()

                if template_content != project_content:
                    # Update project file with template version
                    project_file.write_bytes(template_content)
                    files_updated.append(str(relative))
                    verbose_print(f"   Synced: {relative}")
            except OSError as e:
                verbose_print(f"   Warning: Could not sync {relative}: {e}")

    return files_updated


def _should_skip_sync(relative_path: str) -> bool:
    """Check if a file should be skipped during template sync."""
    skip_patterns = [
        ".copier-answers.yml",
        ".env",
        ".python-version",
        ".venv/",
        "__pycache__/",
        ".git/",
        "*.pyc",
    ]

    for pattern in skip_patterns:
        if pattern.endswith("/"):
            if relative_path.startswith(pattern) or f"/{pattern}" in relative_path:
                return True
        elif pattern.startswith("*"):
            if relative_path.endswith(pattern[1:]):
                return True
        elif relative_path == pattern:
            return True

    return False
