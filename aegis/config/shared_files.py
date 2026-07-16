"""
Centralized configuration for shared template files.

Shared template files are files that:
1. Exist in all generated projects (not component-specific)
2. Contain Jinja2 conditionals for optional components ({% if include_scheduler %})
3. Need to be regenerated when components are added/removed

This single source of truth ensures consistent behavior across all update mechanisms.

Adding a shared file is one line: drop its path in ``_DEFAULT_POLICY_FILES``.
Only files that must NOT use the default (overwrite + backup) policy need an
explicit entry in ``_POLICY_OVERRIDES``. ``tests/cli/test_shared_files_completeness.py``
renders a minimal and a maximal stack and fails if any stack-dependent file
is missing here, so a forgotten file surfaces as a loud test failure naming
the file rather than as silently stale config in generated projects.
"""

from typing import TypedDict


class SharedFilePolicy(TypedDict):
    """Policy for how to handle a shared template file during updates."""

    overwrite: bool  # Whether to overwrite the file with regenerated content
    backup: bool  # Whether to create a backup before overwriting
    warn: bool  # Whether to warn user about manual merge needed


# Default: regenerate the file, keeping a ``.backup`` first. Safe because the
# updater 3-way merges any user edits before overwriting (see issue #715).
DEFAULT_POLICY: SharedFilePolicy = {"overwrite": True, "backup": True, "warn": False}

# Regenerate, but don't bother keeping a backup — these are derived/transient
# files users don't hand-edit (health dispatchers, db init hook, .dockerignore).
_NO_BACKUP: SharedFilePolicy = {"overwrite": True, "backup": False, "warn": False}

# Never overwrite (not even a merge) — only warn. For files users routinely
# customize with content the template can't reproduce (custom build steps).
_WARN_ONLY: SharedFilePolicy = {"overwrite": False, "backup": False, "warn": True}


# Shared files handled with the default overwrite + backup policy. One line each.
_DEFAULT_POLICY_FILES: tuple[str, ...] = (
    # ---- Agent guidance ----
    "CLAUDE.md",  # selection-aware agent guidance, regenerated on update
    # Always-on skills (backend is core). Conditional skills are owned by their
    # component/service spec and flow through the add/remove/update footprint.
    ".claude/skills/add-api-endpoint/SKILL.md",
    ".claude/skills/add-cli-command/SKILL.md",
    ".claude/skills/change-the-stack/SKILL.md",
    # ---- Infrastructure ----
    "docker-compose.yml",
    "docker-compose.dev.yml",
    "docker-compose.prod.yml",
    "pyproject.toml",
    "Makefile",
    # ---- Component/service registration (health checks, routes, cards) ----
    "app/components/backend/startup/component_health.py",
    "app/components/frontend/main.py",  # dashboard card imports
    "app/components/frontend/dashboard/cards/__init__.py",  # card exports
    "app/components/frontend/dashboard/cards/card_utils.py",  # modal_map entries
    "app/components/frontend/dashboard/modals/__init__.py",  # modal exports
    "app/components/frontend/dashboard/status_overview.py",  # auth status surface
    "app/components/frontend/core/routes.py",  # auth route constants (login/register)
    "app/components/frontend/core/routing.py",  # auth redirect-to-login guard
    "app/components/frontend/core/events.py",  # auth check on page reconnect
    "app/components/frontend/state/session_state.py",  # auth session state
    "app/integrations/main.py",  # htmx router + /static mount
    "app/components/backend/api/routing.py",  # conditional router includes
    "app/components/backend/api/deps.py",  # conditional dependency providers
    "app/components/backend/api/models.py",  # worker + scheduler API models
    "app/components/backend/api/traffic.py",  # traffic-monitor endpoint (conditional content)
    # ---- Core configuration with component-conditional content ----
    "app/core/config.py",  # database settings, etc.
    "app/services/system/health.py",  # component-specific health checks
    "app/services/system/ui.py",  # service title/subtitle labels (auth, etc.)
    "app/services/system/backup.py",  # database backup functionality
    "tests/conftest.py",  # component-specific test fixtures
    ".env.example",  # component configuration env vars
    ".gitignore",  # node_modules + built CSS for the htmx frontend
    "scripts/entrypoint.sh",  # worker backend + build-watch dispatch
)


# Files needing a non-default policy.
_POLICY_OVERRIDES: dict[str, SharedFilePolicy] = {
    # Regenerate without a backup (derived/transient content).
    ".dockerignore": _NO_BACKUP,
    "app/services/system/health_db.py": _NO_BACKUP,  # db health dispatcher
    "app/services/system/health_db_sqlite.py": _NO_BACKUP,
    "app/services/system/health_db_postgres.py": _NO_BACKUP,
    "app/components/backend/startup/database_init.py": _NO_BACKUP,
    # Warn instead of touching — users add custom build steps here.
    "Dockerfile": _WARN_ONLY,
}


# Master mapping consumed by the updater. Built from the two declarations above
# so adding a file is a one-line change in the right list.
SHARED_TEMPLATE_FILES: dict[str, SharedFilePolicy] = {
    **dict.fromkeys(_DEFAULT_POLICY_FILES, DEFAULT_POLICY),
    **_POLICY_OVERRIDES,
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
