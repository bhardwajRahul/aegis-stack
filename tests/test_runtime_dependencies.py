"""Guards on [project].dependencies — what an installed aegis-stack can rely on.

Dev extras exist only in this repo's venv. Anything the CLI shells out to at
RUNTIME (uvx / pip installs, no extras) must be a runtime dependency, or the
feature silently degrades in production while every local test passes.
"""

import tomllib
from pathlib import Path

from packaging.requirements import Requirement

PYPROJECT = Path(__file__).parent.parent / "pyproject.toml"


def _runtime_dependencies() -> list[str]:
    with PYPROJECT.open("rb") as handle:
        return tomllib.load(handle)["project"]["dependencies"]


def test_ruff_is_a_runtime_dependency() -> None:
    """The updater's 3-way merges shell out to ruff at runtime.

    ``template_cleanup.run_ruff_on_text`` (used by both the version-update
    sync and the ManualUpdater add/remove path, issue #715) needs a ruff
    binary in the installed environment. When it is only a dev extra, a
    uvx-installed CLI finds no ruff, every Python merge degrades to the raw
    byte-level path, and pristine projects get spurious update conflicts —
    exactly what the 0.9.0 -> 0.9.1rc3 TestPyPI upgrade test caught.
    """
    assert any(Requirement(dep).name == "ruff" for dep in _runtime_dependencies()), (
        "ruff must be declared in [project].dependencies, not only the dev "
        "extra: aegis update / add-service merge correctness depends on it"
    )
