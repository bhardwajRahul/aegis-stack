"""Recurring-stream detection (FIN-27).

Finds subscriptions, bills, and paychecks so the product can answer "what am I
paying every month?" and flag price hikes. Runs nightly (and after each
sync/import) per owner.

Heuristic: group a user's posted, non-transfer transactions by
``(account, direction, normalized payee)``; a group with >= ``MIN_OCCURRENCES``
whose median gap matches a known cadence (within ``INTERVAL_TOLERANCE``) is a
stream. Amounts within ``AMOUNT_TOLERANCE`` of the median are "fixed"; otherwise
the stream is variable (a utility bill). Confidence/maturity rather than a
boolean, because an annual charge is invisible for a year. Idempotent: streams
upsert on the detected-stream unique key and members back-link via
``finance_transaction.recurring_stream_id``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import statistics

from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.log import logger
from app.services.finance.importers.base import normalize_payee
from app.services.finance.models import (
    FinanceAccount,
    FinanceRecurringStream,
    FinanceTransaction,
)

MIN_OCCURRENCES = 3
INTERVAL_TOLERANCE = 0.20  # +/- 20% of a canonical cadence
AMOUNT_TOLERANCE = 0.20  # within 20% of median => fixed amount
# Canonical cadence (median-gap days) -> frequency label.
_CADENCES: tuple[tuple[int, str], ...] = (
    (7, "weekly"),
    (14, "biweekly"),
    (15, "semi_monthly"),
    (30, "monthly"),
    (90, "quarterly"),
    (365, "annually"),
)
_SUBSCRIPTION_FREQUENCIES = {"monthly", "annually"}


@dataclass
class RecurringDetectionResult:
    """Counts from one detection pass."""

    detected: int = 0


def _frequency_for(median_interval: float) -> str | None:
    """Map a median day-gap to a cadence label, or None if it matches none."""
    for days, label in _CADENCES:
        if abs(median_interval - days) <= days * INTERVAL_TOLERANCE:
            return label
    return None


def _payee_key(txn: FinanceTransaction) -> str:
    """Stable grouping key: merchant name / original description, normalized."""
    return normalize_payee(
        txn.merchant_name or txn.original_description or txn.name or ""
    )


def _owner_clause(column, owner_user_id: int | None):
    """Scan the owner's rows; a NULL owner (standalone, no auth) uses IS NULL."""
    return column.is_(None) if owner_user_id is None else column == owner_user_id


