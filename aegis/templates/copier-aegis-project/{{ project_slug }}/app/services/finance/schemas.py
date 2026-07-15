"""Finance service request/response schemas (plain Pydantic DTOs).

Mirrors ``payment/schemas.py``: flat response DTOs with a ``from_row`` mapper,
list responses wrapping ``items`` + ``total``, and request models for writes.
Money fields are integer minor units (cents); the frontend formats them.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from app.services.finance.models import (
        FinanceAccount,
        FinanceConnection,
        FinanceHolding,
        FinanceImportBatch,
        FinanceImportBatchRow,
        FinanceInsight,
        FinanceNetWorthSnapshot,
        FinanceRecurringStream,
        FinanceSecurity,
        FinanceTrade,
        FinanceTransaction,
        FinanceTransfer,
        FinanceValuation,
    )

# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------


class AccountResponse(BaseModel):
    """A single account (manual or provider-linked)."""

    id: int
    name: str
    account_type: str
    classification: str
    current_balance: int | None
    # Balance derived from the sum of imported transactions (the register
    # balance Quicken shows). Useful when no valuation/statement balance was
    # set. Falls back to 0 when there are no transactions.
    activity_balance: int = 0
    currency: str
    is_manual: bool
    institution_id: int | None = None
    connection_id: int | None = None

    @classmethod
    def from_row(
        cls, row: FinanceAccount, *, activity_balance: int = 0
    ) -> AccountResponse:
        return cls(
            id=row.id,
            name=row.name,
            account_type=row.account_type,
            classification=row.classification,
            current_balance=row.current_balance,
            activity_balance=activity_balance,
            currency=row.currency,
            is_manual=row.is_manual,
            institution_id=row.institution_id,
            connection_id=row.connection_id,
        )


class AccountListResponse(BaseModel):
    items: list[AccountResponse]
    total: int


class ConnectionResponse(BaseModel):
    """A provider connection (e.g. a Plaid Item) the user can disconnect. Its
    accounts are matched client-side by ``connection_id`` on the account list."""

    id: int
    provider: str
    environment: str
    status: str
    status_detail: str | None = None
    label: str | None = None
    institution_id: int | None = None
    last_successful_sync_at: datetime | None = None
    created_at: datetime

    @classmethod
    def from_row(cls, row: FinanceConnection) -> ConnectionResponse:
        return cls(
            id=row.id,
            provider=row.provider,
            environment=row.environment,
            status=row.status,
            status_detail=row.status_detail,
            label=row.label,
            institution_id=row.institution_id,
            last_successful_sync_at=row.last_successful_sync_at,
            created_at=row.created_at,
        )


class ConnectionListResponse(BaseModel):
    items: list[ConnectionResponse]
    total: int


class TransactionResponse(BaseModel):
    """A single ledger transaction — full detail.

    Every user-meaningful field ships in one payload so the register, hover
    tooltips, and the click-through detail dialog all read from the same row
    without a per-interaction fetch."""

    id: int
    account_id: int
    date: date
    authorized_date: date | None = None
    posted_at: datetime | None = None
    name: str | None = None
    original_description: str | None = None
    merchant_name: str | None = None
    amount: int
    raw_amount: int | None = None
    currency: str
    source: str
    external_id: str | None = None
    category_id: int | None = None
    category_source: str = "unset"
    pfc_primary: str | None = None
    pfc_detailed: str | None = None
    memo: str | None = None
    check_number: str | None = None
    payment_channel: str | None = None
    pending: bool = False
    status: str = "posted"
    dedup_status: str = "unique"
    is_transfer: bool = False
    excluded_from_reports: bool = False
    is_reversal: bool = False

    @classmethod
    def from_row(cls, row: FinanceTransaction) -> TransactionResponse:
        return cls(
            id=row.id,
            account_id=row.account_id,
            date=row.date_,
            authorized_date=row.authorized_date,
            posted_at=row.datetime_,
            name=row.name,
            original_description=row.original_description,
            merchant_name=row.merchant_name,
            amount=row.amount,
            raw_amount=row.raw_amount,
            currency=row.currency,
            source=row.source,
            external_id=row.external_id,
            category_id=row.category_id,
            category_source=row.category_source,
            pfc_primary=row.pfc_primary,
            pfc_detailed=row.pfc_detailed,
            memo=row.memo,
            check_number=row.check_number,
            payment_channel=row.payment_channel,
            pending=row.pending,
            status=row.status,
            dedup_status=row.dedup_status,
            is_transfer=row.is_transfer,
            excluded_from_reports=row.excluded_from_reports,
            is_reversal=row.is_reversal,
        )


class TransactionListResponse(BaseModel):
    items: list[TransactionResponse]
    total: int


class SpendingCategory(BaseModel):
    """One row of the spending-by-category breakdown."""

    category: str
    amount: int  # positive minor units (outflow magnitude)


class NetWorthResponse(BaseModel):
    """Live net worth = assets - liabilities (signed integer minor units)."""

    net_worth_amount: int
    total_assets_amount: int
    total_liabilities_amount: int
    currency: str


class FinanceStatusSummary(BaseModel):
    """Headline numbers for the dashboard card / health check / CLI status."""

    net_worth_amount: int
    total_assets_amount: int
    total_liabilities_amount: int
    account_count: int
    connection_count: int
    new_insight_count: int = 0
    currency: str


class NetWorthPoint(BaseModel):
    """One day of the net-worth-over-time series (off the snapshot table)."""

    as_of_date: date
    net_worth_amount: int
    total_assets_amount: int
    total_liabilities_amount: int

    @classmethod
    def from_row(cls, row: FinanceNetWorthSnapshot) -> NetWorthPoint:
        return cls(
            as_of_date=row.as_of_date,
            net_worth_amount=row.net_worth_amount,
            total_assets_amount=row.total_assets_amount,
            total_liabilities_amount=row.total_liabilities_amount,
        )


class FinanceHealth(BaseModel):
    """Liveness summary returned by ``GET /api/v1/finance/health``.

    ``status`` is ``"ok"`` when no connection needs the user's attention,
    otherwise ``"attention"``.
    """

    status: str
    accounts: int
    connections: int
    connections_needing_action: int = 0


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------


class ValuationResponse(BaseModel):
    """A dated value mark on a manual/off-aggregator account."""

    id: int
    account_id: int
    as_of_date: date
    value: int
    source: str
    note: str | None = None

    @classmethod
    def from_row(cls, row: FinanceValuation) -> ValuationResponse:
        return cls(
            id=row.id,
            account_id=row.account_id,
            as_of_date=row.as_of_date,
            value=row.value,
            source=row.source,
            note=row.note,
        )


class ValuationListResponse(BaseModel):
    items: list[ValuationResponse]
    total: int


class ImportResultResponse(BaseModel):
    """Summary returned right after an import run."""

    batch_id: int | None
    rows_total: int
    rows_inserted: int
    rows_updated: int
    rows_duplicate: int
    rows_error: int


class ImportBatchSummary(BaseModel):
    """An import batch without its rows — for the batch list."""

    id: int
    source_type: str
    file_name: str | None
    status: str
    rows_total: int
    rows_inserted: int
    rows_duplicate: int
    rows_error: int

    @classmethod
    def from_row(cls, batch: FinanceImportBatch) -> ImportBatchSummary:
        return cls(
            id=batch.id,
            source_type=batch.source_type,
            file_name=batch.file_name,
            status=batch.status,
            rows_total=batch.rows_total,
            rows_inserted=batch.rows_inserted,
            rows_duplicate=batch.rows_duplicate,
            rows_error=batch.rows_error,
        )


class ImportBatchRowResponse(BaseModel):
    row_number: int
    parsed_status: str
    matched_transaction_id: int | None = None
    fitid: str | None = None
    reason: str | None = None

    @classmethod
    def from_row(cls, row: FinanceImportBatchRow) -> ImportBatchRowResponse:
        return cls(
            row_number=row.row_number,
            parsed_status=row.parsed_status,
            matched_transaction_id=row.matched_transaction_id,
            fitid=row.fitid,
            reason=row.reason,
        )


class ImportBatchResponse(BaseModel):
    """An import batch plus its per-row outcomes (the review view)."""

    id: int
    source_type: str
    file_name: str | None
    status: str
    rows_total: int
    rows_inserted: int
    rows_duplicate: int
    rows_error: int
    rows: list[ImportBatchRowResponse]

    @classmethod
    def from_batch(
        cls, batch: FinanceImportBatch, rows: list[FinanceImportBatchRow]
    ) -> ImportBatchResponse:
        return cls(
            id=batch.id,
            source_type=batch.source_type,
            file_name=batch.file_name,
            status=batch.status,
            rows_total=batch.rows_total,
            rows_inserted=batch.rows_inserted,
            rows_duplicate=batch.rows_duplicate,
            rows_error=batch.rows_error,
            rows=[ImportBatchRowResponse.from_row(r) for r in rows],
        )


class ManualAccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    account_type: str
    classification: str
    current_balance: int = 0
    currency: str = "usd"
    institution_id: int | None = None


class AccountUpdate(BaseModel):
    """Partial update — only provided fields change."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    is_hidden: bool | None = None
    is_closed: bool | None = None


