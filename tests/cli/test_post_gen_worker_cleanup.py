"""
Regression tests for `cleanup_components` worker-backend cleanup branch.

Issue #672: `aegis update` silently deleted `app/components/worker/queues/system.py`
and `queues/load_test.py` when re-run on already-renamed projects (the rename
loop found no `*_taskiq.py` / `*_dramatiq.py` files and the deletion glob then
nuked every canonical `*.py`). Tests simulate the post-init state for each
worker backend and assert cleanup is idempotent across init -> update -> update.
"""

from pathlib import Path

import pytest

from aegis.constants import AnswerKeys, WorkerBackends
from aegis.core.post_gen_tasks import cleanup_components


def _make_post_init_worker_project(
    tmp_path: Path, *, backend: str, with_renamed_files: bool
) -> Path:
    """
    Build a minimal project tree mimicking a generated project's worker layout.

    `with_renamed_files=True` simulates the FRESH-RENDER state during `aegis init`:
    the template ships both arq canonicals AND the `*_taskiq.py` / `*_dramatiq.py`
    suffixed sources; cleanup runs and renames/strips them.

    `with_renamed_files=False` simulates the POST-INIT state seen on `aegis
    update`: only the files a real init would have left behind are present.
    For arq that includes `media.py` (cleanup never touches it). For taskiq
    and dramatiq, `media.py` is absent because the init cleanup deletes any
    `*.py` without a backend-suffixed counterpart.
    """
    project = tmp_path / "demo"
    queues_dir = project / "app/components/worker/queues"
    worker_dir = project / "app/components/worker"
    queues_dir.mkdir(parents=True)
    (project / "app/components/backend/api").mkdir(parents=True)
    (project / "app/services").mkdir(parents=True)

    # Canonical queue files always present after a first init.
    (queues_dir / "__init__.py").write_text("")
    (queues_dir / "system.py").write_text("# system broker\n")
    (queues_dir / "load_test.py").write_text("# load test broker\n")

    # media.py is template-shipped but only survives init for arq — for
    # taskiq/dramatiq, the deletion loop strips it because it has no backend
    # variant. So include it post-init only for arq, or unconditionally when
    # we're modelling the pre-cleanup fresh-render state.
    if with_renamed_files or backend == WorkerBackends.ARQ:
        (queues_dir / "media.py").write_text("# media queue\n")

    # Canonical worker-dir files.
    for stem in ("pools", "registry", "middleware", "broker"):
        (worker_dir / f"{stem}.py").write_text(f"# {stem}\n")

    if with_renamed_files:
        # Simulate a fresh init render where suffixed source files coexist
        # with the arq baseline before _rename_backend_files runs.
        (queues_dir / "system_taskiq.py").write_text("# system taskiq source\n")
        (queues_dir / "load_test_taskiq.py").write_text("# load_test taskiq source\n")
        (queues_dir / "system_dramatiq.py").write_text("# system dramatiq source\n")
        (queues_dir / "load_test_dramatiq.py").write_text(
            "# load_test dramatiq source\n"
        )

    return project


def _worker_context(backend: str) -> dict[str, object]:
    """Minimal context selecting only the worker component on the given backend."""
    return {
        AnswerKeys.WORKER: True,
        AnswerKeys.WORKER_BACKEND: backend,
    }


