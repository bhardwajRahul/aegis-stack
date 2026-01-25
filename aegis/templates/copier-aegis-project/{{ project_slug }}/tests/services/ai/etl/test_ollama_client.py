"""Tests for Ollama model discovery client."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from app.services.ai.etl.clients.ollama_client import (
    OllamaClient,
    OllamaModel,
    OllamaRunningModel,
    OllamaServerStatus,
)


class TestOllamaClient:
    """Tests for OllamaClient class."""

    @pytest.mark.asyncio
    async def test_fetch_models_success(self, mock_httpx_ollama: MagicMock) -> None:
        """Test successful fetch and parsing of models."""
        client = OllamaClient()
        models = await client.fetch_models()

        assert len(models) == 3
        assert all(isinstance(m, OllamaModel) for m in models)

        # Verify first model
        llama = models[0]
        assert llama.name == "llama3.2:latest"
        assert llama.model_id == "llama3.2:latest"  # Full name with tag for Ollama API
        assert llama.family == "llama"
        assert llama.parameter_size == "3B"

    @pytest.mark.asyncio
    async def test_fetch_models_custom_base_url(self) -> None:
        """Test client respects custom base URL."""
        with patch("app.services.ai.etl.clients.ollama_client.httpx") as mock_httpx:
            mock_response = MagicMock()
            mock_response.json.return_value = {"models": []}
            mock_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            mock_httpx.AsyncClient.return_value = mock_client

            client = OllamaClient(base_url="http://custom-host:11434")
            await client.fetch_models()

            # Verify correct URL was called
            mock_client.get.assert_called_once_with("http://custom-host:11434/api/tags")

    @pytest.mark.asyncio
    async def test_fetch_models_connection_error(self) -> None:
        """Test that connection errors are propagated."""
        with patch("app.services.ai.etl.clients.ollama_client.httpx") as mock_httpx:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                side_effect=httpx.ConnectError("Connection refused")
            )
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            mock_httpx.AsyncClient.return_value = mock_client
            mock_httpx.ConnectError = httpx.ConnectError

            client = OllamaClient()

            with pytest.raises(httpx.ConnectError):
                await client.fetch_models()

    @pytest.mark.asyncio
    async def test_fetch_models_handles_parse_errors(self) -> None:
        """Test that invalid model entries are skipped with warning."""
        with patch("app.services.ai.etl.clients.ollama_client.httpx") as mock_httpx:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "models": [
                    {
                        "name": "valid-model:latest",
                        "size": 1000,
                        "digest": "abc",
                        "modified_at": "2024-01-01T00:00:00Z",
                    },
                    "not a dict",  # Invalid format
                ]
            }
            mock_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            mock_httpx.AsyncClient.return_value = mock_client

            client = OllamaClient()
            models = await client.fetch_models()

            # Should only have the valid model
            assert len(models) == 1
            assert models[0].name == "valid-model:latest"

    @pytest.mark.asyncio
    async def test_is_available_true(self) -> None:
        """Test is_available returns True when server responds."""
        with patch("app.services.ai.etl.clients.ollama_client.httpx") as mock_httpx:
            mock_response = MagicMock()
            mock_response.status_code = 200

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            mock_httpx.AsyncClient.return_value = mock_client

            client = OllamaClient()
            result = await client.is_available()

            assert result is True

    @pytest.mark.asyncio
    async def test_is_available_false_on_error(self) -> None:
        """Test is_available returns False when server is unreachable."""
        with patch("app.services.ai.etl.clients.ollama_client.httpx") as mock_httpx:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                side_effect=httpx.ConnectError("Connection refused")
            )
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            mock_httpx.AsyncClient.return_value = mock_client

            client = OllamaClient()
            result = await client.is_available()

            assert result is False


class TestOllamaClientParsing:
    """Tests for OllamaClient parsing logic."""

    def test_parse_model_complete(self, mock_ollama_response: dict[str, Any]) -> None:
        """Test parsing a complete model with all fields."""
        client = OllamaClient()
        raw = mock_ollama_response["models"][0]
        model = client._parse_model(raw)

        assert model.name == "llama3.2:latest"
        assert model.size == 2019393189
        assert (
            model.digest
            == "a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72"
        )
        assert model.parameter_size == "3B"
        assert model.quantization_level == "Q4_0"
        assert model.family == "llama"

    def test_parse_model_minimal(
        self, mock_ollama_response_minimal: dict[str, Any]
    ) -> None:
        """Test parsing a model with minimal/missing fields."""
        client = OllamaClient()
        raw = mock_ollama_response_minimal["models"][0]
        model = client._parse_model(raw)

        assert model.name == "test-model:latest"
        assert model.size == 1000000
        assert model.digest == "abc123"
        assert model.parameter_size is None
        assert model.quantization_level is None
        assert model.family is None


class TestOllamaModel:
    """Tests for OllamaModel dataclass."""

    def test_model_id_keeps_full_name(self, sample_ollama_model: OllamaModel) -> None:
        """Test that model_id keeps full name including tag for Ollama API compatibility."""
        assert sample_ollama_model.model_id == "llama3.2:latest"

    def test_model_id_handles_no_tag(self) -> None:
        """Test model_id when there's no tag."""
        model = OllamaModel(
            name="custom-model",
            size=1000,
            digest="abc",
            modified_at=None,
        )
        assert model.model_id == "custom-model"

    def test_size_gb_calculation(self, sample_ollama_model: OllamaModel) -> None:
        """Test size_gb property calculates correctly."""
        # 2019393189 bytes = ~1.88 GB
        assert 1.8 < sample_ollama_model.size_gb < 2.0

    def test_size_gb_zero(self) -> None:
        """Test size_gb with zero size."""
        model = OllamaModel(
            name="empty",
            size=0,
            digest="abc",
            modified_at=None,
        )
        assert model.size_gb == 0.0


