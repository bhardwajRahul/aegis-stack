"""
AI service bracket syntax parser.

Parses ai[framework, backend, providers...] syntax where values are detected by type:
- Frameworks: pydantic-ai, langchain
- Backends: memory, sqlite
- Providers: public, openai, anthropic, google, groq, mistral, cohere

Order doesn't matter. Defaults: pydantic-ai, memory, public
"""

from dataclasses import dataclass

from ..constants import AIFrameworks, AIProviders, StorageBackends


@dataclass
class AIServiceConfig:
    """Parsed AI service configuration."""

    framework: str
    backend: str
    providers: list[str]


# Valid values for detection (using constants)
FRAMEWORKS = set(AIFrameworks.ALL)
BACKENDS = {StorageBackends.MEMORY, StorageBackends.SQLITE}
PROVIDERS = AIProviders.ALL

# Defaults (using constants)
DEFAULT_FRAMEWORK = AIFrameworks.PYDANTIC_AI
DEFAULT_BACKEND = StorageBackends.MEMORY
DEFAULT_PROVIDERS = AIProviders.DEFAULT


def parse_ai_service_config(service_string: str) -> AIServiceConfig:
    """
    Parse ai[...] service string into config.

    Args:
        service_string: Service specification like "ai", "ai[]", or "ai[langchain, sqlite, openai]"

    Returns:
        AIServiceConfig with framework, backend, and providers

    Raises:
        ValueError: If service string is invalid, has unknown values, or has conflicts
    """
    # Strip whitespace
    service_string = service_string.strip()

    # Validate it starts with "ai"
    if not service_string.startswith("ai"):
        raise ValueError(
            f"Expected 'ai' service, got '{service_string}'. "
            "This parser only handles ai[...] syntax."
        )

    # Check if it's just "ai" with no brackets
    if service_string == "ai":
        return AIServiceConfig(
            framework=DEFAULT_FRAMEWORK,
            backend=DEFAULT_BACKEND,
            providers=DEFAULT_PROVIDERS.copy(),
        )

    # Extract bracket contents
    if "[" not in service_string:
        raise ValueError(
            f"Invalid service string '{service_string}'. "
            "Expected 'ai' or 'ai[options]' format."
        )

    # Validate bracket structure
    if not service_string.endswith("]"):
        raise ValueError(
            f"Malformed brackets in '{service_string}'. Expected closing ']'."
        )

    # Extract content between brackets
    bracket_start = service_string.index("[")
    bracket_content = service_string[bracket_start + 1 : -1].strip()

    # Empty brackets = defaults
    if not bracket_content:
        return AIServiceConfig(
            framework=DEFAULT_FRAMEWORK,
            backend=DEFAULT_BACKEND,
            providers=DEFAULT_PROVIDERS.copy(),
        )

    # Split by comma and strip whitespace
    values = [v.strip() for v in bracket_content.split(",") if v.strip()]

    # Categorize each value
    found_frameworks: list[str] = []
    found_backends: list[str] = []
    found_providers: list[str] = []

    for value in values:
        if value in FRAMEWORKS:
            found_frameworks.append(value)
        elif value in BACKENDS:
            found_backends.append(value)
        elif value in PROVIDERS:
            found_providers.append(value)
        else:
            raise ValueError(
                f"Unknown value '{value}' in ai[...] syntax. "
                f"Valid frameworks: {', '.join(sorted(FRAMEWORKS))}. "
                f"Valid backends: {', '.join(sorted(BACKENDS))}. "
                f"Valid providers: {', '.join(sorted(PROVIDERS))}."
            )

    # Validate no duplicates in framework/backend
    if len(found_frameworks) > 1:
        raise ValueError(
            f"Cannot specify multiple frameworks: {', '.join(found_frameworks)}. "
            f"Choose one of: {', '.join(sorted(FRAMEWORKS))}."
        )

    if len(found_backends) > 1:
        raise ValueError(
            f"Cannot specify multiple backends: {', '.join(found_backends)}. "
            f"Choose one of: {', '.join(sorted(BACKENDS))}."
        )

    # Apply defaults for missing values
    framework = found_frameworks[0] if found_frameworks else DEFAULT_FRAMEWORK
    backend = found_backends[0] if found_backends else DEFAULT_BACKEND
    providers = found_providers if found_providers else DEFAULT_PROVIDERS.copy()

    return AIServiceConfig(
        framework=framework,
        backend=backend,
        providers=providers,
    )


def is_ai_service_with_options(service_string: str) -> bool:
    """
    Check if a service string is an AI service with bracket options.

    Args:
        service_string: Service specification string

    Returns:
        True if this is an ai[...] format string
    """
    stripped = service_string.strip()
    return stripped.startswith("ai[") or stripped == "ai"
