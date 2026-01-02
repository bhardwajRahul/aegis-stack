"""
Template cleanup utilities for post-update processing.

This module handles cleanup tasks after Copier updates, particularly
dealing with nested directory structures created during template updates.
"""

import shutil
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
