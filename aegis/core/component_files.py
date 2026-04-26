"""
Component file tracking infrastructure.

This module provides functionality to identify which files belong to which
components by parsing the Copier template's exclusion rules.
"""

import re
from pathlib import Path
from typing import Any

import yaml

# Constants
PROJECT_SLUG_PLACEHOLDER = "{{ project_slug }}"
JINJA_EXTENSION = ".jinja"


def get_template_path() -> Path:
    """Get path to Copier template directory."""
    return Path(__file__).parent.parent / "templates" / "copier-aegis-project"


def load_copier_config() -> dict[str, Any]:
    """
    Load copier.yml configuration.

    Returns:
        Dictionary containing Copier template configuration

    Raises:
        FileNotFoundError: If copier.yml doesn't exist
        yaml.YAMLError: If copier.yml is invalid
    """
    # copier.yml is now at repo root (aegis-stack/copier.yml)
    # not in the template subdirectory
    repo_root = Path(__file__).parent.parent.parent
    copier_yml = repo_root / "copier.yml"

    if not copier_yml.exists():
        raise FileNotFoundError(f"copier.yml not found at {copier_yml}")

    try:
        with open(copier_yml) as f:
            return yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Failed to parse copier.yml: {e}") from e


def get_copier_defaults() -> dict[str, Any]:
    """
    Extract default values for all template variables from copier.yml.

    Used by ManualUpdater to backfill missing answer keys before rendering
    templates. Without this, undefined variables like ``ollama_mode`` cause
    Jinja2 conditionals to inject unrelated component code (#504).

    Returns:
        Dictionary mapping variable names to their default values.
        Skips Jinja2-expression defaults (they depend on other variables).
        Returns empty dict if copier.yml is not available (e.g. pip install).
    """
    try:
        config = load_copier_config()
    except FileNotFoundError:
        # copier.yml lives at repo root, not inside the aegis/ package.
        # When installed via pip/uvx the file won't exist — fall back
        # gracefully so ManualUpdater behaves the same as before this fix.
        return {}

    defaults: dict[str, Any] = {}

    for key, value in config.items():
        # Skip private/internal Copier keys (e.g. _min_copier_version)
        if key.startswith("_"):
            continue

        if isinstance(value, dict) and "default" in value:
            default = value["default"]
            # Skip Jinja2 expression defaults — they depend on other variables
            # and the answers file should already have them when relevant
            if isinstance(default, str) and "{{" in default:
                continue
            defaults[key] = default

    return defaults


def parse_exclusion_pattern(pattern: str, component: str) -> str | None:
    """
    Parse a Jinja2 exclusion pattern to extract the file path for a component.

    Args:
        pattern: Jinja2 pattern like "{% if not include_scheduler %}path/to/file{% endif %}"
        component: Component name to match (e.g., "scheduler", "worker")

    Returns:
        Extracted file path, or None if pattern doesn't match the component

    Examples:
        >>> parse_exclusion_pattern(
        ...     "{% if not include_scheduler %}{{ project_slug }}/app/components/scheduler{% endif %}",
        ...     "scheduler"
        ... )
        "app/components/scheduler"

        >>> parse_exclusion_pattern(
        ...     "{% if scheduler_backend == 'memory' -%}{{ project_slug }}/app/services/scheduler{% endif %}",
        ...     "scheduler"
        ... )
        "app/services/scheduler"
    """
    # Check if pattern references this component
    if f"include_{component}" not in pattern and component not in pattern:
        return None

    # Extract path from pattern
    # Patterns look like: "{% if condition %}{{ project_slug }}/path/to/file{% endif %}"
    # We want to extract: "path/to/file"

    # Match: {% if ... %}...{{ project_slug }}/PATH{% endif %}
    match = re.search(
        r"\{%\s*if\s+.+?\s*%\}\{\{\s*project_slug\s*\}\}/(.+?)\{%\s*endif\s*%\}",
        pattern,
    )

    if match:
        # Remove any trailing wildcards or special characters
        path = match.group(1).rstrip("*")
        return path

    return None