class TestOllamaRunningModel:
    """Tests for OllamaRunningModel dataclass."""

    def test_size_vram_gb_calculation(self) -> None:
        """Test size_vram_gb property calculates correctly."""
        model = OllamaRunningModel(
            name="qwen2.5:14b",
            size=8000000000,  # 8GB
            size_vram=4000000000,  # 4GB VRAM
            digest="abc123",
            expires_at=None,
        )
        # 4GB = 4000000000 / 1024^3 ≈ 3.73
        assert 3.7 < model.size_vram_gb < 3.8

    def test_is_warm(self) -> None:
        """Test is_warm always returns True for running models."""
        model = OllamaRunningModel(
            name="llama3.2:latest",
            size=2000000000,
            size_vram=2000000000,
            digest="def456",
            expires_at=None,
        )
        assert model.is_warm is True


class TestOllamaServerStatus:
    """Tests for OllamaServerStatus dataclass."""

    def test_server_status_available(self) -> None:
        """Test server status when available."""
        running_models = [
            OllamaRunningModel(
                name="qwen2.5:14b",
                size=8000000000,
                size_vram=4000000000,
                digest="abc123",
                expires_at=None,
            )
        ]
        status = OllamaServerStatus(
            available=True,
            version="0.5.0",
            running_models=running_models,
            installed_models_count=5,
            total_vram_gb=3.73,
        )
        assert status.available is True
        assert len(status.running_models) == 1
        assert status.installed_models_count == 5

    def test_server_status_unavailable(self) -> None:
        """Test server status when unavailable."""
        status = OllamaServerStatus(
            available=False,
            version=None,
            running_models=[],
            installed_models_count=0,
            total_vram_gb=0.0,
        )
        assert status.available is False
        assert status.running_models == []


class TestOllamaClientRunningModels:
    """Tests for OllamaClient running models methods."""

    @pytest.mark.asyncio
    async def test_fetch_running_models_success(self) -> None:
        """Test successful fetch of running models."""
        with patch("app.services.ai.etl.clients.ollama_client.httpx") as mock_httpx:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "models": [
                    {
                        "name": "qwen2.5:14b",
                        "size": 8000000000,
                        "size_vram": 4000000000,
                        "digest": "abc123",
                        "expires_at": "2025-01-01T12:00:00Z",
                    }
                ]
            }
            mock_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            mock_httpx.AsyncClient.return_value = mock_client

            client = OllamaClient()
            models = await client.fetch_running_models()

            assert len(models) == 1
            assert models[0].name == "qwen2.5:14b"
            assert models[0].size_vram == 4000000000

    @pytest.mark.asyncio
    async def test_fetch_running_models_empty(self) -> None:
        """Test fetch when no models are running."""
        with patch("app.services.ai.etl.clients.ollama_client.httpx") as mock_httpx:
            mock_response = MagicMock()
            mock_response.json.return_value = {"models": []}
            mock_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            mock_httpx.AsyncClient.return_value = mock_client

            client = OllamaClient()
            models = await client.fetch_running_models()

            assert models == []


class TestOllamaClientServerStatus:
    """Tests for OllamaClient server status method."""

    @pytest.mark.asyncio
    async def test_get_server_status_available(self) -> None:
        """Test get_server_status when server is available."""
        with patch("app.services.ai.etl.clients.ollama_client.httpx") as mock_httpx:
            # Mock responses for is_available, fetch_running_models, fetch_models
            tags_response = MagicMock()
            tags_response.status_code = 200
            tags_response.json.return_value = {
                "models": [
                    {
                        "name": "llama3.2:latest",
                        "size": 2000000000,
                        "digest": "abc",
                        "modified_at": "2024-01-01T00:00:00Z",
                    }
                ]
            }
            tags_response.raise_for_status = MagicMock()

            ps_response = MagicMock()
            ps_response.json.return_value = {
                "models": [
                    {
                        "name": "llama3.2:latest",
                        "size": 2000000000,
                        "size_vram": 1500000000,
                        "digest": "abc",
                        "expires_at": "2025-01-01T12:00:00Z",
                    }
                ]
            }
            ps_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()

            # Return different responses based on URL
            async def mock_get(url: str) -> MagicMock:
                if "/api/ps" in url:
                    return ps_response
                return tags_response

            mock_client.get = mock_get
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            mock_httpx.AsyncClient.return_value = mock_client

            client = OllamaClient()
            status = await client.get_server_status()

            assert status.available is True
            assert status.installed_models_count == 1
            assert len(status.running_models) == 1
            assert status.total_vram_gb > 0

    @pytest.mark.asyncio
    async def test_get_server_status_unavailable(self) -> None:
        """Test get_server_status when server is unavailable."""
        with patch("app.services.ai.etl.clients.ollama_client.httpx") as mock_httpx:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                side_effect=httpx.ConnectError("Connection refused")
            )
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            mock_httpx.AsyncClient.return_value = mock_client

            client = OllamaClient()
            status = await client.get_server_status()

            assert status.available is False
            assert status.running_models == []
            assert status.installed_models_count == 0
            assert status.total_vram_gb == 0.0
