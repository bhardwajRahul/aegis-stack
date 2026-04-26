"""
Template cleanup utilities for post-update processing.

This module handles cleanup tasks after Copier updates, particularly
dealing with nested directory structures created during template updates.
"""

import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from .verbosity import verbose_print


@dataclass
class SyncResult:
    """Result of sync_template_changes() with details about what happened."""

    synced: list[str] = field(default_factory=list)
    """Files updated (clean merge or overwrite)."""

    conflicts: list[str] = field(default_factory=list)
    """Files with merge conflict markers that need manual resolution."""


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

            # Skip files that already exist — sync_template_changes() will
            # handle them with a proper 3-way merge that preserves user
            # customizations. Only move truly NEW files here.
            if dest.exists():
                source.unlink()
                verbose_print(
                    f"   Skipped (exists, will merge): {dest.relative_to(project_path)}"
                )
                continue

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
    template_changed_files: set[str] | None = None,
    old_commit: str | None = None,
) -> SyncResult:
    """
    Sync template changes using 3-way merge to preserve user customizations.

    Copier's update mechanism uses `git apply` which is non-functional for
    Aegis projects due to the {{ project_slug }}/ wrapper causing path
    mismatches. This function is the primary mechanism for updating project
    files.

    It performs a 3-way merge for each changed file:
    - **Base**: Old template render (what the project was originally generated from)
    - **Current**: User's project file (may have customizations)
    - **Other**: New template render (the update target)

    Decision logic per file:
    1. Old template doesn't exist → new file → write new version
    2. Old template == user's file → user didn't customize → safe overwrite
    3. Old template == new template → template didn't change → skip
    4. All three differ → 3-way merge via `git merge-file`

    Note: This function only syncs EXISTING files. New files are handled by
    cleanup_nested_project_directory() which must run BEFORE this function.

    Args:
        project_path: Path to project root
        answers: Copier answers dict (from .copier-answers.yml)
        template_src: Template source (e.g., "gh:user/repo")
        vcs_ref: Git ref for template version (e.g., "v0.5.3-rc1")
        template_changed_files: Set of project-relative file paths that
            actually changed in the template between versions. When provided,
            only these files are eligible for sync.
        old_commit: Git ref for the OLD template version (from _commit in
            .copier-answers.yml). Used to render the base version for 3-way merge.

    Returns:
        SyncResult with lists of synced files and files with conflicts.
    """
    from copier import run_copy

    project_slug = answers.get("project_slug", "")
    if not project_slug:
        return SyncResult()

    result = SyncResult()

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        new_render = temp_path / "new"
        old_render = temp_path / "old"

        # Render the NEW template version
        try:
            run_copy(
                src_path=template_src,
                dst_path=str(new_render),
                data=answers,
                defaults=True,
                overwrite=True,
                unsafe=False,
                vcs_ref=vcs_ref,
                quiet=True,
            )
        except Exception as e:
            verbose_print(f"   Warning: Could not render new template for sync: {e}")
            return SyncResult()

        new_rendered_dir = new_render / project_slug
        if not new_rendered_dir.exists():
            return SyncResult()

        # Render the OLD template version (for 3-way merge base)
        old_rendered_dir: Path | None = None
        if old_commit:
            try:
                run_copy(
                    src_path=template_src,
                    dst_path=str(old_render),
                    data=answers,
                    defaults=True,
                    overwrite=True,
                    unsafe=False,
                    vcs_ref=old_commit,
                    quiet=True,
                )
                candidate = old_render / project_slug
                if candidate.exists():
                    old_rendered_dir = candidate
            except Exception as e:
                verbose_print(
                    f"   Warning: Could not render old template for merge base: {e}"
                )
                # Fall back to overwrite behavior (no old render available)

        # Compare and sync files
        for template_file in new_rendered_dir.rglob("*"):
            if template_file.is_dir():
                continue

            relative = template_file.relative_to(new_rendered_dir)
            if _should_skip_sync(str(relative)):
                continue

            project_file = project_path / relative

            # Only sync files the template actually changed between versions
            if (
                template_changed_files is not None
                and relative.as_posix() not in template_changed_files
            ):
                continue

            # Only update existing files (new files handled by cleanup_nested)
            if not project_file.exists():
                continue

            try:
                new_content = template_file.read_bytes()
                project_content = project_file.read_bytes()

                # No difference — nothing to do
                if new_content == project_content:
                    continue

                old_file = old_rendered_dir / relative if old_rendered_dir else None

                if old_file and old_file.exists():
                    old_content = old_file.read_bytes()

                    if old_content == project_content:
                        # User didn't customize — safe to use new version
                        project_file.write_bytes(new_content)
                        result.synced.append(str(relative))
                        verbose_print(f"   Synced: {relative}")
                    elif old_content == new_content:
                        # Template didn't change this file — keep user's version
                        verbose_print(f"   Preserved: {relative} (user customized)")
                        continue
                    else:
                        # All three differ — 3-way merge
                        _three_way_merge(
                            project_file, old_file, template_file, relative, result
                        )
                else:
                    # No old render available — fall back to overwrite
                    project_file.write_bytes(new_content)
                    result.synced.append(str(relative))
                    verbose_print(f"   Synced: {relative}")

            except OSError as e:
                verbose_print(f"   Warning: Could not sync {relative}: {e}")

    return result


def _three_way_merge(
    project_file: Path,
    old_file: Path,
    new_file: Path,
    relative: Path,
    result: SyncResult,
) -> None:
    """Perform a 3-way merge using git merge-file.

    Non-conflicting changes from both sides are merged automatically.
    When conflicts exist (both sides changed the same region), the merged
    output with conflict markers is written to the file and reported as a
    conflict for manual resolution, similar to how ``git merge`` behaves.

    This avoids both failure modes of auto-resolution:
    - --ours silently dropped template fixes
    - --theirs silently overwrote user customizations

    Args:
        project_file: User's current file (modified in-place on merge).
        old_file: Old template render (base).
        new_file: New template render (other).
        relative: Relative path for logging/reporting.
        result: SyncResult to append synced/conflict info to.
    """
    merge = subprocess.run(
        [
            "git",
            "merge-file",
            "-p",
            str(project_file),
            str(old_file),
            str(new_file),
        ],
        capture_output=True,
        check=False,
    )
    try:
        if merge.returncode == 0:
            # Clean merge — no conflicts, both sides' changes applied
            project_file.write_bytes(merge.stdout)
            result.synced.append(str(relative))
            verbose_print(f"   Merged: {relative}")
        elif merge.returncode == 1:
            # Conflicts exist — write merged output with conflict markers
            # directly into the file, just like git merge does
            project_file.write_bytes(merge.stdout)
            result.conflicts.append(str(relative))
            verbose_print(f"   Conflict (needs manual review): {relative}")
        else:
            # merge-file failed entirely — fall back to overwrite
            new_content = new_file.read_bytes()
            project_file.write_bytes(new_content)
            result.synced.append(str(relative))
            verbose_print(f"   Synced (merge failed, overwrote): {relative}")
    except OSError as e:
        verbose_print(f"   Warning: Could not sync {relative}: {e}")


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
