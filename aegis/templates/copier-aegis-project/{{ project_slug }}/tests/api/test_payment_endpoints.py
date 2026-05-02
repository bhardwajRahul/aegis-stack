"""
Tests for payment API endpoints.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from unittest.mock import AsyncMock

import pytest
import stripe
from app.services.payment.deps import get_payment_service
from app.services.payment.constants import (
    ProviderKeys,
    TransactionStatus,
    TransactionType,
)
from app.services.payment.models import (
    PaymentProvider,
    PaymentTransaction,
)
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel.ext.asyncio.session import AsyncSession


@contextmanager
def _override_payment_service(app: FastAPI, mock_service: object) -> Iterator[None]:
    """Swap ``get_payment_service`` for a stub that yields ``mock_service``.

    The router injects ``PaymentService`` via ``Depends(get_payment_service)``,
    so tests that want to mock service methods must override the dep in
    FastAPI's dependency registry — patching the module-level symbol in
    ``router.py`` no longer bites once DI owns construction.
    """
    app.dependency_overrides[get_payment_service] = lambda: mock_service
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_payment_service, None)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _seed_data(
    session: AsyncSession,
) -> tuple[PaymentProvider, PaymentTransaction]:
    """Seed a provider and transaction for testing."""
    provider = PaymentProvider(
        key=ProviderKeys.STRIPE,
        display_name="Stripe",
        enabled=True,
        is_test_mode=True,
    )
    session.add(provider)
    await session.flush()

    txn = PaymentTransaction(
        provider_id=provider.id,  # type: ignore[arg-type]
        provider_transaction_id="pi_test_endpoint_1",
        type=TransactionType.CHARGE,
        status=TransactionStatus.SUCCEEDED,
        amount=4999,
        currency="usd",
        description="Test charge",
    )
    session.add(txn)
    await session.commit()

    return provider, txn


# ---------------------------------------------------------------------------
# Tests: GET /api/v1/payment/transactions
# ---------------------------------------------------------------------------


class TestListTransactions:
    """Test GET /api/v1/payment/transactions endpoint."""

    @pytest.mark.asyncio
    async def test_empty_transactions(self, async_client_with_db: TestClient) -> None:
        """Returns empty list when no transactions exist.

        Uses ``async_client_with_db`` (which overrides the DB dep with
        an isolated in-memory session) instead of the plain ``client``
        fixture — otherwise the endpoint hits the dev database and
        sees whatever rows happen to be in it, which breaks the empty
        assertion non-deterministically.
        """
        response = async_client_with_db.get("/api/v1/payment/transactions")
        assert response.status_code == 200
        data = response.json()
        assert data["transactions"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_returns_seeded_transactions(
        self, async_client_with_db: TestClient, async_db_session: AsyncSession
    ) -> None:
        """Returns transactions after seeding."""
        await _seed_data(async_db_session)

        response = async_client_with_db.get("/api/v1/payment/transactions")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1


# ---------------------------------------------------------------------------
# Tests: GET /api/v1/payment/status
# ---------------------------------------------------------------------------


class TestPaymentStatus:
    """Test GET /api/v1/payment/status endpoint."""

    def test_status_endpoint(self, client: TestClient) -> None:
        """Status endpoint returns payment service overview."""
        response = client.get("/api/v1/payment/status")
        assert response.status_code == 200
        data = response.json()
        assert "provider" in data
        assert "enabled" in data
        assert "is_test_mode" in data
        assert "total_transactions" in data
        assert "total_revenue_cents" in data
        assert "active_subscriptions" in data


# ---------------------------------------------------------------------------
# Tests: GET /api/v1/payment/subscriptions
# ---------------------------------------------------------------------------


class TestListSubscriptions:
    """Test GET /api/v1/payment/subscriptions endpoint."""

    @pytest.mark.asyncio
    async def test_empty_subscriptions(self, async_client_with_db: TestClient) -> None:
        """Returns empty list when no subscriptions exist.

        Same rationale as ``test_empty_transactions``: use the isolated
        test-DB fixture so the assertion doesn't depend on dev-database
        state.
        """
        response = async_client_with_db.get("/api/v1/payment/subscriptions")
        assert response.status_code == 200
        data = response.json()
        assert data["subscriptions"] == []
        assert data["total"] == 0


# ---------------------------------------------------------------------------
# Tests: POST /api/v1/payment/webhook
# ---------------------------------------------------------------------------


class TestPaymentWebhook:
    """Test POST /api/v1/payment/webhook endpoint."""

    def test_webhook_rejects_bad_signature(self, client: TestClient) -> None:
        """Webhook endpoint rejects invalid signatures."""
        response = client.post(
            "/api/v1/payment/webhook",
            content=b'{"type": "test"}',
            headers={"stripe-signature": "bad_sig"},
        )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Tests: POST /api/v1/payment/checkout URL fallback chain
# ---------------------------------------------------------------------------


CHECKOUT_RESULT = {
    "session_id": "cs_test_stub",
    "checkout_url": "https://checkout.stripe.com/stub",
}


class TestCheckoutUrlFallback:
    """Verify request body > settings > defaults precedence for redirect URLs."""

    @pytest.mark.asyncio
    async def test_uses_settings_defaults_when_body_omits_urls(
        self, async_client_with_db: TestClient, app: FastAPI
    ) -> None:
        """No URLs in request body -> service is called with settings defaults."""
        from app.core.config import settings

        mock_create = AsyncMock(return_value=CHECKOUT_RESULT)
        mock_service = AsyncMock()
        mock_service.create_checkout = mock_create
        with _override_payment_service(app, mock_service):
            response = async_client_with_db.post(
                "/api/v1/payment/checkout",
                json={"price_id": "price_xxx", "mode": "payment"},
            )

        assert response.status_code == 200
        assert response.json()["session_id"] == "cs_test_stub"
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs["success_url"] == settings.PAYMENT_SUCCESS_URL
        assert call_kwargs["cancel_url"] == settings.PAYMENT_CANCEL_URL

    @pytest.mark.asyncio
    async def test_body_urls_win_over_settings(
        self, async_client_with_db: TestClient, app: FastAPI
    ) -> None:
        """URLs in request body override settings defaults."""
        mock_create = AsyncMock(return_value=CHECKOUT_RESULT)
        mock_service = AsyncMock()
        mock_service.create_checkout = mock_create
        with _override_payment_service(app, mock_service):
            response = async_client_with_db.post(
                "/api/v1/payment/checkout",
                json={
                    "price_id": "price_xxx",
                    "mode": "payment",
                    "success_url": "https://app.example.com/thanks",
                    "cancel_url": "https://app.example.com/abort",
                },
            )

        assert response.status_code == 200
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs["success_url"] == "https://app.example.com/thanks"
        assert call_kwargs["cancel_url"] == "https://app.example.com/abort"

    @pytest.mark.asyncio
    async def test_mixed_body_and_settings(
        self, async_client_with_db: TestClient, app: FastAPI
    ) -> None:
        """Caller can override only one URL; the other still falls back."""
        from app.core.config import settings

        mock_create = AsyncMock(return_value=CHECKOUT_RESULT)
        mock_service = AsyncMock()
        mock_service.create_checkout = mock_create
        with _override_payment_service(app, mock_service):
            response = async_client_with_db.post(
                "/api/v1/payment/checkout",
                json={
                    "price_id": "price_xxx",
                    "mode": "payment",
                    "success_url": "https://only-success.example.com",
                },
            )

        assert response.status_code == 200
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs["success_url"] == "https://only-success.example.com"
        assert call_kwargs["cancel_url"] == settings.PAYMENT_CANCEL_URL


# ---------------------------------------------------------------------------
# Tests: POST /api/v1/payment/checkout Stripe error translation
# ---------------------------------------------------------------------------


class TestCheckoutErrorTranslation:
    """Stripe errors should surface as proper 4xx responses, not 500s."""

    @pytest.mark.asyncio
    async def test_invalid_request_returns_400_with_user_message(
        self, async_client_with_db: TestClient, app: FastAPI
    ) -> None:
        """InvalidRequestError -> 400 with Stripe's user_message in detail."""
        err = stripe.InvalidRequestError(
            message="You specified 'payment' mode but passed a recurring price.",
            param="mode",
        )
        mock_create = AsyncMock(side_effect=err)
        mock_service = AsyncMock()
        mock_service.create_checkout = mock_create
        with _override_payment_service(app, mock_service):
            response = async_client_with_db.post(
                "/api/v1/payment/checkout",
                json={"price_id": "price_recurring", "mode": "payment"},
            )

        assert response.status_code == 400
        assert "payment" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_authentication_error_returns_401(
        self, async_client_with_db: TestClient, app: FastAPI
    ) -> None:
        """AuthenticationError -> 401 so operators notice a bad key fast."""
        err = stripe.AuthenticationError(message="Invalid API key provided.")
        mock_create = AsyncMock(side_effect=err)
        mock_service = AsyncMock()
        mock_service.create_checkout = mock_create
        with _override_payment_service(app, mock_service):
            response = async_client_with_db.post(
                "/api/v1/payment/checkout",
                json={"price_id": "price_xxx", "mode": "payment"},
            )

        assert response.status_code == 401
        assert "api key" in response.json()["detail"].lower()
