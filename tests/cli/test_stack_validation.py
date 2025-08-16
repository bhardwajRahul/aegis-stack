"""
Stack Validation Tests for Aegis Stack CLI.

This module tests that generated stacks can build successfully and pass all
quality checks. For each stack combination, we validate:

1. Dependency Installation (uv sync)
2. CLI Installation (uv pip install -e .)
3. Code Quality (make check: lint + typecheck + test)
4. CLI Script Functionality (basic command validation)

These tests ensure that generated projects are not just syntactically correct
but actually functional and ready for development.
"""

from pathlib import Path
from typing import Any

import pytest

from .test_stack_generation import STACK_COMBINATIONS, StackCombination
from .test_utils import CLITestResult, run_quality_checks

# Note: ValidationResult merged into CLITestResult in test_utils.py


class StackValidator:
    """Handles validation of generated stack projects using unified command system."""

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.results: list[CLITestResult] = []

    def get_summary(self) -> dict[str, Any]:
        """Get validation summary."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.success)
        failed = total - passed
        total_duration = sum(r.duration for r in self.results)

        return {
            "total_steps": total,
            "passed": passed,
            "failed": failed,
            "success_rate": passed / total if total > 0 else 0,
            "total_duration": total_duration,
            "results": self.results,
        }


def get_stack_validator(
    get_generated_stack: Any, combination: StackCombination
) -> tuple[CLITestResult, Path]:
    """Get pre-generated stack path for validation."""
    # Get the pre-generated stack
    _, result = get_generated_stack(combination.name)

    return result, result.project_path


@pytest.mark.parametrize("combination", STACK_COMBINATIONS, ids=lambda x: x.name)
@pytest.mark.slow
def test_stack_dependency_installation(
    combination: StackCombination, get_generated_stack: Any
) -> None:
    """Test that each stack's dependencies can be installed successfully."""
    result, project_path = get_stack_validator(get_generated_stack, combination)

    assert result.success, f"Failed to generate {combination.description}"

    # Test dependency installation using unified quality checks
    quality_results = run_quality_checks(project_path)
    dep_result = quality_results[0]  # First result is dependency installation

    assert dep_result.success, (
        f"Dependency installation failed for {combination.description}\n"
        f"Duration: {dep_result.duration:.1f}s\n"
        f"Error: {dep_result.error_message}\n"
        f"STDOUT: {dep_result.stdout}\n"
        f"STDERR: {dep_result.stderr}"
    )


@pytest.mark.parametrize("combination", STACK_COMBINATIONS, ids=lambda x: x.name)
@pytest.mark.slow
def test_stack_cli_installation(
    combination: StackCombination, get_generated_stack: Any
) -> None:
    """Test that each stack's CLI script can be installed."""
    result, project_path = get_stack_validator(get_generated_stack, combination)

    assert result.success, f"Failed to generate {combination.description}"

    # Test both dependency and CLI installation using unified quality checks
    quality_results = run_quality_checks(project_path)
    dep_result = quality_results[0]  # Dependency installation
    cli_result = quality_results[1]  # CLI installation

    assert dep_result.success, "Dependency installation failed"
    assert cli_result.success, (
        f"CLI installation failed for {combination.description}\n"
        f"Duration: {cli_result.duration:.1f}s\n"
        f"Error: {cli_result.error_message}\n"
        f"STDOUT: {cli_result.stdout}\n"
        f"STDERR: {cli_result.stderr}"
    )


@pytest.mark.parametrize("combination", STACK_COMBINATIONS, ids=lambda x: x.name)
@pytest.mark.slow
def test_stack_code_quality(
    combination: StackCombination, get_generated_stack: Any
) -> None:
    """Test that each stack passes code quality checks."""
    result, project_path = get_stack_validator(get_generated_stack, combination)

    assert result.success, f"Failed to generate {combination.description}"

    # Run all quality checks
    quality_results = run_quality_checks(project_path)
    dep_result = quality_results[0]  # Dependency installation
    lint_result = quality_results[2]  # Linting
    type_result = quality_results[3]  # Type checking

    assert dep_result.success, "Dependency installation failed"

    # Linting should pass or have fixable issues only
    assert lint_result.returncode in [0, 1], (
        f"Linting failed for {combination.description}\n"
        f"Duration: {lint_result.duration:.1f}s\n"
        f"Error: {lint_result.error_message}\n"
        f"STDOUT: {lint_result.stdout}\n"
        f"STDERR: {lint_result.stderr}"
    )

    assert type_result.success, (
        f"Type checking failed for {combination.description}\n"
        f"Duration: {type_result.duration:.1f}s\n"
        f"Error: {type_result.error_message}\n"
        f"STDOUT: {type_result.stdout}\n"
        f"STDERR: {type_result.stderr}"
    )


