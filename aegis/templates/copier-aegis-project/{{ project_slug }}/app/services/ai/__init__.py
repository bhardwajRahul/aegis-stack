"""
AI service module.

Provides AI chatbot functionality with configurable AI framework,
including Speech-to-Text (STT) capabilities for voice interactions.
"""

from .voice import (
    AudioFormat,
    AudioInput,
    STTProvider,
    STTService,
    TranscriptionResult,
    TranscriptionSegment,
    VoiceChatResponse,
)

__all__ = [
    # Voice/STT exports
    "STTProvider",
    "AudioFormat",
    "AudioInput",
    "TranscriptionSegment",
    "TranscriptionResult",
    "VoiceChatResponse",
    "STTService",
]
