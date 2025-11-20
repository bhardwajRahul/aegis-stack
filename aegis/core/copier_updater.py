"""
Experimental Copier-based updater using git-aware template at repo root.

This module provides an alternative to the manual updater by using Copier's
native update mechanism with a copier.yml at the repository root.
"""

import logging
import subprocess
from pathlib import Path

from copier import run_update
from packaging.version import parse
from pydantic import BaseModel, Field

from aegis.core.copier_manager import load_copier_answers
from aegis.core.post_gen_tasks import run_post_generation_tasks

logger = logging.getLogger(__name__)


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


def get_template_root(override_path: str | None = None) -> Path:
    """
    Get path to aegis-stack repository root (where copier.yml lives).

    Args:
        override_path: Optional custom template path to use instead of default

    Returns:
        Path to aegis-stack root directory

    Raises:
        ValueError: If override_path is invalid or missing required structure
    """
    if override_path:
        template_path = Path(override_path).expanduser().resolve()

        # Validate path exists
        if not template_path.exists():
            raise ValueError(f"Template path does not exist: {template_path}")

        # Validate it's a directory
        if not template_path.is_dir():
            raise ValueError(f"Template path is not a directory: {template_path}")

        # Validate it has copier.yml
        if not (template_path / "copier.yml").exists():
            raise ValueError(f"Invalid template: missing copier.yml at {template_path}")

        # Validate it's a git repository
        if not (template_path / ".git").exists():
            raise ValueError(f"Template path must be a git repository: {template_path}")

        return template_path

    # Default: This file is at: aegis-stack/aegis/core/copier_updater.py
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

        # CRITICAL: Copy service-specific files for newly-added services
        # Copier can only re-render existing files - it cannot copy new directories
        # that were excluded during initial generation
        answers = load_copier_answers(project_path)

        # Check for services in components_to_add (they start with 'include_')
        # Service names: auth, ai
        service_names = {"auth", "ai"}
        newly_added_services = [
            svc for svc in service_names if f"include_{svc}" in update_data
        ]

        if newly_added_services:
            from aegis.core.post_gen_tasks import copy_service_files

            # Template content is at: template_root/aegis/templates/copier-aegis-project/
            template_path = (
                template_root / "aegis" / "templates" / "copier-aegis-project"
            )

            for service_name in newly_added_services:
                copy_service_files(project_path, service_name, template_path)

        # Run post-generation tasks with explicit working directory control
        # This ensures consistent behavior with initial generation
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


# Version Management Functions


def get_current_template_commit(project_path: Path) -> str | None:
    """
    Get the git commit hash of the template used to generate the project.

    Args:
        project_path: Path to the project directory

    Returns:
        Commit hash string or None if not found
    """
    try:
        answers = load_copier_answers(project_path)
        commit_hash = answers.get("_commit")
        if commit_hash and commit_hash != "None":
            return commit_hash
        return None
    except Exception:
        return None


def get_available_versions(template_root: Path | None = None) -> list[str]:
    """
    Get list of available template versions from git tags.

    Args:
        template_root: Path to template repository (default: auto-detect)

    Returns:
        List of version strings sorted by PEP 440 (newest first)
    """
    if template_root is None:
        template_root = get_template_root()

    try:
        result = subprocess.run(
            ["git", "tag", "--list", "v*"],
            cwd=template_root,
            capture_output=True,
            text=True,
            check=True,
        )

        # Parse tags (remove 'v' prefix and filter valid versions)
        versions = []
        for tag in result.stdout.strip().split("\n"):
            if tag.startswith("v"):
                version_str = tag[1:]  # Remove 'v' prefix
                try:
                    parse(version_str)  # Validate version
                    versions.append(version_str)
                except Exception:
                    continue

        # Sort by PEP 440 (newest first)
        versions.sort(key=lambda v: parse(v), reverse=True)
        return versions

    except Exception:
        return []


def get_latest_version(template_root: Path | None = None) -> str | None:
    """
    Get the latest template version from git tags.

    Args:
        template_root: Path to template repository (default: auto-detect)

    Returns:
        Latest version string or None if no versions found
    """
    versions = get_available_versions(template_root)
    return versions[0] if versions else None


