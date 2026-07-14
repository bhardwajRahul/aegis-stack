"""Rule-based "wasting money" insights (FIN-27), no AI.

Runs nightly after recurring detection. Writes ``finance_insight`` rows
(deduped on ``(owner, dedup_key)``) so the same alert isn't regenerated every
night. Three v1 rules:

- **price_hike** — a fixed-amount recurring stream charged more than last time.
- **fee_charged** — a bank/finance fee or interest charge hit an account.
- **overspend_category** — this month's category spend is way above its recent
  norm (needs >= 3 prior full months, else skipped silently).

This is the finance-local path. When the insights service is present a bridge
can additionally emit through its event machinery; the local rows are the
source of truth for dedup + the finance modal's Insights list.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re
import statistics

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.services.finance.models import (
    FinanceAccount,
    FinanceInsight,
    FinanceRecurringStream,
    FinanceTransaction,
)

PRICE_HIKE_THRESHOLD = 1.10  # >10% over the stream's average
OVERSPEND_MULTIPLE = 1.5  # > 1.5x the 3-month median
OVERSPEND_MIN_HISTORY = 3  # need >= 3 prior full months
_FEE_PFC = "BANK_FEES"
_FEE_RE = re.compile(r"FEE|INTEREST CHARGE|FINANCE CHARGE", re.IGNORECASE)


@dataclass
class InsightGenerationResult:
    """Counts from one generation pass."""

    created: int = 0


def _usd(cents: int) -> str:
    return f"${abs(cents) / 100:,.2f}"


def _month_key(day: date) -> str:
    return f"{day.year:04d}-{day.month:02d}"


def _owner_clause(column, owner_user_id: int | None):
    """Scan the owner's rows; a NULL owner (standalone, no auth) uses IS NULL."""
    return column.is_(None) if owner_user_id is None else column == owner_user_id


async def generate_insights(
    db: AsyncSession, *, owner_user_id: int | None, today: date | None = None
) -> InsightGenerationResult:
    """Run the three insight rules for one owner. Idempotent (dedup_key).

    Insights have a NOT-NULL owner, so a standalone (NULL-owner) install stores
    them under the ``0`` sentinel while scanning its NULL-owner rows.
    """
    result = InsightGenerationResult()
    today = today or date.today()
    store_owner = 0 if owner_user_id is None else owner_user_id

    live_accounts = select(FinanceAccount.id).where(
        FinanceAccount.deleted_at.is_(None),
        _owner_clause(FinanceAccount.owner_user_id, owner_user_id),
    )

    result.created += await _price_hikes(db, store_owner)
    result.created += await _fees(db, owner_user_id, store_owner, live_accounts)
    result.created += await _overspend(
        db, owner_user_id, store_owner, live_accounts, today
    )
    return result


async def _create_if_new(
    db: AsyncSession,
    *,
    owner_user_id: int,
    insight_type: str,
    dedup_key: str,
    severity: str,
    title: str,
    body: str,
    detected_amount: int | None = None,
    related_stream_id: int | None = None,
    related_transaction_id: int | None = None,
    related_category_id: int | None = None,
) -> bool:
    """Insert an insight unless its dedup_key already exists. Returns created?"""
    exists = (
        await db.exec(
            select(FinanceInsight.id).where(
                FinanceInsight.owner_user_id == owner_user_id,
                FinanceInsight.dedup_key == dedup_key,
            )
        )
    ).first()
    if exists is not None:
        return False
    db.add(
        FinanceInsight(
            owner_user_id=owner_user_id,
            insight_type=insight_type,
            severity=severity,
            title=title,
            body=body,
            dedup_key=dedup_key,
            detected_amount=detected_amount,
            related_stream_id=related_stream_id,
            related_transaction_id=related_transaction_id,
            related_category_id=related_category_id,
        )
    )
    await db.flush()
    return True


