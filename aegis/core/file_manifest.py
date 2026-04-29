"""
Declarative file manifest per ``PluginSpec``.

R1 of the plugin system refactor. Centralises the per-spec file
ownership needed for declarative cleanup, replacing the **Pattern A**
imperative blocks ("if X is not selected, remove these files") that
were scattered through ``aegis/core/post_gen_tasks.py``.

Consumed by every ``PluginSpec`` (in-tree services and components today;
third-party plugins under R2+). See ``aegis/core/plugin_spec.py``.

What R1 does NOT do (deliberately deferred to R2):

* ``post_gen_tasks.get_component_file_mapping()`` is still a hard-coded
  dict. ``compute_file_mapping()`` below is a forward-compat helper for
  the eventual migration; it is not currently called by core code. The
  legacy dict and each spec's ``files.primary`` can therefore drift —
  keep them aligned by hand until R2 derives the mapping from manifests.
* Sub-feature, cross-spec, and worker-backend cleanups remain inline in
  ``cleanup_components`` (their gating predicates are non-uniform).

Everything else stays inline in ``cleanup_components`` for R1:

* Pattern B sub-feature cleanup (``ai_rag``, ``ai_voice``, ``auth_org``,
  AI memory backend, ollama mode, scheduler memory backend). Each has
  its own gating predicate; uniform reducer rules don't fit yet.
* Pattern C cross-spec aggregations (``alembic`` only when no service
  needs migrations; ``services_card.py`` only when no services;
  ``docs/components`` only when no components).
* Pattern D worker backend-variant rename + delete-others.

The ``extras`` field on ``FileManifest`` is captured here for
documentation / future use (``get_component_file_mapping`` legacy keys
like ``ai_rag``, ``ai_voice``, ``scheduler_persistence``), but the R1
reducer ignores it. R2 generalises the spec model and lights up
``extras``-driven cleanup uniformly.
"""

from __future__ import annotations

import shutil
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class FileManifest:
    """File ownership for a single service or component spec.

    See module docstring for the role this plays in R1.
    """

    primary: list[str] = field(default_factory=list)
    """Files cleaned up when the parent spec is not selected.

    Paths are relative to the project root. Each entry may be a file path
    or a directory path; directories are removed recursively.
    """

    extras: dict[str, list[str]] = field(default_factory=dict)
    """Sub-feature file groups, keyed by their legacy mapping identifier.

    Captured on the spec for documentation and forward-compatibility
    with ``get_component_file_mapping()``. **Not** consumed by the R1
    cleanup reducer — sub-feature cleanup remains inline in
    ``cleanup_components`` because each sub-feature has its own gating
    predicate (some by AnswerKey toggle, some by option value, some
    only when the parent is also on). R2 unifies the spec model and
    lights up uniform extras-driven cleanup.

    Example: ``{"ai_rag": [...], "ai_voice": [...]}`` on the AI service.
    """


def compute_file_mapping(specs: Iterable[Any]) -> dict[str, list[str]]:
    """Build the legacy component-file mapping from spec manifests.

    Output shape matches ``post_gen_tasks.get_component_file_mapping()``:
    ``{spec_name: [files...], extra_key: [files...], ...}``.

    Specs without a populated ``FileManifest`` are skipped — non-migrated
    specs do not break the reducer.
    """
    mapping: dict[str, list[str]] = {}
    for spec in specs:
        manifest = getattr(spec, "files", None)
        if not isinstance(manifest, FileManifest):
            continue
        if manifest.primary:
            mapping[spec.name] = list(manifest.primary)
        for extra_key, extra_files in manifest.extras.items():
            if extra_files:
                mapping[extra_key] = list(extra_files)
    return mapping


def iter_cleanup_paths(spec: Any, *, selected: bool) -> Iterable[str]:
    """Yield project-relative paths to remove for one spec when it is off.

    R1 scope: only Pattern A primary cleanup. When ``selected`` is True,
    yields nothing (sub-feature cleanup is handled inline). When False,
    yields the spec's ``primary`` paths.

    Args:
        spec: A spec object exposing ``.files: FileManifest``. Specs
            without a manifest yield nothing.
        selected: Whether this spec is selected (its ``include_*`` flag
            is truthy in the context).

    Yields:
        Relative paths to remove (file or directory; caller decides how).
    """
    if selected:
        return
    manifest = getattr(spec, "files", None)
    if not isinstance(manifest, FileManifest):
        return
    yield from manifest.primary


def apply_cleanup_path(project_path: Path, rel_path: str) -> None:
    """Remove a single project-relative path. File or directory; no-op if absent.

    Mirrors the union of ``post_gen_tasks.remove_file`` and
    ``post_gen_tasks.remove_dir`` so callers don't need to know the kind.
    """
    full = project_path / rel_path
    if full.is_file() or full.is_symlink():
        full.unlink()
    elif full.is_dir():
        shutil.rmtree(full)
    # else: missing -> silent no-op, matches existing behaviour.
