"""
Test Copier template conditional logic for Redis configuration.

This test validates that the .env.example.jinja template correctly includes
Redis configuration when include_redis=true (boolean), not when it equals "yes" (string).

This is a regression test for the boolean vs string comparison bug.
"""

from pathlib import Path

import pytest

from aegis.core.manual_updater import ManualUpdater


def test_copier_redis_conditional_uses_boolean_logic(tmp_path: Path) -> None:
    """
    Verify .env.example.jinja uses boolean conditional logic for Redis section.

    The template should use: {% if include_redis or include_cache %}
    NOT: {% if include_redis == "yes" or include_cache == "yes" %}

    Copier uses boolean values (true/false), not strings ("yes"/"no").
    """
    template_file = (
        Path(__file__).parent.parent
        / "aegis"
        / "templates"
        / "copier-aegis-project"
        / "{{ project_slug }}"
        / ".env.example.jinja"
    )

    assert template_file.exists(), f"Template file not found: {template_file}"

    content = template_file.read_text()

    # Verify Redis section uses boolean logic
    assert "{% if include_redis or include_cache %}" in content, (
        "Redis section should use: {% if include_redis or include_cache %}"
    )

    # Ensure it doesn't use string comparison (the bug)
    assert 'include_redis == "yes"' not in content, (
        'Redis section should NOT use: include_redis == "yes" (string comparison)'
    )

    assert 'include_cache == "yes"' not in content, (
        'Redis section should NOT use: include_cache == "yes" (string comparison)'
    )


def test_copier_worker_conditional_uses_boolean_logic(tmp_path: Path) -> None:
    """
    Verify .env.example.jinja uses boolean conditional logic for worker section.

    The template should use: {% if include_worker %}
    NOT: {% if include_worker == "yes" %}
    """
    template_file = (
        Path(__file__).parent.parent
        / "aegis"
        / "templates"
        / "copier-aegis-project"
        / "{{ project_slug }}"
        / ".env.example.jinja"
    )

    assert template_file.exists(), f"Template file not found: {template_file}"

    content = template_file.read_text()

    # Verify worker section uses boolean logic (accept whitespace control variants)
    has_worker_boolean = (
        "{% if include_worker %}" in content or "{%- if include_worker %}" in content
    )
    assert has_worker_boolean, (
        "Worker section should use boolean logic: "
        "{% if include_worker %} or {%- if include_worker %}"
    )

    # Ensure it doesn't use string comparison
    assert 'include_worker == "yes"' not in content, (
        'Worker section should NOT use: include_worker == "yes" (string comparison)'
    )


def test_copier_all_conditionals_use_boolean_logic(tmp_path: Path) -> None:
    """
    Comprehensive check: ensure NO Copier templates use string comparisons.

    This catches any remaining "== 'yes'" or '== "yes"' patterns in Copier templates.
    """
    template_dir = (
        Path(__file__).parent.parent / "aegis" / "templates" / "copier-aegis-project"
    )

    assert template_dir.exists(), f"Template directory not found: {template_dir}"

    violations: list[tuple[Path, int, str]] = []

    # Check all .jinja files
    for jinja_file in template_dir.rglob("*.jinja"):
        content = jinja_file.read_text()
        lines = content.split("\n")

        for line_num, line in enumerate(lines, start=1):
            # Check for string comparison patterns
            if '== "yes"' in line or "== 'yes'" in line:
                violations.append((jinja_file, line_num, line.strip()))

    if violations:
        error_msg = (
            "Found string comparisons in Copier templates (should use boolean logic):\n"
        )
        for file_path, line_num, line_content in violations:
            rel_path = file_path.relative_to(template_dir)
            error_msg += f"  {rel_path}:{line_num}: {line_content}\n"

        pytest.fail(error_msg)


def test_extract_env_vars_handles_commented_variables() -> None:
    """
    Test that _extract_env_vars() correctly extracts both commented and active variables.

    This is a regression test for the bug where commented variables were unreachable
    due to incorrect conditional ordering (checking startswith("#") before checking
    for commented variable definitions).
    """
    # Create a mock ManualUpdater (we only need the _extract_env_vars method)
    # We'll test it directly without needing a real project
    updater = object.__new__(ManualUpdater)

    # Sample .env.example content with both commented and active variables
    env_content = """
# Redis settings
REDIS_URL=redis://redis:6379
REDIS_URL_LOCAL=redis://localhost:6379

# Redis connection settings (for high-load scenarios)
# REDIS_CONN_TIMEOUT=5  # Connection timeout in seconds
# REDIS_CONN_RETRIES=5  # Number of connection retry attempts
# REDIS_CONN_RETRY_DELAY=1  # Delay between retries in seconds

# This is just a comment without a variable
# Another comment

# Active variable
DATABASE_URL=sqlite:///./data/app.db
"""

    result = updater._extract_env_vars(env_content)

    # Verify active variables are extracted
    assert "REDIS_URL" in result
    assert result["REDIS_URL"] == "redis://redis:6379"

    assert "REDIS_URL_LOCAL" in result
    assert result["REDIS_URL_LOCAL"] == "redis://localhost:6379"

    assert "DATABASE_URL" in result
    assert result["DATABASE_URL"] == "sqlite:///./data/app.db"

    # Verify commented variables are extracted (THE CRITICAL BUG FIX)
    assert "REDIS_CONN_TIMEOUT" in result
    assert result["REDIS_CONN_TIMEOUT"] == "5  # Connection timeout in seconds"

    assert "REDIS_CONN_RETRIES" in result
    assert result["REDIS_CONN_RETRIES"] == "5  # Number of connection retry attempts"

    assert "REDIS_CONN_RETRY_DELAY" in result
    assert result["REDIS_CONN_RETRY_DELAY"] == "1  # Delay between retries in seconds"

    # Total should be 6 variables (3 active + 3 commented)
    assert len(result) == 6
