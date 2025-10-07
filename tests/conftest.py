from typing import Any

import pytest


def pytest_addoption(parser: Any) -> None:
    """Add custom pytest options."""
    parser.addoption(
        "--runslow",
        action="store_true",
        default=False,
        help="run slow tests (CLI integration tests with project generation)",
    )
    parser.addoption(
        "--engine",
        action="store",
        default=None,
        help="template engine to test (cookiecutter, copier, or both)",
    )


@pytest.fixture
def skip_slow_tests(request: Any) -> None:
    """Skip tests marked as slow unless --runslow is passed."""
    if request.config.getoption("--runslow"):
        return
    pytest.skip("need --runslow option to run")


@pytest.fixture
def skip_copier_tests(request: Any, engine: str) -> None:
    """
    Skip Copier engine tests until template is fixed (Ticket #128).

    Copier template is incomplete (missing conditional _exclude patterns),
    so tests with Copier engine are skipped by default until the template
    is fixed in ticket #128.
    """
    if engine == "copier":
        pytest.skip(
            "Copier template migration incomplete - missing conditional _exclude "
            "patterns (see ticket #128)"
        )
