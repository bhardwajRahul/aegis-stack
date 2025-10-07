"""Tests for AI service core functionality."""

import pytest
from app.core.config import settings
from app.services.ai.models import AIProvider
from app.services.ai.service import AIService


class TestAIServiceInitialization:
    """Test AI service initialization."""

    def test_service_initialization(self) -> None:
        """Test that AIService initializes correctly."""
        service = AIService(settings)

        assert service.settings == settings
        assert service.config is not None
        assert service.conversation_manager is not None

    def test_service_config_loaded(self) -> None:
        """Test that configuration is loaded from settings."""
        service = AIService(settings)

        assert hasattr(service.config, "enabled")
        assert hasattr(service.config, "provider")
        assert hasattr(service.config, "model")


class TestAIServiceStatus:
    """Test AI service status reporting."""

    def test_get_service_status_structure(self) -> None:
        """Test that service status has expected structure."""
        service = AIService(settings)
        status = service.get_service_status()

        assert isinstance(status, dict)
        assert "enabled" in status
        assert "provider" in status
        assert "model" in status
        assert "agent_initialized" in status
        assert "total_conversations" in status
        assert "configuration_valid" in status

    def test_get_service_status_provider_type(self) -> None:
        """Test that provider is returned as string, not enum.

        This test would have caught the bug where code tried to call
        .value on provider when it was already a string due to
        use_enum_values=True in AIServiceConfig.
        """
        service = AIService(settings)
        status = service.get_service_status()

        provider = status["provider"]

        # Provider should be string (Pydantic converts enum to string)
        assert isinstance(provider, str)
        # Should be a valid provider value
        assert provider in [p.value for p in AIProvider]

    def test_get_service_status_enabled_bool(self) -> None:
        """Test that enabled is a boolean."""
        service = AIService(settings)
        status = service.get_service_status()

        assert isinstance(status["enabled"], bool)

    def test_get_service_status_agent_initialized(self) -> None:
        """Test that agent_initialized is always True."""
        service = AIService(settings)
        status = service.get_service_status()

        # Agents created per request, always available
        assert status["agent_initialized"] is True

    def test_get_service_status_configuration_valid(self) -> None:
        """Test that configuration_valid reflects validation state."""
        service = AIService(settings)
        status = service.get_service_status()

        assert isinstance(status["configuration_valid"], bool)

    def test_get_service_status_conversation_count(self) -> None:
        """Test that total_conversations starts at 0."""
        service = AIService(settings)
        status = service.get_service_status()

        # New service should have no conversations
        assert status["total_conversations"] == 0


class TestAIServiceValidation:
    """Test AI service validation."""

    def test_validate_service_returns_list(self) -> None:
        """Test that validate_service returns list of errors."""
        service = AIService(settings)
        errors = service.validate_service()

        assert isinstance(errors, list)
        assert all(isinstance(e, str) for e in errors)

    def test_validate_service_with_valid_config(self) -> None:
        """Test validation with valid configuration."""
        service = AIService(settings)
        errors = service.validate_service()

        # PUBLIC provider should have no errors (no API key required)
        if service.config.provider == AIProvider.PUBLIC:
            assert len(errors) == 0


class TestAIServiceConversationManagement:
    """Test conversation management methods."""

    def test_get_conversation_not_found(self) -> None:
        """Test getting non-existent conversation."""
        service = AIService(settings)
        conversation = service.get_conversation("nonexistent-id")

        assert conversation is None

    def test_list_conversations_empty(self) -> None:
        """Test listing conversations when none exist."""
        service = AIService(settings)
        conversations = service.list_conversations("test-user")

        assert isinstance(conversations, list)
        assert len(conversations) == 0

    def test_conversation_manager_integration(self) -> None:
        """Test that conversation manager is properly integrated."""
        service = AIService(settings)

        # ConversationManager should be accessible
        assert hasattr(service, "conversation_manager")
        assert hasattr(service.conversation_manager, "conversations")
        assert isinstance(service.conversation_manager.conversations, dict)


class TestAIServiceConfigIntegration:
    """Test integration with configuration."""

    def test_config_provider_enum_to_string_conversion(self) -> None:
        """Test that Pydantic converts provider enum to string.

        This documents the behavior that caused the .value bug:
        AIServiceConfig has use_enum_values=True, which means
        self.config.provider is already a string, not an enum.
        """
        service = AIService(settings)

        # Config provider is a string due to use_enum_values=True
        assert isinstance(service.config.provider, str)

        # Should be able to compare with enum values
        assert service.config.provider == AIProvider.PUBLIC.value

    def test_service_uses_config_correctly(self) -> None:
        """Test that service uses config values correctly."""
        service = AIService(settings)

        # Service should use config values
        assert service.config.enabled is not None
        assert service.config.model is not None
        assert service.config.temperature is not None


class TestAIServiceErrorHandling:
    """Test error handling in AI service."""

    @pytest.mark.asyncio
    async def test_chat_disabled_service_error(self, mock_ai_settings) -> None:
        """Test that chat raises error when service is disabled."""
        # Disable AI service
        mock_ai_settings.AI_ENABLED = False

        service = AIService(mock_ai_settings)

        with pytest.raises(Exception) as exc_info:
            await service.chat("test message")

        assert "disabled" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_stream_chat_disabled_service_error(self, mock_ai_settings) -> None:
        """Test that stream_chat raises error when service is disabled."""
        # Disable AI service
        mock_ai_settings.AI_ENABLED = False

        service = AIService(mock_ai_settings)

        with pytest.raises(Exception) as exc_info:
            async for _ in service.stream_chat("test message"):
                pass

        assert "disabled" in str(exc_info.value).lower()
