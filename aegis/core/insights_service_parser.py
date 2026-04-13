"""
Insights service bracket syntax parser.

Parses insights[sources...] syntax where values are data source names:
- github: GitHub Traffic API + Stargazers API
- pypi: PyPI/pepy.tech download stats
- plausible: Plausible docs analytics
- reddit: Reddit post tracking

Order doesn't matter. Defaults: github, pypi
"""

from dataclasses import dataclass, field

# Valid source names
SOURCES = {"github", "pypi", "plausible", "reddit"}

# Default sources when no brackets specified
DEFAULT_SOURCES = ["github", "pypi"]


@dataclass
class InsightsServiceConfig:
    """Parsed insights service configuration."""

    sources: list[str] = field(default_factory=lambda: DEFAULT_SOURCES.copy())


def parse_insights_service_config(service_string: str) -> InsightsServiceConfig:
    """
    Parse insights[...] service string into config.

    Args:
        service_string: Service specification like "insights", "insights[github]",
                        or "insights[github,pypi,plausible,reddit]"

    Returns:
        InsightsServiceConfig with selected sources

    Raises:
        ValueError: If service string is invalid or has unknown values
    """
    service_string = service_string.strip()

    if not service_string.startswith("insights"):
        raise ValueError(
            f"Expected 'insights' service, got '{service_string}'. "
            "This parser only handles insights[...] syntax."
        )

    # Plain "insights" with no brackets
    if service_string == "insights":
        return InsightsServiceConfig()

    if "[" not in service_string:
        raise ValueError(
            f"Invalid service string '{service_string}'. "
            "Expected 'insights' or 'insights[sources]' format."
        )

    if not service_string.endswith("]"):
        raise ValueError(
            f"Malformed brackets in '{service_string}'. Expected closing ']'."
        )

    bracket_start = service_string.index("[")
    bracket_content = service_string[bracket_start + 1 : -1].strip()

    # Empty brackets = defaults
    if not bracket_content:
        return InsightsServiceConfig()

    # Split by comma and validate
    values = [v.strip().lower() for v in bracket_content.split(",") if v.strip()]

    # Check for duplicates
    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate source '{value}' in insights[...] syntax.")
        seen.add(value)

        if value not in SOURCES:
            raise ValueError(
                f"Unknown source '{value}' in insights[...] syntax. "
                f"Valid sources: {', '.join(sorted(SOURCES))}."
            )

    return InsightsServiceConfig(sources=values)


def is_insights_service_with_options(service_string: str) -> bool:
    """
    Check if a service string is an insights service with bracket options.

    Returns True ONLY when explicit bracket syntax is used (insights[...]).
    Plain "insights" without brackets returns False.

    Args:
        service_string: Service specification string

    Returns:
        True if this is an insights[...] format string with explicit options
    """
    return service_string.strip().startswith("insights[")
