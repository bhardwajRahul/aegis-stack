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


def _balance_points(
    account: FinanceAccount, valuations: list[FinanceValuation]
) -> list[tuple[date, int, str]]:
    """Ordered ``(date, value, source)`` points defining an account's balance.

    Pure: ``valuations`` are the account's rows (ascending by date), preloaded
    in bulk by the caller so recompute issues one query for all accounts rather
    than one per account. Manual accounts follow their valuation series; an
    account with only a ``current_balance`` contributes a single point at
    ``balance_as_of`` (or today). Between points the value is carried forward.
    """
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


def _apply_balance_snapshot(
    db: AsyncSession,
    existing: dict[tuple[int, date], FinanceBalanceSnapshot],
    *,
    account: FinanceAccount,
    balance_date: date,
    balance: int,
    source: str,
    is_estimated: bool,
    owner_user_id: int | None,
) -> None:
    """Upsert a balance snapshot against the preloaded ``existing`` map.

    No query: the caller loads every snapshot in the window up front, so this
    is an in-memory dict lookup. New rows are registered in ``existing`` so a
    repeat within the same run updates in place rather than double-inserting.
    """
    prior = existing.get((account.id, balance_date))
    if prior is not None:
        prior.balance = balance
        prior.source = source
        prior.is_estimated = is_estimated
        db.add(prior)
        return
    snapshot = FinanceBalanceSnapshot(
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
    db.add(snapshot)
    existing[(account.id, balance_date)] = snapshot


def _apply_net_worth_snapshot(
    db: AsyncSession,
    existing: dict[date, FinanceNetWorthSnapshot],
    *,
    owner_user_id: int | None,
    as_of_date: date,
    total_assets: int,
    total_liabilities: int,
) -> None:
    """Upsert a net-worth snapshot against the preloaded ``existing`` map."""
    net_worth = total_assets - total_liabilities
    prior = existing.get(as_of_date)
    if prior is not None:
        prior.total_assets_amount = total_assets
        prior.total_liabilities_amount = total_liabilities
        prior.net_worth_amount = net_worth
        db.add(prior)
        return
    snapshot = FinanceNetWorthSnapshot(
        owner_user_id=owner_user_id,
        as_of_date=as_of_date,
        total_assets_amount=total_assets,
        total_liabilities_amount=total_liabilities,
        net_worth_amount=net_worth,
        currency=_DEFAULT_CURRENCY,
    )
    db.add(snapshot)
    existing[as_of_date] = snapshot


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

    # 1) Accounts in scope.
    account_query = select(FinanceAccount).where(
        FinanceAccount.deleted_at.is_(None)
    )
    if owner_user_id is not None:
        account_query = account_query.where(
            FinanceAccount.owner_user_id == owner_user_id
        )
    accounts = list((await db.exec(account_query)).all())
    if not accounts:
        return 0
    account_ids = [a.id for a in accounts]

    # 2) All valuations for those accounts in one query, grouped in memory
    #    (was one query per account inside the loop).
    valuations_by_account: dict[int, list[FinanceValuation]] = defaultdict(list)
    valuation_rows = (
        await db.exec(
            select(FinanceValuation)
            .where(FinanceValuation.account_id.in_(account_ids))
            .order_by(
                FinanceValuation.account_id, FinanceValuation.as_of_date
            )
        )
    ).all()
    for valuation in valuation_rows:
        valuations_by_account[valuation.account_id].append(valuation)

    # 3) Every existing balance snapshot in the window, keyed for in-memory
    #    upsert (was one existence query per account per day).
    existing_balance: dict[tuple[int, date], FinanceBalanceSnapshot] = {}
    balance_rows = (
        await db.exec(
            select(FinanceBalanceSnapshot).where(
                FinanceBalanceSnapshot.account_id.in_(account_ids),
                FinanceBalanceSnapshot.balance_date >= window_start,
                FinanceBalanceSnapshot.balance_date <= today,
            )
        )
    ).all()
    for snapshot in balance_rows:
        existing_balance[(snapshot.account_id, snapshot.balance_date)] = snapshot

    per_day: dict[date, list[int]] = defaultdict(lambda: [0, 0])  # [assets, liab]

    for account in accounts:
        points = _balance_points(account, valuations_by_account.get(account.id, []))
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
            _apply_balance_snapshot(
                db,
                existing_balance,
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

    # 4) Existing net-worth snapshots for the window in one query (was one
    #    existence query per day).
    existing_net_worth: dict[date, FinanceNetWorthSnapshot] = {}
    net_worth_query = select(FinanceNetWorthSnapshot).where(
        FinanceNetWorthSnapshot.currency == _DEFAULT_CURRENCY,
        FinanceNetWorthSnapshot.as_of_date >= window_start,
        FinanceNetWorthSnapshot.as_of_date <= today,
    )
    # owner_user_id is nullable; `== None` never matches in SQL, so branch on it
    # to keep the upsert idempotent in standalone (no-auth) mode.
    if owner_user_id is None:
        net_worth_query = net_worth_query.where(
            FinanceNetWorthSnapshot.owner_user_id.is_(None)
        )
    else:
        net_worth_query = net_worth_query.where(
            FinanceNetWorthSnapshot.owner_user_id == owner_user_id
        )
    for snapshot in (await db.exec(net_worth_query)).all():
        existing_net_worth[snapshot.as_of_date] = snapshot

    written = 0
    for day, (assets, liabilities) in per_day.items():
        _apply_net_worth_snapshot(
            db,
            existing_net_worth,
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
