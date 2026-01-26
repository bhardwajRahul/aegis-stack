"""
Voice module for AI service.

Provides Speech-to-Text (STT) and Text-to-Speech (TTS) capabilities
with provider abstraction supporting multiple cloud and open-source providers.
"""

from .config import STTConfig, get_stt_config
from .models import (
    AudioFormat,
    AudioInput,
    OpenAIVoice,
    SpeechRequest,
    SpeechResult,
    STTProvider,
    TranscriptionResult,
    TranscriptionSegment,
    TTSProvider,
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
from .tts_config import TTSConfig, get_tts_config
from .tts_providers import (
    BaseTTSProvider,
    OpenAITTSProvider,
    PiperLocalProvider,
    get_tts_provider,
)
from .tts_service import TTSService

__all__ = [
    # STT Config
    "STTConfig",
    "get_stt_config",
    # TTS Config
    "TTSConfig",
    "get_tts_config",
    # Models
    "STTProvider",
    "TTSProvider",
    "OpenAIVoice",
    "AudioFormat",
    "AudioInput",
    "TranscriptionSegment",
    "TranscriptionResult",
    "SpeechRequest",
    "SpeechResult",
    "VoiceChatResponse",
    # STT Providers
    "BaseSTTProvider",
    "OpenAIWhisperProvider",
    "WhisperLocalProvider",
    "FasterWhisperProvider",
    "GroqWhisperProvider",
    "get_stt_provider",
    # TTS Providers
    "BaseTTSProvider",
    "OpenAITTSProvider",
    "PiperLocalProvider",
    "get_tts_provider",
    # Services
    "STTService",
    "TTSService",
]
