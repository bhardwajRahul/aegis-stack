"""Provider connection sync: turn a Plaid Item into finance accounts + txns.

``create_plaid_connection`` stores an exchanged access token (AES-GCM encrypted)
as a ``FinanceConnection``. ``sync_plaid_connection`` pulls the item's accounts
(upserting ``FinanceAccount`` rows keyed by Plaid ``account_id``) and its
transactions via the cursor-based ``transactions/sync`` (LANE-1 dedup on the
Plaid ``transaction_id``). Writes but does not commit — the caller owns the txn.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.encryption import decrypt_secret, encrypt_secret
from app.services.finance.constants import Provider
from app.services.finance.finance_service import FinanceService
from app.services.finance.models import (
    FinanceAccount,
    FinanceConnection,
    FinanceSecurity,
    FinanceTransaction,
    FinanceWebhookEvent,
)
from app.services.finance.providers.plaid import PlaidClient, PlaidError

_ACCESS_TOKEN_CONTEXT = "finance.plaid.access_token"

# Plaid ``type`` -> (account_type, classification). Depository subtypes refine
# checking vs savings below.
_PLAID_TYPE_MAP: dict[str, tuple[str, str]] = {
    "depository": ("checking", "asset"),
    "credit": ("credit_card", "liability"),
    "loan": ("loan", "liability"),
    "investment": ("brokerage", "asset"),
}
_DEPOSITORY_SAVINGS = frozenset({"savings", "cd", "money market", "hsa"})


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _to_cents(amount: float | None) -> int | None:
    return None if amount is None else round(amount * 100)


def _map_account_kind(
    plaid_type: str | None, plaid_subtype: str | None
) -> tuple[str, str]:
    account_type, classification = _PLAID_TYPE_MAP.get(
        plaid_type or "", ("other_asset", "asset")
    )
    if plaid_type == "depository" and (plaid_subtype or "") in _DEPOSITORY_SAVINGS:
        account_type = "savings"
    return account_type, classification


@dataclass
class SyncResult:
    connection_id: int
    accounts: int = 0
    added: int = 0
    updated: int = 0
    removed: int = 0
    holdings: int = 0
    trades: int = 0


async def create_plaid_connection(
    db: AsyncSession,
    *,
    owner_user_id: int | None,
    access_token: str,
    item_id: str,
    institution_id: int | None = None,
    label: str | None = None,
    environment: str = "sandbox",
) -> FinanceConnection:
    """Persist an exchanged Plaid access token as a connection (idempotent on
    the provider item id)."""
    existing = (
        await db.exec(
            select(FinanceConnection).where(
                FinanceConnection.provider == Provider.PLAID,
                FinanceConnection.provider_item_id == item_id,
            )
        )
    ).first()
    if existing is not None:
        existing.access_token_encrypted = encrypt_secret(
            access_token, context=_ACCESS_TOKEN_CONTEXT
        )
        existing.status = "healthy"
        existing.removed_at = None
        existing.deleted_at = None
        db.add(existing)
        await db.flush()
        return existing
    connection = FinanceConnection(
        owner_user_id=owner_user_id,
        provider=Provider.PLAID,
        connection_type="oauth_access_token",
        provider_item_id=item_id,
        institution_id=institution_id,
        label=label,
        environment=environment,
        access_token_encrypted=encrypt_secret(
            access_token, context=_ACCESS_TOKEN_CONTEXT
        ),
        status="healthy",
    )
    db.add(connection)
    await db.flush()
    return connection


async def _find_plaid_account(
    db: AsyncSession,
    connection: FinanceConnection,
    *,
    plaid_id: str,
    persistent: str | None,
    name: str,
    mask: str | None,
) -> FinanceAccount | None:
    """Find the account this Plaid account maps to, so re-linking the same
    institution (a new Item with fresh ``account_id``s) updates the existing
    rows instead of duplicating them."""
    # 1) Stable persistent id — real institutions provide it across re-links.
    if persistent:
        found = (
            await db.exec(
                select(FinanceAccount).where(
                    FinanceAccount.provider == Provider.PLAID,
                    FinanceAccount.persistent_account_id == persistent,
                )
            )
        ).first()
        if found is not None:
            return found
    # 2) Same Item re-sync (unchanged account_id).
    found = (
        await db.exec(
            select(FinanceAccount).where(
                FinanceAccount.provider == Provider.PLAID,
                FinanceAccount.provider_account_id == plaid_id,
            )
        )
    ).first()
    if found is not None:
        return found
    # 3) Re-link fallback (no persistent id, e.g. sandbox): same owner + name +
    # mask. Plaid regenerates account_ids per Item, but name/mask are stable.
    query = select(FinanceAccount).where(
        FinanceAccount.provider == Provider.PLAID,
        FinanceAccount.name == name,
        FinanceAccount.deleted_at.is_(None),
    )
    query = query.where(
        FinanceAccount.mask == mask
        if mask is not None
        else FinanceAccount.mask.is_(None)
    )
    if connection.owner_user_id is not None:
        query = query.where(FinanceAccount.owner_user_id == connection.owner_user_id)
    return (await db.exec(query)).first()


async def _upsert_accounts(
    db: AsyncSession,
    service: FinanceService,
    connection: FinanceConnection,
    plaid_accounts: list[dict[str, Any]],
) -> dict[str, int]:
    """Upsert one FinanceAccount per Plaid account; return {plaid_id: account_id}."""
    mapping: dict[str, int] = {}
    for plaid_account in plaid_accounts:
        plaid_id = plaid_account["account_id"]
        persistent = plaid_account.get("persistent_account_id")
        name = (
            plaid_account.get("name") or plaid_account.get("official_name") or "Account"
        )
        mask = plaid_account.get("mask")
        balances = plaid_account.get("balances") or {}
        currency = (balances.get("iso_currency_code") or "usd").lower()
        await service.get_or_create_currency(currency)
        account_type, classification = _map_account_kind(
            plaid_account.get("type"), plaid_account.get("subtype")
        )
        account = await _find_plaid_account(
            db,
            connection,
            plaid_id=plaid_id,
            persistent=persistent,
            name=name,
            mask=mask,
        )
        if account is None:
            account = FinanceAccount(
                owner_user_id=connection.owner_user_id,
                provider=Provider.PLAID,
                account_type=account_type,
                classification=classification,
                name=name,
                is_manual=False,
            )
        # (Re)point at this connection + refresh the provider ids and balances.
        account.connection_id = connection.id
        account.institution_id = connection.institution_id or account.institution_id
        account.provider_account_id = plaid_id
        account.persistent_account_id = persistent
        account.currency = currency
        account.name = name
        account.mask = mask
        account.current_balance = _to_cents(balances.get("current"))
        account.available_balance = _to_cents(balances.get("available"))
        account.balance_as_of = _utcnow()
        account.deleted_at = None
        db.add(account)
        await db.flush()
        mapping[plaid_id] = account.id
    return mapping


async def _apply_transactions(
    db: AsyncSession,
    service: FinanceService,
    transactions: list[dict[str, Any]],
    account_by_plaid_id: dict[str, int],
    *,
    connection: FinanceConnection,
) -> tuple[int, int]:
    """Insert new / reconcile Plaid transactions. Returns (added, reconciled).

    LANE 1 = ``(account, transaction_id)`` — exact; catches same-Item re-syncs.
    Re-link fallback: Plaid regenerates ``transaction_id`` for a re-linked Item,
    so a transaction already stored under *another* connection is matched by
    content (account, date, amount, normalized payee) as a multiset. Scoping to
    other connections avoids collapsing legitimate repeat charges in a normal
    same-Item sync. The schema forbids a row carrying both id and hash, so this
    is a query-time check, not a stored second lane.
    """
    from app.services.finance.importers.base import normalize_payee

    prepared: list[tuple[int, dict[str, Any], int, str | None, date]] = []
    currencies: set[str] = set()
    for txn in transactions:
        plaid_account_id = txn.get("account_id")
        account_id = (
            account_by_plaid_id.get(plaid_account_id) if plaid_account_id else None
        )
        if account_id is None:
            continue
        raw_amount = txn.get("amount")
        # Plaid: positive = outflow -> negate to our convention.
        amount = -round(raw_amount * 100) if raw_amount is not None else 0
        currency = (txn.get("iso_currency_code") or "usd").lower()
        currencies.add(currency)
        prepared.append(
            (
                account_id,
                txn,
                amount,
                txn.get("merchant_name") or txn.get("name"),
                date.fromisoformat(txn["date"]),
            )
        )
    if not prepared:
        return 0, 0
    for currency in currencies:
        await service.get_or_create_currency(currency)

    touched = {account_id for account_id, *_rest in prepared}
    lane1: dict[tuple[int, str], FinanceTransaction] = {}
    other_content: dict[tuple[int, date, int, str], int] = defaultdict(int)
    for row in (
        await db.exec(
            select(FinanceTransaction).where(
                FinanceTransaction.account_id.in_(touched),
                FinanceTransaction.source == Provider.PLAID,
                FinanceTransaction.deleted_at.is_(None),
            )
        )
    ).all():
        if row.external_id is not None:
            lane1[(row.account_id, row.external_id)] = row
        # Content from OTHER connections = a re-linked Item's existing history.
        if row.connection_id != connection.id:
            other_content[
                (row.account_id, row.date_, row.amount, normalize_payee(row.name or ""))
            ] += 1

    added = reconciled = 0
    for account_id, txn, amount, name, txn_date in prepared:
        external_id = txn["transaction_id"]
        existing = lane1.get((account_id, external_id))
        if existing is not None:  # same Item re-sync -> update in place
            existing.amount = amount
            existing.name = name
            existing.date_ = txn_date
            db.add(existing)
            await db.flush()
            reconciled += 1
            continue
        content_key = (account_id, txn_date, amount, normalize_payee(name or ""))
        if other_content.get(content_key, 0) > 0:  # re-link: already stored
            other_content[content_key] -= 1
            reconciled += 1
            continue

        pfc = txn.get("personal_finance_category") or {}
        category_id: int | None = None
        if pfc.get("primary"):
            category = await service.get_or_create_pfc_category(pfc["primary"])
            category_id = category.id
        await service.create_transaction(
            owner_user_id=connection.owner_user_id,
            account_id=account_id,
            connection_id=connection.id,
            amount=amount,
            txn_date=txn_date,
            name=name,
            source=Provider.PLAID,
            external_id=external_id,
            external_id_source="plaid",
            currency=(txn.get("iso_currency_code") or "usd").lower(),
            original_description=txn.get("name"),
            category_id=category_id,
            category_source="provider" if pfc.get("primary") else "unset",
        )
        added += 1
    return added, reconciled


async def _remove_transactions(db: AsyncSession, removed: list[dict[str, Any]]) -> int:
    count = 0
    for item in removed:
        txn = (
            await db.exec(
                select(FinanceTransaction).where(
                    FinanceTransaction.source == Provider.PLAID,
                    FinanceTransaction.external_id == item["transaction_id"],
                )
            )
        ).first()
        if txn is not None:
            txn.deleted_at = _utcnow()
            db.add(txn)
            count += 1
    return count


async def _upsert_securities(
    db: AsyncSession,
    service: FinanceService,
    plaid_securities: list[dict[str, Any]],
) -> dict[str, int]:
    """Upsert catalog securities keyed by Plaid ``security_id`` (some have no
    ticker, so the provider id is the stable key). Returns {plaid_id: our_id}."""
    mapping: dict[str, int] = {}
    for sec in plaid_securities:
        plaid_id = sec["security_id"]
        currency = (sec.get("iso_currency_code") or "usd").lower()
        await service.get_or_create_currency(currency)
        security = (
            await db.exec(
                select(FinanceSecurity).where(
                    FinanceSecurity.provider == Provider.PLAID,
                    FinanceSecurity.provider_security_id == plaid_id,
                )
            )
        ).first()
        if security is None:
            security = FinanceSecurity(
                provider=Provider.PLAID, provider_security_id=plaid_id
            )
        close = sec.get("close_price")
        security.ticker = sec.get("ticker_symbol")
        security.name = sec.get("name")
        security.security_type = sec.get("type")
        security.cusip = sec.get("cusip")
        security.isin = sec.get("isin")
        security.figi = sec.get("figi")
        security.currency = currency
        security.close_price = round(close * 100) if close is not None else None
        security.price_scale = 2
        db.add(security)
        await db.flush()
        mapping[plaid_id] = security.id
    return mapping


# How far back to pull investment transactions each sync. Plaid's endpoint has
# no cursor; we re-window and dedup by ``investment_transaction_id``, so this is
# just the trailing coverage, not an incremental checkpoint.
_INVESTMENT_LOOKBACK_DAYS = 730


def _map_plaid_trade_type(
    plaid_type: str, subtype: str | None, amount: float
) -> str:
    """Map a Plaid (type, subtype, amount) to a normalized ``FinanceTrade.type``.

    Plaid's coarse ``type`` (buy/sell/cancel/cash/fee/transfer) is often too
    blunt, so the granular ``subtype`` wins when it's meaningful. Plaid signs
    ``amount`` positive when cash is debited (money out: a buy) and negative
    when credited (money in: a sell), which disambiguates the direction of the
    ``transfer``/``cash`` types. Unknown shapes fall back to ``other`` rather
    than raising — an unrecognized trade must never break a sync.
    """
    sub = (subtype or "").lower()
    if "reinvest" in sub:
        return "reinvest"
    if "dividend" in sub:
        return "dividend"
    if "interest" in sub:
        return "interest"
    if "tax" in sub:
        return "tax"
    if "split" in sub:
        return "split"
    if sub in ("deposit", "contribution"):
        return "deposit"
    if sub == "withdrawal":
        return "withdrawal"
    if sub in ("buy", "buy to cover"):
        return "buy"
    if sub in ("sell", "sell short"):
        return "sell"
    if "fee" in sub:
        return "fee"
    coarse = (plaid_type or "").lower()
    if coarse in ("buy", "sell", "cancel", "fee"):
        return coarse
    if coarse == "transfer":
        return "transfer_out" if amount > 0 else "transfer_in"
    if coarse == "cash":
        return "withdrawal" if amount > 0 else "deposit"
    return "other"


async def _apply_trades(
    db: AsyncSession,
    service: FinanceService,
    plaid_txns: list[dict[str, Any]],
    account_by_plaid_id: dict[str, int],
    security_by_plaid_id: dict[str, int],
    *,
    connection: FinanceConnection,
) -> int:
    """Upsert each Plaid investment transaction as a FinanceTrade, deduped by
    ``investment_transaction_id`` (the external-id lane). Cash-only rows (fees,
    dividends, deposits) carry no security and are still recorded."""
    count = 0
    for txn in plaid_txns:
        plaid_account_id = txn.get("account_id")
        account_id = (
            account_by_plaid_id.get(plaid_account_id) if plaid_account_id else None
        )
        if account_id is None:
            continue
        plaid_security_id = txn.get("security_id")
        security_id = (
            security_by_plaid_id.get(plaid_security_id) if plaid_security_id else None
        )
        plaid_amount = txn.get("amount") or 0.0
        quantity = txn.get("quantity")
        price = txn.get("price")
        fees = txn.get("fees")
        # Plaid signs ``amount`` positive when cash is debited (a buy). Store it
        # in the app convention used by cash transactions — negative = money out
        # of the account — so amounts colorize consistently in the UI. The raw
        # provider value is preserved in ``raw_payload``.
        await service.upsert_trade(
            owner_user_id=connection.owner_user_id,
            account_id=account_id,
            security_id=security_id,
            connection_id=connection.id,
            source=Provider.PLAID,
            external_id=txn.get("investment_transaction_id"),
            external_id_source=Provider.PLAID,
            trade_type=_map_plaid_trade_type(
                txn.get("type", ""), txn.get("subtype"), plaid_amount
            ),
            subtype=txn.get("subtype"),
            trade_date=date.fromisoformat(txn["date"]),
            amount=round(-plaid_amount * 100),
            quantity_e8=round(quantity * 10**8) if quantity is not None else None,
            price=round(price * 100) if price is not None else None,
            fees=round(fees * 100) if fees is not None else None,
            currency=(txn.get("iso_currency_code") or "usd").lower(),
            name=txn.get("name"),
            raw_payload=txn,
        )
        count += 1
    return count


async def _apply_holdings(
    db: AsyncSession,
    service: FinanceService,
    plaid_holdings: list[dict[str, Any]],
    account_by_plaid_id: dict[str, int],
    security_by_plaid_id: dict[str, int],
    *,
    owner_user_id: int | None,
) -> int:
    """Upsert each Plaid position as a FinanceHolding. Balances come from
    ``accounts/get``, so holdings don't drive the account balance here."""
    count = 0
    for holding in plaid_holdings:
        plaid_account_id = holding.get("account_id")
        plaid_security_id = holding.get("security_id")
        if not plaid_account_id or not plaid_security_id:
            continue
        account_id = account_by_plaid_id.get(plaid_account_id)
        security_id = security_by_plaid_id.get(plaid_security_id)
        if account_id is None or security_id is None:
            continue
        price = holding.get("institution_price")
        cost = holding.get("cost_basis")
        as_of = holding.get("institution_price_as_of")
        await service.upsert_holding(
            owner_user_id=owner_user_id,
            account_id=account_id,
            security_id=security_id,
            as_of_date=date.fromisoformat(as_of) if as_of else _utcnow().date(),
            quantity_e8=round((holding.get("quantity") or 0) * 10**8),
            price=round(price * 100) if price is not None else None,
            cost_basis=round(cost * 100) if cost is not None else None,
            currency=(holding.get("iso_currency_code") or "usd").lower(),
            source=Provider.PLAID,
            sync_account_balance=False,
        )
        count += 1
    return count


