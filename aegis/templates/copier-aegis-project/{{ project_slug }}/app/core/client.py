"""
Shared HTTP client for internal API calls.

Used by frontend components to call backend API endpoints.
Provides consistent base URL, timeout, error handling, and JSON parsing.
"""

from typing import Any

import httpx
from app.core.config import settings
from app.core.log import logger


class APIClient:
    """HTTP client for internal API calls."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.base_url = base_url or f"http://localhost:{settings.PORT}"
        self.timeout = timeout

    async def get(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> dict | list | None:
        """GET request. Returns parsed JSON or None on error."""
        return await self._request("GET", endpoint, params=params)

    async def post(
        self, endpoint: str, json: dict[str, Any] | None = None
    ) -> dict | list | None:
        """POST request. Returns parsed JSON or None on error."""
        return await self._request("POST", endpoint, json=json)

    async def put(
        self, endpoint: str, json: dict[str, Any] | None = None
    ) -> dict | list | None:
        """PUT request. Returns parsed JSON or None on error."""
        return await self._request("PUT", endpoint, json=json)

    async def delete(self, endpoint: str) -> dict | list | None:
        """DELETE request. Returns parsed JSON or None on error."""
        return await self._request("DELETE", endpoint)

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict | list | None:
        url = f"{self.base_url}{endpoint}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method,
                    url,
                    params=params,
                    json=json,
                )
                response.raise_for_status()
                if response.status_code == 204:
                    return None
                return response.json()
        except httpx.TimeoutException:
            logger.error("api_client.timeout", url=url, method=method)
        except httpx.HTTPStatusError as e:
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
