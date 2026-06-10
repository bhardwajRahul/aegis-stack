"""Completeness guard for ``aegis/config/shared_files.py``.

Shared template files (those whose rendered content depends on which
components/services are selected) must be registered in
``SHARED_TEMPLATE_FILES`` so ``aegis update`` / ``aegis add`` regenerate them.
Forgetting one used to be a silent bug: the file would ship stale content in
existing projects after a stack change.

This test makes that impossible. It generates a minimal stack and a maximal
stack, then diffs every file present in BOTH. A file whose content differs
across the two stacks is stack-dependent and must either be registered for
regeneration or be on the explicit ``INTENTIONALLY_NOT_REGENERATED``
allowlist. Component-owned files only ship in the maximal stack, so they
never appear in the diff — no special-casing needed.
"""

from __future__ import annotations

from pathlib import Path

from aegis.config.shared_files import SHARED_TEMPLATE_FILES
from tests.cli.conftest import ProjectFactory

# Files whose content varies with the stack but which we deliberately do NOT
# force-regenerate. Two reasons, kept separate by comment:
#   (a) user-owned prose/config we must not clobber on every update, and
#   (b) known regeneration gaps we accept for now (tracked, to revisit).
# The guard requires every entry here to actually exist and actually differ
# across stacks, so this list can't rot into a dumping ground.
INTENTIONALLY_NOT_REGENERATED: frozenset[str] = frozenset(
    {
        # (a) User-owned content — regenerating/merging these on every stack
        # change would fight the user; left untouched by design.
        "README.md",
        "mkdocs.yml",
        ".copier-answers.yml",  # owned by Copier itself
        "docs/api.md",
        "docs/development.md",
        "docs/health.md",
        # (b) Known regeneration gaps. These are files with
        # component-conditional content that are not yet regenerated on
        # update. Captured explicitly so they're tracked rather than silent;
        # promoting them to SHARED_TEMPLATE_FILES (or to a component manifest,
        # for the worker/observability ones) is a follow-up — it changes
        # update behavior, so out of scope for the no-behavior-change pass.
        "app/cli/main.py",  # conditional subcommand registration
        "app/cli/migrate_fix.py",
        "app/i18n/registry.py",  # conditional translation-module registration
        "app/components/frontend/core/routing.py",
        "app/components/frontend/core/routes.py",
        "app/components/frontend/core/events.py",
        "app/components/frontend/state/session_state.py",
        "app/components/frontend/dashboard/status_overview.py",
        "app/services/system/ui.py",
        "app/components/backend/api/load_test_api.py",
        "app/components/backend/api/metrics.py",
        "app/components/backend/api/task_history.py",
        "app/services/load_test/__init__.py",
        "tests/api/test_health_endpoints.py",
        "tests/api/test_load_test_api_endpoints.py",
        "tests/api/test_metrics_endpoints.py",
        "tests/components/test_frontend_routing.py",
    }
)

_SKIP_DIR_PARTS = frozenset(
    {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".git", ".venv"}
)
_SKIP_SUFFIXES = (".pyc", ".pyo", ".backup", ".lock", ".png", ".ico", ".woff2")
# Post-generation runtime artifacts (not template files): their content varies
# per project (generated secrets, ports), not with the stack selection.
_SKIP_NAMES = frozenset({".env"})


def _should_skip(rel: Path) -> bool:
    if any(part in _SKIP_DIR_PARTS for part in rel.parts):
        return True
    if rel.name in _SKIP_NAMES:
        return True
    return rel.suffix.lower() in _SKIP_SUFFIXES


def _normalize(content: str, slug: str) -> str:
    """Strip the per-project slug so only stack-driven differences remain."""
    return content.replace(slug, "PROJECT").replace(slug.replace("-", "_"), "PROJECT")


def test_stack_dependent_files_are_registered(
    project_factory: ProjectFactory,
) -> None:
    base = project_factory("base")
    everything = project_factory("everything")
    base_slug, all_slug = base.name, everything.name

    unregistered: list[str] = []
    for path in sorted(everything.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(everything)
        if _should_skip(rel):
            continue

        base_path = base / rel
        if not base_path.is_file():
            # Present only in the maximal stack -> component-owned, not shared.
            continue

        rel_str = rel.as_posix()
        if rel_str in SHARED_TEMPLATE_FILES or rel_str in INTENTIONALLY_NOT_REGENERATED:
            continue

        all_content = _normalize(path.read_text(errors="ignore"), all_slug)
        base_content = _normalize(base_path.read_text(errors="ignore"), base_slug)
        if all_content != base_content:
            unregistered.append(rel_str)

    assert not unregistered, (
        "These files render differently across stacks but are neither in "
        "SHARED_TEMPLATE_FILES (so `aegis update` won't regenerate them) nor "
        "on the INTENTIONALLY_NOT_REGENERATED allowlist. Add each to the "
        "right place in aegis/config/shared_files.py:\n  - "
        + "\n  - ".join(unregistered)
    )


def test_allowlist_has_no_stale_entries(
    project_factory: ProjectFactory,
) -> None:
    """Every allowlisted path must still exist and still vary across stacks.

    Keeps the allowlist honest: a file that stopped shipping, or stopped being
    stack-dependent, must be removed from the allowlist.
    """
    base = project_factory("base")
    everything = project_factory("everything")
    base_slug, all_slug = base.name, everything.name

    stale: list[str] = []
    for rel_str in sorted(INTENTIONALLY_NOT_REGENERATED):
        all_path = everything / rel_str
        base_path = base / rel_str
        if not (all_path.is_file() and base_path.is_file()):
            stale.append(f"{rel_str} (missing from a stack)")
            continue
        all_content = _normalize(all_path.read_text(errors="ignore"), all_slug)
        base_content = _normalize(base_path.read_text(errors="ignore"), base_slug)
        if all_content == base_content:
            stale.append(f"{rel_str} (no longer stack-dependent)")

    assert not stale, (
        "INTENTIONALLY_NOT_REGENERATED entries that no longer apply "
        "(remove them from aegis/config/shared_files.py's allowlist):\n  - "
        + "\n  - ".join(stale)
    )
