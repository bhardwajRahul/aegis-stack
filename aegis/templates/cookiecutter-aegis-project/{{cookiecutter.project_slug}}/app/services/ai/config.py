"""
AI service configuration models.

Configuration management for AI service providers, models, and settings.
Integrates with main application settings through app.core.config.
"""

from typing import Any

from pydantic import BaseModel, Field

from .models import (
    AIProvider,
    ProviderConfig,
    get_provider_capabilities,
)


class AIServiceConfig(BaseModel):
    """
    AI service configuration that integrates with main app settings.

    This class provides convenience methods and validation for AI service
    configuration while the actual settings live in app.core.config.Settings.
    """

    enabled: bool = True
    provider: AIProvider = (
        AIProvider.PUBLIC
    )  # Default to public endpoints (no API key required)
    model: str = "gpt-3.5-turbo"  # Default to widely supported model
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1000, gt=0, le=8000)
    timeout_seconds: float = Field(default=30.0, gt=0)

    # RAG-Chat integration settings (used when RAG is enabled)
    rag_default_collection: str = "default"
    rag_top_k: int = Field(default=10, gt=0, le=50)
    rag_min_score: float = Field(default=0.1, ge=0.0, le=1.0)

    @classmethod
    def from_settings(cls, settings: Any) -> "AIServiceConfig":
        """Create configuration from main application settings."""
        return cls(
            enabled=getattr(settings, "AI_ENABLED", True),
            provider=AIProvider(getattr(settings, "AI_PROVIDER", "public")),
            model=getattr(settings, "AI_MODEL", "gpt-3.5-turbo"),
            temperature=getattr(settings, "AI_TEMPERATURE", 0.7),
            max_tokens=getattr(settings, "AI_MAX_TOKENS", 1000),
            timeout_seconds=getattr(settings, "AI_TIMEOUT_SECONDS", 30.0),
            # RAG-Chat integration settings
            rag_default_collection=getattr(
                settings, "RAG_CHAT_DEFAULT_COLLECTION", "default"
            ),
            rag_top_k=getattr(settings, "RAG_CHAT_TOP_K", 10),
            rag_min_score=getattr(settings, "RAG_CHAT_MIN_SCORE", 0.1),
        )

    def get_provider_config(self, settings: Any) -> ProviderConfig:
        """Get provider-specific configuration."""
        # Get API key based on provider
        api_key_mapping = {
            AIProvider.OPENAI: getattr(settings, "OPENAI_API_KEY", None),
            AIProvider.ANTHROPIC: getattr(settings, "ANTHROPIC_API_KEY", None),
            AIProvider.GOOGLE: getattr(settings, "GOOGLE_API_KEY", None),
            AIProvider.GROQ: getattr(settings, "GROQ_API_KEY", None),
            AIProvider.MISTRAL: getattr(settings, "MISTRAL_API_KEY", None),
            AIProvider.COHERE: getattr(settings, "COHERE_API_KEY", None),
            AIProvider.PUBLIC: None,  # No API key required for public endpoints
        }

        return ProviderConfig(
            name=self.provider,
            api_key=api_key_mapping.get(self.provider),
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            timeout_seconds=self.timeout_seconds,
        )

    def validate_configuration(self, settings: Any) -> list[str]:
        """
        Validate AI service configuration and return list of issues.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        if not self.enabled:
            return errors  # Skip validation if disabled

        # Check if provider is supported
        capabilities = get_provider_capabilities(self.provider)
        if not capabilities:
            errors.append(f"Unsupported provider: {self.provider}")

        # Check API key requirement (only PUBLIC provider requires no API key)
        provider_config = self.get_provider_config(settings)

        if self.provider != AIProvider.PUBLIC and not provider_config.api_key:
            errors.append(
                f"Missing API key for {self.provider} provider. "
                f"Set {self.provider.upper()}_API_KEY environment variable."
            )

        # Note: Token limits vary by model within each provider,
        # so we don't validate them here

        return errors

    def is_provider_available(self, settings: Any) -> bool:
        """Check if the configured provider is available and properly configured."""
        errors = self.validate_configuration(settings)
        return len(errors) == 0

    def get_available_providers(self, settings: Any) -> list[AIProvider]:
        """Get list of providers that are properly configured."""
        available = []

        for provider in AIProvider:
            # Temporarily check each provider
            temp_config = AIServiceConfig(
                enabled=True,
                provider=provider,
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            if len(temp_config.validate_configuration(settings)) == 0:
                available.append(provider)

        return available


def get_ai_config(settings: Any) -> AIServiceConfig:
    """Get AI service configuration from application settings."""
    return AIServiceConfig.from_settings(settings)