@pytest.mark.parametrize(
    "backend",
    [WorkerBackends.ARQ, WorkerBackends.TASKIQ, WorkerBackends.DRAMATIQ],
)
def test_update_preserves_worker_queue_files(tmp_path: Path, backend: str) -> None:
    """
    Regression for issue #672: re-running cleanup on an already-renamed project
    (the `aegis update` path) MUST NOT delete canonical `system.py` /
    `load_test.py` queue brokers.

    Covers all three worker backends — arq was already safe but we pin the
    baseline so a future refactor of the cleanup helpers can't regress it.
    """
    project = _make_post_init_worker_project(
        tmp_path, backend=backend, with_renamed_files=False
    )
    queues_dir = project / "app/components/worker/queues"

    cleanup_components(project, _worker_context(backend))

    assert (queues_dir / "system.py").exists(), (
        f"system.py was deleted on update with worker_backend={backend} "
        "(issue #672 regression)"
    )
    assert (queues_dir / "load_test.py").exists(), (
        f"load_test.py was deleted on update with worker_backend={backend} "
        "(issue #672 regression)"
    )
    # media.py only exists post-init for arq — for taskiq/dramatiq the init
    # cleanup already stripped it, so it shouldn't be in the fixture and we
    # don't assert anything about it.
    if backend == WorkerBackends.ARQ:
        assert (queues_dir / "media.py").exists()
    # Worker-dir canonicals must also survive.
    for stem in ("pools", "registry", "middleware", "broker"):
        assert (project / f"app/components/worker/{stem}.py").exists(), (
            f"{stem}.py disappeared on update for worker_backend={backend}"
        )


@pytest.mark.parametrize(
    "backend",
    [WorkerBackends.TASKIQ, WorkerBackends.DRAMATIQ],
)
def test_init_renames_sources_and_strips_arq_only_files(
    tmp_path: Path, backend: str
) -> None:
    """
    Confirm the fix doesn't break the original `aegis init` flow: when the
    suffixed source files DO exist (fresh render), cleanup must

    1. rename the chosen backend's `*_<backend>.py` sources to canonical names,
    2. strip the OTHER backend's `*_<other>.py` sources, and
    3. strip arq-only canonicals like `media.py` that have no backend variant
       (this is the loop the #672 fix guards on update — it MUST still run on
       init).
    """
    project = _make_post_init_worker_project(
        tmp_path, backend=backend, with_renamed_files=True
    )
    queues_dir = project / "app/components/worker/queues"

    cleanup_components(project, _worker_context(backend))

    # Canonical files for the chosen backend exist, sourced from the rename.
    assert (queues_dir / "system.py").exists()
    assert (queues_dir / "load_test.py").exists()
    # The other backend's source files are gone.
    other_suffix = "_dramatiq.py" if backend == WorkerBackends.TASKIQ else "_taskiq.py"
    assert not list(queues_dir.glob(f"*{other_suffix}"))
    # The chosen backend's source files were renamed away.
    chosen_suffix = "_taskiq.py" if backend == WorkerBackends.TASKIQ else "_dramatiq.py"
    assert not list(queues_dir.glob(f"*{chosen_suffix}"))
    # arq-only canonicals (no backend variant) must be stripped on a fresh
    # taskiq/dramatiq init — this is the deletion loop the #672 fix guards.
    assert not (queues_dir / "media.py").exists(), (
        f"media.py (arq-only canonical) should be stripped on a fresh "
        f"{backend} init but survived"
    )


def _snapshot(root: Path) -> dict[str, str]:
    """Map of relative path -> file contents for every file under root."""
    return {
        str(p.relative_to(root)): p.read_text()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


@pytest.mark.parametrize(
    "backend",
    [WorkerBackends.ARQ, WorkerBackends.TASKIQ, WorkerBackends.DRAMATIQ],
)
def test_cleanup_components_is_idempotent(tmp_path: Path, backend: str) -> None:
    """
    Running `cleanup_components` twice in a row on the same project tree must
    produce identical results — anything else is a latent bug of the same
    class as #672 (cleanup logic that assumes a fresh render).

    This is the general guard: if a future cleanup branch introduces a
    rename-then-glob-delete pattern (or any other non-idempotent step),
    this test fails for whichever backend triggers it.
    """
    project = _make_post_init_worker_project(
        tmp_path, backend=backend, with_renamed_files=True
    )
    context = _worker_context(backend)

    cleanup_components(project, context)
    after_first = _snapshot(project)

    cleanup_components(project, context)
    after_second = _snapshot(project)

    assert after_first == after_second, (
        f"cleanup_components is non-idempotent for worker_backend={backend}: "
        f"second run added/removed/changed files"
    )
