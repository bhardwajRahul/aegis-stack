"""Net-worth snapshot engine (FIN-13).

Materializes ``finance_balance_snapshot`` (per account per day) and
``finance_net_worth_snapshot`` (per user per day) so the net-worth-over-time
chart is a cheap indexed range scan, not a recompute. Net worth is a
persistence problem — history can't be derived after the fact, so snapshots
start day one.

v1 reads balances/valuations only (never transactions): manual accounts follow
their ``finance_valuation`` series; accounts with only a ``current_balance``
carry that value forward. Bounded to a 35-day window by default so the job
never scans deep history.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime, timedelta

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.services.finance.models import (
    FinanceAccount,
    FinanceBalanceSnapshot,
    FinanceNetWorthSnapshot,
    FinanceValuation,
)

_DEFAULT_CURRENCY = "usd"
_DEFAULT_WINDOW_DAYS = 35


def _today() -> date:
    return datetime.now(UTC).date()


async def _balance_points(
    db: AsyncSession, account: FinanceAccount
) -> list[tuple[date, int, str]]:
    """Ordered ``(date, value, source)`` points defining an account's balance.

    Manual accounts follow their valuation series; an account with only a
    ``current_balance`` contributes a single point at ``balance_as_of`` (or
    today). Between points the value is carried forward.
    """
    valuations = list(
        (
            await db.exec(
                select(FinanceValuation)
                .where(FinanceValuation.account_id == account.id)
                .order_by(FinanceValuation.as_of_date)
            )
        ).all()
    )
    if valuations:
        return [(v.as_of_date, v.value, "manual") for v in valuations]
    if account.current_balance is not None:
        as_of = (
            account.balance_as_of.date()
            if account.balance_as_of is not None
            else _today()
        )
        source = "manual" if account.is_manual else "sync"
        return [(as_of, account.current_balance, source)]
    return []


async def _upsert_balance_snapshot(
    db: AsyncSession,
    *,
    account: FinanceAccount,
    balance_date: date,
    balance: int,
    source: str,
    is_estimated: bool,
    owner_user_id: int | None,
) -> None:
    existing = (
        await db.exec(
            select(FinanceBalanceSnapshot).where(
                FinanceBalanceSnapshot.account_id == account.id,
                FinanceBalanceSnapshot.balance_date == balance_date,
            )
        )
    ).first()
    if existing is not None:
        existing.balance = balance
        existing.source = source
        existing.is_estimated = is_estimated
        db.add(existing)
        return
    db.add(
        FinanceBalanceSnapshot(
            account_id=account.id,
            owner_user_id=owner_user_id
            if owner_user_id is not None
            else account.owner_user_id,
            balance_date=balance_date,
            balance=balance,
            currency=account.currency,
            source=source,
            is_estimated=is_estimated,
        )
    )


async def _upsert_net_worth_snapshot(
    db: AsyncSession,
    *,
    owner_user_id: int | None,
    as_of_date: date,
    total_assets: int,
    total_liabilities: int,
    currency: str = _DEFAULT_CURRENCY,
) -> None:
    query = select(FinanceNetWorthSnapshot).where(
        FinanceNetWorthSnapshot.as_of_date == as_of_date,
        FinanceNetWorthSnapshot.currency == currency,
    )
    # owner_user_id is nullable; `== None` never matches in SQL, so branch on it
    # to keep the upsert idempotent in standalone (no-auth) mode.
    if owner_user_id is None:
        query = query.where(FinanceNetWorthSnapshot.owner_user_id.is_(None))
    else:
        query = query.where(
            FinanceNetWorthSnapshot.owner_user_id == owner_user_id
        )
    net_worth = total_assets - total_liabilities
    existing = (await db.exec(query)).first()
    if existing is not None:
        existing.total_assets_amount = total_assets
        existing.total_liabilities_amount = total_liabilities
        existing.net_worth_amount = net_worth
        db.add(existing)
        return
    db.add(
        FinanceNetWorthSnapshot(
            owner_user_id=owner_user_id,
            as_of_date=as_of_date,
            total_assets_amount=total_assets,
            total_liabilities_amount=total_liabilities,
            net_worth_amount=net_worth,
            currency=currency,
        )
    )


async def recompute_snapshots(
    db: AsyncSession,
    *,
    owner_user_id: int | None = None,
    start_date: date | None = None,
) -> int:
    """Recompute balance + net-worth snapshots over the recent window.

    Returns the number of net-worth days written. Idempotent: repeat runs
    upsert the same rows. Writes but does not commit (caller owns the txn).
    """
    today = _today()
    window_start = start_date or (today - timedelta(days=_DEFAULT_WINDOW_DAYS - 1))
    if window_start > today:
        return 0
    days = [
        window_start + timedelta(days=i)
        for i in range((today - window_start).days + 1)
    ]

    account_query = select(FinanceAccount).where(
        FinanceAccount.deleted_at.is_(None)
    )
    if owner_user_id is not None:
        account_query = account_query.where(
            FinanceAccount.owner_user_id == owner_user_id
        )
    accounts = list((await db.exec(account_query)).all())

    per_day: dict[date, list[int]] = defaultdict(lambda: [0, 0])  # [assets, liab]

    for account in accounts:
        points = await _balance_points(db, account)
        if not points:
            continue
        index = 0
        current: tuple[date, int, str] | None = None
        for day in days:
            while index < len(points) and points[index][0] <= day:
                current = points[index]
                index += 1
            if current is None:
                continue  # account has no known balance yet on this day
            point_date, value, native_source = current
            is_exact = point_date == day
            await _upsert_balance_snapshot(
                db,
                account=account,
                balance_date=day,
                balance=value,
                source=native_source if is_exact else "carried_forward",
                is_estimated=not is_exact,
                owner_user_id=owner_user_id,
            )
            if account.classification == "asset":
                per_day[day][0] += value
            elif account.classification == "liability":
                per_day[day][1] += value

    written = 0
    for day, (assets, liabilities) in per_day.items():
        await _upsert_net_worth_snapshot(
            db,
            owner_user_id=owner_user_id,
            as_of_date=day,
            total_assets=assets,
            total_liabilities=liabilities,
        )
        written += 1
    await db.flush()
    return written


async def get_net_worth_series(
    db: AsyncSession,
    *,
    owner_user_id: int | None = None,
    days: int = 90,
    currency: str = _DEFAULT_CURRENCY,
) -> list[FinanceNetWorthSnapshot]:
    """The net-worth snapshot series (oldest first) — one indexed range scan."""
    since = _today() - timedelta(days=max(days, 1) - 1)
    query = select(FinanceNetWorthSnapshot).where(
        FinanceNetWorthSnapshot.as_of_date >= since,
        FinanceNetWorthSnapshot.currency == currency,
    )
    if owner_user_id is None:
        query = query.where(FinanceNetWorthSnapshot.owner_user_id.is_(None))
    else:
        query = query.where(
            FinanceNetWorthSnapshot.owner_user_id == owner_user_id
        )
    query = query.order_by(FinanceNetWorthSnapshot.as_of_date)
    return list((await db.exec(query)).all())