def resolve_ref_to_commit(ref: str, repo_path: Path) -> str | None:
    """
    Resolve a git reference (HEAD, branch, tag, commit) to full commit SHA.

    Args:
        ref: Git reference (HEAD, branch name, tag, or commit hash)
        repo_path: Path to git repository

    Returns:
        Full commit SHA or None if resolution fails
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", ref],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def resolve_version_to_ref(
    version: str | None, template_root: Path | None = None
) -> str:
    """
    Resolve a version string to a git reference.

    Args:
        version: Version string ("latest", "0.2.0", commit hash, or None)
        template_root: Path to template repository (default: auto-detect)

    Returns:
        Git reference string (tag name, commit hash, or "HEAD")
    """
    if template_root is None:
        template_root = get_template_root()

    # None or "latest" -> use latest version tag
    if not version or version == "latest":
        latest = get_latest_version(template_root)
        if latest:
            return f"v{latest}"
        return "HEAD"

    # Check if it's a commit hash (40 hex characters)
    if len(version) == 40 and all(c in "0123456789abcdef" for c in version.lower()):
        return version

    # Check if it looks like a version number (add 'v' prefix)
    try:
        parse(version)
        # Valid version number - check if tag exists
        tag_name = f"v{version}"
        result = subprocess.run(
            ["git", "rev-parse", "--verify", f"refs/tags/{tag_name}"],
            cwd=template_root,
            capture_output=True,
            check=False,
        )
        if result.returncode == 0:
            return tag_name
    except Exception:
        pass

    # Fall back to using the version string as-is (might be a branch name)
    return version


def validate_clean_git_tree(project_path: Path) -> tuple[bool, str]:
    """
    Check if the project's git working tree is clean.

    Args:
        project_path: Path to project directory

    Returns:
        Tuple of (is_clean: bool, message: str)
    """
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True,
        )

        if result.stdout.strip():
            return False, "Git tree has uncommitted changes"

        return True, "Git tree is clean"

    except subprocess.CalledProcessError as e:
        return False, f"Failed to check git status: {e}"
    except Exception as e:
        return False, f"Error checking git status: {e}"


def get_changelog(from_ref: str, to_ref: str, template_root: Path | None = None) -> str:
    """
    Get changelog between two git references.

    Args:
        from_ref: Starting git reference (commit, tag, or branch)
        to_ref: Ending git reference
        template_root: Path to template repository (default: auto-detect)

    Returns:
        Formatted changelog string
    """
    if template_root is None:
        template_root = get_template_root()

    try:
        # Get commit log between refs
        result = subprocess.run(
            [
                "git",
                "log",
                "--oneline",
                "--no-merges",
                "--pretty=format:%s",
                f"{from_ref}..{to_ref}",
            ],
            cwd=template_root,
            capture_output=True,
            text=True,
            check=True,
        )

        if not result.stdout.strip():
            return "No changes"

        # Parse commits and categorize
        commits = result.stdout.strip().split("\n")
        features = []
        fixes = []
        breaking = []
        other = []

        for commit in commits:
            commit_lower = commit.lower()
            if "breaking:" in commit_lower or "breaking change" in commit_lower:
                breaking.append(commit)
            elif commit.startswith("feat:") or commit.startswith("feature:"):
                features.append(commit)
            elif commit.startswith("fix:"):
                fixes.append(commit)
            else:
                other.append(commit)

        # Format changelog
        lines = []

        if breaking:
            lines.append("⚠️  Breaking Changes:")
            for commit in breaking:
                lines.append(f"  • {commit}")
            lines.append("")

        if features:
            lines.append("✨ New Features:")
            for commit in features:
                lines.append(f"  • {commit}")
            lines.append("")

        if fixes:
            lines.append("🐛 Bug Fixes:")
            for commit in fixes:
                lines.append(f"  • {commit}")
            lines.append("")

        if other:
            lines.append("📝 Other Changes:")
            for commit in other:
                lines.append(f"  • {commit}")

        return "\n".join(lines).strip()

    except Exception as e:
        return f"Error generating changelog: {e}"


def create_backup_point(project_path: Path) -> str | None:
    """
    Create a backup point before update by tagging current HEAD.

    Args:
        project_path: Path to project directory

    Returns:
        Backup tag name or None if creation failed
    """
    import time

    backup_tag = f"aegis-backup-{int(time.time())}"

    try:
        # Create lightweight tag at current HEAD
        subprocess.run(
            ["git", "tag", backup_tag],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return backup_tag
    except subprocess.CalledProcessError:
        return None


def rollback_to_backup(project_path: Path, backup_tag: str) -> tuple[bool, str]:
    """
    Rollback project to backup point.

    Args:
        project_path: Path to project directory
        backup_tag: Tag name to rollback to

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Hard reset to backup tag
        subprocess.run(
            ["git", "reset", "--hard", backup_tag],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True,
        )

        # Clean untracked files that may have been added
        subprocess.run(
            ["git", "clean", "-fd"],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False,  # Don't fail if clean has issues
        )

        return True, f"Successfully rolled back to {backup_tag}"
    except subprocess.CalledProcessError as e:
        return False, f"Rollback failed: {e}"


