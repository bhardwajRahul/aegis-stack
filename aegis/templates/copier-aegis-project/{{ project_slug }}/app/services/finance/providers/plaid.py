"""Plaid API client — a thin async httpx wrapper over the endpoints the finance
service uses. No SDK dependency; verified against the sandbox.

Endpoints: ``link/token/create``, ``item/public_token/exchange``,
``accounts/get``, ``transactions/sync`` (cursor-paged), plus the
``sandbox/public_token/create`` shortcut used by the sandbox-connect flow.

Sign convention: Plaid amounts are POSITIVE for money leaving the account
(outflow). The sync layer negates them to this project's convention where a
negative amount is an outflow.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings

_ENV_HOSTS = {
    "sandbox": "https://sandbox.plaid.com",
    "development": "https://development.plaid.com",
    "production": "https://production.plaid.com",
}


class PlaidError(RuntimeError):
    """A Plaid API error (``error_code`` carries the machine-readable reason)."""

    def __init__(self, error_code: str, message: str) -> None:
        self.error_code = error_code
        super().__init__(f"{error_code}: {message}")


class PlaidClient:
    """Async Plaid client. Reads credentials/environment from settings unless
    overridden (handy for tests)."""

    def __init__(
        self,
        *,
        client_id: str | None = None,
        secret: str | None = None,
        environment: str | None = None,
    ) -> None:
        self._client_id = client_id or settings.PLAID_CLIENT_ID
        self._secret = secret or settings.PLAID_SECRET
        self._environment = environment or settings.PLAID_ENV
        self._base_url = _ENV_HOSTS.get(self._environment, _ENV_HOSTS["sandbox"])

    @property
    def environment(self) -> str:
        return self._environment

    async def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        if not (self._client_id and self._secret):
            raise PlaidError(
                "missing_credentials",
                "PLAID_CLIENT_ID / PLAID_SECRET are not configured.",
            )
        payload = {"client_id": self._client_id, "secret": self._secret, **body}
        async with httpx.AsyncClient(base_url=self._base_url, timeout=30.0) as client:
            response = await client.post(path, json=payload)
        try:
            data = response.json()
        except ValueError:
            # Non-JSON body (e.g. an HTML 502 from an upstream proxy). Surface it
            # as a PlaidError so callers get consistent error handling instead of
            # a raw JSONDecodeError.
            raise PlaidError(
                "invalid_response",
                f"Non-JSON response (HTTP {response.status_code}): "
                f"{response.text[:200]}",
            ) from None
        if response.status_code >= 400:
            raise PlaidError(
                data.get("error_code", "unknown_error"),
                data.get("error_message", response.text),
            )
        return data

    async def create_link_token(
        self,
        *,
        user_id: object,
        client_name: str = "Aegis Finance",
        products: list[str] | None = None,
    ) -> str:
        """Create a Link token the frontend hands to Plaid Link."""
        body: dict[str, Any] = {
            "user": {"client_user_id": str(user_id)},
            "client_name": client_name,
            "products": products or ["transactions"],
            "country_codes": ["US"],
            "language": "en",
        }
        if settings.PLAID_WEBHOOK_URL:
            body["webhook"] = settings.PLAID_WEBHOOK_URL
        if settings.PLAID_REDIRECT_URI:
            body["redirect_uri"] = settings.PLAID_REDIRECT_URI
        return (await self._post("/link/token/create", body))["link_token"]

    async def create_hosted_link(
        self,
        *,
        user_id: object,
        client_name: str = "Aegis Finance",
        products: list[str] | None = None,
    ) -> tuple[str, str]:
        """Create a Hosted Link session: Plaid hosts the entire connect UI.

        Returns ``(hosted_link_url, link_token)``. Open the URL in the browser;
        poll ``link_public_tokens(link_token)`` server-side for the result.
        """
        body: dict[str, Any] = {
            "user": {"client_user_id": str(user_id)},
            "client_name": client_name,
            "products": products or ["transactions"],
            "country_codes": ["US"],
            "language": "en",
            "hosted_link": {},
        }
        if settings.PLAID_WEBHOOK_URL:
            body["webhook"] = settings.PLAID_WEBHOOK_URL
        data = await self._post("/link/token/create", body)
        return data["hosted_link_url"], data["link_token"]

    async def link_public_tokens(self, link_token: str) -> list[str]:
        """Public tokens produced by a (completed) Hosted Link session. Empty
        while the user hasn't finished — the caller polls until non-empty."""
        data = await self._post("/link/token/get", {"link_token": link_token})
        tokens: list[str] = []
        for session in data.get("link_sessions") or []:
            results = session.get("results") or {}
            for added in results.get("item_add_results") or []:
                public_token = added.get("public_token")
                if public_token:
                    tokens.append(public_token)
        return tokens

    async def exchange_public_token(self, public_token: str) -> tuple[str, str]:
        """Exchange a public token for a long-lived (access_token, item_id)."""
        data = await self._post(
            "/item/public_token/exchange", {"public_token": public_token}
        )
        return data["access_token"], data["item_id"]

    async def get_accounts(
        self, access_token: str
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Return ``(accounts, item)`` for a connection."""
        data = await self._post("/accounts/get", {"access_token": access_token})
        return data["accounts"], data.get("item", {})

    async def get_institution_name(self, institution_id: str) -> str | None:
        """Human-readable institution name for a Plaid institution id (``ins_*``).
        Returns None if Plaid can't resolve it."""
        data = await self._post(
            "/institutions/get_by_id",
            {"institution_id": institution_id, "country_codes": ["US"]},
        )
        return (data.get("institution") or {}).get("name")

    async def remove_item(self, access_token: str) -> None:
        """Remove the Item at Plaid so the access token is invalidated and Plaid
        stops billing/updating it. Idempotent from our side: the caller disconnects
        locally regardless of the outcome here."""
        await self._post("/item/remove", {"access_token": access_token})

    async def sync_transactions(
        self, access_token: str, cursor: str | None = None
    ) -> dict[str, Any]:
        """One page of the cursor-based transaction sync (added/modified/removed
        + ``next_cursor`` + ``has_more``)."""
        body: dict[str, Any] = {"access_token": access_token}
        if cursor:
            body["cursor"] = cursor
        return await self._post("/transactions/sync", body)

    async def get_holdings(
        self, access_token: str
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Return ``(holdings, securities)`` for an investments-enabled item."""
        data = await self._post(
            "/investments/holdings/get", {"access_token": access_token}
        )
        return data.get("holdings", []), data.get("securities", [])

    async def get_investment_transactions(
        self,
        access_token: str,
        start_date: str,
        end_date: str,
        *,
        offset: int = 0,
        count: int = 500,
    ) -> dict[str, Any]:
        """One page of ``/investments/transactions/get``.

        Unlike ``/transactions/sync`` this endpoint has no cursor: it pages a
        date range by ``offset`` and reports ``total_investment_transactions``.
        Callers re-fetch the window and dedup by ``investment_transaction_id``.
        Returns the raw payload (``investment_transactions`` + ``securities`` +
        ``total_investment_transactions``)."""
        return await self._post(
            "/investments/transactions/get",
            {
                "access_token": access_token,
                "start_date": start_date,
                "end_date": end_date,
                "options": {"offset": offset, "count": count},
            },
        )

    async def sandbox_public_token(
        self,
        *,
        institution_id: str = "ins_109508",
        products: list[str] | None = None,
    ) -> str:
        """Sandbox-only: mint a public token without the Link UI (for testing)."""
        data = await self._post(
            "/sandbox/public_token/create",
            {
                "institution_id": institution_id,
                "initial_products": products or ["transactions", "investments"],
            },
        )
        return data["public_token"]