def _expand_directories_to_files(paths: list[str]) -> list[str]:
    """
    Expand directory paths to include all nested files.

    For each directory path, recursively discover all files within it
    by scanning the template directory.

    Args:
        paths: List of file/directory paths (e.g., ["app/components/scheduler", "app/core/db.py"])

    Returns:
        Expanded list with all nested files discovered

    Example:
        >>> _expand_directories_to_files(["app/components/scheduler"])
        ["app/components/scheduler/__init__.py", "app/components/scheduler/main.py"]
    """
    template_path = get_template_path()
    expanded_paths: list[str] = []

    for path in paths:
        # Full path in template: template/{{ project_slug }}/path
        template_dir = template_path / PROJECT_SLUG_PLACEHOLDER / path

        if template_dir.exists() and template_dir.is_dir():
            # Recursively find all files in this directory
            for file_path in template_dir.rglob("*"):
                if file_path.is_file():
                    # Convert back to relative path
                    # /path/to/template/{{ project_slug }}/app/components/scheduler/main.py.jinja
                    # -> app/components/scheduler/main.py.jinja
                    relative_path = file_path.relative_to(
                        template_path / PROJECT_SLUG_PLACEHOLDER
                    )

                    # Remove .jinja extension for the final path
                    path_str = str(relative_path)
                    if path_str.endswith(JINJA_EXTENSION):
                        path_str = path_str[: -len(JINJA_EXTENSION)]

                    expanded_paths.append(path_str)
        else:
            # Not a directory or doesn't exist - keep as-is (it's a file path)
            expanded_paths.append(path)

    return expanded_paths


def get_component_files(
    component: str, backend_variant: str | None = None
) -> list[str]:
    """
    Get list of file paths that belong to a component.

    Uses the centralized component file mapping from post_gen_tasks.py
    to ensure consistency between generation and updates.

    Args:
        component: Component name (e.g., "scheduler", "worker", "database")
        backend_variant: Optional backend variant (e.g., "memory", "sqlite") for scheduler

    Returns:
        List of file paths relative to project root

    Examples:
        >>> get_component_files("scheduler")
        ['app/components/scheduler', 'app/entrypoints/scheduler.py', ...]

        >>> get_component_files("scheduler", "sqlite")
        ['app/services/scheduler', 'app/cli/tasks.py', ...]
    """
    from .post_gen_tasks import get_component_file_mapping

    mapping = get_component_file_mapping()

    # Get base component files
    component_files = mapping.get(component, []).copy()

    # For scheduler, handle backend variants
    if component == "scheduler" and backend_variant == "sqlite":
        # Add persistence files for sqlite backend
        persistence_files = mapping.get("scheduler_persistence", [])
        component_files.extend(persistence_files)

    # Expand directories to include all nested files
    component_files = _expand_directories_to_files(component_files)

    return sorted(set(component_files))


def get_all_component_files() -> dict[str, list[str]]:
    """
    Get file mappings for all components.

    Returns:
        Dictionary mapping component names to their file paths

    Example:
        >>> files = get_all_component_files()
        >>> files["scheduler"]
        ['app/components/scheduler', 'app/entrypoints/scheduler.py', ...]
    """
    # List of known components and services (from copier.yml variables)
    # Uses constants where available via ComponentNames and AnswerKeys
    from ..constants import AnswerKeys, ComponentNames

    components = [
        ComponentNames.SCHEDULER,
        ComponentNames.WORKER,
        ComponentNames.DATABASE,
        AnswerKeys.SERVICE_AUTH,
        AnswerKeys.SERVICE_AI,
        ComponentNames.OBSERVABILITY,
    ]

    result: dict[str, list[str]] = {}

    for component in components:
        files = get_component_files(component)
        if files:
            result[component] = files

    # Add scheduler backend variants
    result["scheduler_memory"] = get_component_files("scheduler", "memory")
    result["scheduler_sqlite"] = get_component_files("scheduler", "sqlite")

    return result


def get_service_files(service: str) -> list[str]:
    """
    Get list of file paths that belong to a service.

    Services are components that provide business logic (auth, ai).
    This is an alias for get_component_files for clarity.

    Args:
        service: Service name (e.g., "auth", "ai")

    Returns:
        List of file paths relative to project root
    """
    return get_component_files(service)
