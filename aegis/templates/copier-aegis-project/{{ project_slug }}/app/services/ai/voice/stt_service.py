"""
Speech-to-Text service.

Provides a high-level interface for transcription with provider abstraction,
configuration management, and optional caching.
"""

import logging
from typing import Any

from .config import STTConfig, get_stt_config
from .models import AudioInput, STTProvider, TranscriptionResult
from .stt_providers import BaseSTTProvider, get_stt_provider

logger = logging.getLogger(__name__)


class STTService:
    """Speech-to-Text service with provider abstraction.

    Manages STT provider lifecycle and provides a unified transcription interface.
    Supports lazy-loading of providers and configuration from application settings.

    Example usage:
        ```python
        from app.services.ai.voice import STTService, AudioInput, STTProvider

        # Initialize with settings
        stt = STTService(settings)

        # Or with explicit configuration
        stt = STTService(provider=STTProvider.OPENAI_WHISPER, model="whisper-1")

        # Transcribe audio
        audio = AudioInput(content=audio_bytes, format="wav")
        result = await stt.transcribe(audio)
        print(result.text)
        ```
    """

    def __init__(
        self,
        settings: Any | None = None,
        provider: STTProvider | None = None,
        model: str | None = None,
        api_key: str | None = None,
    ) -> None:
        """Initialize STT service.

        Args:
            settings: Application settings object (optional).
                If provided, reads STT configuration from settings.
            provider: Explicit STT provider to use (overrides settings).
            model: Explicit model name/size to use (overrides settings).
            api_key: Explicit API key for cloud providers (overrides settings).
        """
        self._settings = settings
        self._explicit_api_key = api_key
        self._provider_instance: BaseSTTProvider | None = None

        # Build config from settings or explicit values
        if provider or model:
            # Explicit configuration overrides settings
            self._config = STTConfig(
                provider=provider or STTProvider.OPENAI_WHISPER,
                model=model,
            )
        elif settings:
            # Load from settings
            self._config = get_stt_config(settings)
        else:
            # Default configuration
            self._config = STTConfig()

    @property
    def config(self) -> STTConfig:
        """Get the current STT configuration."""
        return self._config

    @property
    def provider_type(self) -> STTProvider:
        """Get the configured STT provider type."""
        return self._config.provider

    @property
    def model(self) -> str:
        """Get the configured model name/size (with provider default fallback)."""
        return self._config.get_model()

    def _get_api_key(self) -> str | None:
        """Get API key for the current provider."""
        if self._explicit_api_key:
            return self._explicit_api_key

        if self._settings:
            return self._config.get_api_key(self._settings)

        return None

    def _get_provider(self) -> BaseSTTProvider:
        """Get or create the STT provider instance."""
        if self._provider_instance is None:
            provider_type = self.provider_type
            model = self.model
            api_key = self._get_api_key()

            logger.info(f"Initializing STT provider: {provider_type.value}")

            # Build provider-specific kwargs
            kwargs: dict[str, Any] = {}

            # Add device for local providers if configured
            if provider_type == STTProvider.WHISPER_LOCAL and self._config.device:
                kwargs["device"] = self._config.device

            self._provider_instance = get_stt_provider(
                provider=provider_type,
                api_key=api_key,
                model=model,
                **kwargs,
            )

        return self._provider_instance

    async def transcribe(self, audio: AudioInput) -> TranscriptionResult:
        """Transcribe audio to text.

        Args:
            audio: AudioInput containing raw audio bytes and metadata.

        Returns:
            TranscriptionResult with transcribed text and metadata.

        Raises:
            RuntimeError: If transcription fails.
        """
        provider = self._get_provider()

        logger.debug(
            f"Transcribing audio ({len(audio.content)} bytes, "
            f"format={audio.format.value}) with {provider.provider_type.value}"
        )

        result = await provider.transcribe(audio)

        logger.debug(
            f"Transcription complete: {len(result.text)} chars, "
            f"language={result.language}"
        )

        return result

    def reset_provider(self) -> None:
        """Reset the provider instance.

        Call this after changing configuration to force re-initialization.
        """
        self._provider_instance = None

    def validate(self) -> list[str]:
        """Validate the STT configuration.

        Returns:
            List of validation error messages (empty if valid).
        """
        if self._settings:
            return self._config.validate(self._settings)
        return []

    def is_available(self) -> bool:
        """Check if the configured STT provider is available.

        Returns:
            True if the provider is properly configured and available.
        """
        if self._settings:
            return self._config.is_available(self._settings)
        # Without settings, assume available (will fail at runtime if not)
        return True

    def get_status(self) -> dict[str, Any]:
        """Get STT service status information.

        Returns:
            Dictionary with provider type, model, availability, and validation info.
        """
        errors = self.validate()
        return {
            "provider": self.provider_type.value,
            "model": self.model,
            "language": self._config.language,
            "device": self._config.device,
            "initialized": self._provider_instance is not None,
            "available": len(errors) == 0,
            "errors": errors if errors else None,
        }
