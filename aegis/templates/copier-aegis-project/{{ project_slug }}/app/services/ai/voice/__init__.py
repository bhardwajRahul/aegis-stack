"""
Voice module for AI service.

Provides Speech-to-Text (STT) capabilities with provider abstraction
supporting multiple cloud and open-source transcription providers.
"""

from .config import STTConfig, get_stt_config
from .models import (
    AudioFormat,
    AudioInput,
    STTProvider,
    TranscriptionResult,
    TranscriptionSegment,
    VoiceChatResponse,
)
from .stt_providers import (
    BaseSTTProvider,
    FasterWhisperProvider,
    GroqWhisperProvider,
    OpenAIWhisperProvider,
    WhisperLocalProvider,
    get_stt_provider,
)
from .stt_service import STTService

__all__ = [
    # Config
    "STTConfig",
    "get_stt_config",
    # Models
    "STTProvider",
    "AudioFormat",
    "AudioInput",
    "TranscriptionSegment",
    "TranscriptionResult",
    "VoiceChatResponse",
    # Providers
    "BaseSTTProvider",
    "OpenAIWhisperProvider",
    "WhisperLocalProvider",
    "FasterWhisperProvider",
    "GroqWhisperProvider",
    "get_stt_provider",
    # Service
    "STTService",
]
