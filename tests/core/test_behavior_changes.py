"""#1029. Updating across a template version that changes runtime behavior
must say so, and name the setting that restores the old behavior.

Nothing here is derived from a diff. Each entry is declared by the author at
release time and filtered against the project's answers - "does this stack
have the component the change touches?" - and the update's version range.
That is the whole design: a human wrote the line, the code only decides
whether to show it.
"""

from __future__ import annotations

from aegis.core.behavior_changes import (
    BEHAVIOR_CHANGES,
    BehaviorChange,
    behavior_changes_for,
)


def _auth_gate() -> BehaviorChange:
    """The entry that motivated the ticket: sector-7g's public dashboard
    came back auth-gated after 0.6 -> 0.10.1."""
    return next(c for c in BEHAVIOR_CHANGES if "AUTH_ENABLED" in (c.restore or ""))


class TestFiltering:
    def test_crossing_the_version_with_the_component_reports_it(self) -> None:
        gate = _auth_gate()
        hits = behavior_changes_for(
            from_version="0.6.11",
            to_version="0.10.1",
            answers={"include_auth": True},
        )
        assert gate in hits

    def test_project_already_past_the_version_is_silent(self) -> None:
        """The ticket's validation gate: a project already past the gate's
        introduction prints nothing."""
        gate = _auth_gate()
        hits = behavior_changes_for(
            from_version=gate.since,
            to_version="0.11.1",
            answers={"include_auth": True},
        )
        assert gate not in hits

    def test_project_without_the_component_is_silent(self) -> None:
        """A change to auth's login gate means nothing to a stack that has
        no auth; noise here trains operators to skip the block."""
        gate = _auth_gate()
        hits = behavior_changes_for(
            from_version="0.6.11",
            to_version="0.10.1",
            answers={"include_auth": False},
        )
        assert gate not in hits

    def test_prerelease_of_the_introducing_version_still_crosses(self) -> None:
        """0.6.12-rc1 sorts BEFORE 0.6.12; a project on the rc has not
        crossed the gate yet and must be told."""
        gate = _auth_gate()
        hits = behavior_changes_for(
            from_version="0.6.12-rc1",
            to_version="0.6.12",
            answers={"include_auth": True},
        )
        assert gate in hits

    def test_unparseable_from_version_reports_everything_applicable(self) -> None:
        """A project whose stored version is a bare sha (dev-mode init) cannot
        be placed on the line. Over-reporting is the safe failure: a notice
        the operator did not need beats a silent behavior flip."""
        gate = _auth_gate()
        hits = behavior_changes_for(
            from_version="HEAD", to_version="0.10.1", answers={"include_auth": True}
        )
        assert gate in hits


class TestRegistryHygiene:
    def test_every_entry_has_a_parseable_version_and_a_message(self) -> None:
        from packaging.version import parse

        for change in BEHAVIOR_CHANGES:
            parse(change.since)  # raises if not a version
            assert change.message.strip()
            assert change.when, (
                f"{change.since}: an entry with no condition fires for every stack"
            )

    def test_the_auth_gate_entry_exists_and_names_the_escape_hatch(self) -> None:
        gate = _auth_gate()
        assert gate.since == "0.6.12"
        assert gate.restore is not None and "AUTH_ENABLED=false" in gate.restore
