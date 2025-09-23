"""
AI service data models and enums.

This module defines the core data structures for AI service configuration,
conversation management, and provider integration.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AIProvider(str, Enum):
    """Supported AI providers for PydanticAI integration."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    GROQ = "groq"
    MISTRAL = "mistral"
    COHERE = "cohere"


class MessageRole(str, Enum):
    """Message roles in a conversation."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ProviderConfig(BaseModel):
    """Configuration for a specific AI provider."""

    name: AIProvider
    api_key: str | None = None
    base_url: str | None = None
    max_tokens: int = 1000
    temperature: float = 0.7
    timeout_seconds: float = 30.0
    rate_limit_rpm: int = 10  # Requests per minute

    class Config:
        use_enum_values = True


class ConversationMessage(BaseModel):
    """A single message in a conversation."""

    id: str = Field(..., description="Unique message identifier")
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)


class Conversation(BaseModel):
    """A conversation containing multiple messages."""

    id: str = Field(..., description="Unique conversation identifier")
    title: str | None = None
    messages: list[ConversationMessage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    provider: AIProvider
    model: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    def add_message(
        self, role: MessageRole, content: str, message_id: str | None = None
    ) -> ConversationMessage:
        """Add a new message to the conversation."""
        import uuid

        message = ConversationMessage(
            id=message_id or str(uuid.uuid4()), role=role, content=content
        )
        self.messages.append(message)
        self.updated_at = datetime.now(UTC)

        # Auto-generate title from first user message
        if not self.title and role == MessageRole.USER and len(self.messages) == 1:
            # Use first 50 characters as title
            self.title = content[:50] + "..." if len(content) > 50 else content

        return message

    def get_message_count(self) -> int:
        """Get total number of messages in conversation."""
        return len(self.messages)

    def get_last_message(self) -> ConversationMessage | None:
        """Get the most recent message."""
        return self.messages[-1] if self.messages else None


class AIServiceStatus(BaseModel):
    """Status information for the AI service."""

    enabled: bool
    provider: AIProvider
    model: str
    available_providers: list[AIProvider]
    conversation_count: int = 0
    last_activity: datetime | None = None


class ProviderCapabilities(BaseModel):
    """Capabilities and limits for an AI provider."""

    provider: AIProvider
    supports_streaming: bool = True
    supports_function_calling: bool = False
    supports_vision: bool = False
    max_tokens: int = 4000
    context_length: int = 4000
    free_tier_available: bool = False
    rate_limits: dict[str, int] = Field(default_factory=dict)


# Provider capability definitions
PROVIDER_CAPABILITIES = {
    AIProvider.OPENAI: ProviderCapabilities(
        provider=AIProvider.OPENAI,
        supports_streaming=True,
        supports_function_calling=True,
        supports_vision=True,
        max_tokens=4000,
        context_length=16000,
        free_tier_available=False,
        rate_limits={"requests_per_minute": 3000, "tokens_per_minute": 250000},
    ),
    AIProvider.ANTHROPIC: ProviderCapabilities(
        provider=AIProvider.ANTHROPIC,
        supports_streaming=True,
        supports_function_calling=True,
        supports_vision=True,
        max_tokens=4000,
        context_length=200000,
        free_tier_available=False,
        rate_limits={"requests_per_minute": 1000, "tokens_per_minute": 100000},
    ),
    AIProvider.GOOGLE: ProviderCapabilities(
        provider=AIProvider.GOOGLE,
        supports_streaming=True,
        supports_function_calling=True,
        supports_vision=True,
        max_tokens=2048,
        context_length=30000,
        free_tier_available=True,
        rate_limits={"requests_per_minute": 1500, "tokens_per_minute": 32000},
    ),
    AIProvider.GROQ: ProviderCapabilities(
        provider=AIProvider.GROQ,
        supports_streaming=True,
        supports_function_calling=False,
        supports_vision=False,
        max_tokens=8000,
        context_length=8000,
        free_tier_available=True,  # Very generous free tier
        rate_limits={"requests_per_minute": 30, "tokens_per_minute": 14400},
    ),
    AIProvider.MISTRAL: ProviderCapabilities(
        provider=AIProvider.MISTRAL,
        supports_streaming=True,
        supports_function_calling=True,
        supports_vision=False,
        max_tokens=4000,
        context_length=32000,
        free_tier_available=False,
        rate_limits={"requests_per_minute": 1000, "tokens_per_minute": 100000},
    ),
    AIProvider.COHERE: ProviderCapabilities(
        provider=AIProvider.COHERE,
        supports_streaming=True,
        supports_function_calling=False,
        supports_vision=False,
        max_tokens=4000,
        context_length=4000,
        free_tier_available=True,
        rate_limits={"requests_per_minute": 1000, "tokens_per_minute": 10000},
    ),
}


def get_provider_capabilities(provider: AIProvider) -> ProviderCapabilities:
    """Get capabilities for a specific provider."""
    return PROVIDER_CAPABILITIES.get(provider, ProviderCapabilities(provider=provider))


def get_free_providers() -> list[AIProvider]:
    """Get list of providers that offer free tiers."""
    return [
        provider
        for provider, caps in PROVIDER_CAPABILITIES.items()
        if caps.free_tier_available
    ]


def get_recommended_free_providers() -> list[AIProvider]:
    """Get recommended free providers for getting started."""
    return [AIProvider.GROQ, AIProvider.GOOGLE]  # Best free tiers
