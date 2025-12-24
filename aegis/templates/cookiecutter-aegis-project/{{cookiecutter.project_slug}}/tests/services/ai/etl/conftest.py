"""Shared fixtures for LLM ETL service tests."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.services.ai.etl.clients.litellm_client import LiteLLMModel
from app.services.ai.etl.clients.openrouter_client import OpenRouterModel


@pytest.fixture
def mock_openrouter_response() -> dict[str, Any]:
    """Sample OpenRouter API response with multiple models."""
    return {
        "data": [
            {
                "id": "openai/gpt-4o",
                "name": "GPT-4o",
                "description": "OpenAI's most advanced multimodal model",
                "context_length": 128000,
                "pricing": {
                    "prompt": "0.000005",
                    "completion": "0.000015",
                    "input_cache_read": "0.0000025",
                },
                "architecture": {
                    "input_modalities": ["text", "image"],
                    "output_modalities": ["text"],
                    "tokenizer": "o200k_base",
                },
                "top_provider": {
                    "max_completion_tokens": 16384,
                    "is_moderated": True,
                },
            },
            {
                "id": "anthropic/claude-3-5-sonnet",
                "name": "Claude 3.5 Sonnet",
                "description": "Anthropic's most intelligent model",
                "context_length": 200000,
                "pricing": {
                    "prompt": "0.000003",
                    "completion": "0.000015",
                },
                "architecture": {
                    "input_modalities": ["text", "image"],
                    "output_modalities": ["text"],
                },
                "top_provider": {
                    "max_completion_tokens": 8192,
                    "is_moderated": False,
                },
            },
        ]
    }


@pytest.fixture
def mock_openrouter_response_minimal() -> dict[str, Any]:
    """Minimal OpenRouter API response with optional fields missing."""
    return {
        "data": [
            {
                "id": "test/minimal-model",
            },
        ]
    }


@pytest.fixture
def mock_litellm_response() -> dict[str, Any]:
    """Sample LiteLLM model cost map response."""
    return {
        "sample_spec": {
            "max_tokens": 4096,
            "input_cost_per_token": 0.0,
            "output_cost_per_token": 0.0,
        },
        "openai/gpt-4o": {
            "litellm_provider": "openai",
            "mode": "chat",
            "max_tokens": 128000,
            "max_input_tokens": 128000,
            "max_output_tokens": 16384,
            "input_cost_per_token": 0.000005,
            "output_cost_per_token": 0.000015,
            "supports_function_calling": True,
            "supports_parallel_function_calling": True,
            "supports_vision": True,
            "supports_audio_input": False,
            "supports_audio_output": False,
            "supports_reasoning": False,
            "supports_response_schema": True,
            "supports_system_messages": True,
            "supports_prompt_caching": True,
        },
        "anthropic/claude-3-5-sonnet": {
            "litellm_provider": "anthropic",
            "mode": "chat",
            "max_tokens": 200000,
            "max_output_tokens": 8192,
            "input_cost_per_token": 0.000003,
            "output_cost_per_token": 0.000015,
            "supports_function_calling": True,
            "supports_vision": True,
            "supports_prompt_caching": True,
        },
        "text-embedding-3-small": {
            "litellm_provider": "openai",
            "mode": "embedding",
            "max_tokens": 8191,
            "input_cost_per_token": 0.00000002,
            "output_cost_per_token": 0.0,
        },
    }


@pytest.fixture
def mock_litellm_response_minimal() -> dict[str, Any]:
    """Minimal LiteLLM response with only required fields."""
    return {
        "test/minimal-model": {
            "mode": "chat",
        },
    }


@pytest.fixture
def sample_openrouter_model() -> OpenRouterModel:
    """Pre-constructed OpenRouterModel for testing."""
    return OpenRouterModel(
        model_id="openai/gpt-4o",
        name="GPT-4o",
        description="OpenAI's most advanced multimodal model",
        context_length=128000,
        max_completion_tokens=16384,
        input_modalities=["text", "image"],
        output_modalities=["text"],
        tokenizer="o200k_base",
        input_cost_per_token=0.000005,
        output_cost_per_token=0.000015,
        cache_read_cost_per_token=0.0000025,
        cache_write_cost_per_token=None,
        is_moderated=True,
    )


@pytest.fixture
def sample_litellm_model() -> LiteLLMModel:
    """Pre-constructed LiteLLMModel for testing."""
    return LiteLLMModel(
        model_id="openai/gpt-4o",
        provider="openai",
        mode="chat",
        max_tokens=128000,
        max_input_tokens=128000,
        max_output_tokens=16384,
        input_cost_per_token=0.000005,
        output_cost_per_token=0.000015,
        supports_function_calling=True,
        supports_parallel_function_calling=True,
        supports_vision=True,
        supports_audio_input=False,
        supports_audio_output=False,
        supports_reasoning=False,
        supports_response_schema=True,
        supports_system_messages=True,
        supports_prompt_caching=True,
        deprecation_date=None,
    )


@pytest.fixture
def mock_httpx_openrouter(mock_openrouter_response: dict[str, Any]):
    """Mock httpx for OpenRouter API calls."""
    with patch("app.services.ai.etl.clients.openrouter_client.httpx") as mock_httpx:
        mock_response = MagicMock()
        mock_response.json.return_value = mock_openrouter_response
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mock_httpx.AsyncClient.return_value = mock_client

        yield mock_httpx


@pytest.fixture
def mock_httpx_litellm(mock_litellm_response: dict[str, Any]):
    """Mock httpx for LiteLLM API calls."""
    with patch("app.services.ai.etl.clients.litellm_client.httpx") as mock_httpx:
        mock_response = MagicMock()
        mock_response.json.return_value = mock_litellm_response
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mock_httpx.AsyncClient.return_value = mock_client

        yield mock_httpx
