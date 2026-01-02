import subprocess
from typing import Any

import pytest


def pytest_configure(config: Any) -> None:
    """Configure git for CI environments.

    This ensures git user.name and user.email are set globally,
    which is required for project generation tests that run git commit.
    """
    subprocess.run(
        ["git", "config", "--global", "user.name", "Aegis Test"],
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "--global", "user.email", "test@aegis-stack.dev"],
        capture_output=True,
    )


def pytest_addoption(parser: Any) -> None:
    """Add custom pytest options."""
    parser.addoption(
        "--runslow",
        action="store_true",
        default=False,
        help="run slow tests (CLI integration tests with project generation)",
    )


@pytest.fixture
def skip_slow_tests(request: Any) -> None:
    """Skip tests marked as slow unless --runslow is passed."""
    if request.config.getoption("--runslow"):
        return
    pytest.skip("need --runslow option to run")
