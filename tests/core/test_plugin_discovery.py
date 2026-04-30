"""
Tests for plugin discovery (#768) and CLI sub-app mounting (R5).

The discovery layer is the bridge between in-tree plugin data (R1-R4)
and runtime plugin objects shipped via PyPI. These tests pin down:

* the happy path (entry point → ``PluginSpec`` / ``typer.Typer``);
* error tolerance — a single broken plugin must never break core CLI;
* collision handling — duplicates and reserved-name conflicts skip the
  offending entry, not the whole discovery pass;
* cache semantics so repeated calls are cheap and tests can reset.
"""

from __future__ import annotations

from importlib.metadata import EntryPoint
from unittest.mock import patch

import pytest
import typer

from aegis.core import plugin_discovery
from aegis.core.plugin_discovery import (
    PLUGIN_CLI_ENTRY_POINT_GROUP,
    PLUGIN_ENTRY_POINT_GROUP,
    clear_cache,
    discover_plugin_cli_apps,
    discover_plugins,
)
from aegis.core.plugin_spec import PluginKind, PluginSpec

# ---------------------------------------------------------------------
# Fixtures + helpers
# ---------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_discovery_cache() -> None:
    """Module-level caches must be reset between tests."""
    clear_cache()


def _make_ep(name: str, value: str, group: str) -> EntryPoint:
    return EntryPoint(name=name, value=value, group=group)


def _patch_entry_points(eps_by_group: dict[str, list[EntryPoint]]):
    """Patch ``_entry_points_for`` to return canned entry points by group."""
    return patch.object(
        plugin_discovery,
        "_entry_points_for",
        side_effect=lambda group: eps_by_group.get(group, []),
    )


def _make_spec(name: str = "scraper") -> PluginSpec:
    return PluginSpec(name=name, kind=PluginKind.SERVICE, description="x")


# ---------------------------------------------------------------------
# discover_plugins() — happy path
# ---------------------------------------------------------------------


class TestDiscoverPluginsHappyPath:
    def test_no_entry_points_returns_empty(self) -> None:
        with _patch_entry_points({}):
            assert discover_plugins() == []

    def test_single_plugin(self) -> None:
        spec = _make_spec("scraper")

        def get_spec() -> PluginSpec:
            return spec

        ep = _make_ep("scraper", "fake:get_spec", PLUGIN_ENTRY_POINT_GROUP)
        with (
            _patch_entry_points({PLUGIN_ENTRY_POINT_GROUP: [ep]}),
            patch.object(EntryPoint, "load", return_value=get_spec),
        ):
            result = discover_plugins()
        assert result == [spec]

    def test_multiple_plugins(self) -> None:
        a, b = _make_spec("alpha"), _make_spec("beta")
        eps = [
            _make_ep("alpha", "f:a", PLUGIN_ENTRY_POINT_GROUP),
            _make_ep("beta", "f:b", PLUGIN_ENTRY_POINT_GROUP),
        ]
        with (
            _patch_entry_points({PLUGIN_ENTRY_POINT_GROUP: eps}),
            patch.object(EntryPoint, "load", side_effect=[lambda: a, lambda: b]),
        ):
            assert {s.name for s in discover_plugins()} == {"alpha", "beta"}

    def test_load_returns_plugin_spec_directly(self) -> None:
        """Some plugins may export the spec instance directly rather than a
        callable factory. Both shapes should work."""
        spec = _make_spec("direct")
        ep = _make_ep("direct", "f:spec", PLUGIN_ENTRY_POINT_GROUP)
        with (
            _patch_entry_points({PLUGIN_ENTRY_POINT_GROUP: [ep]}),
            patch.object(EntryPoint, "load", return_value=spec),
        ):
            assert discover_plugins() == [spec]


# ---------------------------------------------------------------------
# discover_plugins() — error tolerance
# ---------------------------------------------------------------------


