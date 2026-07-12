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
        FinanceNetWorthSnapshot,
        FinanceSecurity,
        FinanceTransaction,
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
    """A single ledger transaction."""

    id: int
    account_id: int
    date: date
    name: str | None
    amount: int
    currency: str
    source: str
    category_id: int | None = None
    pending: bool = False

    @classmethod
    def from_row(cls, row: FinanceTransaction) -> TransactionResponse:
        return cls(
            id=row.id,
            account_id=row.account_id,
            date=row.date_,
            name=row.name,
            amount=row.amount,
            currency=row.currency,
            source=row.source,
            category_id=row.category_id,
            pending=row.pending,
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
# Provider connectivity (Plaid)
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
