"""
Auth service bracket syntax parser.

Parses auth[level, engine, modifier] syntax where values are detected
by type:

- Levels: basic, rbac, org
- Engines: sqlite, postgres
- Modifiers: oauth (boolean toggle for social login)

Order doesn't matter. Defaults: basic, (no engine override), no
modifiers.
"""

from dataclasses import dataclass

from ..constants import AuthLevels, StorageBackends

# Valid values for detection
LEVELS = set(AuthLevels.ALL)
ENGINES = {StorageBackends.SQLITE, StorageBackends.POSTGRES}
# Modifiers are bracket tokens that flip a boolean on the config — they
# coexist with the level + engine slots rather than replacing them. Add
# new modifiers here when adding bracket-toggleable auth features.
MODIFIERS = {"oauth"}

DEFAULT_LEVEL = AuthLevels.BASIC


@dataclass
class AuthServiceConfig:
    """Parsed auth service configuration."""

    level: str
    engine: str | None = None
    oauth: bool = False


def parse_auth_service_config(service_string: str) -> AuthServiceConfig:
    """
    Parse auth[...] service string into config.

    Args:
        service_string: Service specification like "auth", "auth[rbac]",
                        or "auth[org,postgres]"

    Returns:
        AuthServiceConfig with level and optional engine

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

    # Split by comma and categorize
    values = [v.strip().lower() for v in bracket_content.split(",") if v.strip()]

    found_levels: list[str] = []
    found_engines: list[str] = []
    found_modifiers: list[str] = []

    for value in values:
        if value in LEVELS:
            found_levels.append(value)
        elif value in ENGINES:
            found_engines.append(value)
        elif value in MODIFIERS:
            found_modifiers.append(value)
        else:
            raise ValueError(
                f"Unknown value '{value}' in auth[...] syntax. "
                f"Valid levels: {', '.join(sorted(LEVELS))}. "
                f"Valid engines: {', '.join(sorted(ENGINES))}. "
                f"Valid modifiers: {', '.join(sorted(MODIFIERS))}."
            )

    if len(found_levels) > 1:
        raise ValueError(
            f"Cannot specify multiple levels: {', '.join(found_levels)}. "
            f"Choose one of: {', '.join(sorted(LEVELS))}."
        )

    if len(found_engines) > 1:
        raise ValueError(
            f"Cannot specify multiple engines: {', '.join(found_engines)}. "
            f"Choose one of: {', '.join(sorted(ENGINES))}."
        )

    # Modifiers are flags — repeating one is a typo, not a different
    # selection, so reject it the same way duplicate levels/engines are
    # rejected.
    if len(found_modifiers) != len(set(found_modifiers)):
        duplicates = sorted(
            {m for m in found_modifiers if found_modifiers.count(m) > 1}
        )
        raise ValueError(
            f"Duplicate modifier(s) in auth[...] syntax: {', '.join(duplicates)}."
        )

    level = found_levels[0] if found_levels else DEFAULT_LEVEL
    engine = found_engines[0] if found_engines else None
    oauth = "oauth" in found_modifiers

    return AuthServiceConfig(level=level, engine=engine, oauth=oauth)


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
