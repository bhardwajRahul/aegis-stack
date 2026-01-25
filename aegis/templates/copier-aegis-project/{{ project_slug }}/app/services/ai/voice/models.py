"""
Voice module data models.

Defines the core data structures for Speech-to-Text transcription,
audio input handling, and voice chat responses.
"""

from enum import Enum

from pydantic import BaseModel, Field


class STTProvider(str, Enum):
    """Supported Speech-to-Text providers."""

    OPENAI_WHISPER = "openai_whisper"  # OpenAI Whisper API
    WHISPER_LOCAL = "whisper_local"  # Local Whisper via HuggingFace transformers
    FASTER_WHISPER = "faster_whisper"  # SYSTRAN faster-whisper (optimized local)
    GROQ_WHISPER = "groq_whisper"  # Groq API (ultra-fast)


class AudioFormat(str, Enum):
    """Supported audio formats for transcription."""

    WAV = "wav"
    MP3 = "mp3"
    M4A = "m4a"
    WEBM = "webm"
    OGG = "ogg"
    FLAC = "flac"
    MP4 = "mp4"  # Audio track extraction


class AudioInput(BaseModel):
    """Input audio for transcription."""

    content: bytes = Field(..., description="Raw audio bytes")
    format: AudioFormat = Field(
        default=AudioFormat.WAV, description="Audio format (wav, mp3, m4a, webm, etc.)"
    )
    sample_rate: int | None = Field(
        default=None, description="Sample rate in Hz (optional)"
    )
    language: str | None = Field(
        default=None,
        description="ISO 639-1 language code (e.g., 'en', 'es'). If None, auto-detect.",
    )

    model_config = {"arbitrary_types_allowed": True}


class TranscriptionSegment(BaseModel):
    """A segment of transcribed audio with timing information."""

    text: str = Field(..., description="Transcribed text for this segment")
    start: float = Field(..., description="Start time in seconds")
    end: float = Field(..., description="End time in seconds")
    confidence: float | None = Field(
        default=None, description="Confidence score (0-1) if available"
    )


class TranscriptionResult(BaseModel):
    """Result of STT transcription."""

    text: str = Field(..., description="Full transcribed text")
    language: str | None = Field(
        default=None, description="Detected or specified language code"
    )
    duration_seconds: float | None = Field(
        default=None, description="Audio duration in seconds"
    )
    confidence: float | None = Field(
        default=None, description="Overall confidence score (0-1) if available"
    )
    provider: STTProvider = Field(..., description="Provider used for transcription")
    segments: list[TranscriptionSegment] | None = Field(
        default=None, description="Word/phrase-level segments with timing"
    )


class VoiceChatResponse(BaseModel):
    """Response from voice chat with both full and voice-optimized versions."""

    transcription: TranscriptionResult = Field(
        ..., description="The transcription of what the user said"
    )
    full_response: str = Field(..., description="Full AI agent response")
    voice_response: str = Field(
        ...,
        description="Voice-optimized response (summarized if voice_mode=True, "
        "otherwise same as full_response)",
    )
    conversation_id: str | None = Field(
        default=None, description="Conversation ID for continuity"
    )
