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

    @pytest.mark.asyncio
    async def test_bearer_token_attached_when_get_token_returns_value(
        self,
    ) -> None:
        client = APIClient(base_url="http://test", get_token=lambda: "tok-abc")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True}
        mock_response.raise_for_status = MagicMock()

        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=None)
        mock_http.request = AsyncMock(return_value=mock_response)

        with patch("app.core.client.httpx.AsyncClient", return_value=mock_http):
            await client.get("/api/test")

        _, kwargs = mock_http.request.call_args
        assert kwargs["headers"]["Authorization"] == "Bearer tok-abc"

    @pytest.mark.asyncio
    async def test_no_authorization_header_when_get_token_returns_none(
        self,
    ) -> None:
        client = APIClient(base_url="http://test", get_token=lambda: None)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True}
        mock_response.raise_for_status = MagicMock()

        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=None)
        mock_http.request = AsyncMock(return_value=mock_response)

        with patch("app.core.client.httpx.AsyncClient", return_value=mock_http):
            await client.get("/api/test")

        _, kwargs = mock_http.request.call_args
        headers = kwargs.get("headers") or {}
        assert "Authorization" not in headers

    @pytest.mark.asyncio
    async def test_no_authorization_header_when_get_token_not_provided(
        self,
    ) -> None:
        client = APIClient(base_url="http://test")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True}
        mock_response.raise_for_status = MagicMock()

        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=None)
        mock_http.request = AsyncMock(return_value=mock_response)

        with patch("app.core.client.httpx.AsyncClient", return_value=mock_http):
            await client.get("/api/test")

        _, kwargs = mock_http.request.call_args
        headers = kwargs.get("headers") or {}
        assert "Authorization" not in headers

    @pytest.mark.asyncio
    async def test_401_invokes_on_unauthorized_callback(self) -> None:
        import httpx

        called: list[bool] = []

        def on_unauthorized() -> None:
            called.append(True)

        client = APIClient(
            base_url="http://test",
            get_token=lambda: "tok",
            on_unauthorized=on_unauthorized,
        )
        mock_response = MagicMock()
        mock_response.status_code = 401

        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=None)
        mock_http.request = AsyncMock(return_value=mock_response)
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401", request=MagicMock(), response=mock_response
        )

        with patch("app.core.client.httpx.AsyncClient", return_value=mock_http):
            result = await client.get("/api/test")

        assert result is None
        assert called == [True]

    @pytest.mark.asyncio
    async def test_async_get_token_supported(self) -> None:
        async def fetch_token() -> str:
            return "async-tok"

        client = APIClient(base_url="http://test", get_token=fetch_token)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True}
        mock_response.raise_for_status = MagicMock()

        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=None)
        mock_http.request = AsyncMock(return_value=mock_response)

        with patch("app.core.client.httpx.AsyncClient", return_value=mock_http):
            await client.get("/api/test")

        _, kwargs = mock_http.request.call_args
        assert kwargs["headers"]["Authorization"] == "Bearer async-tok"

    @pytest.mark.asyncio
    async def test_post_form_sends_form_encoded_body(self) -> None:
        client = APIClient(base_url="http://test")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "abc"}
        mock_response.raise_for_status = MagicMock()

        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=None)
        mock_http.request = AsyncMock(return_value=mock_response)

        with patch("app.core.client.httpx.AsyncClient", return_value=mock_http):
            result = await client.post_form(
                "/api/v1/auth/token",
                {"username": "u@x.com", "password": "pw"},
            )

        assert result == {"access_token": "abc"}
        _, kwargs = mock_http.request.call_args
        # httpx accepts ``data=`` kwarg for form-encoded bodies
        assert kwargs["data"] == {"username": "u@x.com", "password": "pw"}
        # Should NOT have set json= for a form post
        assert kwargs.get("json") is None
        # Content-Type header set explicitly
        assert kwargs["headers"]["Content-Type"] == "application/x-www-form-urlencoded"

    @pytest.mark.asyncio
    async def test_post_form_attaches_bearer_token(self) -> None:
        client = APIClient(base_url="http://test", get_token=lambda: "tok")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_response.raise_for_status = MagicMock()

        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=None)
        mock_http.request = AsyncMock(return_value=mock_response)

        with patch("app.core.client.httpx.AsyncClient", return_value=mock_http):
            await client.post_form("/api/v1/foo", {"k": "v"})

        _, kwargs = mock_http.request.call_args
        assert kwargs["headers"]["Authorization"] == "Bearer tok"

    @pytest.mark.asyncio
    async def test_post_form_returns_none_on_error(self) -> None:
        import httpx

        client = APIClient(base_url="http://test")
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401", request=MagicMock(), response=mock_response
        )

        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=None)
        mock_http.request = AsyncMock(return_value=mock_response)

        with patch("app.core.client.httpx.AsyncClient", return_value=mock_http):
            result = await client.post_form("/api/v1/auth/token", {"x": "y"})

        assert result is None

    @pytest.mark.asyncio
    async def test_stream_attaches_bearer_token(self) -> None:
        client = APIClient(base_url="http://test", get_token=lambda: "tok")

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_stream_ctx = AsyncMock()
        mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream_ctx.__aexit__ = AsyncMock(return_value=None)

        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=None)
        mock_http.stream = MagicMock(return_value=mock_stream_ctx)

        with patch("app.core.client.httpx.AsyncClient", return_value=mock_http):
            async with client.stream("GET", "/events/stream") as resp:
                assert resp is mock_response

        _, kwargs = mock_http.stream.call_args
        assert kwargs["headers"]["Authorization"] == "Bearer tok"

    @pytest.mark.asyncio
    async def test_stream_emits_unauthorized_on_401(self) -> None:
        called: list[bool] = []

        client = APIClient(
            base_url="http://test",
            get_token=lambda: "tok",
            on_unauthorized=lambda: called.append(True),
        )

        mock_response = MagicMock()
        mock_response.status_code = 401

        mock_stream_ctx = AsyncMock()
        mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream_ctx.__aexit__ = AsyncMock(return_value=None)

        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=None)
        mock_http.stream = MagicMock(return_value=mock_stream_ctx)

        with patch("app.core.client.httpx.AsyncClient", return_value=mock_http):
            async with client.stream("GET", "/events/stream") as _:
                pass

        assert called == [True]

    # ---- request_with_status ----

    @pytest.mark.asyncio
    async def test_request_with_status_returns_status_and_body_on_200(
        self,
    ) -> None:
        client = APIClient(base_url="http://test")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True}

        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=None)
        mock_http.request = AsyncMock(return_value=mock_response)

        with patch("app.core.client.httpx.AsyncClient", return_value=mock_http):
            status, body = await client.request_with_status("GET", "/api/x")

        assert status == 200
        assert body == {"ok": True}

    @pytest.mark.asyncio
    async def test_request_with_status_returns_204_with_none_body(self) -> None:
        client = APIClient(base_url="http://test")
        mock_response = MagicMock()
        mock_response.status_code = 204

        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=None)
        mock_http.request = AsyncMock(return_value=mock_response)

        with patch("app.core.client.httpx.AsyncClient", return_value=mock_http):
            status, body = await client.request_with_status("DELETE", "/api/x")

        assert status == 204
        assert body is None

    @pytest.mark.asyncio
    async def test_request_with_status_returns_4xx_without_raising(self) -> None:
        client = APIClient(base_url="http://test")
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.json.return_value = {"detail": "forbidden"}

        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=None)
        mock_http.request = AsyncMock(return_value=mock_response)

        with patch("app.core.client.httpx.AsyncClient", return_value=mock_http):
            status, body = await client.request_with_status("DELETE", "/api/orgs/1")

        assert status == 403
        assert body == {"detail": "forbidden"}

    @pytest.mark.asyncio
    async def test_request_with_status_returns_zero_on_network_error(
        self,
    ) -> None:
        import httpx

        client = APIClient(base_url="http://test")
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=None)
        mock_http.request = AsyncMock(side_effect=httpx.ConnectError("refused"))

        with patch("app.core.client.httpx.AsyncClient", return_value=mock_http):
            status, body = await client.request_with_status("GET", "/api/x")

        assert status == 0
        assert body is None

    @pytest.mark.asyncio
    async def test_request_with_status_attaches_bearer(self) -> None:
        client = APIClient(base_url="http://test", get_token=lambda: "tok")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}

        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=None)
        mock_http.request = AsyncMock(return_value=mock_response)

        with patch("app.core.client.httpx.AsyncClient", return_value=mock_http):
            await client.request_with_status("GET", "/api/x")

        _, kwargs = mock_http.request.call_args
        assert kwargs["headers"]["Authorization"] == "Bearer tok"

    @pytest.mark.asyncio
    async def test_request_with_status_fires_on_unauthorized_on_401(
        self,
    ) -> None:
        called: list[bool] = []

        client = APIClient(
            base_url="http://test",
            on_unauthorized=lambda: called.append(True),
        )
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"detail": "expired"}

        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=None)
        mock_http.request = AsyncMock(return_value=mock_response)

        with patch("app.core.client.httpx.AsyncClient", return_value=mock_http):
            status, _body = await client.request_with_status("GET", "/api/x")

        assert status == 401
        assert called == [True]

    # ---- post_multipart ----

    @pytest.mark.asyncio
    async def test_post_multipart_sends_files_and_attaches_bearer(self) -> None:
        client = APIClient(base_url="http://test", get_token=lambda: "tok")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"text": "hello"}
        mock_response.raise_for_status = MagicMock()

        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=None)
        mock_http.request = AsyncMock(return_value=mock_response)

        files = {"file": ("audio.wav", b"\x00\x01", "audio/wav")}
        with patch("app.core.client.httpx.AsyncClient", return_value=mock_http):
            result = await client.post_multipart("/api/v1/transcribe", files=files)

        assert result == {"text": "hello"}
        _, kwargs = mock_http.request.call_args
        assert kwargs["files"] == files
        # httpx infers multipart Content-Type from files=, so we must NOT
        # set it manually (would clobber the boundary).
        assert "Content-Type" not in kwargs.get("headers", {})
        assert kwargs["headers"]["Authorization"] == "Bearer tok"

    @pytest.mark.asyncio
    async def test_post_multipart_fires_on_unauthorized_on_401(self) -> None:
        import httpx

        called: list[bool] = []
        client = APIClient(
            base_url="http://test",
            on_unauthorized=lambda: called.append(True),
        )
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401", request=MagicMock(), response=mock_response
        )

        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=None)
        mock_http.request = AsyncMock(return_value=mock_response)

        files = {"file": ("a.wav", b"\x00", "audio/wav")}
        with patch("app.core.client.httpx.AsyncClient", return_value=mock_http):
            result = await client.post_multipart("/api/v1/transcribe", files=files)

        assert result is None
        assert called == [True]

    @pytest.mark.asyncio
    async def test_post_multipart_returns_none_on_network_error(self) -> None:
        import httpx

        client = APIClient(base_url="http://test")
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=None)
        mock_http.request = AsyncMock(side_effect=httpx.ConnectError("refused"))

        files = {"file": ("a.wav", b"\x00", "audio/wav")}
        with patch("app.core.client.httpx.AsyncClient", return_value=mock_http):
            result = await client.post_multipart("/api/v1/transcribe", files=files)

        assert result is None