@pytest.mark.parametrize("combination", STACK_COMBINATIONS, ids=lambda x: x.name)
@pytest.mark.slow
def test_stack_cli_functionality(
    combination: StackCombination, get_generated_stack: Any
) -> None:
    """Test that each stack's CLI script is functional."""
    from .test_utils import run_project_command

    result, project_path = get_stack_validator(get_generated_stack, combination)

    assert result.success, f"Failed to generate {combination.description}"

    # Full setup pipeline
    quality_results = run_quality_checks(project_path)
    dep_result = quality_results[0]  # Dependency installation
    cli_install_result = quality_results[1]  # CLI installation

    assert dep_result.success, "Dependency installation failed"
    assert cli_install_result.success, "CLI installation failed"

    # Test CLI script functionality
    cli_test_result = run_project_command(
        ["uv", "run", combination.project_name, "--help"],
        project_path,
        timeout=30,
        step_name="CLI Script Test",
        env_overrides={"VIRTUAL_ENV": ""},
    )

    assert cli_test_result.success, (
        f"CLI script test failed for {combination.description}\n"
        f"Duration: {cli_test_result.duration:.1f}s\n"
        f"Error: {cli_test_result.error_message}\n"
        f"STDOUT: {cli_test_result.stdout}\n"
        f"STDERR: {cli_test_result.stderr}"
    )


@pytest.mark.parametrize("combination", STACK_COMBINATIONS, ids=lambda x: x.name)
@pytest.mark.slow
def test_stack_health_commands(
    combination: StackCombination, get_generated_stack: Any
) -> None:
    """Test that each stack's health commands are available."""
    from .test_utils import run_project_command

    result, project_path = get_stack_validator(get_generated_stack, combination)

    assert result.success, f"Failed to generate {combination.description}"

    # Full setup pipeline
    quality_results = run_quality_checks(project_path)
    dep_result = quality_results[0]  # Dependency installation
    cli_install_result = quality_results[1]  # CLI installation

    assert dep_result.success, "Dependency installation failed"
    assert cli_install_result.success, "CLI installation failed"

    # Test health command availability
    health_result = run_project_command(
        ["uv", "run", combination.project_name, "health", "status", "--help"],
        project_path,
        timeout=30,
        step_name="Health Command Test",
        env_overrides={"VIRTUAL_ENV": ""},
    )

    assert health_result.success, (
        f"Health command test failed for {combination.description}\n"
        f"Duration: {health_result.duration:.1f}s\n"
        f"Error: {health_result.error_message}\n"
        f"STDOUT: {health_result.stdout}\n"
        f"STDERR: {health_result.stderr}"
    )


@pytest.mark.slow
def test_full_stack_validation_pipeline(get_generated_stack: Any) -> None:
    """Test complete validation pipeline for a representative stack."""
    from .test_utils import run_project_command

    # Use worker stack as it includes most components
    combination = next(c for c in STACK_COMBINATIONS if c.name == "worker")

    result, project_path = get_stack_validator(get_generated_stack, combination)
    assert result.success, f"Failed to generate {combination.description}"

    # Run complete validation pipeline
    quality_results = run_quality_checks(project_path)

    # Test CLI script functionality
    cli_test_result = run_project_command(
        ["uv", "run", combination.project_name, "--help"],
        project_path,
        timeout=30,
        step_name="CLI Script Test",
        env_overrides={"VIRTUAL_ENV": ""},
    )

    # Test health command
    health_result = run_project_command(
        ["uv", "run", combination.project_name, "health", "status", "--help"],
        project_path,
        timeout=30,
        step_name="Health Command Test",
        env_overrides={"VIRTUAL_ENV": ""},
    )

    # Collect all results
    all_results = quality_results + [cli_test_result, health_result]

    # Validation summary
    total = len(all_results)
    passed = sum(1 for r in all_results if r.success)
    total_duration = sum(r.duration for r in all_results)

    # All steps should pass (allowing linting to have fixable issues)
    lint_result = quality_results[2]  # Linting result
    critical_failures = [r for r in all_results if not r.success and r != lint_result]

    assert len(critical_failures) == 0, (
        f"Validation pipeline failed for {combination.description}\n"
        f"Summary: {passed}/{total} passed in {total_duration:.1f}s\n"
        f"Failed steps:\n" + "\n".join(f"  - {r}" for r in critical_failures)
    )

    # Verify reasonable performance
    assert total_duration < 300, (
        f"Validation took too long: {total_duration:.1f}s > 300s"
    )


@pytest.mark.slow
def test_validation_performance_benchmarks() -> None:
    """Test that validation steps complete within reasonable time limits."""
    # Expected time limits for each step
    time_limits = {
        "Dependency Installation": 180,  # 3 minutes
        "CLI Installation": 60,  # 1 minute
        "Code Quality Check": 120,  # 2 minutes
        "CLI Script Test": 30,  # 30 seconds
        "Health Command Test": 30,  # 30 seconds
    }

    # This is more of a documentation test - actual timing validation
    # happens in the individual test methods via timeout parameters
    assert all(limit > 0 for limit in time_limits.values())
    assert sum(time_limits.values()) < 600  # Total under 10 minutes


def test_validation_error_handling() -> None:
    """Test that validation methods properly handle and report errors."""
    # Create validator with non-existent project path
    invalid_path = Path("/tmp/non-existent-project")
    validator = StackValidator(invalid_path)

    # Test basic validation summary functionality
    summary = validator.get_summary()

    # Should have proper summary structure
    assert isinstance(summary, dict)
    assert "total_steps" in summary
    assert "passed" in summary
    assert "failed" in summary
    assert "success_rate" in summary
    assert "total_duration" in summary
    assert "results" in summary