def cleanup_backup_tag(project_path: Path, backup_tag: str) -> None:
    """
    Remove backup tag after successful update.

    Args:
        project_path: Path to project directory
        backup_tag: Tag name to remove
    """
    import contextlib

    with contextlib.suppress(Exception):
        subprocess.run(
            ["git", "tag", "-d", backup_tag],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False,  # Don't fail if tag doesn't exist
        )


def get_commit_for_version(
    version: str, template_root: Path | None = None
) -> str | None:
    """
    Get the git commit hash for a version tag.

    Args:
        version: Version string (with or without 'v' prefix)
        template_root: Path to template repository (default: auto-detect)

    Returns:
        Commit hash or None if tag not found
    """
    if template_root is None:
        template_root = get_template_root()

    # Ensure version has 'v' prefix
    tag_name = version if version.startswith("v") else f"v{version}"

    try:
        result = subprocess.run(
            ["git", "rev-list", "-n", "1", tag_name],
            cwd=template_root,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except Exception:
        return None


def analyze_conflict_files(project_path: Path) -> list[dict[str, str]]:
    """
    Analyze .rej files created by Copier during conflict resolution.

    Args:
        project_path: Path to project directory

    Returns:
        List of conflict info dicts with keys: path, original, size, summary
    """
    conflicts = []

    # Find all .rej files
    rej_files = list(project_path.rglob("*.rej"))

    for rej_file in rej_files:
        # Get the original file path
        original_path = rej_file.with_suffix("")
        relative_path = rej_file.relative_to(project_path)
        relative_original = original_path.relative_to(project_path)

        # Read the .rej file content to get a summary
        try:
            rej_content = rej_file.read_text()
            line_count = len(rej_content.strip().split("\n"))
            summary = f"{line_count} lines in conflict file"
        except Exception as e:
            logger.debug(f"Failed to read .rej file {rej_file}: {e}")
            summary = "Unable to read conflict details"

        conflicts.append(
            {
                "path": str(relative_path),
                "original": str(relative_original),
                "size": f"{rej_file.stat().st_size} bytes",
                "summary": summary,
            }
        )

    return conflicts


def format_conflict_report(conflicts: list[dict[str, str]]) -> str:
    """
    Format a detailed conflict report for display.

    Args:
        conflicts: List of conflict info dicts from analyze_conflict_files

    Returns:
        Formatted string report
    """
    if not conflicts:
        return ""

    lines = []
    lines.append("⚠️  Conflicts detected - manual resolution required")
    lines.append("")

    for conflict in conflicts:
        lines.append(f"  📄 {conflict['original']}")
        lines.append(f"     Rejected changes: {conflict['path']}")
        lines.append(f"     Details: {conflict['summary']}")
        lines.append("")

    lines.append("📋 Resolution steps:")
    lines.append("   1. Open the .rej file to see rejected changes")
    lines.append("   2. Manually apply changes to the original file")
    lines.append("   3. Delete the .rej file when resolved")
    lines.append("")
    lines.append("💡 Tip: Use 'git diff' to see all changes made by the update")

    return "\n".join(lines)
