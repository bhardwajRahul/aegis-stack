"""The guided setup is a renderer over the shared selection engine.

These drive ``GuidedSelectionUI`` with scripted keypresses (no TTY, rendering
no-ops, welcome page skipped) through the real ``run_project_selection``
engine, asserting the resulting ``ProjectSelection``. They prove the guided
setup reuses the engine and rules — there is no separate selection logic to
test, only the key->action wiring. Quick mode and guided mode converge on the
same state object.

Confirm prompts accept ``y``/``n`` shortcuts; the engine asks about each
infrastructure component in INFRASTRUCTURE_ORDER (worker, scheduler,
database, redis, ingress, observability) then every service grouped by
ServiceType order (auth, payment, ai, comms, insights, blog).
"""

from __future__ import annotations

import pytest

from aegis.cli.guided import (
    GuidedBuildError,
    GuidedSelectionUI,
    run_guided_init_flow,
    run_guided_selection,
)
from aegis.cli.interactive import run_project_selection


def _drive(keys: list[str]):
    return run_guided_selection(GuidedSelectionUI(keys=keys))


# worker scheduler database redis ingress observability |
# auth payment ai comms insights blog
# (redis is skipped entirely when an accepted worker already bundled it)
_DECLINE_ALL = ["n"] * 12


class TestGuidedDrivesEngine:
    def test_decline_everything(self) -> None:
        state = _drive(_DECLINE_ALL)
        assert state.components == []
        assert state.services == []

    def test_add_database_only(self) -> None:
        # yes only on the 3rd confirm (database); engine screen -> enter = SQLite
        keys = ["n", "n", "y", "\r"] + ["n"] * 9
        state = _drive(keys)
        assert state.components == ["database"]
        assert state.services == []

    def test_add_database_postgres_neon(self) -> None:
        # database yes -> engine: right+enter = PostgreSQL -> host: right+enter
        # = Neon. Encodes as database[neon] (engine normalizes to postgres).
        keys = ["n", "n", "y", "right", "\r", "right", "\r"] + ["n"] * 9
        state = _drive(keys)
        assert state.components == ["database[neon]"]
        assert state.postgres_provider == "neon"

    def test_add_database_postgres_container(self) -> None:
        # database yes -> engine: right+enter = PostgreSQL -> host: enter =
        # local container (the default). Encodes as database[postgres].
        keys = ["n", "n", "y", "right", "\r", "\r"] + ["n"] * 9
        state = _drive(keys)
        assert state.components == ["database[postgres]"]
        assert state.postgres_provider == "container"

    def test_worker_bundles_redis_via_engine_rules(self) -> None:
        # Worker leads the order now; accepting it pulls redis in AND
        # skips the redis screen entirely (no point asking for something
        # already added). worker(y) backend(enter), then decline the
        # remaining 4 asked components and all 6 services.
        keys = ["y", "\r"] + ["n"] * 10
        state = _drive(keys)
        assert "redis" in state.components
        assert "worker" in state.components

    def test_scheduler_persistence_sets_engine(self) -> None:
        # decline worker, accept scheduler, then the single backend
        # screen: chips are [In-memory, SQLite, PostgreSQL] — right twice
        # lands on PostgreSQL. Database is auto-skipped; redis still asks.
        keys = ["n", "y", "right", "right", "\r"] + ["n"] * 9
        state = _drive(keys)
        assert "scheduler[postgres]" in state.components
        assert "database[postgres]" in state.components
        assert state.scheduler_backend == "postgres"

    def test_auth_configures_level(self) -> None:
        # decline all 6 components, accept auth, pick RBAC (right+enter), then
        # confirm the "auth needs a database" prompt (y), decline the rest.
        keys = _DECLINE_ALL[:6] + ["y", "right", "\r", "y"] + ["n"] * 5
        state = _drive(keys)
        assert "auth[rbac]" in state.services

    def test_offers_all_registered_services(self) -> None:
        # comms, insights, and payment were silently skipped by the old
        # hand-written AUTH/AI/CONTENT trio; accepting their confirms must
        # now land them in the selection.
        keys = _DECLINE_ALL[:6] + ["n", "y", "n", "y", "y", "n"]
        state = _drive(keys)
        assert state.services == ["payment", "comms", "insights"]

    def test_ai_rag_and_voice_toggles(self) -> None:
        # Accept AI: framework chip (enter = pydantic-ai), storage chip
        # (enter = memory), providers (up wraps to Continue, enter keeps
        # the recommended default), rag yes, voice no; rest declined.
        keys = _DECLINE_ALL[:6] + ["n", "n", "y", "\r", "\r", "up", "\r", "y", "n"]
        keys += ["n", "n", "n", "n"]
        state = _drive(keys)
        assert state.services == ["ai[memory,pydantic-ai,public,rag]"]

    def test_ai_storage_question_skipped_with_scheduler_postgres(self) -> None:
        # One datastore, used everywhere: scheduler persistence picked
        # postgres, so AI never asks about storage — conversations persist
        # to the project database, full stop.
        keys = (
            ["n", "y", "right", "right", "\r"]  # worker n, scheduler -> postgres
            + ["n", "n", "n"]  # redis, ingress, observability (db auto-skipped)
            + ["n", "n", "y", "\r", "up", "\r", "n", "n"]  # auth n, payment n,
            # ai y -> framework, providers (Continue), rag n, voice n
            # (NO storage screen)
            + ["n", "n", "n"]  # comms, insights, blog
        )
        state = _drive(keys)
        assert "ai[postgres,pydantic-ai,public]" in state.services
        db_entries = [c for c in state.components if c.startswith("database")]
        assert db_entries == ["database[postgres]"]

    def test_ai_storage_question_skipped_with_plain_database(self) -> None:
        # A plain database selection means the default engine (sqlite); AI
        # persists to it without asking.
        keys = (
            ["n", "n", "y", "\r", "n", "n", "n"]  # database accepted, engine=sqlite
            + ["n", "n", "y", "\r", "up", "\r", "n", "n"]  # ai: framework,
            # providers (Continue), rag, voice — no storage screen
            + ["n", "n", "n"]
        )
        state = _drive(keys)
        assert "ai[sqlite,pydantic-ai,public]" in state.services
        assert "database" in state.components

    def test_ai_provider_multi_select_adds_providers(self) -> None:
        # LLM7.io is pre-checked (recommended); enter on a focused row
        # TOGGLES it (OpenAI here), and only Continue advances.
        keys = (
            _DECLINE_ALL[:6]
            + ["n", "n", "y", "\r", "\r"]  # ai y, framework, storage memory
            + ["down", "\r", "up", "up", "\r"]  # toggle openai via enter,
            # wrap up to Continue, accept
            + ["n", "n"]  # rag, voice
            + ["n", "n", "n"]
        )
        state = _drive(keys)
        assert state.services == ["ai[memory,pydantic-ai,public,openai]"]

    def test_ai_provider_none_selected_falls_back_to_default(self) -> None:
        # Unchecking everything still yields the free tier, like quick mode.
        keys = (
            _DECLINE_ALL[:6]
            + ["n", "n", "y", "\r", "\r"]
            + [" ", "up", "\r"]  # uncheck LLM7.io, Continue with none
            + ["n", "n"]
            + ["n", "n", "n"]
        )
        state = _drive(keys)
        assert state.services == ["ai[memory,pydantic-ai,public]"]

    def test_finish_declines_everything_remaining(self) -> None:
        # "f" on the first screen: every remaining question auto-answers
        # its decline — one key ends the whole selection.
        state = _drive(["f"])
        assert state.components == []
        assert state.services == []

    def test_finish_keeps_earlier_choices(self) -> None:
        # Accept worker first, then finish: worker (and its bundled redis)
        # survive; everything after is declined.
        keys = ["y", "\r", "f"]
        state = _drive(keys)
        assert state.components == ["redis", "worker"]
        assert state.services == []

    def test_finish_journals_skipped_screens_for_back_nav(self) -> None:
        # The auto-declines are real journal entries: the trail shows every
        # skipped screen as declined, so esc from review still rewinds.
        ui = GuidedSelectionUI(keys=["f"])
        run_guided_selection(ui)
        assert len(ui.breadcrumbs) == 12
        assert all("✗" in crumb for crumb in ui.breadcrumbs)

    def test_skip_to_services_goes_live_at_service_phase(self) -> None:
        # "s" declines the remaining components but services are still
        # asked for real — accepting auth here proves the screen was live.
        keys = ["s", "y", "right", "\r", "y"] + ["n"] * 5
        state = _drive(keys)
        assert state.components == []
        assert "auth[rbac]" in state.services

    def test_quit_aborts(self) -> None:
        import typer

        with pytest.raises(typer.Abort):
            _drive(["q"])

    def test_welcome_consumes_no_keys_in_scripted_mode(self) -> None:
        """show_welcome must early-return when scripted, so engine key counts
        in this file stay valid for callers that show the welcome first."""
        ui = GuidedSelectionUI(keys=list(_DECLINE_ALL))
        ui.show_welcome()  # must not consume a key
        state = run_project_selection(ui)
        assert state.components == []

    def test_core_stack_page_consumes_no_keys_in_scripted_mode(self) -> None:
        """show_core_stack is informational chrome like the welcome page —
        zero keys when scripted, so engine key counts stay valid."""
        ui = GuidedSelectionUI(keys=list(_DECLINE_ALL))
        ui.show_core_stack()  # must not consume a key
        state = run_project_selection(ui)
        assert state.components == []


