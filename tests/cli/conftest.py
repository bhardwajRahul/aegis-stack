"""
Pytest configuration for CLI integration tests.
"""

from collections.abc import Generator
from pathlib import Path
import tempfile
from typing import Any

import pytest

from .test_stack_generation import STACK_COMBINATIONS, StackCombination
from .test_utils import CLITestResult, run_aegis_init


@pytest.fixture(scope="session")
def cli_test_timeout() -> int:
    """Default timeout for CLI commands."""
    return 60  # seconds


@pytest.fixture
def temp_output_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test project generation."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture(scope="session")
def session_temp_dir() -> Generator[Path, None, None]:
    """Create a session-scoped temporary directory for shared stack generation."""
    with tempfile.TemporaryDirectory(prefix="aegis-test-session-") as temp_dir:
        yield Path(temp_dir)


@pytest.fixture(scope="session")
def generated_stacks(
    session_temp_dir: Path,
) -> dict[str, tuple[StackCombination, CLITestResult]]:
    """
    Generate all stack combinations once per test session.

    This dramatically reduces test time by avoiding duplicate stack generation.
    Returns a dict mapping stack names to (combination, result) tuples.
    """
    stacks = {}

    print(f"\n🏗️  Generating {len(STACK_COMBINATIONS)} stacks for session...")

    for combination in STACK_COMBINATIONS:
        print(f"   - Generating {combination.name} stack...")

        result = run_aegis_init(
            combination.project_name,
            combination.components,
            session_temp_dir,
            timeout=60,
        )

        if not result.success:
            raise RuntimeError(
                f"Failed to generate {combination.name} stack for test session:\n"
                f"STDOUT: {result.stdout}\n"
                f"STDERR: {result.stderr}"
            )

        stacks[combination.name] = (combination, result)

    print(f"✅ All {len(stacks)} stacks generated successfully!")
    return stacks


@pytest.fixture
def get_generated_stack(
    generated_stacks: dict[str, tuple[StackCombination, CLITestResult]],
) -> Any:
    """Helper to get a specific generated stack by name."""

    def _get_stack(name: str) -> tuple[StackCombination, CLITestResult]:
        if name not in generated_stacks:
            raise KeyError(
                f"Stack '{name}' not found. Available: {list(generated_stacks.keys())}"
            )
        return generated_stacks[name]

    return _get_stack