async def sync_plaid_connection(
    db: AsyncSession,
    connection: FinanceConnection,
    *,
    client: PlaidClient | None = None,
) -> SyncResult:
    """Pull accounts + transactions (+ holdings) for a connection."""
    client = client or PlaidClient()
    service = FinanceService(db)
    access_token = decrypt_secret(
        connection.access_token_encrypted, context=_ACCESS_TOKEN_CONTEXT
    )
    result = SyncResult(connection_id=connection.id)

    accounts, item = await client.get_accounts(access_token)
    # Label the connection with the real institution name once, so the UI shows
    # "Chase" rather than "Plaid · Sandbox".
    if not connection.label and item.get("institution_id"):
        try:
            connection.label = await client.get_institution_name(
                item["institution_id"]
            )
        except PlaidError:
            pass
    account_by_plaid_id = await _upsert_accounts(db, service, connection, accounts)
    result.accounts = len(account_by_plaid_id)

    # Investment positions — only items linked with the ``investments`` product
    # return holdings; anything else raises and is skipped.
    try:
        plaid_holdings, plaid_securities = await client.get_holdings(access_token)
    except PlaidError:
        plaid_holdings, plaid_securities = [], []
    if plaid_holdings:
        security_by_plaid_id = await _upsert_securities(db, service, plaid_securities)
        result.holdings = await _apply_holdings(
            db,
            service,
            plaid_holdings,
            account_by_plaid_id,
            security_by_plaid_id,
            owner_user_id=connection.owner_user_id,
        )

    # Investment transactions (trades) — same investments-product gate as
    # holdings. No cursor: page a trailing date window by offset and dedup on
    # ``investment_transaction_id``. Securities here can include ones not held
    # anymore, so re-upsert the catalog from this response too.
    inv_txns: list[dict[str, Any]] = []
    inv_securities: list[dict[str, Any]] = []
    try:
        end = _utcnow().date()
        start = end - timedelta(days=_INVESTMENT_LOOKBACK_DAYS)
        offset = 0
        while True:
            page = await client.get_investment_transactions(
                access_token, start.isoformat(), end.isoformat(), offset=offset
            )
            batch = page.get("investment_transactions", [])
            inv_txns.extend(batch)
            inv_securities.extend(page.get("securities", []))
            total = page.get("total_investment_transactions", len(inv_txns))
            offset += len(batch)
            if not batch or offset >= total:
                break
    except PlaidError:
        inv_txns, inv_securities = [], []
    if inv_txns:
        trade_security_by_plaid_id = await _upsert_securities(
            db, service, inv_securities
        )
        result.trades = await _apply_trades(
            db,
            service,
            inv_txns,
            account_by_plaid_id,
            trade_security_by_plaid_id,
            connection=connection,
        )

    cursor = connection.sync_cursor
    connection.last_sync_attempt_at = _utcnow()
    # Collect every page first so within-day ordinals span the full set (they
    # must be stable for the LANE-2 re-link dedup to line up).
    collected: list[dict[str, Any]] = []
    while True:
        page = await client.sync_transactions(access_token, cursor)
        collected.extend(page.get("added", []) + page.get("modified", []))
        result.removed += await _remove_transactions(db, page.get("removed", []))
        cursor = page.get("next_cursor")
        if not page.get("has_more"):
            break

    result.added, result.updated = await _apply_transactions(
        db,
        service,
        collected,
        account_by_plaid_id,
        connection=connection,
    )

    connection.sync_cursor = cursor
    connection.status = "healthy"
    connection.needs_user_action = False
    connection.last_successful_sync_at = _utcnow()
    db.add(connection)
    await db.flush()
    return result


