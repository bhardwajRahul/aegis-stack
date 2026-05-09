"""Unit tests for pure helpers in ``aegis.commands.deploy``.

Pins regressions caught during the deploy-cd-setup PR review:
- ``_detect_github_repo`` must accept repo names containing dots (``next.js``)
  and strip optional ``.git`` / trailing slashes across SSH and HTTPS forms.
- ``_render_deploy_workflow`` must conditionally inject the
  ``uv python install`` step and the tag-push trigger.
- ``_project_python_minor`` must extract major.minor from a
  ``requires-python`` constraint and degrade gracefully when missing.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

from aegis.commands.deploy import (
    _detect_github_repo,
    _project_python_minor,
    _render_deploy_workflow,
)


def _git_init_with_origin(path: Path, remote: str) -> None:
    subprocess.run(["git", "-C", str(path), "init", "-q"], check=True)
    subprocess.run(
        ["git", "-C", str(path), "remote", "add", "origin", remote], check=True
    )


@pytest.mark.parametrize(
    "remote,expected",
    [
        ("git@github.com:lbedner/aegis-stack.git", "lbedner/aegis-stack"),
        ("https://github.com/lbedner/aegis-stack.git", "lbedner/aegis-stack"),
        ("https://github.com/lbedner/aegis-stack", "lbedner/aegis-stack"),
        ("https://github.com/foo/bar/", "foo/bar"),
    ],
)
def test_detect_github_repo_parses_common_forms(
    tmp_path: Path, remote: str, expected: str
) -> None:
    _git_init_with_origin(tmp_path, remote)
    assert _detect_github_repo(tmp_path) == expected


@pytest.mark.parametrize(
    "remote",
    [
        "git@github.com:vercel/next.js.git",
        "https://github.com/vercel/next.js.git",
        "https://github.com/vercel/next.js",
    ],
)
def test_detect_github_repo_handles_dotted_repo_names(
    tmp_path: Path, remote: str
) -> None:
    _git_init_with_origin(tmp_path, remote)
    assert _detect_github_repo(tmp_path) == "vercel/next.js"


def test_detect_github_repo_returns_none_for_non_github(tmp_path: Path) -> None:
    _git_init_with_origin(tmp_path, "git@gitlab.com:foo/bar.git")
    assert _detect_github_repo(tmp_path) is None


def test_detect_github_repo_returns_none_when_not_a_repo(tmp_path: Path) -> None:
    assert _detect_github_repo(tmp_path) is None


def test_render_deploy_workflow_default_is_workflow_dispatch_only() -> None:
    out = _render_deploy_workflow(on_tag=False)
    yaml.safe_load(out)  # validate structure
    # YAML 1.1 parses bare "on:" as boolean True, so we assert on text.
    assert "workflow_dispatch:" in out
    assert "push:" not in out


def test_render_deploy_workflow_on_tag_adds_v_star_trigger() -> None:
    out = _render_deploy_workflow(on_tag=True)
    yaml.safe_load(out)
    assert "workflow_dispatch:" in out
    assert "push:" in out
    assert "- 'v*'" in out


def test_render_deploy_workflow_pins_python_when_version_provided() -> None:
    out = _render_deploy_workflow(on_tag=False, python_version="3.13")
    yaml.safe_load(out)  # must remain valid YAML
    assert "uv python install 3.13" in out


def test_render_deploy_workflow_omits_python_step_when_none() -> None:
    out = _render_deploy_workflow(on_tag=False, python_version=None)
    yaml.safe_load(out)
    assert "uv python install" not in out


def test_render_deploy_workflow_references_required_secrets() -> None:
    out = _render_deploy_workflow(on_tag=False)
    assert "${{ secrets.DEPLOY_SSH_KEY }}" in out
    assert "${{ secrets.DEPLOY_HOST }}" in out


def test_project_python_minor_parses_requires_python(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nrequires-python = ">=3.13,<3.15"\n'
    )
    assert _project_python_minor(tmp_path) == "3.13"


def test_project_python_minor_returns_none_for_missing_pyproject(
    tmp_path: Path,
) -> None:
    assert _project_python_minor(tmp_path) is None


def test_project_python_minor_returns_none_when_constraint_missing(
    tmp_path: Path,
) -> None:
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "foo"\n')
    assert _project_python_minor(tmp_path) is None


def test_project_python_minor_returns_none_for_malformed_toml(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("this is = not :: valid toml [")
    assert _project_python_minor(tmp_path) is None
