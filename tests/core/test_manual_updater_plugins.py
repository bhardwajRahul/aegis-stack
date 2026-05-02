"""
ManualUpdater plugin-template integration test.

Exercises ``ManualUpdater.install_plugin_template_tree`` end-to-end:
the in-repo fake plugin (``tests.fixtures.aegis_plugin_test``) ships
a tiny ``templates/{{ project_slug }}/...`` tree. This test installs
it into a synthetic project directory and verifies the rendered files
land at the right paths with ``{{ project_slug }}`` substituted.

This is the round-8a proof point for plugin distribution: a plugin's
own template files reach the project tree via the same Jinja2
machinery aegis-stack uses for its own templates.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from aegis.core.manual_updater import ManualUpdater

# Make sure the in-repo fake plugin is importable via importlib.resources.
TESTS_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
if str(TESTS_FIXTURES) not in sys.path:
    sys.path.insert(0, str(TESTS_FIXTURES))


COPIER_ANSWERS_TEMPLATE = """\
# Changes here will be overwritten by Copier; NEVER EDIT MANUALLY
project_name: Demo Project
project_slug: demo-project
include_database: false
_commit: None
_src_path: aegis/templates/copier-aegis-project
"""


@pytest.fixture
def fake_project(tmp_path: Path) -> Path:
    """A directory shaped like a Copier-generated Aegis project, just
    enough for ManualUpdater to bind to it. We don't need the project's
    own files for these tests — only the answers file and a project-slug
    name."""
    project = tmp_path / "demo-project"
    project.mkdir()
    (project / ".copier-answers.yml").write_text(COPIER_ANSWERS_TEMPLATE)
    return project


class TestInstallPluginTemplateTree:
    def test_renders_plugin_files_into_project(self, fake_project: Path) -> None:
        updater = ManualUpdater(fake_project)
        written = updater.install_plugin_template_tree("aegis_plugin_test")

        # Two .jinja files in the fake plugin: __init__.py.jinja +
        # service.py.jinja, both under app/services/test_plugin/.
        assert sorted(written) == sorted(
            [
                "app/services/test_plugin/__init__.py",
                "app/services/test_plugin/service.py",
            ]
        )

    def test_files_land_at_expected_paths(self, fake_project: Path) -> None:
        updater = ManualUpdater(fake_project)
        updater.install_plugin_template_tree("aegis_plugin_test")

        init_file = fake_project / "app/services/test_plugin/__init__.py"
        service_file = fake_project / "app/services/test_plugin/service.py"
        assert init_file.is_file()
        assert service_file.is_file()

    def test_jinja_rendered_with_project_answers(self, fake_project: Path) -> None:
        """The plugin template references ``{{ project_slug }}`` —
        confirm it was substituted with the project's actual slug."""
        updater = ManualUpdater(fake_project)
        updater.install_plugin_template_tree("aegis_plugin_test")

        init_content = (
            fake_project / "app/services/test_plugin/__init__.py"
        ).read_text()
        assert 'PLUGIN_NAME = "demo-project-test-plugin"' in init_content

        service_content = (
            fake_project / "app/services/test_plugin/service.py"
        ).read_text()
        assert 'project_slug = "demo-project"' in service_content

    def test_pure_code_plugin_returns_empty_list(self, fake_project: Path) -> None:
        """Plugins without a ``templates/`` dir (pure-code plugins —
        wiring data only) return an empty list and write nothing."""
        updater = ManualUpdater(fake_project)
        # ``json`` is a stdlib package without templates; resolver
        # returns None → install method short-circuits.
        written = updater.install_plugin_template_tree("json")
        assert written == []

    def test_overwrites_existing_files(self, fake_project: Path) -> None:
        """Re-running install on the same plugin overwrites — the test
        plugin's content should be deterministic, so the second run
        produces the same output."""
        updater = ManualUpdater(fake_project)
        updater.install_plugin_template_tree("aegis_plugin_test")
        first_content = (
            fake_project / "app/services/test_plugin/service.py"
        ).read_text()

        # Tamper with the file, then re-install.
        (fake_project / "app/services/test_plugin/service.py").write_text("tampered")
        updater.install_plugin_template_tree("aegis_plugin_test")

        second_content = (
            fake_project / "app/services/test_plugin/service.py"
        ).read_text()
        assert second_content == first_content
