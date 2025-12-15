"""
AI service data models and enums.

This module defines the core data structures for AI service configuration,
conversation management, and provider integration.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from .llm import (
    Direction,
    LargeLanguageModel,
    LLMDeployment,
    LLMModality,
    LLMPrice,
    LLMUsage,
    LLMVendor,
    Modality,
)


class AIProvider(str, Enum):
    """Supported AI providers for PydanticAI integration."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    GROQ = "groq"
    MISTRAL = "mistral"
    COHERE = "cohere"
    PUBLIC = "public"  # Free public endpoints (no API key required)


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


class StreamingMessage(BaseModel):
    """A streaming message chunk with metadata."""

    content: str = Field(..., description="Partial or complete message content")
    is_final: bool = Field(False, description="Whether this is the final chunk")
    is_delta: bool = Field(False, description="Whether content is delta or cumulative")
    message_id: str | None = Field(None, description="Message ID once finalized")
    conversation_id: str | None = Field(None, description="Associated conversation ID")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)


class StreamingConversation(BaseModel):
    """Extended conversation model for streaming state management."""

    conversation: Conversation
    current_message_id: str | None = None
    accumulated_content: str = ""
    stream_start_time: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def reset_stream(self) -> None:
        """Reset streaming state for new message."""
        self.current_message_id = None
        self.accumulated_content = ""
        self.stream_start_time = datetime.now(UTC)

    def accumulate_content(self, content: str, is_delta: bool = False) -> str:
        """Accumulate streaming content and return total content."""
        if is_delta:
            self.accumulated_content += content
        else:
            self.accumulated_content = content
        return self.accumulated_content


class AIServiceStatus(BaseModel):
    """Status information for the AI service."""

    enabled: bool
    provider: AIProvider
    model: str
    available_providers: list[AIProvider]
    conversation_count: int = 0
    last_activity: datetime | None = None


class ProviderCapabilities(BaseModel):
    """Capabilities for an AI provider (binary features only)."""

    provider: AIProvider
    supports_streaming: bool = True
    supports_function_calling: bool = False
    supports_vision: bool = False
    free_tier_available: bool = False


# Provider capability definitions (binary features only)
PROVIDER_CAPABILITIES = {
    AIProvider.OPENAI: ProviderCapabilities(
        provider=AIProvider.OPENAI,
        supports_streaming=True,
        supports_function_calling=True,
        supports_vision=True,
        free_tier_available=False,
    ),
    AIProvider.ANTHROPIC: ProviderCapabilities(
        provider=AIProvider.ANTHROPIC,
        supports_streaming=True,
        supports_function_calling=True,
        supports_vision=True,
        free_tier_available=False,
    ),
    AIProvider.GOOGLE: ProviderCapabilities(
        provider=AIProvider.GOOGLE,
        supports_streaming=True,
        supports_function_calling=True,
        supports_vision=True,
        free_tier_available=True,
    ),
    AIProvider.GROQ: ProviderCapabilities(
        provider=AIProvider.GROQ,
        supports_streaming=True,
        supports_function_calling=False,
        supports_vision=False,
        free_tier_available=True,  # Very generous free tier
    ),
    AIProvider.MISTRAL: ProviderCapabilities(
        provider=AIProvider.MISTRAL,
        supports_streaming=True,
        supports_function_calling=True,
        supports_vision=False,
        free_tier_available=False,
    ),
    AIProvider.COHERE: ProviderCapabilities(
        provider=AIProvider.COHERE,
        supports_streaming=True,
        supports_function_calling=False,
        supports_vision=False,
        free_tier_available=True,
    ),
    AIProvider.PUBLIC: ProviderCapabilities(
        provider=AIProvider.PUBLIC,
        supports_streaming=False,
        supports_function_calling=False,
        supports_vision=False,
        free_tier_available=True,  # No API key required
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


__all__ = [
    # LLM tracking models
    "LLMVendor",
    "LargeLanguageModel",
    "LLMPrice",
    "LLMModality",
    "Modality",
    "Direction",
    "LLMDeployment",
    "LLMUsage",
    # AI service models
    "AIProvider",
    "MessageRole",
    "ProviderConfig",
    "ConversationMessage",
    "Conversation",
    "StreamingMessage",
    "StreamingConversation",
    "AIServiceStatus",
    "ProviderCapabilities",
    "PROVIDER_CAPABILITIES",
    "get_provider_capabilities",
    "get_free_providers",
]
