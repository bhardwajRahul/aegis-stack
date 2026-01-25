"""
TTS provider implementations.

Provides a unified interface for Text-to-Speech synthesis across
multiple providers: OpenAI TTS and local Piper.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from .models import (
    AudioFormat,
    SpeechRequest,
    SpeechResult,
    TTSProvider,
)

logger = logging.getLogger(__name__)


class BaseTTSProvider(ABC):
    """Abstract base class for TTS providers."""

    provider_type: TTSProvider

    @abstractmethod
    async def synthesize(self, request: SpeechRequest) -> SpeechResult:
        """Synthesize speech from text.

        Args:
            request: SpeechRequest containing text and synthesis options.

        Returns:
            SpeechResult with synthesized audio data and metadata.

        Raises:
            RuntimeError: If synthesis fails.
        """
        pass

    async def synthesize_stream(self, request: SpeechRequest) -> AsyncIterator[bytes]:
        """Stream synthesized audio chunks.

        Default implementation falls back to non-streaming synthesis.
        Override in providers that support native streaming.

        Args:
            request: SpeechRequest containing text and synthesis options.

        Yields:
            Audio data chunks as bytes.
        """
        result = await self.synthesize(request)
        yield result.audio


class OpenAITTSProvider(BaseTTSProvider):
    """OpenAI TTS API provider.

    Uses the OpenAI API for high-quality cloud-based speech synthesis.
    Requires OPENAI_API_KEY environment variable.

    Supports two models:
    - tts-1: Optimized for speed
    - tts-1-hd: Higher quality, slightly slower
    """

    provider_type = TTSProvider.OPENAI

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "tts-1",
        voice: str = "alloy",
        base_url: str | None = None,
    ) -> None:
        """Initialize OpenAI TTS provider.

        Args:
            api_key: OpenAI API key. If None, uses OPENAI_API_KEY env var.
            model: TTS model to use (tts-1 or tts-1-hd).
            voice: Default voice (alloy, echo, fable, onyx, nova, shimmer).
            base_url: Optional base URL for OpenAI-compatible APIs.
        """
        self.api_key = api_key
        self.model = model
        self.default_voice = voice
        self.base_url = base_url
        self._client: Any = None

    def _get_client(self) -> Any:
        """Lazy-load the OpenAI client."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError as e:
                raise RuntimeError(
                    "OpenAI SDK not installed. Install with: uv add openai"
                ) from e

            kwargs: dict[str, Any] = {}
            if self.api_key:
                kwargs["api_key"] = self.api_key
            if self.base_url:
                kwargs["base_url"] = self.base_url

            self._client = AsyncOpenAI(**kwargs)

        return self._client

    async def synthesize(self, request: SpeechRequest) -> SpeechResult:
        """Synthesize speech using OpenAI TTS API."""
        client = self._get_client()

        voice = request.voice or self.default_voice

        try:
            response = await client.audio.speech.create(
                model=self.model,
                voice=voice,
                input=request.text,
                speed=request.speed,
                response_format="mp3",
            )

            # Read the audio content
            audio_data = response.content

            return SpeechResult(
                audio=audio_data,
                format=AudioFormat.MP3,
                provider=self.provider_type,
            )

        except Exception as e:
            logger.error(f"OpenAI TTS synthesis failed: {e}")
            raise RuntimeError(f"Speech synthesis failed: {e}") from e

    async def synthesize_stream(self, request: SpeechRequest) -> AsyncIterator[bytes]:
        """Stream audio from OpenAI TTS."""
        client = self._get_client()

        voice = request.voice or self.default_voice

        try:
            response = await client.audio.speech.create(
                model=self.model,
                voice=voice,
                input=request.text,
                speed=request.speed,
                response_format="mp3",
            )

            # OpenAI returns the full response, stream in chunks
            audio_data = response.content
            chunk_size = 4096

            for i in range(0, len(audio_data), chunk_size):
                yield audio_data[i : i + chunk_size]

        except Exception as e:
            logger.error(f"OpenAI TTS streaming failed: {e}")
            raise RuntimeError(f"Speech synthesis failed: {e}") from e


class PiperLocalProvider(BaseTTSProvider):
    """Piper local TTS provider (ONNX-based).

    High-quality, fast local TTS that doesn't require a GPU.
    Requires piper-tts to be installed.
    """

    provider_type = TTSProvider.PIPER_LOCAL

    def __init__(
        self,
        model_path: str | None = None,
        voice: str = "en_US-lessac-medium",
    ) -> None:
        """Initialize Piper local TTS provider.

        Args:
            model_path: Path to Piper model file (.onnx).
                If None, uses voice name to find model.
            voice: Voice/model name (e.g., en_US-lessac-medium).
        """
        self.model_path = model_path
        self.voice = voice
        self._piper: Any = None

    def _get_piper(self) -> Any:
        """Lazy-load the Piper TTS engine."""
        if self._piper is None:
            try:
                from piper import PiperVoice
            except ImportError as e:
                raise RuntimeError(
                    "Piper TTS not installed. Install with: uv add piper-tts"
                ) from e

            if self.model_path:
                self._piper = PiperVoice.load(self.model_path)
            else:
                # Try to find model by voice name
                raise RuntimeError(
                    f"Piper model path required. Download a model for voice '{self.voice}' "
                    "from https://github.com/rhasspy/piper/releases"
                )

        return self._piper

    async def synthesize(self, request: SpeechRequest) -> SpeechResult:
        """Synthesize speech using local Piper TTS."""
        import io
        import wave

        piper = self._get_piper()

        try:
            # Run synthesis in thread pool to avoid blocking
            loop = asyncio.get_event_loop()

            def _synthesize() -> bytes:
                # Piper outputs raw PCM audio, we need to wrap it in WAV
                audio_buffer = io.BytesIO()

                with wave.open(audio_buffer, "wb") as wav_file:
                    wav_file.setnchannels(1)  # Mono
                    wav_file.setsampwidth(2)  # 16-bit
                    wav_file.setframerate(22050)  # Piper default sample rate

                    for audio_chunk in piper.synthesize(request.text):
                        wav_file.writeframes(audio_chunk)

                return audio_buffer.getvalue()

            audio_data = await loop.run_in_executor(None, _synthesize)

            return SpeechResult(
                audio=audio_data,
                format=AudioFormat.WAV,
                provider=self.provider_type,
            )

        except Exception as e:
            logger.error(f"Piper TTS synthesis failed: {e}")
            raise RuntimeError(f"Speech synthesis failed: {e}") from e


def get_tts_provider(
    provider: TTSProvider,
    api_key: str | None = None,
    model: str | None = None,
    voice: str | None = None,
    **kwargs: Any,
) -> BaseTTSProvider:
    """Factory function to create a TTS provider instance.

    Args:
        provider: The TTS provider type to create.
        api_key: Optional API key for cloud providers.
        model: Optional model name to use.
        voice: Optional voice name to use.
        **kwargs: Additional provider-specific arguments.

    Returns:
        Configured TTS provider instance.

    Raises:
        ValueError: If provider type is not supported.
    """
    if provider == TTSProvider.OPENAI:
        return OpenAITTSProvider(
            api_key=api_key,
            model=model or "tts-1",
            voice=voice or "alloy",
            **kwargs,
        )
    elif provider == TTSProvider.PIPER_LOCAL:
        return PiperLocalProvider(
            voice=voice or "en_US-lessac-medium",
            **kwargs,
        )
    else:
        raise ValueError(f"Unsupported TTS provider: {provider}")