class TransactionCreate(BaseModel):
    account_id: int
    amount: int
    date: date
    name: str | None = None
    category_id: int | None = None


class ValuationCreateRequest(BaseModel):
    """POST body for /accounts/{id}/valuations (account comes from the path)."""

    as_of_date: date
    value: int
    source: str = "manual"
    note: str | None = None


# ---------------------------------------------------------------------------
# Investments (securities + holdings)
# ---------------------------------------------------------------------------
class SecurityResponse(BaseModel):
    """A catalog security (equity, ETF, fund, crypto, ...)."""

    id: int
    ticker: str | None
    name: str | None
    security_type: str | None
    currency: str | None

    @classmethod
    def from_row(cls, row: FinanceSecurity) -> SecurityResponse:
        return cls(
            id=row.id,
            ticker=row.ticker,
            name=row.name,
            security_type=row.security_type,
            currency=row.currency,
        )


class HoldingResponse(BaseModel):
    """A current position with its computed market value (cents)."""

    id: int
    account_id: int
    security_id: int
    ticker: str | None = None
    name: str | None = None
    security_type: str | None = None
    as_of_date: date
    quantity: float  # shares = quantity_e8 / 1e8
    price: int | None  # unit price in scaled minor units
    price_scale: int
    cost_basis: int | None
    market_value: int  # cents
    currency: str

    @classmethod
    def from_parts(
        cls,
        holding: FinanceHolding,
        security: FinanceSecurity | None,
        market_value: int,
    ) -> HoldingResponse:
        return cls(
            id=holding.id,
            account_id=holding.account_id,
            security_id=holding.security_id,
            ticker=security.ticker if security else None,
            name=security.name if security else None,
            security_type=security.security_type if security else None,
            as_of_date=holding.as_of_date,
            quantity=holding.quantity_e8 / 100_000_000,
            price=holding.price,
            price_scale=holding.price_scale,
            cost_basis=holding.cost_basis,
            market_value=market_value,
            currency=holding.currency,
        )