class TestBackNavigation:
    """esc rewinds one screen via journal pop + full engine replay."""

    def test_back_revises_previous_answer(self) -> None:
        # Accept worker, then esc on the backend chips -> worker is
        # re-asked (journal popped) and this time declined. With worker
        # gone, redis IS asked, so the full 12 declines follow.
        keys = ["y", "esc"] + ["n"] * 12
        state = _drive(keys)
        assert state.components == []

    def test_back_at_first_question_is_safe(self) -> None:
        # esc with an empty journal re-shows the welcome (a no-op when
        # scripted) and re-asks the first question.
        keys = ["esc"] + ["n"] * 12
        state = _drive(keys)
        assert state.components == []

    def test_back_recomputes_dependent_components(self) -> None:
        # Accept worker (which bundles redis), esc out of the backend chips,
        # then decline worker -> the auto-added redis must vanish too,
        # because the engine genuinely re-runs (and the redis screen comes
        # back, hence 11 trailing declines).
        keys = ["y", "esc", "n"] + ["n"] * 11
        state = _drive(keys)
        assert "worker" not in state.components
        assert "redis" not in state.components
        assert state.components == []


class TestReviewScreen:
    """The full flow: questions -> resolved plan -> REVIEW -> confirm/back."""

    def test_review_enter_confirms_plan(self) -> None:
        # database accepted (engine screen -> enter = SQLite), everything else
        # declined, enter on REVIEW.
        keys = ["n", "n", "y", "\r"] + ["n"] * 9 + ["\r"]
        ui = GuidedSelectionUI(keys=keys)
        plan, _ = run_guided_init_flow("demo", "3.13", ui=ui)
        assert "database" in plan.components
        assert plan.template_gen is not None
        assert plan.template_files  # previews resolved for the screen

    def test_review_back_revises_last_answer(self) -> None:
        # Accept blog (last question), esc on REVIEW -> blog re-asked and
        # declined -> second REVIEW confirmed. The plan must reflect the
        # revision, not the original answer.
        keys = _DECLINE_ALL[:11] + ["y", "esc", "n", "\r"]
        ui = GuidedSelectionUI(keys=keys)
        plan, _ = run_guided_init_flow("demo", "3.13", ui=ui)
        assert plan.services == []

    def test_review_detail_panes_toggle_harmlessly(self) -> None:
        keys = ["n", "n", "y"] + ["n"] * 9 + ["f", "d", "f", "\r"]
        ui = GuidedSelectionUI(keys=keys)
        plan, _ = run_guided_init_flow("demo", "3.13", ui=ui)
        assert "database" in plan.components

    def test_yes_skips_review(self) -> None:
        # With --yes the review is skipped entirely: no extra key consumed.
        keys = ["n", "n", "y", "\r"] + ["n"] * 9
        ui = GuidedSelectionUI(keys=keys)
        plan, _ = run_guided_init_flow("demo", "3.13", yes=True, ui=ui)
        assert "database" in plan.components

    def test_plan_includes_dependency_auto_adds(self) -> None:
        # Worker accepted -> the resolved plan carries the auto-added redis
        # (same resolution quick mode runs; REVIEW shows it tagged "auto").
        keys = ["y", "\r"] + ["n"] * 10 + ["\r"]
        ui = GuidedSelectionUI(keys=keys)
        plan, _ = run_guided_init_flow("demo", "3.13", ui=ui)
        bases = [c.split("[", 1)[0] for c in plan.components]
        assert "worker" in bases
        assert "redis" in bases