async def list_plaid_connections(
    db: AsyncSession, *, owner_user_id: int | None = None
) -> list[FinanceConnection]:
    """Active (non-deleted) Plaid connections for an owner."""
    query = select(FinanceConnection).where(
        FinanceConnection.provider == Provider.PLAID,
        FinanceConnection.deleted_at.is_(None),
    )
    if owner_user_id is not None:
        query = query.where(FinanceConnection.owner_user_id == owner_user_id)
    return list((await db.exec(query)).all())


async def get_connection(
    db: AsyncSession, connection_id: int, *, owner_user_id: int | None = None
) -> FinanceConnection | None:
    """A single non-deleted connection, scoped to the owner when given."""
    query = select(FinanceConnection).where(
        FinanceConnection.id == connection_id,
        FinanceConnection.deleted_at.is_(None),
    )
    if owner_user_id is not None:
        query = query.where(FinanceConnection.owner_user_id == owner_user_id)
    return (await db.exec(query)).first()


async def disconnect_connection(
    db: AsyncSession,
    connection_id: int,
    *,
    owner_user_id: int | None = None,
    client: PlaidClient | None = None,
) -> bool:
    """Disconnect a connection: revoke the Item at Plaid (best-effort), then
    soft-delete the connection and every account under it. Transactions/history
    rows are kept. Returns False if the connection doesn't exist for this owner.

    The remote revoke is best-effort: if Plaid is unreachable or the token is
    already invalid, we still tear down locally so a stuck connection can always
    be removed.
    """
    connection = await get_connection(db, connection_id, owner_user_id=owner_user_id)
    if connection is None:
        return False

    if connection.access_token_encrypted:
        try:
            access_token = decrypt_secret(
                connection.access_token_encrypted, context=_ACCESS_TOKEN_CONTEXT
            )
            await (client or PlaidClient()).remove_item(access_token)
        except (PlaidError, httpx.HTTPError):
            # already-invalid token (PlaidError) or Plaid unreachable
            # (timeout/connect error from httpx) — tear down locally anyway so a
            # stuck connection can always be removed.
            pass

    now = _utcnow()
    accounts = (
        await db.exec(
            select(FinanceAccount).where(
                FinanceAccount.connection_id == connection_id,
                FinanceAccount.deleted_at.is_(None),
            )
        )
    ).all()
    for account in accounts:
        account.deleted_at = now
        db.add(account)

    connection.status = "revoked"
    connection.removed_at = now
    connection.deleted_at = now
    connection.access_token_encrypted = None
    db.add(connection)
    await db.flush()
    return True


