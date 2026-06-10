"""Characterization tests for ``interactive_service_selection`` (add flow).

Pin the behavior of the per-service-type prompt loop in
``aegis/cli/interactive.py`` before (and after) collapsing the four
copy-pasted type branches into one data-driven loop: skip-when-enabled,
auto-add requirement hints, auth's level configurator, and plain-name
selection for everything else.

``TestRegistryDrivenAdditions`` covers what the collapse fixed: comms
(NOTIFICATION) and insights (ANALYTICS) were missing from the hand-written
branches, so ``aegis add-service`` interactive mode never offered them.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml

from aegis.cli.interactive import interactive_service_selection


def _fake_project(tmp_path: Path, **answers: Any) -> Path:
    """Minimal Copier project: just the answers file the function loads."""
    project = tmp_path / "proj"
    project.mkdir()
    (project / ".copier-answers.yml").write_text(yaml.safe_dump(answers))
    return project


def _run(
    project: Path, confirm_answers: list[bool], auth_level: str = "basic"
) -> tuple[list[str], list[str]]:
    """Drive the prompt loop with scripted confirms.

    Returns (selected_services, prompts shown to the user).
    """
    prompts: list[str] = []

    def fake_confirm(prompt: str, default: bool = True) -> bool:
        prompts.append(prompt)
        return confirm_answers[len(prompts) - 1]

    with (
        patch("aegis.cli.interactive.typer.confirm", side_effect=fake_confirm),
        patch(
            "aegis.cli.interactive.interactive_auth_service_config",
            return_value=auth_level,
        ),
    ):
        return interactive_service_selection(project), prompts


class TestSelectionCharacterization:
    """Behavior pinned from the hand-written type branches."""

    def test_decline_everything_selects_nothing(self, tmp_path: Path) -> None:
        project = _fake_project(tmp_path)
        selected, prompts = _run(project, [False] * 20)
        assert selected == []
        assert prompts, "at least one service should have been offered"

    def test_auth_accepted_gets_level_bracket(self, tmp_path: Path) -> None:
        project = _fake_project(tmp_path)
        # Accept the first prompt (auth), decline the rest.
        selected, prompts = _run(project, [True] + [False] * 20, auth_level="rbac")
        assert "auth[rbac]" in selected
        assert "auth" not in selected  # bracket string, not the plain name

    def test_non_auth_services_selected_as_plain_names(self, tmp_path: Path) -> None:
        project = _fake_project(tmp_path)
        selected, _ = _run(project, [True] * 20, auth_level="basic")
        # Every selection except auth's is a plain service name.
        assert all("[" not in s for s in selected if not s.startswith("auth"))

    def test_enabled_service_skipped_without_prompt(self, tmp_path: Path) -> None:
        project = _fake_project(tmp_path, include_auth=True)
        selected, prompts = _run(project, [False] * 20)
        assert all("authentication" not in p.lower() for p in prompts)
        assert not any(s.startswith("auth") for s in selected)

    def test_missing_components_shown_in_prompt(self, tmp_path: Path) -> None:
        project = _fake_project(tmp_path)  # no database enabled
        _, prompts = _run(project, [False] * 20)
        # Services requiring database advertise the auto-add.
        assert any("will auto-add" in p and "database" in p for p in prompts)


class TestRegistryDrivenAdditions:
    """Coverage gained by deriving the type loop from ServiceType.

    The hand-written branches covered AUTH/AI/PAYMENT/CONTENT only;
    NOTIFICATION (comms) and ANALYTICS (insights) services existed in the
    registry but were never offered interactively.
    """

    def test_comms_offered(self, tmp_path: Path) -> None:
        project = _fake_project(tmp_path)
        selected, prompts = _run(project, [True] * 20)
        assert "comms" in selected

    def test_insights_offered(self, tmp_path: Path) -> None:
        project = _fake_project(tmp_path)
        selected, prompts = _run(project, [True] * 20)
        assert "insights" in selected


@pytest.fixture(autouse=True)
def _clear_auth_selection() -> Any:
    from aegis.cli.interactive import clear_auth_level_selection

    clear_auth_level_selection()
    yield
    clear_auth_level_selection()