class TestInExperienceBuild:
    """Phase 2: the build runs inside the flow; DONE closes it out."""

    def test_builder_runs_and_done_consumes_key(self) -> None:
        # review enter -> builder called -> DONE screen consumes one key.
        calls: list[str] = []

        def builder(plan, reporter):
            reporter.step("deps", "Installing dependencies", "uv sync")
            reporter.done("deps")
            calls.append(plan.project_name)
            return "/tmp/demo"

        keys = ["n", "n", "y", "\r"] + ["n"] * 9 + ["\r", "\r"]
        ui = GuidedSelectionUI(keys=keys)
        plan, _ = run_guided_init_flow(
            "demo",
            "3.13",
            ui=ui,
            builder=builder,
            replay_command=lambda p: "uvx aegis-stack init demo --no-interactive",
        )
        assert calls == ["demo"]
        assert "database" in plan.components

    def test_builder_stdout_is_captured_not_leaked(self, capsys) -> None:
        # Prints during the build would corrupt the alternate screen; they
        # must be swallowed by the capture, not reach the terminal.
        def builder(plan, reporter):
            print("loud generation output")
            return "/tmp/demo"

        keys = _DECLINE_ALL + ["\r", "\r"]
        run_guided_init_flow(
            "demo", "3.13", ui=GuidedSelectionUI(keys=keys), builder=builder
        )
        assert "loud generation output" not in capsys.readouterr().out

    def test_reporter_events_update_build_steps(self) -> None:
        # The reporter mutates the UI's step list: running -> done, with
        # labels/details preserved for the live screen.
        def builder(plan, reporter):
            reporter.step("render", "Rendering project files")
            reporter.done("render")
            reporter.step("deps", "Installing dependencies", "uv sync")
            return "/tmp/demo"

        keys = _DECLINE_ALL + ["\r", "\r"]
        ui = GuidedSelectionUI(keys=keys)
        run_guided_init_flow("demo", "3.13", ui=ui, builder=builder)
        recorded = ui._build_steps
        assert [(s["key"], s["state"]) for s in recorded] == [
            ("render", "done"),
            ("deps", "running"),
        ]
        assert recorded[1]["detail"] == "uv sync"

    def test_done_screen_copy_key(self, monkeypatch) -> None:
        # 'c' on the DONE card copies the FULL replay command (the display
        # is ellipsized; the clipboard must not be).
        import aegis.cli.guided as guided_mod

        copied: list[str] = []
        monkeypatch.setattr(
            guided_mod, "_copy_to_clipboard", lambda text: copied.append(text) or True
        )

        long_replay = "uvx aegis-stack init demo --components " + "x" * 200
        keys = _DECLINE_ALL + ["\r", "c", "\r"]  # review, copy, finish
        ui = GuidedSelectionUI(keys=keys)
        run_guided_init_flow(
            "demo",
            "3.13",
            ui=ui,
            builder=lambda plan, reporter: "/tmp/demo",
            replay_command=lambda p: long_replay,
        )
        assert copied == [long_replay]

    def test_receipt_replay_is_one_logical_line(self) -> None:
        # The persistent receipt must emit the command as ONE logical line:
        # rich soft_wrap output contains no injected newlines even when the
        # command exceeds the console width.
        from rich.console import Console
        from rich.text import Text

        cmd = "uvx aegis-stack init demo --components " + ",".join(
            ["database[postgres]"] * 12
        )
        console = Console(record=True, width=60, highlight=False)
        console.print(Text(f"   {cmd}", style="#17CCBF"), soft_wrap=True)
        out = console.export_text()
        assert out.count("\n") == 1  # the single trailing newline
        assert cmd in out

    def test_builder_failure_carries_captured_log(self) -> None:
        def builder(plan, reporter):
            print("partial progress line")
            raise RuntimeError("uv sync exploded")

        keys = _DECLINE_ALL + ["\r"]
        with pytest.raises(GuidedBuildError) as excinfo:
            run_guided_init_flow(
                "demo", "3.13", ui=GuidedSelectionUI(keys=keys), builder=builder
            )
        assert "partial progress line" in excinfo.value.log
        assert isinstance(excinfo.value.__cause__, RuntimeError)


