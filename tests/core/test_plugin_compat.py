"""
Tests for ``aegis.core.plugin_compat``.

Round 8 (#771) introduced :func:`reverse_dependents` to support the
reverse-dependency check that ``aegis remove`` runs before letting the
user delete a service or plugin that something else still relies on.
"""

from __future__ import annotations

from aegis.core.plugin_compat import reverse_dependents
from aegis.core.plugin_spec import PluginKind, PluginSpec


def _spec(name: str, **kwargs) -> PluginSpec:
    return PluginSpec(
        name=name,
        kind=PluginKind.SERVICE,
        description="",
        **kwargs,
    )


class TestReverseDependents:
    def test_no_dependents_returns_empty(self) -> None:
        candidates = [
            _spec("auth"),
            _spec("ai"),
        ]
        answers = {"include_auth": True, "include_ai": True}
        assert reverse_dependents("auth", candidates, answers) == []

    def test_required_service_dependency_detected(self) -> None:
        """``insights.required_services = ["auth"]`` means insights
        depends on auth — removing auth should flag insights."""
        candidates = [
            _spec("auth"),
            _spec("insights", required_services=["auth"]),
        ]
        answers = {"include_auth": True, "include_insights": True}

        deps = reverse_dependents("auth", candidates, answers)
        assert deps == ["insights"]

    def test_required_plugin_dependency_detected(self) -> None:
        """A plugin's ``required_plugins`` entry blocks removal of a
        plugin it depends on."""
        candidates = [
            _spec("scraper"),
            _spec("dashboard", required_plugins=["scraper"]),
        ]
        # Plugins recorded in ``_plugins`` answer key.
        answers = {
            "_plugins": [{"name": "scraper"}, {"name": "dashboard"}],
        }

        deps = reverse_dependents("scraper", candidates, answers)
        assert deps == ["dashboard"]

    def test_required_component_dependency_detected(self) -> None:
        candidates = [
            _spec("auth", required_components=["database"]),
        ]
        answers = {"include_auth": True, "include_database": True}

        deps = reverse_dependents("database", candidates, answers)
        assert deps == ["auth"]

    def test_uninstalled_dependent_ignored(self) -> None:
        """A spec that *would* depend on the target but isn't installed
        in the project doesn't count — removing the target is safe."""
        candidates = [
            _spec("auth"),
            _spec("insights", required_services=["auth"]),
        ]
        # insights is not installed.
        answers = {"include_auth": True, "include_insights": False}

        assert reverse_dependents("auth", candidates, answers) == []

    def test_self_excluded(self) -> None:
        """A spec doesn't count itself as a reverse-dependent (defensive
        — this would only happen with a malformed self-referential spec,
        but the helper should still handle it)."""
        candidates = [_spec("auth", required_services=["auth"])]
        answers = {"include_auth": True}

        assert reverse_dependents("auth", candidates, answers) == []

    def test_constraint_versions_stripped(self) -> None:
        """``required_plugins=["scraper>=1.0"]`` matches target
        ``"scraper"`` — version constraints don't break the lookup."""
        candidates = [
            _spec("scraper"),
            _spec("dashboard", required_plugins=["scraper>=1.0"]),
        ]
        answers = {"_plugins": [{"name": "scraper"}, {"name": "dashboard"}]}

        deps = reverse_dependents("scraper", candidates, answers)
        assert deps == ["dashboard"]
