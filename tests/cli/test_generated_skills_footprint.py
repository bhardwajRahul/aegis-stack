"""Round-trip tests: skills join the aegis add/remove footprint.

A conditional skill directory is owned by its component or service spec, so
adding the capability delivers the skill and removing it deletes the skill, with
no special-casing in the add/remove commands.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from tests.cli.test_utils import run_aegis_command


def test_worker_skill_rides_add_and_remove(
    project_factory: Callable[..., Path],
) -> None:
    project = project_factory("base")
    skill = project / ".claude" / "skills" / "add-background-job"
    assert not skill.exists(), "base project should not ship the worker skill"

    added = run_aegis_command("add", "worker", "--project-path", str(project), "--yes")
    assert added.returncode == 0, f"add worker failed: {added.stderr}"
    assert (skill / "SKILL.md").exists(), "add worker did not deliver the skill"

    removed = run_aegis_command(
        "remove", "worker", "--project-path", str(project), "--yes"
    )
    assert removed.returncode == 0, f"remove worker failed: {removed.stderr}"
    assert not skill.exists(), "remove worker did not delete the skill"


def test_auth_skill_rides_add_and_remove_service(
    project_factory: Callable[..., Path],
) -> None:
    # auth requires the database component.
    project = project_factory("base_with_database")
    skill = project / ".claude" / "skills" / "protect-an-endpoint"
    assert not skill.exists(), "pre-auth project should not ship the auth skill"

    added = run_aegis_command(
        "add-service", "auth", "--project-path", str(project), "--yes"
    )
    assert added.returncode == 0, f"add-service auth failed: {added.stderr}"
    assert (skill / "SKILL.md").exists(), "add-service auth did not deliver the skill"

    removed = run_aegis_command(
        "remove-service", "auth", "--project-path", str(project), "--yes"
    )
    assert removed.returncode == 0, f"remove-service auth failed: {removed.stderr}"
    assert not skill.exists(), "remove-service auth did not delete the skill"
