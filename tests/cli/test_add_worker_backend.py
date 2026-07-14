"""Regression: `aegis add worker[<backend>]` must honor the chosen backend.

Previously the add path threaded only scheduler_backend and database_engine, so
`aegis add worker[dramatiq]` silently discarded the bracket and installed the
arq default.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from aegis.core.copier_manager import load_copier_answers
from tests.cli.test_utils import run_aegis_command


def test_add_worker_dramatiq_honors_backend(
    project_factory: Callable[..., Path],
) -> None:
    project = project_factory("base")

    result = run_aegis_command(
        "add", "worker[dramatiq]", "--project-path", str(project), "--yes"
    )
    assert result.returncode == 0, f"add worker[dramatiq] failed: {result.stderr}"

    answers = load_copier_answers(project)
    assert answers.get("worker_backend") == "dramatiq", (
        f"expected dramatiq, got {answers.get('worker_backend')!r}"
    )
    # The dramatiq dependency must be pulled, not arq's.
    pyproject = (project / "pyproject.toml").read_text()
    assert "dramatiq" in pyproject


def test_add_worker_taskiq_honors_backend(
    project_factory: Callable[..., Path],
) -> None:
    project = project_factory("base")

    result = run_aegis_command(
        "add", "worker[taskiq]", "--project-path", str(project), "--yes"
    )
    assert result.returncode == 0, f"add worker[taskiq] failed: {result.stderr}"

    answers = load_copier_answers(project)
    assert answers.get("worker_backend") == "taskiq", (
        f"expected taskiq, got {answers.get('worker_backend')!r}"
    )


def test_add_worker_rejects_unknown_backend(
    project_factory: Callable[..., Path],
) -> None:
    project = project_factory("base")

    result = run_aegis_command(
        "add", "worker[dramatq]", "--project-path", str(project), "--yes"
    )
    assert result.returncode != 0, "typo backend should be rejected"

    answers = load_copier_answers(project)
    assert answers.get("include_worker") is not True, (
        "rejected add must not enable the worker"
    )
