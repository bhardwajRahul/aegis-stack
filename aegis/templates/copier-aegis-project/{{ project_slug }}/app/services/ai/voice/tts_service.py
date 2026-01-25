"""
Text-to-Speech service.

Provides a high-level interface for speech synthesis with provider abstraction,
configuration management, and streaming support.
"""

import logging
from collections.abc import AsyncIterator
from typing import Any

from .models import SpeechRequest, SpeechResult, TTSProvider
from .tts_config import TTSConfig, get_tts_config
from .tts_providers import BaseTTSProvider, get_tts_provider

logger = logging.getLogger(__name__)


class TTSService:
    """Text-to-Speech service with provider abstraction.

    Manages TTS provider lifecycle and provides a unified synthesis interface.
    Supports lazy-loading of providers and configuration from application settings.

    Example usage:
        ```python
        from app.services.ai.voice import TTSService, SpeechRequest, TTSProvider

        # Initialize with settings
        tts = TTSService(settings)

        # Or with explicit configuration
        tts = TTSService(provider=TTSProvider.OPENAI, voice="nova")

        # Synthesize speech
        request = SpeechRequest(text="Hello, world!")
        result = await tts.synthesize(request)

        # Save audio
        with open("hello.mp3", "wb") as f:
            f.write(result.audio)
        ```
    """

    def __init__(
        self,
        settings: Any | None = None,
        provider: TTSProvider | None = None,
        model: str | None = None,
        voice: str | None = None,
        api_key: str | None = None,
    ) -> None:
        """Initialize TTS service.

        Args:
            settings: Application settings object (optional).
                If provided, reads TTS configuration from settings.
            provider: Explicit TTS provider to use (overrides settings).
            model: Explicit model name to use (overrides settings).
            voice: Explicit voice to use (overrides settings).
            api_key: Explicit API key for cloud providers (overrides settings).
        """
        self._settings = settings
        self._explicit_api_key = api_key
        self._provider_instance: BaseTTSProvider | None = None

        # Build config from settings or explicit values
        if provider or model or voice:
            # Explicit configuration overrides settings
            self._config = TTSConfig(
                provider=provider or TTSProvider.OPENAI,
                model=model,
                voice=voice,
            )
        elif settings:
            # Load from settings
            self._config = get_tts_config(settings)
        else:
            # Default configuration
            self._config = TTSConfig()

    @property
    def config(self) -> TTSConfig:
        """Get the current TTS configuration."""
        return self._config

    @property
    def provider_type(self) -> TTSProvider:
        """Get the configured TTS provider type."""
        return self._config.provider

    @property
    def model(self) -> str:
        """Get the configured model name (with provider default fallback)."""
        return self._config.get_model()

    @property
    def voice(self) -> str:
        """Get the configured voice (with provider default fallback)."""
        return self._config.get_voice()

    def _get_api_key(self) -> str | None:
        """Get API key for the current provider."""
        if self._explicit_api_key:
            return self._explicit_api_key

        if self._settings:
            return self._config.get_api_key(self._settings)

        return None

    def _get_provider(self) -> BaseTTSProvider:
        """Get or create the TTS provider instance."""
        if self._provider_instance is None:
            provider_type = self.provider_type
            model = self.model
            voice = self.voice
            api_key = self._get_api_key()

            logger.info(f"Initializing TTS provider: {provider_type.value}")

            self._provider_instance = get_tts_provider(
                provider=provider_type,
                api_key=api_key,
                model=model,
                voice=voice,
            )

        return self._provider_instance

    async def synthesize(self, request: SpeechRequest) -> SpeechResult:
        """Synthesize speech from text.

        Args:
            request: SpeechRequest containing text and synthesis options.

        Returns:
            SpeechResult with synthesized audio data and metadata.

        Raises:
            RuntimeError: If synthesis fails.
        """
        provider = self._get_provider()

        logger.debug(
            f"Synthesizing speech ({len(request.text)} chars, "
            f"voice={request.voice or self.voice}) with {provider.provider_type.value}"
        )

        result = await provider.synthesize(request)

        logger.debug(
            f"Synthesis complete: {len(result.audio)} bytes, "
            f"format={result.format.value}"
        )

        return result

    async def synthesize_stream(self, request: SpeechRequest) -> AsyncIterator[bytes]:
        """Stream synthesized audio.

        Args:
            request: SpeechRequest containing text and synthesis options.

        Yields:
            Audio data chunks as bytes.

        Raises:
            RuntimeError: If synthesis fails.
        """
        provider = self._get_provider()

        logger.debug(
            f"Streaming speech synthesis ({len(request.text)} chars) "
            f"with {provider.provider_type.value}"
        )

        async for chunk in provider.synthesize_stream(request):
            yield chunk

    def reset_provider(self) -> None:
        """Reset the provider instance.

        Call this after changing configuration to force re-initialization.
        """
        self._provider_instance = None

    def validate(self) -> list[str]:
        """Validate the TTS configuration.

        Returns:
            List of validation error messages (empty if valid).
        """
        if self._settings:
            return self._config.validate(self._settings)
        return []

    def is_available(self) -> bool:
        """Check if the configured TTS provider is available.

        Returns:
            True if the provider is properly configured and available.
        """
        if self._settings:
            return self._config.is_available(self._settings)
        # Without settings, assume available (will fail at runtime if not)
        return True

    def get_status(self) -> dict[str, Any]:
        """Get TTS service status information.

        Returns:
            Dictionary with provider type, model, voice, availability, and validation info.
        """
        errors = self.validate()
        return {
            "provider": self.provider_type.value,
            "model": self.model,
            "voice": self.voice,
            "speed": self._config.speed,
            "initialized": self._provider_instance is not None,
            "available": len(errors) == 0,
            "errors": errors if errors else None,
        }
