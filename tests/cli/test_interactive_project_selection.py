"""Characterization tests for ``interactive_project_selection`` (init flow).

The scheduler and AI paths are pinned by ``test_interactive_scheduler.py``,
``test_scheduler_persistence.py`` and ``test_ai_configuration.py``; this file
pins the remaining branches ahead of the step-engine refactor (issue #487
prep): the worker+redis bundling, auth's database-confirmation dance, the
plain content-service path, and the decline-everything baseline.

Prompt order (must hold for the scripted side_effect lists):
redis, worker, scheduler, database, ingress, observability, then services
auth, ai, blog. Accepting scheduler inserts a persistence prompt; accepting
auth without a database inserts a database-confirmation prompt.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from aegis.cli.interactive import interactive_project_selection
from aegis.constants import WorkerBackends


class TestProjectSelectionBaseline:
    @patch("typer.confirm")
    def test_decline_everything(self, mock_confirm: Any) -> None:
        mock_confirm.side_effect = [False] * 9
        components, scheduler_backend, services, skip_llm = (
            interactive_project_selection()
        )
        assert components == []
        assert scheduler_backend == "memory"
        assert services == []
        assert skip_llm is False
        assert mock_confirm.call_count == 9


class TestWorkerRedisBundling:
    @patch("aegis.cli.interactive.select_worker_backend")
    @patch("typer.confirm")
    def test_worker_without_redis_bundles_redis(
        self, mock_confirm: Any, mock_backend: Any
    ) -> None:
        mock_backend.return_value = WorkerBackends.ARQ
        # redis=no, worker(+redis)=yes, then decline the rest
        mock_confirm.side_effect = [False, True] + [False] * 7
        components, _, _, _ = interactive_project_selection()
        assert "redis" in components
        assert "worker" in components

    @patch("aegis.cli.interactive.select_worker_backend")
    @patch("typer.confirm")
    def test_worker_with_redis_already_selected(
        self, mock_confirm: Any, mock_backend: Any
    ) -> None:
        mock_backend.return_value = WorkerBackends.ARQ
        # redis=yes, worker=yes, decline the rest
        mock_confirm.side_effect = [True, True] + [False] * 7
        components, _, _, _ = interactive_project_selection()
        assert components.count("redis") == 1
        assert "worker" in components

    @patch("aegis.cli.interactive.select_worker_backend")
    @patch("typer.confirm")
    def test_non_default_backend_gets_bracket(
        self, mock_confirm: Any, mock_backend: Any
    ) -> None:
        mock_backend.return_value = WorkerBackends.TASKIQ
        mock_confirm.side_effect = [False, True] + [False] * 7
        components, _, _, _ = interactive_project_selection()
        assert "worker[taskiq]" in components
        assert "worker" not in components  # bracket form replaces plain name


class TestAuthDatabaseDance:
    @patch("aegis.cli.interactive.interactive_auth_service_config")
    @patch("typer.confirm")
    def test_auth_without_database_confirms_db_addition(
        self, mock_confirm: Any, mock_auth_config: Any
    ) -> None:
        mock_auth_config.return_value = "basic"
        # 6 components declined, auth=yes, db-confirm=yes, ai=no, blog=no
        mock_confirm.side_effect = [False] * 6 + [True, True, False, False]
        components, _, services, _ = interactive_project_selection()
        assert "auth[basic]" in services
        assert mock_confirm.call_count == 10  # db-confirm prompt was inserted

    @patch("aegis.cli.interactive.interactive_auth_service_config")
    @patch("typer.confirm")
    def test_auth_cancelled_when_db_confirm_declined(
        self, mock_confirm: Any, mock_auth_config: Any
    ) -> None:
        mock_auth_config.return_value = "basic"
        # auth=yes but decline the database confirmation -> auth dropped
        mock_confirm.side_effect = [False] * 6 + [True, False, False, False]
        _, _, services, _ = interactive_project_selection()
        assert services == []

    @patch("aegis.cli.interactive.interactive_auth_service_config")
    @patch("typer.confirm")
    def test_auth_with_database_skips_confirmation(
        self, mock_confirm: Any, mock_auth_config: Any
    ) -> None:
        mock_auth_config.return_value = "rbac"
        # database=yes among components, auth=yes -> no extra db prompt
        mock_confirm.side_effect = [False, False, False, True, False, False] + [
            True,
            False,
            False,
        ]
        components, _, services, _ = interactive_project_selection()
        assert "database" in components
        assert "auth[rbac]" in services
        assert mock_confirm.call_count == 9  # no inserted db-confirm prompt


class TestContentServices:
    @patch("typer.confirm")
    def test_blog_selected_as_plain_name(self, mock_confirm: Any) -> None:
        # decline all components + auth + ai, accept blog
        mock_confirm.side_effect = [False] * 8 + [True]
        _, _, services, _ = interactive_project_selection()
        assert services == ["blog"]


class ScriptedUI:
    """SelectionUI driven by scripted answers — no monkeypatching needed.

    This is the renderer seam the step engine exists for (issue #487 prep):
    tests (and the future wizard) implement the protocol instead of patching
    typer/questionary internals. Records the transcript for assertions.
    """

    def __init__(
        self,
        confirms: list[bool],
        *,
        worker_backend: str = "arq",
        database_engine: str = "sqlite",
        auth_level: str = "basic",
        ai_config: tuple[str, str, list[str], bool, bool] = (
            "memory",
            "pydantic-ai",
            ["public"],
            False,
            False,
        ),
    ) -> None:
        self._confirms = iter(confirms)
        self._worker_backend = worker_backend
        self._database_engine = database_engine
        self._auth_level = auth_level
        self._ai_config = ai_config
        self.transcript: list[str] = []

    def section(self, title: str, *, newline_before: bool = False) -> None:
        self.transcript.append(f"[section] {title}")

    def confirm(self, prompt: str, *, default: bool = True) -> bool:
        self.transcript.append(f"[confirm] {prompt}")
        return next(self._confirms)

    def echo(self, message: str = "") -> None:
        self.transcript.append(message)

    def success(self, message: str) -> None:
        self.transcript.append(message)

    def choose_worker_backend(self) -> str:
        return self._worker_backend

    def choose_database_engine(self, context: str) -> str:
        self.transcript.append(f"[engine for {context}]")
        return self._database_engine

    def configure_auth(self, service_name: str) -> str:
        return self._auth_level

    def configure_ai(self, service_name: str) -> tuple[str, str, list[str], bool, bool]:
        return self._ai_config


class TestEngineWithScriptedUI:
    """The engine is testable through the protocol alone."""

    def test_full_stack_selection_no_patching(self) -> None:
        from aegis.cli.interactive import run_project_selection

        # redis=y, worker=y, scheduler=y, persistence=y, (db skipped),
        # ingress=n, observability=n, auth=y, ai=y, blog=y
        ui = ScriptedUI(
            confirms=[True, True, True, True, False, False, True, True, True],
            worker_backend="taskiq",
            database_engine="postgres",
            auth_level="rbac",
            ai_config=("sqlite", "langchain", ["openai"], True, False),
        )
        state = run_project_selection(ui)

        assert state.components == [
            "redis",
            "worker[taskiq]",
            "scheduler[postgres]",
            "database[postgres]",
        ]
        assert state.scheduler_backend == "postgres"
        assert state.services == [
            "auth[rbac]",
            "ai[sqlite,langchain,openai,rag]",
            "blog",
        ]
        # AI wanted sqlite but a database (postgres) already existed -> no
        # second database appended.
        assert sum("database" in c for c in state.components) == 1

    def test_transcript_captures_flow(self) -> None:
        from aegis.cli.interactive import run_project_selection

        ui = ScriptedUI(confirms=[False] * 9)
        state = run_project_selection(ui)
        assert state.components == []
        assert state.services == []
        confirms = [line for line in ui.transcript if line.startswith("[confirm]")]
        assert len(confirms) == 9
