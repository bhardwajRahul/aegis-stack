"""
Auth service bracket-syntax parser.

R3 of the plugin system refactor: thin shim around the generic
``parse_options`` driven by the auth service's declarative ``options``
list. The typed ``AuthServiceConfig`` dataclass is preserved for
back-compat with existing callers.
"""

from dataclasses import dataclass

from .option_spec import is_spec_with_options, parse_options
from .services import SERVICES


@dataclass
class AuthServiceConfig:
    """Parsed auth service configuration (back-compat shape)."""

    level: str
    engine: str | None = None
    oauth: bool = False


def parse_auth_service_config(service_string: str) -> AuthServiceConfig:
    """Parse an ``auth[...]`` string into the legacy typed dataclass."""
    parsed = parse_options(service_string, SERVICES["auth"])
    return AuthServiceConfig(
        level=parsed["level"],
        engine=parsed.get("engine"),
        oauth=bool(parsed.get("oauth", False)),
    )


def is_auth_service_with_options(service_string: str) -> bool:
    """True when ``service_string`` uses ``auth[...]`` bracket syntax."""
    s = service_string.strip()
    return s.startswith("auth[") and is_spec_with_options(s)
