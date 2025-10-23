"""
Centralized configuration for shared template files.

Shared template files are files that:
1. Exist in all generated projects (not component-specific)
2. Contain Jinja2 conditionals for optional components ({% if include_scheduler %})
3. Need to be regenerated when components are added/removed

This single source of truth ensures consistent behavior across all update mechanisms.
"""

from typing import TypedDict


class SharedFilePolicy(TypedDict):
    """Policy for how to handle a shared template file during updates."""

    overwrite: bool  # Whether to overwrite the file with regenerated content
    backup: bool  # Whether to create a backup before overwriting
    warn: bool  # Whether to warn user about manual merge needed


# Master list of shared template files and their update policies
SHARED_TEMPLATE_FILES: dict[str, SharedFilePolicy] = {
    # ==========================================
    # Infrastructure Files
    # ==========================================
    # These files configure the project infrastructure and should be
    # automatically regenerated when components change.
    "docker-compose.yml": {"overwrite": True, "backup": True, "warn": False},
    "pyproject.toml": {"overwrite": True, "backup": True, "warn": False},
    "Makefile": {"overwrite": True, "backup": True, "warn": False},
    ".dockerignore": {"overwrite": True, "backup": False, "warn": False},
    # ==========================================
    # Component Registration Files
    # ==========================================
    # These files register components and services with the application.
    # They MUST be regenerated when components are added to include
    # the new component's health checks, routes, etc.
    "app/components/backend/startup/component_health.py": {
        "overwrite": True,
        "backup": True,
        "warn": False,
    },
    "app/components/frontend/main.py": {
        "overwrite": True,
        "backup": True,
        "warn": False,
    },  # Frontend dashboard card imports
    "app/components/frontend/dashboard/cards/__init__.py": {
        "overwrite": True,
        "backup": True,
        "warn": False,
    },  # Card exports
    # ==========================================
    # Core Configuration Files
    # ==========================================
    # These files contain conditional logic for components (database settings,
    # health checks, etc.) and must be regenerated when components change.
    "app/core/config.py": {
        "overwrite": True,
        "backup": True,
        "warn": False,
    },  # Contains database settings (DATABASE_URL, etc.)
    "app/services/system/health.py": {
        "overwrite": True,
        "backup": True,
        "warn": False,
    },  # Contains component-specific health checks (database, etc.)
    "app/services/system/backup.py": {
        "overwrite": True,
        "backup": True,
        "warn": False,
    },  # Contains database backup functionality
    "tests/conftest.py": {
        "overwrite": True,
        "backup": True,
        "warn": False,
    },  # Contains component-specific test fixtures (database, etc.)
    # ==========================================
    # User-Customizable Files
    # ==========================================
    # These files may be customized by users, so we warn instead of
    # overwriting. Users must manually merge changes.
    "Dockerfile": {
        "overwrite": False,
        "backup": False,
        "warn": True,
    },  # Users may add custom build steps
    ".env.example": {
        "overwrite": True,
        "backup": True,
        "warn": False,
    },  # Contains component configuration (regenerated when components change)
}


def get_shared_files() -> dict[str, SharedFilePolicy]:
    """
    Get the list of shared template files and their policies.

    Returns:
        Dictionary mapping file paths to their update policies
    """
    return SHARED_TEMPLATE_FILES.copy()


def is_shared_file(file_path: str) -> bool:
    """
    Check if a file is a shared template file.

    Args:
        file_path: Path to check (relative to project root)

    Returns:
        True if the file is a shared template file
    """
    return file_path in SHARED_TEMPLATE_FILES


def get_file_policy(file_path: str) -> SharedFilePolicy | None:
    """
    Get the update policy for a shared template file.

    Args:
        file_path: Path to the file (relative to project root)

    Returns:
        The file's update policy, or None if not a shared file
    """
    return SHARED_TEMPLATE_FILES.get(file_path)
