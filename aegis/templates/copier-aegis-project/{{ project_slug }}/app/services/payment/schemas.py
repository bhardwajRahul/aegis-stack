"""
Pydantic schemas for payment API requests and responses.
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from .constants import RefundReason

# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class CheckoutRequest(BaseModel):
    """Request to create a checkout session."""

    price_id: str = Field(description="Stripe Price ID (e.g., price_xxx)")
    quantity: int = Field(default=1, ge=1)
    mode: str = Field(default="payment", description="payment or subscription")
    success_url: str | None = Field(
        default=None,
        description=(
            "URL to redirect after success. Falls back to PAYMENT_SUCCESS_URL "
            "setting when omitted."
        ),
    )
    cancel_url: str | None = Field(
        default=None,
        description=(
            "URL to redirect on cancel. Falls back to PAYMENT_CANCEL_URL "
            "setting when omitted."
        ),
    )

    @model_validator(mode="after")
    def _enforce_subscription_quantity(self) -> "CheckoutRequest":
        """Subscription checkouts must have ``quantity == 1``.

        Stripe technically allows ``quantity > 1`` on subscriptions for
        per-seat / per-unit pricing, but that's a deliberate product
        design (Teams plans, license counts) — not something a generic
        app should permit by default. For the common case of "one
        customer subscribes to one plan," allowing quantity > 1 just
        produces confusing inflated amounts. Apps that genuinely want
        seat-based pricing should remove this validator locally.
        """
        if self.mode == "subscription" and self.quantity != 1:
            raise ValueError(
                "Subscription checkouts must have quantity=1. For "
                "per-seat pricing, use a quantity-aware price in Stripe "
                "and remove this guard in your CheckoutRequest."
            )
        return self


class RefundRequest(BaseModel):
    """Request to refund a transaction."""

    amount: int | None = Field(
        default=None,
        ge=1,
        description="Amount to refund in cents (None for full refund)",
    )
    reason: str = Field(
        default=RefundReason.DEFAULT,
        description=(
            "Reason code. One of: duplicate, fraudulent, "
            "requested_by_customer, other. Values other than Stripe's "
            "accepted enum (duplicate/fraudulent/requested_by_customer) "
            "are stored locally but not sent to Stripe."
        ),
    )

    @field_validator("reason")
    @classmethod
    def _validate_reason(cls, v: str) -> str:
        if v not in RefundReason.ALL:
            raise ValueError(
                f"Invalid reason '{v}'. Must be one of: {', '.join(RefundReason.ALL)}"
            )
        return v


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class CheckoutResponse(BaseModel):
    """Response from creating a checkout session."""

    session_id: str
    checkout_url: str


class TransactionResponse(BaseModel):
    """Single transaction in API responses."""

    id: int
    provider_transaction_id: str
    type: str
    status: str
    amount: int
    currency: str
    description: str | None = None
    created_at: datetime


class TransactionListResponse(BaseModel):
    """Paginated list of transactions."""

    transactions: list[TransactionResponse]
    total: int
    page: int
    page_size: int


class SubscriptionResponse(BaseModel):
    """Single subscription in API responses."""

    id: int
    provider_subscription_id: str
    plan_name: str
    status: str
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool


class SubscriptionListResponse(BaseModel):
    """List of subscriptions."""

    subscriptions: list[SubscriptionResponse]
    total: int


class PaymentStatusResponse(BaseModel):
    """Payment service status overview."""

    provider: str
    enabled: bool
    is_test_mode: bool
    total_transactions: int
    total_revenue_cents: int
    active_subscriptions: int
    currency: str = "usd"


class DisputeResponse(BaseModel):
    """A single dispute or early fraud warning."""

    id: int
    transaction_id: int
    provider_dispute_id: str
    status: str
    reason: str | None = None
    amount: int
    currency: str
    evidence_due_by: datetime | None = None
    event_type: str | None = None
    created_at: datetime
    updated_at: datetime


class DisputeListResponse(BaseModel):
    """List of disputes."""

    disputes: list[DisputeResponse]
    total: int


class CatalogEntryResponse(BaseModel):
    """One entry in the provider catalog."""

    price_id: str
    product_name: str
    amount: int
    currency: str
    interval: str | None = None
    price_type: str


class CatalogResponse(BaseModel):
    """Active catalog entries from the payment provider."""

    entries: list[CatalogEntryResponse]
    total: int


class RevenueTimeseriesPoint(BaseModel):
    """One day of succeeded-charge revenue."""

    date: str  # ISO date (YYYY-MM-DD)
    amount_cents: int


class RevenueTimeseriesResponse(BaseModel):
    """Daily revenue series, dense across the requested window."""

    points: list[RevenueTimeseriesPoint]
    days: int