class TestDiscoverPluginsErrors:
    def test_import_failure_skips_only_that_plugin(self, capsys) -> None:
        good_spec = _make_spec("good")
        eps = [
            _make_ep("bad", "broken:nope", PLUGIN_ENTRY_POINT_GROUP),
            _make_ep("good", "f:get", PLUGIN_ENTRY_POINT_GROUP),
        ]

        def fake_load(self: EntryPoint):
            if self.name == "bad":
                raise ImportError("boom")
            return lambda: good_spec

        with (
            _patch_entry_points({PLUGIN_ENTRY_POINT_GROUP: eps}),
            patch.object(EntryPoint, "load", autospec=True, side_effect=fake_load),
        ):
            result = discover_plugins()

        assert result == [good_spec]
        assert "failed to import" in capsys.readouterr().err

    def test_get_spec_raises_skips_only_that_plugin(self, capsys) -> None:
        good_spec = _make_spec("good")

        def bad_factory() -> PluginSpec:
            raise RuntimeError("kaboom")

        eps = [
            _make_ep("bad", "f:bad", PLUGIN_ENTRY_POINT_GROUP),
            _make_ep("good", "f:good", PLUGIN_ENTRY_POINT_GROUP),
        ]
        with (
            _patch_entry_points({PLUGIN_ENTRY_POINT_GROUP: eps}),
            patch.object(
                EntryPoint, "load", side_effect=[bad_factory, lambda: good_spec]
            ),
        ):
            result = discover_plugins()

        assert result == [good_spec]
        assert "raised" in capsys.readouterr().err

    def test_wrong_return_type_skipped(self, capsys) -> None:
        ep = _make_ep("bad", "f:not_a_spec", PLUGIN_ENTRY_POINT_GROUP)
        with (
            _patch_entry_points({PLUGIN_ENTRY_POINT_GROUP: [ep]}),
            patch.object(EntryPoint, "load", return_value=lambda: {"not": "a spec"}),
        ):
            assert discover_plugins() == []
        assert "expected PluginSpec" in capsys.readouterr().err

    def test_duplicate_plugin_name_skipped(self, capsys) -> None:
        spec_a = _make_spec("dup")
        spec_b = _make_spec("dup")  # second package using the same name
        eps = [
            _make_ep("first", "f:a", PLUGIN_ENTRY_POINT_GROUP),
            _make_ep("second", "f:b", PLUGIN_ENTRY_POINT_GROUP),
        ]
        with (
            _patch_entry_points({PLUGIN_ENTRY_POINT_GROUP: eps}),
            patch.object(
                EntryPoint, "load", side_effect=[lambda: spec_a, lambda: spec_b]
            ),
        ):
            assert discover_plugins() == [spec_a]
        assert "collides" in capsys.readouterr().err


# ---------------------------------------------------------------------
# discover_plugin_cli_apps() — happy path + collisions
# ---------------------------------------------------------------------


class TestDiscoverPluginCliApps:
    def test_no_entry_points_empty_dict(self) -> None:
        with _patch_entry_points({}):
            assert discover_plugin_cli_apps() == {}

    def test_mounts_typer_app(self) -> None:
        sub_app = typer.Typer(name="scraper")
        ep = _make_ep("scraper", "f:app", PLUGIN_CLI_ENTRY_POINT_GROUP)
        with (
            _patch_entry_points({PLUGIN_CLI_ENTRY_POINT_GROUP: [ep]}),
            patch.object(EntryPoint, "load", return_value=sub_app),
        ):
            result = discover_plugin_cli_apps()
        assert result == {"scraper": sub_app}

    def test_reserved_name_collision_rejected(self, capsys) -> None:
        sub_app = typer.Typer()
        ep = _make_ep("init", "f:app", PLUGIN_CLI_ENTRY_POINT_GROUP)
        with (
            _patch_entry_points({PLUGIN_CLI_ENTRY_POINT_GROUP: [ep]}),
            patch.object(EntryPoint, "load", return_value=sub_app),
        ):
            assert discover_plugin_cli_apps(reserved_names={"init"}) == {}
        assert "reserved core command" in capsys.readouterr().err

    def test_wrong_return_type_skipped(self, capsys) -> None:
        ep = _make_ep("bad", "f:not_typer", PLUGIN_CLI_ENTRY_POINT_GROUP)
        with (
            _patch_entry_points({PLUGIN_CLI_ENTRY_POINT_GROUP: [ep]}),
            patch.object(EntryPoint, "load", return_value="not a typer instance"),
        ):
            assert discover_plugin_cli_apps() == {}
        assert "expected typer.Typer" in capsys.readouterr().err

    def test_import_failure_skipped(self, capsys) -> None:
        ep = _make_ep("bad", "broken:app", PLUGIN_CLI_ENTRY_POINT_GROUP)
        with (
            _patch_entry_points({PLUGIN_CLI_ENTRY_POINT_GROUP: [ep]}),
            patch.object(EntryPoint, "load", side_effect=ImportError("boom")),
        ):
            assert discover_plugin_cli_apps() == {}
        assert "failed to import CLI plugin" in capsys.readouterr().err


# ---------------------------------------------------------------------
# Caching
# ---------------------------------------------------------------------


class TestCaching:
    def test_discover_plugins_is_memoised(self) -> None:
        spec = _make_spec("only")
        ep = _make_ep("only", "f:s", PLUGIN_ENTRY_POINT_GROUP)
        with (
            _patch_entry_points({PLUGIN_ENTRY_POINT_GROUP: [ep]}) as ep_mock,
            patch.object(EntryPoint, "load", return_value=lambda: spec),
        ):
            r1 = discover_plugins()
            r2 = discover_plugins()
        # Equal but independent lists (caller should be free to mutate).
        assert r1 == r2 == [spec]
        assert r1 is not r2
        # Underlying entry-point enumeration only happens once.
        assert ep_mock.call_count == 1

    def test_clear_cache_forces_re_enumeration(self) -> None:
        spec = _make_spec("x")
        ep = _make_ep("x", "f:s", PLUGIN_ENTRY_POINT_GROUP)
        with (
            _patch_entry_points({PLUGIN_ENTRY_POINT_GROUP: [ep]}) as ep_mock,
            patch.object(EntryPoint, "load", return_value=lambda: spec),
        ):
            discover_plugins()
            clear_cache()
            discover_plugins()
        assert ep_mock.call_count == 2