class HoldingListResponse(BaseModel):
    items: list[HoldingResponse]
    total: int
    portfolio_value: int  # cents


class TradeResponse(BaseModel):
    """One investment trade / security movement (buy/sell/dividend/...).

    ``amount`` is in cents, negative when cash left the account (a buy/fee)
    and positive when it arrived (a sell/dividend) — the same convention as
    cash transactions.
    """

    id: int
    account_id: int
    security_id: int | None = None
    type: str
    subtype: str | None = None
    trade_date: date
    quantity: float | None  # shares = quantity_e8 / 1e8
    price: int | None  # unit price in scaled minor units
    price_scale: int
    amount: int  # cents (signed: negative = cash out)
    fees: int | None
    name: str | None = None
    currency: str

    @classmethod
    def from_row(cls, trade: FinanceTrade) -> TradeResponse:
        return cls(
            id=trade.id,
            account_id=trade.account_id,
            security_id=trade.security_id,
            type=trade.type,
            subtype=trade.subtype,
            trade_date=trade.trade_date,
            quantity=(
                trade.quantity_e8 / 100_000_000
                if trade.quantity_e8 is not None
                else None
            ),
            price=trade.price,
            price_scale=trade.price_scale,
            amount=trade.amount,
            fees=trade.fees,
            name=trade.name,
            currency=trade.currency,
        )


class TradeListResponse(BaseModel):
    items: list[TradeResponse]
    total: int


class TransferResponse(BaseModel):
    """A matched internal transfer between two of the user's own accounts."""

    id: int
    from_account_id: int | None
    to_account_id: int | None
    from_transaction_id: int | None
    to_transaction_id: int | None
    amount: int | None  # cents
    currency: str
    transfer_date: date | None
    is_credit_card_payment: bool
    match_method: str
    confidence: int | None
    status: str  # suggested | confirmed | rejected
    # The full leg transactions — the decisive context for a review decision
    # ("Starbucks -> INTRST PYMNT" is obviously not a transfer), and the same
    # payload the click-through detail dialog renders.
    from_transaction: TransactionResponse | None = None
    to_transaction: TransactionResponse | None = None

    @classmethod
    def from_row(
        cls,
        transfer: FinanceTransfer,
        *,
        from_txn: FinanceTransaction | None = None,
        to_txn: FinanceTransaction | None = None,
    ) -> TransferResponse:
        return cls(
            id=transfer.id,
            from_account_id=transfer.from_account_id,
            to_account_id=transfer.to_account_id,
            from_transaction_id=transfer.from_transaction_id,
            to_transaction_id=transfer.to_transaction_id,
            amount=transfer.amount,
            currency=transfer.currency,
            transfer_date=transfer.transfer_date,
            is_credit_card_payment=transfer.is_credit_card_payment,
            match_method=transfer.match_method,
            confidence=transfer.confidence,
            status=transfer.status,
            from_transaction=(
                TransactionResponse.from_row(from_txn) if from_txn else None
            ),
            to_transaction=(
                TransactionResponse.from_row(to_txn) if to_txn else None
            ),
        )