async def _recompute_net_worth(
    db: AsyncSession, owner_user_id: int | None, results: list[SyncResult]
) -> None:
    """Post-sync reconcile: pair internal transfers (so a card payment doesn't
    double-count as spend), detect recurring streams + "wasting money" insights,
    then refresh the net-worth snapshot series so the Overview trend reflects
    the new data. No-op if nothing synced."""
    if not results:
        return
    from app.services.finance import networth_service
    from app.services.finance.categorize import (
        detect_recurring,
        detect_transfers,
        generate_insights,
    )

    await detect_transfers(db, owner_user_id=owner_user_id)
    await detect_recurring(db, owner_user_id=owner_user_id)
    await generate_insights(db, owner_user_id=owner_user_id)
    await networth_service.recompute_snapshots(db, owner_user_id=owner_user_id)


async def sync_owner_connections(
    db: AsyncSession,
    *,
    owner_user_id: int | None = None,
    client: PlaidClient | None = None,
) -> list[SyncResult]:
    """Sync every Plaid connection for an owner; returns one result each."""
    client = client or PlaidClient()
    results: list[SyncResult] = []
    for connection in await list_plaid_connections(db, owner_user_id=owner_user_id):
        results.append(await sync_plaid_connection(db, connection, client=client))
    await _recompute_net_worth(db, owner_user_id, results)
    return results