async def _price_hikes(db: AsyncSession, store_owner: int) -> int:
    """A fixed-amount recurring stream now costs more than its average."""
    streams = (
        await db.exec(
            select(FinanceRecurringStream).where(
                FinanceRecurringStream.owner_user_id == store_owner,
                FinanceRecurringStream.deleted_at.is_(None),
                FinanceRecurringStream.status == "mature",
                FinanceRecurringStream.is_muted.is_(False),
                FinanceRecurringStream.amount_is_variable.is_(False),
                FinanceRecurringStream.direction == "outflow",
            )
        )
    ).all()
    created = 0
    for stream in streams:
        avg = stream.average_amount or 0
        last = stream.last_amount or 0
        if avg <= 0 or last <= avg * PRICE_HIKE_THRESHOLD:
            continue
        # Re-alert only on a NEW price (last_amount in the key).
        if await _create_if_new(
            db,
            owner_user_id=store_owner,
            insight_type="price_hike",
            dedup_key=f"price_hike:{stream.id}:{last}",
            severity="warning",
            title=f"{stream.name} went up to {_usd(last)}",
            body=(
                f"{stream.name} usually costs about {_usd(avg)} but the latest "
                f"charge was {_usd(last)}."
            ),
            detected_amount=last,
            related_stream_id=stream.id,
        ):
            created += 1
    return created


async def _fees(
    db: AsyncSession, owner_user_id: int | None, store_owner: int, live_accounts
) -> int:
    """Bank/finance fees + interest charges."""
    txns = (
        await db.exec(
            select(FinanceTransaction).where(
                _owner_clause(FinanceTransaction.owner_user_id, owner_user_id),
                FinanceTransaction.deleted_at.is_(None),
                FinanceTransaction.dedup_status != "duplicate",
                FinanceTransaction.excluded_from_reports.is_(False),
                FinanceTransaction.amount < 0,
                FinanceTransaction.account_id.in_(live_accounts),
            )
        )
    ).all()
    created = 0
    for txn in txns:
        is_fee = txn.pfc_primary == _FEE_PFC or bool(
            _FEE_RE.search(txn.name or "")
        )
        if not is_fee:
            continue
        if await _create_if_new(
            db,
            owner_user_id=store_owner,
            insight_type="fee_charged",
            dedup_key=f"fee:{txn.id}",
            severity="warning",
            title=f"Fee charged: {_usd(txn.amount)}",
            body=f"{txn.name or 'A fee'} on {txn.date_} cost {_usd(txn.amount)}.",
            detected_amount=txn.amount,
            related_transaction_id=txn.id,
            related_category_id=txn.category_id,
        ):
            created += 1
    return created


async def _overspend(
    db: AsyncSession,
    owner_user_id: int | None,
    store_owner: int,
    live_accounts,
    today: date,
) -> int:
    """This month's category spend is > 1.5x the prior-3-month median."""
    # Pull the last ~4 months of categorized outflows and bucket by month.
    window_start = date(today.year, today.month, 1)
    for _ in range(3):  # step back 3 full months
        window_start = (
            date(window_start.year - 1, 12, 1)
            if window_start.month == 1
            else date(window_start.year, window_start.month - 1, 1)
        )
    rows = (
        await db.exec(
            select(FinanceTransaction).where(
                _owner_clause(FinanceTransaction.owner_user_id, owner_user_id),
                FinanceTransaction.deleted_at.is_(None),
                FinanceTransaction.dedup_status != "duplicate",
                FinanceTransaction.excluded_from_reports.is_(False),
                FinanceTransaction.amount < 0,
                FinanceTransaction.category_id.is_not(None),
                FinanceTransaction.date_ >= window_start,
                FinanceTransaction.account_id.in_(live_accounts),
            )
        )
    ).all()

    current_key = _month_key(today)
    # {category_id: {month_key: spend_cents}}
    by_cat: dict[int, dict[str, int]] = {}
    for txn in rows:
        month = _month_key(txn.date_)
        cat = by_cat.setdefault(txn.category_id, {})
        cat[month] = cat.get(month, 0) + abs(txn.amount)

    created = 0
    for category_id, months in by_cat.items():
        current = months.get(current_key, 0)
        prior = [amount for key, amount in months.items() if key != current_key]
        if current <= 0 or len(prior) < OVERSPEND_MIN_HISTORY:
            continue  # not enough history -> skip silently
        median_prior = statistics.median(prior)
        if median_prior <= 0 or current <= median_prior * OVERSPEND_MULTIPLE:
            continue
        if await _create_if_new(
            db,
            owner_user_id=store_owner,
            insight_type="overspend_category",
            dedup_key=f"overspend:{category_id}:{current_key.replace('-', '')}",
            severity="warning",
            title=f"Spending up this month ({_usd(current)})",
            body=(
                f"This month is {_usd(current)} vs a typical {_usd(int(median_prior))} "
                "for this category."
            ),
            detected_amount=current,
            related_category_id=category_id,
        ):
            created += 1
    return created
