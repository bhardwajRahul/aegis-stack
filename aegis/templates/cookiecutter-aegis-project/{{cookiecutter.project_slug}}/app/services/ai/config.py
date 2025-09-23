"""
AI service configuration models.

Configuration management for AI service providers, models, and settings.
Full implementation will be added in ticket #162.
"""

from pydantic import BaseModel


class AIServiceConfig(BaseModel):
    """
    Base configuration for AI service.

    This is a foundation stub - full configuration implementation
    will be added in ticket #162 (AI Service Configuration).
    """

    enabled: bool = True

    # Provider and model configuration will be added in #162
    # provider: str = "groq"
    # model: str = "llama-3.1-8b-instant"
    # temperature: float = 0.7
    # max_tokens: int = 1000