async def complete_hosted_link(
    db: AsyncSession,
    link_token: str,
    *,
    owner_user_id: int | None = None,
    client: PlaidClient | None = None,
) -> list[SyncResult]:
    """Finish a Hosted Link: pull any public tokens the user produced, exchange
    each into a connection, and sync it. Returns ``[]`` while still pending."""
    client = client or PlaidClient()
    results: list[SyncResult] = []
    for public_token in await client.link_public_tokens(link_token):
        access_token, item_id = await client.exchange_public_token(public_token)
        connection = await create_plaid_connection(
            db,
            owner_user_id=owner_user_id,
            access_token=access_token,
            item_id=item_id,
            environment=client.environment,
        )
        results.append(await sync_plaid_connection(db, connection, client=client))
    await _recompute_net_worth(db, owner_user_id, results)
    return results


async def process_plaid_webhook(
    db: AsyncSession,
    payload: dict[str, Any],
    *,
    client: PlaidClient | None = None,
) -> str:
    """Log an inbound Plaid webhook and, for transaction updates, sync the item
    it names. Every webhook is recorded to ``finance_webhook_event`` (the replay
    buffer); the sync itself is idempotent, so a re-delivered webhook is safe.

    Returns a short status: ``synced`` | ``ignored`` | ``unknown_item``.
    """
    item_id = payload.get("item_id")
    webhook_type = payload.get("webhook_type")
    event = FinanceWebhookEvent(
        provider=Provider.PLAID,
        provider_item_id=item_id,
        webhook_type=webhook_type,
        webhook_code=payload.get("webhook_code"),
        payload=payload,
        status="received",
    )
    db.add(event)
    await db.flush()

    if webhook_type != "TRANSACTIONS":
        event.status = "ignored"
        return "ignored"
    connection = (
        await db.exec(
            select(FinanceConnection).where(
                FinanceConnection.provider == Provider.PLAID,
                FinanceConnection.provider_item_id == item_id,
                FinanceConnection.deleted_at.is_(None),
            )
        )
    ).first()
    if connection is None:
        event.status = "ignored"
        return "unknown_item"
    result = await sync_plaid_connection(
        db, connection, client=client or PlaidClient()
    )
    event.connection_id = connection.id
    event.status = "processed"
    await _recompute_net_worth(db, connection.owner_user_id, [result])
    return "synced"
