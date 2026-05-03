"""
Tests for ``aegis plugins update`` (#772).

Exercises the dispatch logic + version-check semantics. The actual
template rendering is covered by ``test_manual_updater_plugins.py``,
so these tests mock ``ManualUpdater`` to keep them fast and focused.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from typer.testing import CliRunner

from aegis.commands.plugins import plugins_app

runner = CliRunner()


COPIER_ANSWERS_BASE = """\
# Changes here will be overwritten by Copier; NEVER EDIT MANUALLY
project_name: Demo
project_slug: demo
include_database: false
_commit: None
_src_path: aegis/templates/copier-aegis-project
"""


@pytest.fixture
def project_with_plugin(tmp_path: Path) -> Path:
    """Synthetic project with one installed plugin entry."""
    project = tmp_path / "demo"
    project.mkdir()
    answers_path = project / ".copier-answers.yml"
    answers_path.write_text(
        COPIER_ANSWERS_BASE
        + yaml.safe_dump({"_plugins": [{"name": "test_plugin", "version": "0.0.0"}]})
    )
    return project


@pytest.fixture
def project_no_plugins(tmp_path: Path) -> Path:
    """Synthetic project with no installed plugins."""
    project = tmp_path / "demo"
    project.mkdir()
    (project / ".copier-answers.yml").write_text(COPIER_ANSWERS_BASE)
    return project


class TestArgValidation:
    def test_neither_name_nor_all_errors(self, project_with_plugin: Path) -> None:
        result = runner.invoke(
            plugins_app,
            ["update", "--project-path", str(project_with_plugin)],
        )
        assert result.exit_code == 1
        assert "Pass a plugin name or use --all" in result.output

    def test_both_name_and_all_errors(self, project_with_plugin: Path) -> None:
        result = runner.invoke(
            plugins_app,
            [
                "update",
                "test_plugin",
                "--all",
                "--project-path",
                str(project_with_plugin),
            ],
        )
        assert result.exit_code == 1
        assert "either a plugin name OR --all" in result.output


class TestLegacyShape:
    def test_legacy_string_entries_warn_with_re_add_hint(self, tmp_path: Path) -> None:
        """Pre-Round-8 ``_plugins`` could be a list of strings. Surface
        a migration hint instead of silently dropping them."""
        project = tmp_path / "demo"
        project.mkdir()
        (project / ".copier-answers.yml").write_text(
            COPIER_ANSWERS_BASE
            + yaml.safe_dump({"_plugins": ["scraper>=1.0", "monitor"]})
        )

        result = runner.invoke(
            plugins_app,
            ["update", "--all", "--project-path", str(project)],
        )
        assert "Skipping legacy string-shaped" in result.output
        assert "scraper>=1.0" in result.output
        assert "aegis add" in result.output


class TestNoOpPaths:
    def test_no_plugins_in_project_friendly_message(
        self, project_no_plugins: Path
    ) -> None:
        result = runner.invoke(
            plugins_app,
            ["update", "--all", "--project-path", str(project_no_plugins)],
        )
        assert result.exit_code == 0
        assert "No plugins are installed" in result.output

    def test_unknown_plugin_name_errors(self, project_with_plugin: Path) -> None:
        result = runner.invoke(
            plugins_app,
            [
                "update",
                "not_installed",
                "--project-path",
                str(project_with_plugin),
            ],
        )
        assert result.exit_code == 1
        assert "not installed in this project" in result.output


class TestUpdateFlow:
    def test_skips_when_versions_match(self, project_with_plugin: Path) -> None:
        # Project records version "0.0.0"; mock pip-installed spec at the
        # same version so update is a no-op.
        from aegis_plugin_test.spec import get_spec

        installed_spec = get_spec()
        installed_spec.version = "0.0.0"

        with patch(
            "aegis.commands.plugins._resolve_installed_spec",
            return_value=(installed_spec, "aegis_plugin_test"),
        ):
            result = runner.invoke(
                plugins_app,
                [
                    "update",
                    "test_plugin",
                    "--yes",
                    "--project-path",
                    str(project_with_plugin),
                ],
            )

        assert result.exit_code == 0
        assert "already at 0.0.0" in result.output

    def test_applies_when_versions_differ(
        self, project_with_plugin: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Newer pip-installed version triggers a re-add via
        ``ManualUpdater.add_plugin``. We mock the updater to verify
        wiring without touching disk."""
        from aegis_plugin_test.spec import get_spec

        installed_spec = get_spec()
        installed_spec.version = "9.9.9"  # bump

        mock_updater = MagicMock()
        mock_updater.add_plugin.return_value = MagicMock(
            success=True, error_message=None
        )
        with (
            patch(
                "aegis.commands.plugins._resolve_installed_spec",
                return_value=(installed_spec, "aegis_plugin_test"),
            ),
            patch(
                "aegis.core.manual_updater.ManualUpdater",
                return_value=mock_updater,
            ),
        ):
            result = runner.invoke(
                plugins_app,
                [
                    "update",
                    "test_plugin",
                    "--yes",
                    "--project-path",
                    str(project_with_plugin),
                ],
            )

        assert result.exit_code == 0
        assert "0.0.0 → 9.9.9" in result.output
        assert "Updated: 1" in result.output
        mock_updater.add_plugin.assert_called_once()

    def test_failed_update_exits_nonzero(self, project_with_plugin: Path) -> None:
        from aegis_plugin_test.spec import get_spec

        installed_spec = get_spec()
        installed_spec.version = "9.9.9"

        mock_updater = MagicMock()
        mock_updater.add_plugin.return_value = MagicMock(
            success=False, error_message="boom"
        )
        with (
            patch(
                "aegis.commands.plugins._resolve_installed_spec",
                return_value=(installed_spec, "aegis_plugin_test"),
            ),
            patch(
                "aegis.core.manual_updater.ManualUpdater",
                return_value=mock_updater,
            ),
        ):
            result = runner.invoke(
                plugins_app,
                [
                    "update",
                    "test_plugin",
                    "--yes",
                    "--project-path",
                    str(project_with_plugin),
                ],
            )

        assert result.exit_code == 1
        assert "Failed: 1" in result.output
        assert "boom" in result.output

    def test_aegis_version_mismatch_blocks_update(
        self, project_with_plugin: Path
    ) -> None:
        """Plugin's new version declares an aegis_version range that
        excludes the running CLI — update should fail without
        --force (#777)."""
        from aegis_plugin_test.spec import get_spec

        installed_spec = get_spec()
        installed_spec.version = "9.9.9"
        installed_spec.aegis_version = ">=99.0"  # impossible

        with patch(
            "aegis.commands.plugins._resolve_installed_spec",
            return_value=(installed_spec, "aegis_plugin_test"),
        ):
            result = runner.invoke(
                plugins_app,
                [
                    "update",
                    "test_plugin",
                    "--yes",
                    "--project-path",
                    str(project_with_plugin),
                ],
            )

        assert result.exit_code == 1
        assert "requires aegis >=99.0" in result.output
        assert "Failed: 1" in result.output

    def test_aegis_version_mismatch_force_overrides(
        self, project_with_plugin: Path
    ) -> None:
        """``--force`` lets the user proceed past a version-compat
        rejection — plugin author / user is on the hook for the
        consequences."""
        from aegis_plugin_test.spec import get_spec

        installed_spec = get_spec()
        installed_spec.version = "9.9.9"
        installed_spec.aegis_version = ">=99.0"

        mock_updater = MagicMock()
        mock_updater.add_plugin.return_value = MagicMock(
            success=True, error_message=None
        )
        with (
            patch(
                "aegis.commands.plugins._resolve_installed_spec",
                return_value=(installed_spec, "aegis_plugin_test"),
            ),
            patch(
                "aegis.core.manual_updater.ManualUpdater",
                return_value=mock_updater,
            ),
        ):
            result = runner.invoke(
                plugins_app,
                [
                    "update",
                    "test_plugin",
                    "--yes",
                    "--force",
                    "--project-path",
                    str(project_with_plugin),
                ],
            )

        assert result.exit_code == 0
        assert "Forcing update despite version mismatch" in result.output
        assert "Updated: 1" in result.output

    def test_pip_uninstalled_plugin_reports_clearly(
        self, project_with_plugin: Path
    ) -> None:
        """Plugin recorded in ``_plugins`` but no longer pip-installed —
        ``_resolve_installed_spec`` returns ``None``, update fails with
        a pip-install hint."""
        with patch(
            "aegis.commands.plugins._resolve_installed_spec",
            return_value=None,
        ):
            result = runner.invoke(
                plugins_app,
                [
                    "update",
                    "test_plugin",
                    "--yes",
                    "--project-path",
                    str(project_with_plugin),
                ],
            )

        assert result.exit_code == 1
        assert "not currently pip-installed" in result.output
