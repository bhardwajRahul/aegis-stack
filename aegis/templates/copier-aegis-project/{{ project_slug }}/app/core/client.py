"""
Shared HTTP client for internal API calls.

Used by frontend components to call backend API endpoints. Provides
consistent base URL, timeout, error handling, JSON parsing, automatic
bearer-token attachment, and an unauthorized callback for triggering
session-level logout.

This is the **One True Client** for the Aegis frontend — every server
call from a view, modal, or service should go through it. Raw
``httpx.AsyncClient`` use outside this module is a code smell.
"""

import inspect
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

import httpx
from app.core.config import settings
from app.core.log import logger

TokenProvider = Callable[[], str | None] | Callable[[], Awaitable[str | None]]
UnauthorizedHandler = Callable[[], None] | Callable[[], Awaitable[None]]


class APIClient:
    """HTTP client for internal API calls."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 10.0,
        get_token: TokenProvider | None = None,
        on_unauthorized: UnauthorizedHandler | None = None,
    ) -> None:
        self.base_url = base_url or f"http://localhost:{settings.PORT}"
        self.timeout = timeout
        self.get_token = get_token
        self.on_unauthorized = on_unauthorized

    async def get(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> dict | list | None:
        """GET request. Returns parsed JSON or None on error."""
        return await self._request("GET", endpoint, params=params)

    async def post(
        self, endpoint: str, json: dict[str, Any] | None = None
    ) -> dict | list | None:
        """POST request with a JSON body. Returns parsed JSON or None on error."""
        return await self._request("POST", endpoint, json=json)

    async def post_form(
        self, endpoint: str, data: dict[str, str]
    ) -> dict | list | None:
        """
        POST request with a form-encoded body.

        Used for endpoints that consume ``application/x-www-form-urlencoded``
        — most notably FastAPI's ``OAuth2PasswordRequestForm`` at
        ``/api/v1/auth/token``.
        """
        return await self._request("POST", endpoint, form_data=data)

    async def post_multipart(
        self,
        endpoint: str,
        files: dict[str, tuple[str, bytes, str]],
    ) -> dict | list | None:
        """
        POST a ``multipart/form-data`` body.

        ``files`` shape matches httpx: ``{field_name: (filename, bytes, mime)}``.
        Bearer token + 401 → ``on_unauthorized`` are handled the same as
        the JSON-bodied methods. ``Content-Type`` is **not** set manually —
        httpx infers ``multipart/form-data; boundary=…`` from ``files=``.
        """
        return await self._request("POST", endpoint, files=files)

    async def put(
        self, endpoint: str, json: dict[str, Any] | None = None
    ) -> dict | list | None:
        """PUT request. Returns parsed JSON or None on error."""
        return await self._request("PUT", endpoint, json=json)

    async def delete(self, endpoint: str) -> dict | list | None:
        """DELETE request. Returns parsed JSON or None on error."""
        return await self._request("DELETE", endpoint)

    async def request_with_status(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        form_data: dict[str, str] | None = None,
    ) -> tuple[int, dict | list | None]:
        """
        Status-aware variant: returns ``(status_code, body)`` instead of
        raising or hiding the status code.

        Use this when the caller needs to branch on specific status codes
        (e.g. 204 success vs 403 forbidden, or 200 vs 400 validation).
        Bearer token is still attached and 401 still fires
        ``on_unauthorized`` — the caller just additionally sees the code.

        Returns:
            ``(0, None)`` on network/timeout errors;
            ``(status_code, parsed_json or None)`` otherwise.
        """
        url = f"{self.base_url}{endpoint}"
        headers: dict[str, str] = {}
        token = await self._resolve_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if form_data is not None:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method,
                    url,
                    params=params,
                    json=json,
                    data=form_data,
                    headers=headers,
                )
                if response.status_code == 401:
                    await self._emit_unauthorized()
                if response.status_code == 204 or not response.content:
                    return response.status_code, None
                try:
                    return response.status_code, response.json()
                except Exception:
                    return response.status_code, None
        except httpx.TimeoutException:
            logger.error("api_client.timeout", url=url, method=method)
        except httpx.ConnectError:
            logger.error("api_client.connect_error", url=url, method=method)
        except Exception as e:
            logger.error("api_client.error", url=url, method=method, error=str(e))
        return 0, None

    @asynccontextmanager
    async def stream(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> AsyncIterator[httpx.Response]:
        """
        Open a streaming response (used for SSE).

        Yields the raw ``httpx.Response`` so the caller can iterate via
        ``response.aiter_lines()`` or ``response.aiter_bytes()``. Bearer
        token is attached automatically; a 401 fires
        ``on_unauthorized``.

        Example::

            async with api_client.stream("GET", "/events/stream") as resp:
                async for line in resp.aiter_lines():
                    ...
        """
        url = f"{self.base_url}{endpoint}"
        headers: dict[str, str] = dict(kwargs.pop("headers", None) or {})
        token = await self._resolve_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"

        async with (
            httpx.AsyncClient(timeout=self.timeout) as client,
            client.stream(method, url, headers=headers, **kwargs) as response,
        ):
            if response.status_code == 401:
                await self._emit_unauthorized()
            yield response

    async def _resolve_token(self) -> str | None:
        if self.get_token is None:
            return None
        result = self.get_token()
        if inspect.isawaitable(result):
            return await result
        return result

    async def _emit_unauthorized(self) -> None:
        if self.on_unauthorized is None:
            return
        result = self.on_unauthorized()
        if inspect.isawaitable(result):
            await result

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        form_data: dict[str, str] | None = None,
        files: dict[str, tuple[str, bytes, str]] | None = None,
    ) -> dict | list | None:
        url = f"{self.base_url}{endpoint}"
        headers: dict[str, str] = {}
        token = await self._resolve_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if form_data is not None:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        # NOTE: do NOT set Content-Type for ``files=`` — httpx generates
        # the multipart boundary itself. Setting it here would clobber it.
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method,
                    url,
                    params=params,
                    json=json,
                    data=form_data,
                    files=files,
                    headers=headers,
                )
                response.raise_for_status()
                if response.status_code == 204:
                    return None
                return response.json()
        except httpx.TimeoutException:
            logger.error("api_client.timeout", url=url, method=method)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                await self._emit_unauthorized()
            logger.error(
                "api_client.http_error",
                url=url,
                method=method,
                status_code=e.response.status_code,
            )
        except httpx.ConnectError:
            logger.error("api_client.connect_error", url=url, method=method)
        except Exception as e:
            logger.error("api_client.error", url=url, method=method, error=str(e))
        return None


def get_api_client() -> APIClient:
    """Dependency provider for APIClient."""
    return APIClient()