class TestBreadcrumbs:
    """The trail mirrors the journal: every screen answered, back included."""

    def test_crumbs_record_each_component_decision(self) -> None:
        # Worker leads now; accepting it amends its crumb with the backend
        # and pushes the auto-added redis crumb (capability-first name).
        ui = GuidedSelectionUI(keys=["y", "\r"] + ["n"] * 10)
        run_guided_selection(ui)
        assert ui.breadcrumbs[0] == "Worker ✓ arq"
        assert "Cache/Broker/Pubsub ✓" in ui.breadcrumbs
        assert "Scheduler ✗" in ui.breadcrumbs
        # 12 entries: the skipped redis screen contributes no crumb of its
        # own, but the auto-add pushed one in its place.
        assert len(ui.breadcrumbs) == 12

    def test_chip_selections_amend_the_owning_crumb(self) -> None:
        # scheduler accepted, postgres backend: the engine choice attaches
        # to the Scheduler crumb instead of adding noise.
        keys = ["n", "y", "right", "right", "\r"] + ["n"] * 9
        ui = GuidedSelectionUI(keys=keys)
        run_guided_selection(ui)
        assert "Scheduler ✓ postgres" in ui.breadcrumbs

    def test_worker_auto_added_redis_pushes_its_crumb(self) -> None:
        # Worker accepted: the engine bundles redis and pushes its crumb
        # (the redis screen itself is skipped, so this is its only trace).
        keys = ["y", "\r"] + ["n"] * 10
        ui = GuidedSelectionUI(keys=keys)
        run_guided_selection(ui)
        assert "Cache/Broker/Pubsub ✓" in ui.breadcrumbs
        assert "Cache/Broker/Pubsub ✗" not in ui.breadcrumbs

    def test_back_from_worker_removes_redis_crumb(self) -> None:
        # esc at the screen after the worker backend chip pops the chip
        # answer; the auto-pushed redis crumb rides with it. esc again to
        # back out of worker entirely, then decline it — redis is asked
        # for real this time and declined.
        keys = ["y", "\r", "esc", "esc", "n"] + ["n"] * 11
        ui = GuidedSelectionUI(keys=keys)
        run_guided_selection(ui)
        assert "Cache/Broker/Pubsub ✗" in ui.breadcrumbs
        assert "Cache/Broker/Pubsub ✓" not in ui.breadcrumbs
        assert "Worker ✗" in ui.breadcrumbs

    def test_auto_added_database_gets_its_own_crumb(self) -> None:
        # Picking a persistent scheduler backend pulls in Database; the
        # sidebar must show that, not hide it inside the Scheduler crumb.
        keys = ["n", "y", "right", "right", "\r"] + ["n"] * 9
        ui = GuidedSelectionUI(keys=keys)
        run_guided_selection(ui)
        assert "Database ✓ postgres" in ui.breadcrumbs

    def test_back_from_scheduler_backend_removes_database_crumb(self) -> None:
        # Choose postgres, esc back to the backend screen (which re-focuses
        # postgres), move left twice to In-memory: the auto-pushed Database
        # crumb must disappear with the answer.
        # In-memory means no auto database, so the Database screen comes
        # back on the replayed pass: 10 declines, not 9.
        keys = ["n", "y", "right", "right", "\r", "esc"]
        keys += ["left", "left", "\r"] + ["n"] * 10
        ui = GuidedSelectionUI(keys=keys)
        run_guided_selection(ui)
        # The auto-pushed crumb is gone; what remains is the re-asked (and
        # declined) Database screen's own crumb.
        assert "Database ✓ postgres" not in ui.breadcrumbs
        assert "Database ✗" in ui.breadcrumbs
        assert "Scheduler ✓ memory" in ui.breadcrumbs

    def test_ai_persistent_storage_pushes_database_crumb(self) -> None:
        # AI alone choosing sqlite storage auto-adds Database — sidebar too.
        keys = (
            _DECLINE_ALL[:6]
            + ["n", "n", "y", "\r", "right", "\r", "up", "\r", "n", "n"]
            # ai -> framework, storage right (sqlite), providers Continue,
            # rag n, voice n
            + ["n", "n", "n"]
        )
        ui = GuidedSelectionUI(keys=keys)
        run_guided_selection(ui)
        assert "Database ✓ sqlite" in ui.breadcrumbs

    def test_sidebar_groups_components_and_services(self) -> None:
        from rich.console import Console

        keys = (
            _DECLINE_ALL[:6]
            + ["n", "n", "y", "\r", "right", "\r", "up", "\r", "n", "n"]
            + ["n", "n", "n"]
        )
        ui = GuidedSelectionUI(keys=keys)
        run_guided_selection(ui)
        ui._console = Console(width=100, height=60)
        console = Console(width=100, height=60, record=True)
        console.print(ui._sidebar())
        out = console.export_text()
        comp_at = out.index("COMPONENTS")
        svc_at = out.index("SERVICES")
        assert comp_at < svc_at
        # The preselected core stack leads the components section.
        assert comp_at < out.index("Backend") < out.index("Frontend") < svc_at
        # The auto-added Database crumb files under COMPONENTS even though
        # it was pushed during the AI service screens.
        assert comp_at < out.index("Database") < svc_at
        assert out.index("AI") > svc_at

    def test_screen_shows_visible_docs_url(self) -> None:
        # Plain URLs the terminal auto-linkifies — styled OSC 8 links
        # proved unreliable, mirroring the post-init "Docs:" line instead.
        from rich.console import Console

        from aegis.cli.guided import _Choice, _docs_url
        from aegis.core.components import COMPONENTS

        assert (
            _docs_url(COMPONENTS["worker"])
            == "https://docs.aegis-stack.io/components/worker/"
        )
        assert _docs_url(COMPONENTS["redis"]) is None  # no page, no link

        ui = GuidedSelectionUI(keys=[])
        choices = [_Choice("yes", "Add"), _Choice("no", "Skip")]
        console = Console(width=100, record=True)
        console.print(ui._body("Add?", choices, 0, COMPONENTS["worker"], True))
        assert "https://docs.aegis-stack.io/components/worker/" in (
            console.export_text()
        )
        console = Console(width=100, record=True)
        console.print(ui._body("Add?", choices, 0, COMPONENTS["redis"], True))
        assert "docs.aegis-stack.io" not in console.export_text()

    def test_back_rewinds_the_trail(self) -> None:
        # Worker accepted then revised to declined via esc on the backend
        # chips: the trail must show the revised answer, not the original.
        ui = GuidedSelectionUI(keys=["y", "esc"] + ["n"] * 12)
        run_guided_selection(ui)
        assert ui.breadcrumbs[0] == "Worker ✗"
        assert all("✓" not in crumb for crumb in ui.breadcrumbs)
