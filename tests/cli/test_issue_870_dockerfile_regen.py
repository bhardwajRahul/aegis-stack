"""Regression tests for issue #870 — Dockerfile left stale by add/remove htmx.

The Dockerfile carries the htmx frontend's ``css-build`` stage (HF-09). Under
the old ``_WARN_ONLY`` policy the updater never rewrote it, so:

- ``aegis add htmx``    left the stage missing → the image ships no compiled
  CSS (degraded, unfingerprinted styling).
- ``aegis remove htmx`` left the stage present → ``COPY package.json`` points
  at a deleted file and ``docker build`` fails outright.

The fix regenerates the Dockerfile when it is still *pristine* (byte-identical
to the template default for the project's current configuration) and warns-only
once the user has actually hand-edited it — preserving the protection that
motivated the ``_WARN_ONLY`` exemption in the first place.
"""

from __future__ import annotations

import pytest

from aegis.constants import AnswerKeys
from aegis.core.manual_updater import ManualUpdater
from tests.cli.conftest import ProjectFactory

# Shares the shared-file regen path (ruff + git merge-file for diverged files),
# so it carries the same subprocess-contention flake risk as the #715 suites.
# Pin to the same xdist group to serialize it away from the fork-heavy stacks.
pytestmark = pytest.mark.xdist_group("generated_stacks")

DOCKERFILE = "Dockerfile"
CSS_BUILD_MARKER = "css-build"
CUSTOM_MARKER = "# PROJECT_CUSTOM_build_step_keep_me"


class TestPristineDockerfileRegenerated:
    """A pristine Dockerfile must track the htmx toggle in both directions."""

    def test_add_htmx_adds_css_build_stage(
        self, project_factory: ProjectFactory
    ) -> None:
        project = project_factory("base")
        dockerfile = project / DOCKERFILE
        assert CSS_BUILD_MARKER not in dockerfile.read_text()

        updater = ManualUpdater(project)
        updated_answers = {**updater.answers, AnswerKeys.include_key("htmx"): True}
        updated, _, need_merge = updater._regenerate_shared_files(updated_answers)

        assert CSS_BUILD_MARKER in dockerfile.read_text(), (
            "add htmx left the Dockerfile without its css-build stage (issue #870)"
        )
        assert DOCKERFILE in updated
        assert DOCKERFILE not in need_merge

    def test_remove_htmx_drops_css_build_stage(
        self, project_factory: ProjectFactory
    ) -> None:
        project = project_factory("base_htmx")
        dockerfile = project / DOCKERFILE
        assert CSS_BUILD_MARKER in dockerfile.read_text()

        updater = ManualUpdater(project)
        updated_answers = {**updater.answers, AnswerKeys.include_key("htmx"): False}
        updated, _, need_merge = updater._regenerate_shared_files(updated_answers)

        assert CSS_BUILD_MARKER not in dockerfile.read_text(), (
            "remove htmx left the css-build stage behind — docker build breaks "
            "on COPY of the deleted package.json (issue #870)"
        )
        assert DOCKERFILE in updated
        assert DOCKERFILE not in need_merge


class TestDivergedDockerfilePreserved:
    """A hand-edited Dockerfile keeps the ``_WARN_ONLY`` protection."""

    def test_diverged_dockerfile_is_preserved_and_warned(
        self, project_factory: ProjectFactory
    ) -> None:
        project = project_factory("base")
        dockerfile = project / DOCKERFILE
        dockerfile.write_text(dockerfile.read_text() + f"\n{CUSTOM_MARKER}\n")
        before = dockerfile.read_text()

        updater = ManualUpdater(project)
        updated_answers = {**updater.answers, AnswerKeys.include_key("htmx"): True}
        updated, _, need_merge = updater._regenerate_shared_files(updated_answers)

        assert dockerfile.read_text() == before, (
            "regen clobbered a hand-edited Dockerfile — the WARN_ONLY "
            "protection must survive (issue #870)"
        )
        assert CSS_BUILD_MARKER not in dockerfile.read_text()
        assert DOCKERFILE in need_merge
        assert DOCKERFILE not in updated