async def detect_recurring(
    db: AsyncSession, *, owner_user_id: int | None
) -> RecurringDetectionResult:
    """Detect + upsert recurring streams for one owner. Idempotent.

    Streams/insights have a NOT-NULL owner, so a standalone (NULL-owner) install
    stores them under the ``0`` sentinel while scanning its NULL-owner rows.
    """
    result = RecurringDetectionResult()
    store_owner = 0 if owner_user_id is None else owner_user_id

    acct_ids = (
        await db.exec(
            select(FinanceAccount.id).where(
                FinanceAccount.deleted_at.is_(None),
                _owner_clause(FinanceAccount.owner_user_id, owner_user_id),
            )
        )
    ).all()
    if not acct_ids:
        return result

    txns = (
        await db.exec(
            select(FinanceTransaction).where(
                _owner_clause(FinanceTransaction.owner_user_id, owner_user_id),
                FinanceTransaction.deleted_at.is_(None),
                FinanceTransaction.dedup_status != "duplicate",
                FinanceTransaction.is_transfer.is_(False),
                FinanceTransaction.status == "posted",
                FinanceTransaction.account_id.in_(list(acct_ids)),
            )
        )
    ).all()

    # Group by (account, direction, normalized payee).
    groups: dict[tuple[int, str, str], list[FinanceTransaction]] = {}
    for txn in txns:
        key = _payee_key(txn)
        if not key:
            continue
        direction = "outflow" if txn.amount < 0 else "inflow"
        groups.setdefault((txn.account_id, direction, key), []).append(txn)

    for (account_id, direction, payee), members in groups.items():
        if len(members) < MIN_OCCURRENCES:
            continue
        members.sort(key=lambda t: (t.date_, t.id or 0))
        gaps = [
            (members[i].date_ - members[i - 1].date_).days
            for i in range(1, len(members))
        ]
        gaps = [g for g in gaps if g > 0]
        if not gaps:
            continue
        median_interval = statistics.median(gaps)
        frequency = _frequency_for(median_interval)
        if frequency is None:
            continue  # no stable cadence -> not a recurring stream

        amounts = [abs(t.amount) for t in members]
        median_amount = int(statistics.median(amounts))
        variable = any(
            abs(a - median_amount) > median_amount * AMOUNT_TOLERANCE
            for a in amounts
        )
        last = members[-1]
        is_subscription = (
            direction == "outflow"
            and frequency in _SUBSCRIPTION_FREQUENCIES
            and not variable
        )
        confidence = min(
            100, 50 + 10 * len(members) + (0 if variable else 20)
        )
        try:
            async with db.begin_nested():
                stream = await _upsert_stream(
                    db,
                    owner_user_id=store_owner,
                    account_id=account_id,
                    direction=direction,
                    payee=payee,
                    name=last.merchant_name or last.name or payee,
                    frequency=frequency,
                    average_amount=median_amount,
                    last_amount=abs(last.amount),
                    first_date=members[0].date_,
                    last_date=last.date_,
                    next_expected_date=last.date_
                    + timedelta(days=int(median_interval)),
                    occurrence_count=len(members),
                    variable=variable,
                    is_subscription=is_subscription,
                    confidence=confidence,
                    currency=last.currency,
                )
                for member in members:
                    member.recurring_stream_id = stream.id
                    db.add(member)
                await db.flush()
        except IntegrityError:
            logger.debug("recurring upsert skipped (race)")
            continue
        result.detected += 1
    return result


async def _upsert_stream(
    db: AsyncSession,
    *,
    owner_user_id: int,
    account_id: int,
    direction: str,
    payee: str,
    name: str,
    frequency: str,
    average_amount: int,
    last_amount: int,
    first_date,
    last_date,
    next_expected_date,
    occurrence_count: int,
    variable: bool,
    is_subscription: bool,
    confidence: int,
    currency: str,
) -> FinanceRecurringStream:
    """Insert or update the detected stream (keyed by the detected unique)."""
    existing = (
        await db.exec(
            select(FinanceRecurringStream).where(
                FinanceRecurringStream.owner_user_id == owner_user_id,
                FinanceRecurringStream.account_id == account_id,
                FinanceRecurringStream.direction == direction,
                FinanceRecurringStream.normalized_payee == payee,
                FinanceRecurringStream.provider_stream_id.is_(None),
            )
        )
    ).first()
    status = "mature" if occurrence_count >= MIN_OCCURRENCES else "early_detection"
    if existing is not None:
        existing.name = name
        existing.frequency = frequency
        existing.average_amount = average_amount
        existing.last_amount = last_amount
        existing.first_date = first_date
        existing.last_date = last_date
        existing.next_expected_date = next_expected_date
        existing.occurrence_count = occurrence_count
        existing.amount_is_variable = variable
        existing.is_subscription = is_subscription
        existing.confidence = confidence
        existing.status = status
        existing.deleted_at = None
        db.add(existing)
        await db.flush()
        return existing
    stream = FinanceRecurringStream(
        owner_user_id=owner_user_id,
        account_id=account_id,
        direction=direction,
        normalized_payee=payee,
        name=name,
        frequency=frequency,
        average_amount=average_amount,
        last_amount=last_amount,
        currency=currency,
        first_date=first_date,
        last_date=last_date,
        next_expected_date=next_expected_date,
        occurrence_count=occurrence_count,
        amount_is_variable=variable,
        is_subscription=is_subscription,
        confidence=confidence,
        status=status,
        source="derived",
    )
    db.add(stream)
    await db.flush()
    return stream