class TransferListResponse(BaseModel):
    items: list[TransferResponse]
    total: int


class SpendingSummaryResponse(BaseModel):
    """Per-category spend for a month (transfers excluded)."""

    month: str  # YYYY-MM
    categories: list[SpendingCategory]
    total: int  # cents


class RecurringStreamResponse(BaseModel):
    """A detected recurring stream (subscription, bill, or paycheck)."""

    id: int
    account_id: int | None
    name: str
    direction: str  # inflow | outflow
    frequency: str
    average_amount: int | None  # cents (magnitude)
    last_amount: int | None
    amount_is_variable: bool
    currency: str
    next_expected_date: date | None
    occurrence_count: int
    status: str
    confidence: int | None
    is_subscription: bool
    is_muted: bool

    @classmethod
    def from_row(cls, row: FinanceRecurringStream) -> RecurringStreamResponse:
        return cls(
            id=row.id,
            account_id=row.account_id,
            name=row.name,
            direction=row.direction,
            frequency=row.frequency,
            average_amount=row.average_amount,
            last_amount=row.last_amount,
            amount_is_variable=row.amount_is_variable,
            currency=row.currency,
            next_expected_date=row.next_expected_date,
            occurrence_count=row.occurrence_count,
            status=row.status,
            confidence=row.confidence,
            is_subscription=row.is_subscription,
            is_muted=row.is_muted,
        )


class RecurringListResponse(BaseModel):
    items: list[RecurringStreamResponse]
    total: int
    monthly_cost: int  # cents — monthly-equivalent of recurring outflows


class InsightResponse(BaseModel):
    """A rule-based "wasting money" insight."""

    id: int
    insight_type: str
    severity: str
    title: str
    body: str | None
    detected_amount: int | None
    related_stream_id: int | None
    related_transaction_id: int | None
    related_category_id: int | None
    status: str

    @classmethod
    def from_row(cls, row: FinanceInsight) -> InsightResponse:
        return cls(
            id=row.id,
            insight_type=row.insight_type,
            severity=row.severity,
            title=row.title,
            body=row.body,
            detected_amount=row.detected_amount,
            related_stream_id=row.related_stream_id,
            related_transaction_id=row.related_transaction_id,
            related_category_id=row.related_category_id,
            status=row.status,
        )


class InsightListResponse(BaseModel):
    items: list[InsightResponse]
    total: int


class SecurityCreate(BaseModel):
    """POST body for /securities."""

    ticker: str
    name: str | None = None
    security_type: str | None = None
    currency: str = "usd"


class HoldingCreate(BaseModel):
    """POST body for /accounts/{id}/holdings (account from the path).

    ``ticker`` resolves or creates the security; ``quantity`` is in shares;
    ``price`` is the unit price in minor units (cents, price_scale 2).
    """

    ticker: str
    name: str | None = None
    security_type: str | None = None
    as_of_date: date | None = None
    quantity: float
    price: int | None = None
    cost_basis: int | None = None


# ---------------------------------------------------------------------------
# Provider connectivity (Plaid + SnapTrade)
# ---------------------------------------------------------------------------
class LinkTokenResponse(BaseModel):
    """A Plaid Link token the frontend hands to Plaid Link."""

    link_token: str


class PlaidExchangeRequest(BaseModel):
    """POST body for /plaid/exchange — the public token from Plaid Link."""

    public_token: str
    label: str | None = None


class SyncResultResponse(BaseModel):
    """Outcome of a connection sync."""

    connection_id: int
    accounts: int
    added: int
    updated: int
    removed: int
    holdings: int = 0
    trades: int = 0


class SyncSummaryResponse(BaseModel):
    """Aggregate outcome of syncing every connection for the caller."""

    connections: int
    results: list[SyncResultResponse]


class HostedLinkResponse(BaseModel):
    """A Plaid Hosted Link session — open the URL, poll with the token."""

    hosted_link_url: str
    link_token: str


class HostedLinkCompleteRequest(BaseModel):
    """POST body for /plaid/hosted-link/complete."""

    link_token: str


class SnapTradeConnectResponse(BaseModel):
    """A SnapTrade connection-portal session — open the URL in a new tab
    (expires in ~5 minutes) and poll ``/snaptrade/connect/complete``."""

    redirect_uri: str
    connection_id: int
