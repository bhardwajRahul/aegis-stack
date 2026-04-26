"""
Model Import Validation Tests for Aegis Stack CLI.

This module tests that generated projects contain the correct model classes
in app.components.backend.api.models, ensuring that template conditional logic
doesn't accidentally exclude models needed by components.

These tests catch issues where models are incorrectly nested under conditional
blocks that don't match the components that need them.
"""

import ast
from pathlib import Path
from typing import Any

import pytest

from .test_stack_generation import STACK_COMBINATIONS, StackCombination


def _get_expected_models_for_combination(combination: StackCombination) -> list[str]:
    """Get expected model classes for a given component combination."""
    expected_models = []

    # Worker-specific models
    if "worker" in combination.components:
        expected_models.extend(
            [
                "TaskRequest",
                "TaskResponse",
                "TaskListResponse",
                "TaskStatusResponse",
                "TaskResultResponse",
                "LoadTestRequest",
                "LoadTestStatus",
                "LoadTestResults",
            ]
        )

    # Scheduler-specific models (only when scheduler backend != memory)
    if "scheduler" in combination.components:
        # Note: scheduler models only exist when scheduler_backend != "memory"
        # For default memory backend, no scheduler models are generated
        pass

    return expected_models


def _get_models_in_file(models_file: Path) -> list[str]:
    """Extract all model class names from the models.py file."""
    if not models_file.exists():
        return []

    try:
        with open(models_file) as f:
            content = f.read()

        # Parse the file to extract class definitions
        tree = ast.parse(content)
        model_classes = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                model_classes.append(node.name)

        return model_classes

    except Exception as e:
        pytest.fail(f"Failed to parse models file: {e}")
        return []


def _validate_models_file_exists_with_content(
    project_path: Path, expected_models: list[str]
) -> bool:
    """Check if the models.py file exists and has expected content."""
    models_file = project_path / "app" / "components" / "backend" / "api" / "models.py"

    if not expected_models:
        # If no models expected, file should either not exist or be minimal
        return True

    if not models_file.exists():
        return False

    # Check if file has meaningful content
    actual_models = _get_models_in_file(models_file)
    return len(actual_models) > 0


def get_stack_validator(
    get_generated_stack: Any, combination: StackCombination
) -> tuple[Any, Path]:
    """Get pre-generated stack path for validation."""
    # Get the pre-generated stack
    _, result = get_generated_stack(combination.name)

    return result, result.project_path


@pytest.mark.parametrize("combination", STACK_COMBINATIONS, ids=lambda x: x.name)
def test_model_classes_generated(
    combination: StackCombination, get_generated_stack: Any
) -> None:
    """Test that expected model classes are generated in projects."""
    result, project_path = get_stack_validator(get_generated_stack, combination)

    assert result.success, f"Failed to generate {combination.description}"

    # Get expected and actual models
    expected_models = _get_expected_models_for_combination(combination)
    models_file = project_path / "app" / "components" / "backend" / "api" / "models.py"
    actual_models = _get_models_in_file(models_file)

    # If worker components are included, we should have worker models
    if "worker" in combination.components:
        assert models_file.exists(), (
            f"Models file should exist for {combination.description} with worker"
        )

        # Check that all expected worker models are present
        missing_models = [
            model for model in expected_models if model not in actual_models
        ]
        assert not missing_models, (
            f"Missing worker models in {combination.description}:\n"
            f"Missing: {missing_models}\n"
            f"Expected: {expected_models}\n"
            f"Actual: {actual_models}\n"
            f"This suggests worker models are nested under scheduler conditionals"
        )
    else:
        # If no worker component, we shouldn't have worker models
        worker_models_present = [
            model
            for model in actual_models
            if model in ["TaskRequest", "TaskResponse", "LoadTestRequest"]
        ]
        assert not worker_models_present, (
            f"Unexpected worker models in {combination.description} (no worker):\n"
            f"Found: {worker_models_present}"
        )


@pytest.mark.parametrize(
    "combination",
    [c for c in STACK_COMBINATIONS if "worker" in c.components],
    ids=lambda x: x.name,
)
def test_worker_critical_models_present(
    combination: StackCombination, get_generated_stack: Any
) -> None:
    """Test that worker components have all critical models they need."""
    result, project_path = get_stack_validator(get_generated_stack, combination)

    assert result.success, f"Failed to generate {combination.description}"

    # These are the critical models that worker.py specifically imports
    critical_models = [
        "LoadTestRequest",
        "TaskListResponse",
        "TaskRequest",
        "TaskResponse",
        "TaskResultResponse",
        "TaskStatusResponse",
    ]

    models_file = project_path / "app" / "components" / "backend" / "api" / "models.py"
    actual_models = _get_models_in_file(models_file)

    missing_critical_models = [
        model for model in critical_models if model not in actual_models
    ]

    assert not missing_critical_models, (
        f"Critical worker models missing in {combination.description}:\n"
        f"Missing: {missing_critical_models}\n"
        f"Available models: {actual_models}\n"
        f"This indicates that worker models are missing from the generated models.py\n"
        f"Check that worker models are placed in template conditional blocks"
    )


def test_worker_only_project_has_models(
    project_factory: Any,
) -> None:
    """Specific test for worker-only projects to catch conditional nesting issues."""
    # This test specifically targets the issue we just fixed where worker models
    # were nested under scheduler conditionals

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        pass

    # Use cached worker project
    project_path = project_factory("base_with_worker")

    # Check that critical worker models exist
    models_file = project_path / "app" / "components" / "backend" / "api" / "models.py"
    actual_models = _get_models_in_file(models_file)

    critical_models = ["LoadTestRequest", "TaskRequest"]
    missing_models = [model for model in critical_models if model not in actual_models]

    assert not missing_models, (
        f"Worker-only project missing critical models:\n"
        f"Missing: {missing_models}\n"
        f"Available: {actual_models}\n"
        "This suggests worker models are still nested under scheduler conditionals"
    )
