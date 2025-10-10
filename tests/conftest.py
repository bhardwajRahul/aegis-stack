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
    Copier engine tests are now enabled (Ticket #128 resolved).

    The conditional file exclusion is now handled by cleanup_components()
    in post_gen_tasks.py, ensuring consistent behavior between Cookiecutter
    and Copier template engines.
    """
    # Tests no longer skipped - Copier template is working
    pass
