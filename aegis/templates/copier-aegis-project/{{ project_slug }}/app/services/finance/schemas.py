"""Finance service request/response schemas (plain Pydantic DTOs).

Mirrors ``payment/schemas.py``: flat response DTOs with a ``from_row`` mapper,
list responses wrapping ``items`` + ``total``, and request models for writes.
Money fields are integer minor units (cents); the frontend formats them.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from app.services.finance.models import (
        FinanceAccount,
        FinanceImportBatch,
        FinanceImportBatchRow,
        FinanceNetWorthSnapshot,
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
    currency: str
    is_manual: bool
    institution_id: int | None = None
    connection_id: int | None = None

    @classmethod
    def from_row(cls, row: FinanceAccount) -> AccountResponse:
        return cls(
            id=row.id,
            name=row.name,
            account_type=row.account_type,
            classification=row.classification,
            current_balance=row.current_balance,
            currency=row.currency,
            is_manual=row.is_manual,
            institution_id=row.institution_id,
            connection_id=row.connection_id,
        )


class AccountListResponse(BaseModel):
    items: list[AccountResponse]
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
