"""Integration matrix for issue #686 — `aegis add-service` cross-service safety.

Generates a real project with one service installed (via the cached
``project_factory``), then exercises ``ManualUpdater.add_component`` for
a second service, and asserts that:

1. Both services' include flags survive in ``.copier-answers.yml``.
2. The regenerated ``app/core/config.py`` contains the union of env-bound
   fields contributed by both services (this is the original ticket
   failure: ``INSIGHT_*`` fields dropped when auth was added on top of
   an insights project).
3. No empty / whitespace-only ``.py`` files remain under ``app/`` —
   whole-file Jinja-gate stubs must be cleaned, otherwise the project
   crashes at import time (``ImportError: login_rate_limit``).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from aegis.core.manual_updater import ManualUpdater

ProjectFactory = Callable[..., Path]


def _read_config_py(project_path: Path) -> str:
    return (project_path / "app" / "core" / "config.py").read_text()


def _empty_py_under_app(project_path: Path) -> list[str]:
    bad: list[str] = []
    app_dir = project_path / "app"
    if not app_dir.exists():
        return bad
    for path in app_dir.rglob("*.py"):
        if path.name == "__init__.py":
            continue
        try:
            if not path.read_text().strip():
                bad.append(str(path.relative_to(project_path)))
        except (OSError, UnicodeDecodeError):
            continue
    return bad


@pytest.mark.slow
class TestAddServicePreservesPriorServiceFields:
    def test_auth_then_insights_preserves_auth_and_adds_insights(
        self, project_factory: ProjectFactory
    ) -> None:
        project_path = project_factory("base_with_auth_service")

        updater = ManualUpdater(project_path)
        result = updater.add_component(
            "insights",
            {
                "insights_github": True,
                "insights_pypi": True,
                "insights_plausible": False,
                "insights_reddit": False,
            },
            run_post_gen=False,
        )
        assert result.success, result.error_message

        answers = (project_path / ".copier-answers.yml").read_text()
        assert "include_auth: true" in answers
        assert "include_insights: true" in answers

        config = _read_config_py(project_path)
        assert "INSIGHT_GITHUB_OWNER" in config
        assert "INSIGHT_PYPI_PACKAGE" in config

        assert _empty_py_under_app(project_path) == []

    def test_drifted_answers_get_reconciled_before_regen(
        self, project_factory: ProjectFactory
    ) -> None:
        """Reproduces the original ticket: an insights-installed project
        whose ``.copier-answers.yml`` is missing the insights flags.
        Adding auth must not drop ``INSIGHT_*`` Settings fields from
        ``app/core/config.py``."""
        project_path = project_factory("insights_full")

        answers_file = project_path / ".copier-answers.yml"
        scrubbed = "\n".join(
            line
            for line in answers_file.read_text().splitlines()
            if not line.startswith(("include_insights", "insights_"))
        )
        answers_file.write_text(scrubbed + "\n")

        updater = ManualUpdater(project_path)

        # Reconciliation runs in __init__ and rewrites the answers file
        # before any shared-file regen.
        restored = answers_file.read_text()
        assert "include_insights: true" in restored

        result = updater.add_component(
            "auth",
            {"auth_level": "basic"},
            run_post_gen=False,
        )
        assert result.success, result.error_message

        config = _read_config_py(project_path)
        assert "INSIGHT_GITHUB_OWNER" in config
        assert "INSIGHT_PYPI_PACKAGE" in config

        assert _empty_py_under_app(project_path) == []