# ---------------------------------------------------------------------
# Group-name constants are stable (plugin authors depend on these)
# ---------------------------------------------------------------------


class TestEntryPointGroupNames:
    def test_plugin_group_name_is_stable(self) -> None:
        # If this changes, every existing plugin's pyproject.toml breaks.
        assert PLUGIN_ENTRY_POINT_GROUP == "aegis.plugins"

    def test_cli_group_name_is_stable(self) -> None:
        assert PLUGIN_CLI_ENTRY_POINT_GROUP == "aegis.plugins.cli"


# ---------------------------------------------------------------------
# CLI cache / reserved-names interaction
# ---------------------------------------------------------------------


class TestCliCacheReservedFilter:
    """Cache stores raw discovery; reserved filter applies per call.

    Prevents a stale-cache bug where calling the function with one
    reserved set, then again with a different set, would return the
    first call's filtered view (or worse — leak a now-reserved name).
    """

    def test_different_reserved_sets_get_different_results(self) -> None:
        sub_a = typer.Typer()
        sub_b = typer.Typer()
        eps = [
            _make_ep("alpha", "f:a", PLUGIN_CLI_ENTRY_POINT_GROUP),
            _make_ep("beta", "f:b", PLUGIN_CLI_ENTRY_POINT_GROUP),
        ]
        with (
            _patch_entry_points({PLUGIN_CLI_ENTRY_POINT_GROUP: eps}),
            patch.object(EntryPoint, "load", side_effect=[sub_a, sub_b]),
        ):
            # First call reserves alpha → expect only beta
            r1 = discover_plugin_cli_apps(reserved_names={"alpha"})
            # Second call reserves beta → expect only alpha
            r2 = discover_plugin_cli_apps(reserved_names={"beta"})
            # Third call reserves nothing → expect both
            r3 = discover_plugin_cli_apps()

        assert set(r1.keys()) == {"beta"}
        assert set(r2.keys()) == {"alpha"}
        assert set(r3.keys()) == {"alpha", "beta"}

    def test_raw_discovery_is_cached(self) -> None:
        """Underlying entry-point enumeration runs once across calls."""
        sub_app = typer.Typer()
        ep = _make_ep("only", "f:app", PLUGIN_CLI_ENTRY_POINT_GROUP)
        with (
            _patch_entry_points({PLUGIN_CLI_ENTRY_POINT_GROUP: [ep]}) as ep_mock,
            patch.object(EntryPoint, "load", return_value=sub_app),
        ):
            discover_plugin_cli_apps()
            discover_plugin_cli_apps(reserved_names={"x"})
            discover_plugin_cli_apps(reserved_names={"y"})
        assert ep_mock.call_count == 1


# ---------------------------------------------------------------------
# __main__ wiring (R5)
# ---------------------------------------------------------------------


class TestMountPluginCliApps:
    """``_mount_plugin_cli_apps`` is the integration seam between
    ``aegis.__main__`` and ``plugin_discovery``. Tests use a fresh Typer
    app to verify the mount call path without depending on the
    module-level ``aegis.__main__:app`` state.
    """

    def test_mounts_plugin_app_under_plugin_name(self) -> None:
        from aegis.__main__ import _mount_plugin_cli_apps

        fresh_app = typer.Typer(name="aegis")
        plugin_app = typer.Typer()
        with patch(
            "aegis.core.plugin_discovery.discover_plugin_cli_apps",
            return_value={"scraper": plugin_app},
        ):
            _mount_plugin_cli_apps(fresh_app)

        mounted = {grp.name for grp in fresh_app.registered_groups if grp.name}
        assert "scraper" in mounted

    def test_passes_existing_command_names_as_reserved(self) -> None:
        """The reserved set passed to discover should include every core
        command + group already registered on the app."""
        from aegis.__main__ import _mount_plugin_cli_apps

        fresh_app = typer.Typer(name="aegis")

        @fresh_app.command(name="init")
        def _init() -> None: ...

        @fresh_app.command(name="add")
        def _add() -> None: ...

        captured: list[set[str] | None] = []

        def fake_discover(reserved_names: set[str] | None = None) -> dict[str, object]:
            captured.append(reserved_names)
            return {}

        with patch(
            "aegis.core.plugin_discovery.discover_plugin_cli_apps",
            side_effect=fake_discover,
        ):
            _mount_plugin_cli_apps(fresh_app)

        assert len(captured) == 1
        assert captured[0] is not None
        assert {"init", "add"}.issubset(captured[0])

    def test_skips_mounting_when_no_plugins(self) -> None:
        """Empty discovery → no groups added; sanity check the no-op path."""
        from aegis.__main__ import _mount_plugin_cli_apps

        fresh_app = typer.Typer(name="aegis")
        before = len(fresh_app.registered_groups)
        with patch(
            "aegis.core.plugin_discovery.discover_plugin_cli_apps",
            return_value={},
        ):
            _mount_plugin_cli_apps(fresh_app)
        assert len(fresh_app.registered_groups) == before
