"""
Auth service bracket syntax parser.

Parses auth[level] syntax where level is one of: basic, rbac.
Default (plain "auth" without brackets): basic.
"""

from dataclasses import dataclass

from ..constants import AuthLevels

# Valid auth levels
LEVELS = set(AuthLevels.ALL)

DEFAULT_LEVEL = AuthLevels.BASIC


@dataclass
class AuthServiceConfig:
    """Parsed auth service configuration."""

    level: str


def parse_auth_service_config(service_string: str) -> AuthServiceConfig:
    """
    Parse auth[...] service string into config.

    Args:
        service_string: Service specification like "auth", "auth[]", or "auth[rbac]"

    Returns:
        AuthServiceConfig with level

    Raises:
        ValueError: If service string is invalid or has unknown values
    """
    service_string = service_string.strip()

    if not service_string.startswith("auth"):
        raise ValueError(
            f"Expected 'auth' service, got '{service_string}'. "
            "This parser only handles auth[...] syntax."
        )

    # Plain "auth" with no brackets
    if service_string == "auth":
        return AuthServiceConfig(level=DEFAULT_LEVEL)

    if "[" not in service_string:
        raise ValueError(
            f"Invalid service string '{service_string}'. "
            "Expected 'auth' or 'auth[level]' format."
        )

    if not service_string.endswith("]"):
        raise ValueError(
            f"Malformed brackets in '{service_string}'. Expected closing ']'."
        )

    bracket_start = service_string.index("[")
    bracket_content = service_string[bracket_start + 1 : -1].strip()

    # Empty brackets = defaults
    if not bracket_content:
        return AuthServiceConfig(level=DEFAULT_LEVEL)

    # Single value expected
    level = bracket_content.lower()

    if level not in LEVELS:
        raise ValueError(
            f"Unknown auth level '{level}'. Valid levels: {', '.join(sorted(LEVELS))}."
        )

    return AuthServiceConfig(level=level)


def is_auth_service_with_options(service_string: str) -> bool:
    """
    Check if a service string is an auth service with bracket options.

    Returns True ONLY when explicit bracket syntax is used (auth[...]).
    Plain "auth" without brackets returns False.

    Args:
        service_string: Service specification string

    Returns:
        True if this is an auth[...] format string with explicit options
    """
    return service_string.strip().startswith("auth[")
