"""
Insights service bracket-syntax parser.

R3 of the plugin system refactor: thin shim around the generic
``parse_options`` driven by the insights service's declarative
``options`` list. The typed ``InsightsServiceConfig`` dataclass is
preserved for back-compat with existing callers.
"""

from dataclasses import dataclass, field

from .option_spec import is_spec_with_options, parse_options
from .services import SERVICES

# Re-exported for back-compat with callers and tests; the canonical
# source is SERVICES["insights"].options.
DEFAULT_SOURCES = ["github", "pypi"]


@dataclass
class InsightsServiceConfig:
    """Parsed insights service configuration (back-compat shape)."""

    sources: list[str] = field(default_factory=lambda: DEFAULT_SOURCES.copy())
    per_user: bool = False


def parse_insights_service_config(service_string: str) -> InsightsServiceConfig:
    """Parse an ``insights[...]`` string into the legacy typed dataclass."""
    parsed = parse_options(service_string, SERVICES["insights"])
    return InsightsServiceConfig(
        sources=list(parsed["sources"]),
        per_user=bool(parsed.get("per_user", False)),
    )


def is_insights_service_with_options(service_string: str) -> bool:
    """True when ``service_string`` uses ``insights[...]`` bracket syntax."""
    s = service_string.strip()
    return s.startswith("insights[") and is_spec_with_options(s)
