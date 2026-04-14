"""
Tests for APIClient.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.core.client import APIClient


class TestAPIClient:
    def test_default_base_url(self) -> None:
        client = APIClient()
        assert "localhost" in client.base_url
        assert "8000" in client.base_url

    def test_custom_base_url(self) -> None:
        client = APIClient(base_url="http://example.com")
        assert client.base_url == "http://example.com"

    def test_custom_timeout(self) -> None:
        client = APIClient(timeout=30.0)
        assert client.timeout == 30.0

    @pytest.mark.asyncio
    async def test_get_success(self) -> None:
        client = APIClient(base_url="http://test")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "ok"}
        mock_response.raise_for_status = MagicMock()

        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=None)
        mock_http.request = AsyncMock(return_value=mock_response)

        with patch("app.core.client.httpx.AsyncClient", return_value=mock_http):
            result = await client.get("/api/test")

        assert result == {"data": "ok"}

    @pytest.mark.asyncio
    async def test_get_timeout_returns_none(self) -> None:
        import httpx

        client = APIClient(base_url="http://test")
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=None)
        mock_http.request = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

        with patch("app.core.client.httpx.AsyncClient", return_value=mock_http):
            result = await client.get("/api/test")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_connect_error_returns_none(self) -> None:
        import httpx

        client = APIClient(base_url="http://test")
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=None)
        mock_http.request = AsyncMock(side_effect=httpx.ConnectError("refused"))

        with patch("app.core.client.httpx.AsyncClient", return_value=mock_http):
            result = await client.get("/api/test")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_http_error_returns_none(self) -> None:
        import httpx

        client = APIClient(base_url="http://test")
        mock_response = MagicMock()
        mock_response.status_code = 500

        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=None)
        mock_http.request = AsyncMock(return_value=mock_response)
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500", request=MagicMock(), response=mock_response
        )

        with patch("app.core.client.httpx.AsyncClient", return_value=mock_http):
            result = await client.get("/api/test")

        assert result is None

    @pytest.mark.asyncio
    async def test_204_returns_none(self) -> None:
        client = APIClient(base_url="http://test")
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.raise_for_status = MagicMock()

        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=None)
        mock_http.request = AsyncMock(return_value=mock_response)

        with patch("app.core.client.httpx.AsyncClient", return_value=mock_http):
            result = await client.get("/api/test")

        assert result is None
