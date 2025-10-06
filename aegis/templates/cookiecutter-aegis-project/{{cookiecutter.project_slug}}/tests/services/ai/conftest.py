"""Shared fixtures for AI service tests."""

from unittest.mock import MagicMock

import pytest
from app.services.ai.models import AIProvider, Conversation, MessageRole
from app.services.ai.service import AIService


@pytest.fixture
def mock_ai_settings():
    """Create mock settings for AI service testing."""
    settings = MagicMock()
    settings.AI_ENABLED = True
    settings.AI_PROVIDER = "public"
    settings.AI_MODEL = "gpt-3.5-turbo"
    settings.AI_TEMPERATURE = 0.7
    settings.AI_MAX_TOKENS = 1000
    settings.AI_TIMEOUT_SECONDS = 30.0

    # Provider API keys (None for PUBLIC)
    settings.OPENAI_API_KEY = None
    settings.ANTHROPIC_API_KEY = None
    settings.GOOGLE_API_KEY = None
    settings.GROQ_API_KEY = None
    settings.MISTRAL_API_KEY = None
    settings.COHERE_API_KEY = None

    return settings


@pytest.fixture
def ai_service(mock_ai_settings):
    """Create AI service instance for testing."""
    return AIService(mock_ai_settings)


@pytest.fixture
def sample_conversation():
    """Create a sample conversation for testing."""
    return Conversation(
        id="test-conversation-123",
        provider=AIProvider.PUBLIC,
        model="gpt-3.5-turbo",
        title="Test Conversation",
    )


@pytest.fixture
def conversation_with_messages(sample_conversation):
    """Create a conversation with sample messages."""
    sample_conversation.add_message(MessageRole.USER, "Hello, how are you?")
    sample_conversation.add_message(MessageRole.ASSISTANT, "I'm doing well, thank you!")
    sample_conversation.add_message(MessageRole.USER, "What's the weather like?")
    return sample_conversation


@pytest.fixture
def free_provider_settings(mock_ai_settings):
    """Create settings with a free provider."""
    mock_ai_settings.AI_PROVIDER = "public"
    return mock_ai_settings


@pytest.fixture
def paid_provider_settings(mock_ai_settings):
    """Create settings with a paid provider (no API key)."""
    mock_ai_settings.AI_PROVIDER = "openai"
    mock_ai_settings.OPENAI_API_KEY = None  # Missing API key
    return mock_ai_settings


@pytest.fixture
def paid_provider_with_key_settings(mock_ai_settings):
    """Create settings with a paid provider and API key."""
    mock_ai_settings.AI_PROVIDER = "openai"
    mock_ai_settings.OPENAI_API_KEY = "sk-test-key-123"
    return mock_ai_settings
