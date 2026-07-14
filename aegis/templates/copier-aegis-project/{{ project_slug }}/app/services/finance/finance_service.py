"""Finance service: manual accounts, transactions, valuations, net worth.

Mirrors ``payment_service.py``: a plain class taking an ``AsyncSession`` in
``__init__`` (the FastAPI dependency wrapper lives in ``deps.py``). Reads go
through ``self.db.exec(select(...))``; writes ``self.db.add(...)`` +
``self.db.flush()`` but do NOT commit — the caller (route / CLI / scheduler
job) owns the transaction boundary.

Rows are owner-scoped by ``owner_user_id``; the FK to the auth ``user`` table
is added only when auth is present (via the finance_auth_link migration), so
methods take ``owner_user_id`` as a plain, optional filter. Money is integer
minor units. Provider integration (Plaid/SnapTrade) lands in later tickets;
this layer is manual + import only.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import and_, case, func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.services.finance.constants import Provider
from app.services.finance.models import (
    FinanceAccount,
    FinanceCategory,
    FinanceCategoryAlias,
    FinanceConnection,
    FinanceCurrency,
    FinanceHolding,
    FinanceImportBatch,
    FinanceImportBatchRow,
    FinanceInsight,
    FinanceInstitution,
    FinanceRecurringStream,
    FinanceSecurity,
    FinanceSecurityPrice,
    FinanceTrade,
    FinanceTransaction,
    FinanceTransactionSplit,
    FinanceTransfer,
    FinanceValuation,
)
from app.services.finance.schemas import (
    FinanceHealth,
    FinanceStatusSummary,
    NetWorthResponse,
)

_DEFAULT_CURRENCY = "usd"
# Holdings store quantity as units x 1e8 (``quantity_e8``); prices are scaled
# integers (``price / 10**price_scale`` = unit price).
_QUANTITY_SCALE = 10**8


def _utcnow() -> datetime:
    """Naive-UTC timestamp (matches the models' convention)."""
    return datetime.now(UTC).replace(tzinfo=None)


def market_value_cents(
    quantity_e8: int, price: int | None, price_scale: int
) -> int:
    """Position value in integer cents: shares x unit-price, rounded.

    ``shares = quantity_e8 / 1e8``; ``unit_price = price / 10**price_scale``;
    value in cents = shares * unit_price * 100.

    Stays in integer arithmetic (Python ints are arbitrary-precision) so large
    positions never lose precision to float rounding; the result is rounded to
    the nearest cent, half away from zero.
    """
    if not price:
        return 0
    denom = _QUANTITY_SCALE * (10**price_scale)
    numerator = quantity_e8 * price * 100
    if numerator < 0:
        return -((-numerator + denom // 2) // denom)
    return (numerator + denom // 2) // denom


class FinanceService:
    """Manual account / transaction / valuation CRUD + the net-worth read."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------ #
    # Reference data (get-or-create)
    # ------------------------------------------------------------------ #
    async def get_or_create_currency(
        self,
        code: str = _DEFAULT_CURRENCY,
        *,
        name: str | None = None,
        symbol: str | None = None,
        decimals: int = 2,
    ) -> FinanceCurrency:
        code = code.lower()
        existing = (
            await self.db.exec(
                select(FinanceCurrency).where(FinanceCurrency.code == code)
            )
        ).first()
        if existing:
            return existing
        currency = FinanceCurrency(
            code=code, name=name or code.upper(), symbol=symbol, decimals=decimals
        )
        self.db.add(currency)
        await self.db.flush()
        return currency

    async def get_or_create_institution(
        self,
        *,
        provider: str,
        name: str,
        provider_institution_id: str | None = None,
    ) -> FinanceInstitution:
        if provider_institution_id is not None:
            existing = (
                await self.db.exec(
                    select(FinanceInstitution).where(
                        FinanceInstitution.provider == provider,
                        FinanceInstitution.provider_institution_id
                        == provider_institution_id,
                    )
                )
            ).first()
            if existing:
                return existing
        inst = FinanceInstitution(
            provider=provider,
            name=name,
            provider_institution_id=provider_institution_id,
        )
        self.db.add(inst)
        await self.db.flush()
        return inst

    # ------------------------------------------------------------------ #
    # Accounts
    # ------------------------------------------------------------------ #
    async def create_manual_account(
        self,
        *,
        name: str,
        account_type: str,
        classification: str,
        owner_user_id: int | None = None,
        organization_id: int | None = None,
        current_balance: int = 0,
        currency: str = _DEFAULT_CURRENCY,
        institution_id: int | None = None,
    ) -> FinanceAccount:
        await self.get_or_create_currency(currency)
        account = FinanceAccount(
            owner_user_id=owner_user_id,
            organization_id=organization_id,
            provider=Provider.MANUAL,
            name=name,
            account_type=account_type,
            classification=classification,
            current_balance=current_balance,
            currency=currency,
            institution_id=institution_id,
            is_manual=True,
        )
        self.db.add(account)
        await self.db.flush()
        return account

    async def get_account(
        self, account_id: int, *, owner_user_id: int | None = None
    ) -> FinanceAccount | None:
        query = select(FinanceAccount).where(
            FinanceAccount.id == account_id,
            FinanceAccount.deleted_at.is_(None),
        )
        if owner_user_id is not None:
            query = query.where(FinanceAccount.owner_user_id == owner_user_id)
        return (await self.db.exec(query)).first()

    async def list_accounts(
        self,
        *,
        owner_user_id: int | None = None,
        include_hidden: bool = False,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[FinanceAccount], int]:
        query = select(FinanceAccount).where(FinanceAccount.deleted_at.is_(None))
        count_query = (
            select(func.count())
            .select_from(FinanceAccount)
            .where(FinanceAccount.deleted_at.is_(None))
        )
        if owner_user_id is not None:
            query = query.where(FinanceAccount.owner_user_id == owner_user_id)
            count_query = count_query.where(
                FinanceAccount.owner_user_id == owner_user_id
            )
        if not include_hidden:
            query = query.where(~FinanceAccount.is_hidden)
            count_query = count_query.where(~FinanceAccount.is_hidden)
        total = (await self.db.exec(count_query)).one()
        query = (
            query.order_by(FinanceAccount.classification, FinanceAccount.name)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list((await self.db.exec(query)).all()), total

    async def update_account_balance(
        self,
        account_id: int,
        *,
        current_balance: int,
        owner_user_id: int | None = None,
    ) -> FinanceAccount | None:
        account = await self.get_account(account_id, owner_user_id=owner_user_id)
        if account is None:
            return None
        account.current_balance = current_balance
        account.balance_as_of = _utcnow()
        account.updated_at = _utcnow()
        self.db.add(account)
        await self.db.flush()
        return account

    # ------------------------------------------------------------------ #
    # Transactions (with two-lane dedup)
    # ------------------------------------------------------------------ #
    async def transaction_exists(
        self,
        *,
        account_id: int,
        source: str,
        external_id: str | None = None,
        import_hash: str | None = None,
    ) -> bool:
        """Two-lane dedup probe.

        LANE 1 keys on ``(account_id, source, external_id)`` for provider rows;
        LANE 2 keys on ``(account_id, import_hash)`` for id-less file imports.
        Soft-deleted rows don't count (they release the key).
        """
        query = select(FinanceTransaction.id).where(
            FinanceTransaction.account_id == account_id,
            FinanceTransaction.deleted_at.is_(None),
        )
        if external_id is not None:
            query = query.where(
                FinanceTransaction.source == source,
                FinanceTransaction.external_id == external_id,
            )
        elif import_hash is not None:
            query = query.where(FinanceTransaction.import_hash == import_hash)
        else:
            return False
        return (await self.db.exec(query)).first() is not None

    async def find_transaction(
        self,
        *,
        account_id: int,
        source: str,
        external_id: str | None = None,
        import_hash: str | None = None,
    ) -> FinanceTransaction | None:
        """Return the existing two-lane-dedup match, or None (for importers)."""
        query = select(FinanceTransaction).where(
            FinanceTransaction.account_id == account_id,
            FinanceTransaction.deleted_at.is_(None),
        )
        if external_id is not None:
            query = query.where(
                FinanceTransaction.source == source,
                FinanceTransaction.external_id == external_id,
            )
        elif import_hash is not None:
            query = query.where(FinanceTransaction.import_hash == import_hash)
        else:
            return None
        return (await self.db.exec(query)).first()

    async def create_transaction(
        self,
        *,
        account_id: int,
        amount: int,
        txn_date: date,
        owner_user_id: int | None = None,
        name: str | None = None,
        source: str = Provider.MANUAL,
        external_id: str | None = None,
        external_id_source: str | None = None,
        import_hash: str | None = None,
        within_day_ordinal: int = 0,
        import_batch_id: int | None = None,
        connection_id: int | None = None,
        raw_amount: int | None = None,
        raw_sign_convention: str | None = None,
        original_description: str | None = None,
        memo: str | None = None,
        check_number: str | None = None,
        currency: str = _DEFAULT_CURRENCY,
        category_id: int | None = None,
        category_source: str = "unset",
        is_split: bool = False,
    ) -> FinanceTransaction:
        txn = FinanceTransaction(
            owner_user_id=owner_user_id,
            account_id=account_id,
            connection_id=connection_id,
            amount=amount,
            date_=txn_date,
            name=name,
            source=source,
            external_id=external_id,
            external_id_source=external_id_source,
            import_hash=import_hash,
            within_day_ordinal=within_day_ordinal,
            import_batch_id=import_batch_id,
            raw_amount=raw_amount,
            raw_sign_convention=raw_sign_convention,
            original_description=original_description,
            memo=memo,
            check_number=check_number,
            currency=currency,
            category_id=category_id,
            category_source=category_source,
            is_split=is_split,
        )
        self.db.add(txn)
        await self.db.flush()
        return txn

    async def create_split(
        self,
        *,
        parent_transaction_id: int,
        amount: int,
        owner_user_id: int | None = None,
        category_id: int | None = None,
        memo: str | None = None,
        sort_order: int = 0,
        currency: str = _DEFAULT_CURRENCY,
    ) -> FinanceTransactionSplit:
        split = FinanceTransactionSplit(
            owner_user_id=owner_user_id,
            parent_transaction_id=parent_transaction_id,
            amount=amount,
            category_id=category_id,
            memo=memo,
            sort_order=sort_order,
            currency=currency,
        )
        self.db.add(split)
        await self.db.flush()
        return split

    async def resolve_category_alias(
        self, category_hint: str | None
    ) -> int | None:
        """Map a free-text category string to a category id via
        finance_category_alias (normalized lookup). None if unmatched.

        Prefers a user alias over a global (owner NULL) seed when both match.
        """
        if not category_hint:
            return None
        from app.services.finance.importers.base import normalize_payee

        normalized = normalize_payee(category_hint)
        if not normalized:
            return None
        query = (
            select(FinanceCategoryAlias.category_id)
            .where(FinanceCategoryAlias.normalized_alias == normalized)
            .order_by(FinanceCategoryAlias.owner_user_id.desc())
        )
        return (await self.db.exec(query)).first()

    async def get_or_create_pfc_category(
        self, pfc_primary: str
    ) -> FinanceCategory:
        """Fetch (or create) the system category for a Plaid personal-finance
        category primary (e.g. ``FOOD_AND_DRINK``). Categories are global/system
        seeds (owner NULL), shared across users and created on first sight."""
        slug = pfc_primary.strip().lower()
        existing = (
            await self.db.exec(
                select(FinanceCategory).where(
                    FinanceCategory.slug == slug,
                    FinanceCategory.owner_user_id.is_(None),
                )
            )
        ).first()
        if existing is not None:
            return existing
        upper = pfc_primary.strip().upper()
        classification = (
            "income"
            if upper == "INCOME"
            else "transfer"
            if upper.startswith("TRANSFER")
            else "expense"
        )
        category = FinanceCategory(
            name=pfc_primary.replace("_", " ").title(),
            slug=slug,
            classification=classification,
            plaid_pfc_primary=upper,
            is_system=True,
        )
        self.db.add(category)
        await self.db.flush()
        return category

    async def spending_by_category(
        self, *, owner_user_id: int | None = None, days: int = 30
    ) -> list[tuple[str, int]]:
        """Total outflow per category over the recent window — the spending
        breakdown. Expense outflows only (amount < 0), on live accounts, keyed
        by category name and returned largest-first as positive cents."""
        cutoff = date.today() - timedelta(days=days)
        live_accounts = select(FinanceAccount.id).where(
            FinanceAccount.deleted_at.is_(None)
        )
        filters = [
            FinanceTransaction.deleted_at.is_(None),
            FinanceTransaction.dedup_status != "duplicate",
            FinanceTransaction.excluded_from_reports.is_(False),
            FinanceTransaction.account_id.in_(live_accounts),
            FinanceTransaction.category_id.is_not(None),
            FinanceTransaction.amount < 0,
            FinanceTransaction.date_ >= cutoff,
        ]
        if owner_user_id is not None:
            filters.append(FinanceTransaction.owner_user_id == owner_user_id)
        rows = (
            await self.db.exec(
                select(
                    FinanceCategory.name,
                    func.sum(FinanceTransaction.amount),
                )
                .join(
                    FinanceCategory,
                    FinanceTransaction.category_id == FinanceCategory.id,
                )
                .where(*filters)
                .group_by(FinanceCategory.name)
            )
        ).all()
        result = [(name, -int(total)) for name, total in rows]
        result.sort(key=lambda pair: pair[1], reverse=True)
        return result

    async def spending_summary(
        self, *, owner_user_id: int | None = None, month: str | None = None
    ) -> list[tuple[str, int]]:
        """Per-category spend for one calendar month (default: current month),
        transfers excluded. ``month`` is ``YYYY-MM``. This is the report the
        insights + UI consume, so a card payment never inflates a category."""
        if month:
            year, mon = (int(part) for part in month.split("-", 1))
            start = date(year, mon, 1)
        else:
            today = date.today()
            start = date(today.year, today.month, 1)
        end = (
            date(start.year + 1, 1, 1)
            if start.month == 12
            else date(start.year, start.month + 1, 1)
        )
        live_accounts = select(FinanceAccount.id).where(
            FinanceAccount.deleted_at.is_(None)
        )
        filters = [
            FinanceTransaction.deleted_at.is_(None),
            FinanceTransaction.dedup_status != "duplicate",
            FinanceTransaction.excluded_from_reports.is_(False),
            FinanceTransaction.account_id.in_(live_accounts),
            FinanceTransaction.category_id.is_not(None),
            FinanceTransaction.amount < 0,
            FinanceTransaction.date_ >= start,
            FinanceTransaction.date_ < end,
        ]
        if owner_user_id is not None:
            filters.append(FinanceTransaction.owner_user_id == owner_user_id)
        rows = (
            await self.db.exec(
                select(FinanceCategory.name, func.sum(FinanceTransaction.amount))
                .join(
                    FinanceCategory,
                    FinanceTransaction.category_id == FinanceCategory.id,
                )
                .where(*filters)
                .group_by(FinanceCategory.name)
            )
        ).all()
        result = [(name, -int(total)) for name, total in rows]
        result.sort(key=lambda pair: pair[1], reverse=True)
        return result

    async def _get_transfer(
        self, transfer_id: int, *, owner_user_id: int | None
    ) -> FinanceTransfer | None:
        query = select(FinanceTransfer).where(FinanceTransfer.id == transfer_id)
        if owner_user_id is not None:
            query = query.where(FinanceTransfer.owner_user_id == owner_user_id)
        return (await self.db.exec(query)).first()

    async def list_transfers(
        self, *, owner_user_id: int | None = None, status: str | None = None
    ) -> list[FinanceTransfer]:
        """Transfers for an owner (optionally one ``status``), newest first."""
        query = select(FinanceTransfer)
        if owner_user_id is not None:
            query = query.where(FinanceTransfer.owner_user_id == owner_user_id)
        if status is not None:
            query = query.where(FinanceTransfer.status == status)
        query = query.order_by(
            FinanceTransfer.transfer_date.desc(), FinanceTransfer.id.desc()
        )
        return list((await self.db.exec(query)).all())

    async def transactions_by_ids(
        self, ids: list[int]
    ) -> dict[int, FinanceTransaction]:
        """Fetch transactions by id in one query, keyed by id (for enrichment)."""
        if not ids:
            return {}
        rows = (
            await self.db.exec(
                select(FinanceTransaction).where(FinanceTransaction.id.in_(ids))
            )
        ).all()
        return {t.id: t for t in rows}

    # -- Recurring streams ---------------------------------------------------

    async def list_recurring(
        self, *, owner_user_id: int | None = None
    ) -> list[FinanceRecurringStream]:
        """Active recurring streams, soonest-due first."""
        query = select(FinanceRecurringStream).where(
            FinanceRecurringStream.deleted_at.is_(None),
            FinanceRecurringStream.status != "cancelled",
        )
        if owner_user_id is not None:
            query = query.where(
                FinanceRecurringStream.owner_user_id == owner_user_id
            )
        query = query.order_by(FinanceRecurringStream.next_expected_date)
        return list((await self.db.exec(query)).all())

    async def mute_recurring(
        self, stream_id: int, *, owner_user_id: int | None = None
    ) -> FinanceRecurringStream | None:
        """Mute a stream so it stops raising price-hike insights."""
        query = select(FinanceRecurringStream).where(
            FinanceRecurringStream.id == stream_id
        )
        if owner_user_id is not None:
            query = query.where(
                FinanceRecurringStream.owner_user_id == owner_user_id
            )
        stream = (await self.db.exec(query)).first()
        if stream is None:
            return None
        stream.is_muted = True
        self.db.add(stream)
        await self.db.flush()
        return stream

    # -- Insights ------------------------------------------------------------

    async def list_insights(
        self, *, owner_user_id: int | None = None, status: str | None = "new"
    ) -> list[FinanceInsight]:
        """Insights for an owner (default: only ``new``), newest first."""
        query = select(FinanceInsight)
        if owner_user_id is not None:
            query = query.where(FinanceInsight.owner_user_id == owner_user_id)
        if status is not None:
            query = query.where(FinanceInsight.status == status)
        query = query.order_by(FinanceInsight.id.desc())
        return list((await self.db.exec(query)).all())

    async def count_new_insights(self, *, owner_user_id: int | None = None) -> int:
        """How many unseen insights — the finance card's badge count."""
        query = select(func.count()).select_from(FinanceInsight).where(
            FinanceInsight.status == "new"
        )
        if owner_user_id is not None:
            query = query.where(FinanceInsight.owner_user_id == owner_user_id)
        return (await self.db.exec(query)).one()

    async def dismiss_insight(
        self, insight_id: int, *, owner_user_id: int | None = None
    ) -> FinanceInsight | None:
        """Dismiss an insight (survives re-runs via its dedup_key)."""
        query = select(FinanceInsight).where(FinanceInsight.id == insight_id)
        if owner_user_id is not None:
            query = query.where(FinanceInsight.owner_user_id == owner_user_id)
        insight = (await self.db.exec(query)).first()
        if insight is None:
            return None
        insight.status = "dismissed"
        insight.is_read = True
        insight.dismissed_at = datetime.now(UTC).replace(tzinfo=None)
        self.db.add(insight)
        await self.db.flush()
        return insight

    async def confirm_transfer(
        self, transfer_id: int, *, owner_user_id: int | None = None
    ) -> FinanceTransfer | None:
        """Confirm a suggested transfer: flip to ``confirmed`` and flag both
        legs out of reports + cross-link them. Returns None if not found for
        this owner."""
        transfer = await self._get_transfer(transfer_id, owner_user_id=owner_user_id)
        if transfer is None:
            return None
        transfer.status = "confirmed"
        self.db.add(transfer)
        legs = [
            await self.db.get(FinanceTransaction, txn_id)
            for txn_id in (transfer.from_transaction_id, transfer.to_transaction_id)
            if txn_id is not None
        ]
        legs = [leg for leg in legs if leg is not None]
        for leg in legs:
            leg.is_transfer = True
            leg.excluded_from_reports = True
            leg.transfer_group_id = transfer.id
            self.db.add(leg)
        if len(legs) == 2:
            legs[0].transfer_pair_transaction_id = legs[1].id
            legs[1].transfer_pair_transaction_id = legs[0].id
        await self.db.flush()
        return transfer

    async def reject_transfer(
        self, transfer_id: int, *, owner_user_id: int | None = None
    ) -> FinanceTransfer | None:
        """Reject a transfer: mark ``rejected`` and restore both legs to normal
        spend/income. The row persists so the pair is never re-suggested."""
        transfer = await self._get_transfer(transfer_id, owner_user_id=owner_user_id)
        if transfer is None:
            return None
        transfer.status = "rejected"
        self.db.add(transfer)
        for txn_id in (transfer.from_transaction_id, transfer.to_transaction_id):
            if txn_id is None:
                continue
            leg = await self.db.get(FinanceTransaction, txn_id)
            if leg is not None and leg.transfer_group_id == transfer.id:
                leg.is_transfer = False
                leg.excluded_from_reports = False
                leg.transfer_group_id = None
                leg.transfer_pair_transaction_id = None
                self.db.add(leg)
        await self.db.flush()
        return transfer

    async def list_transactions(
        self,
        *,
        owner_user_id: int | None = None,
        account_id: int | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        category_id: int | None = None,
        query: str | None = None,
        include_transfers: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[FinanceTransaction], int]:
        # Default view: not soft-deleted, and never the losing side of a dedup.
        # Also hide transactions whose account was removed/disconnected — the
        # rows are kept for history + re-link reconciliation, but shouldn't show
        # in the register once the account is gone. Paired transfer legs are
        # hidden by default (``include_transfers``) so a checking->card payment
        # doesn't show as two lines of spend/income.
        filters = [
            FinanceTransaction.deleted_at.is_(None),
            FinanceTransaction.dedup_status != "duplicate",
            FinanceTransaction.account_id.in_(
                select(FinanceAccount.id).where(FinanceAccount.deleted_at.is_(None))
            ),
        ]
        if not include_transfers:
            filters.append(FinanceTransaction.is_transfer.is_(False))
        if owner_user_id is not None:
            filters.append(FinanceTransaction.owner_user_id == owner_user_id)
        if account_id is not None:
            filters.append(FinanceTransaction.account_id == account_id)
        if from_date is not None:
            filters.append(FinanceTransaction.date_ >= from_date)
        if to_date is not None:
            filters.append(FinanceTransaction.date_ <= to_date)
        if category_id is not None:
            filters.append(FinanceTransaction.category_id == category_id)
        if query:
            filters.append(FinanceTransaction.name.ilike(f"%{query}%"))
        select_query = select(FinanceTransaction).where(*filters)
        count_query = (
            select(func.count()).select_from(FinanceTransaction).where(*filters)
        )
        total = (await self.db.exec(count_query)).one()
        query_obj = (
            select_query.order_by(
                FinanceTransaction.date_.desc(), FinanceTransaction.id.desc()
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list((await self.db.exec(query_obj)).all()), total

    async def account_transaction_totals(
        self,
        *,
        owner_user_id: int | None = None,
        account_ids: list[int] | None = None,
    ) -> dict[int, int]:
        """Sum of (non-duplicate, non-deleted) transaction amounts per account.

        The register-style balance shown per account in the UI when no
        statement balance/valuation is set. One aggregate query, keyed by
        account id — never one query per account. Pass ``account_ids`` to scope
        the aggregate to a page's accounts instead of the whole owner.
        """
        if account_ids is not None and not account_ids:
            return {}
        filters = [
            FinanceTransaction.deleted_at.is_(None),
            FinanceTransaction.dedup_status != "duplicate",
        ]
        if owner_user_id is not None:
            filters.append(FinanceTransaction.owner_user_id == owner_user_id)
        if account_ids is not None:
            filters.append(FinanceTransaction.account_id.in_(account_ids))
        query = (
            select(
                FinanceTransaction.account_id,
                func.coalesce(func.sum(FinanceTransaction.amount), 0),
            )
            .where(*filters)
            .group_by(FinanceTransaction.account_id)
        )
        return {
            account_id: int(total or 0)
            for account_id, total in (await self.db.exec(query)).all()
        }

    # ------------------------------------------------------------------ #
    # Valuations (manual / off-aggregator asset marks)
    # ------------------------------------------------------------------ #
    async def add_valuation(
        self,
        *,
        account_id: int,
        as_of_date: date,
        value: int,
        owner_user_id: int | None = None,
        source: str = "manual",
        source_ref: str | None = None,
    ) -> FinanceValuation:
        valuation = FinanceValuation(
            owner_user_id=owner_user_id,
            account_id=account_id,
            as_of_date=as_of_date,
            value=value,
            source=source,
            source_ref=source_ref,
        )
        self.db.add(valuation)
        await self.db.flush()
        return valuation

    # ------------------------------------------------------------------ #
    # Net worth
    # ------------------------------------------------------------------ #
    async def _account_rollup(
        self, *, owner_user_id: int | None = None
    ) -> tuple[int, int, int]:
        """(assets, liabilities, account_count) in a single aggregate query.

        Assets/liabilities sum only *visible* accounts; the count includes
        hidden ones — the two filters differ, so they're expressed as
        conditional sums over one scan rather than three separate queries.
        """
        query = (
            select(
                func.coalesce(
                    func.sum(
                        case(
                            (
                                and_(
                                    FinanceAccount.classification == "asset",
                                    ~FinanceAccount.is_hidden,
                                ),
                                FinanceAccount.current_balance,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                and_(
                                    FinanceAccount.classification == "liability",
                                    ~FinanceAccount.is_hidden,
                                ),
                                FinanceAccount.current_balance,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ),
                func.count(),
            )
            .select_from(FinanceAccount)
            .where(FinanceAccount.deleted_at.is_(None))
        )
        if owner_user_id is not None:
            query = query.where(FinanceAccount.owner_user_id == owner_user_id)
        assets, liabilities, count = (await self.db.exec(query)).one()
        return int(assets or 0), int(liabilities or 0), int(count or 0)

    async def _connection_rollup(
        self, *, owner_user_id: int | None = None
    ) -> tuple[int, int]:
        """(connection_count, needs_action_count) in a single aggregate query."""
        query = (
            select(
                func.count(),
                func.coalesce(
                    func.sum(
                        case((FinanceConnection.needs_user_action, 1), else_=0)
                    ),
                    0,
                ),
            )
            .select_from(FinanceConnection)
            .where(FinanceConnection.deleted_at.is_(None))
        )
        if owner_user_id is not None:
            query = query.where(
                FinanceConnection.owner_user_id == owner_user_id
            )
        connections, needs_action = (await self.db.exec(query)).one()
        return int(connections or 0), int(needs_action or 0)

    async def _asset_liability_totals(
        self, *, owner_user_id: int | None = None
    ) -> tuple[int, int]:
        """Live (assets, liabilities) totals summed across visible accounts."""
        assets, liabilities, _ = await self._account_rollup(
            owner_user_id=owner_user_id
        )
        return assets, liabilities

    async def get_net_worth(
        self, *, owner_user_id: int | None = None, currency: str = _DEFAULT_CURRENCY
    ) -> NetWorthResponse:
        assets, liabilities = await self._asset_liability_totals(
            owner_user_id=owner_user_id
        )
        return NetWorthResponse(
            net_worth_amount=assets - liabilities,
            total_assets_amount=assets,
            total_liabilities_amount=liabilities,
            currency=currency,
        )

    async def get_status_summary(
        self, *, owner_user_id: int | None = None, currency: str = _DEFAULT_CURRENCY
    ) -> FinanceStatusSummary:
        """Headline numbers for the dashboard card, health check, and CLI."""
        assets, liabilities, account_count = await self._account_rollup(
            owner_user_id=owner_user_id
        )
        connection_count, _ = await self._connection_rollup(
            owner_user_id=owner_user_id
        )
        new_insight_count = await self.count_new_insights(
            owner_user_id=owner_user_id
        )
        return FinanceStatusSummary(
            net_worth_amount=assets - liabilities,
            total_assets_amount=assets,
            total_liabilities_amount=liabilities,
            account_count=account_count,
            connection_count=connection_count,
            new_insight_count=new_insight_count,
            currency=currency,
        )

    async def health(self, *, owner_user_id: int | None = None) -> FinanceHealth:
        """Liveness summary: account/connection counts + worst connection state.

        Backs ``GET /api/v1/finance/health``. ``status`` is ``"ok"`` unless a
        connection needs the user's attention (re-auth, consent expired, ...).
        """
        _, _, accounts = await self._account_rollup(owner_user_id=owner_user_id)
        connections, needs_action = await self._connection_rollup(
            owner_user_id=owner_user_id
        )
        return FinanceHealth(
            status="ok" if needs_action == 0 else "attention",
            accounts=accounts,
            connections=connections,
            connections_needing_action=needs_action,
        )

    # ------------------------------------------------------------------ #
    # Account edits (FIN-12)
    # ------------------------------------------------------------------ #
    async def update_account(
        self,
        account_id: int,
        *,
        owner_user_id: int | None = None,
        name: str | None = None,
        is_hidden: bool | None = None,
        is_closed: bool | None = None,
    ) -> FinanceAccount | None:
        """Rename / hide / close an account. Returns None if not found/owned."""
        account = await self.get_account(account_id, owner_user_id=owner_user_id)
        if account is None:
            return None
        if name is not None:
            account.name = name
        if is_hidden is not None:
            account.is_hidden = is_hidden
        if is_closed is not None:
            account.is_closed = is_closed
        account.updated_at = _utcnow()
        self.db.add(account)
        await self.db.flush()
        return account

    async def soft_delete_account(
        self, account_id: int, *, owner_user_id: int | None = None
    ) -> bool:
        """Soft-delete (set ``deleted_at``); never hard-delete. False if absent."""
        account = await self.get_account(account_id, owner_user_id=owner_user_id)
        if account is None:
            return False
        account.deleted_at = _utcnow()
        self.db.add(account)
        await self.db.flush()
        return True

    # ------------------------------------------------------------------ #
    # Valuations (dated value marks; current_balance tracks the latest)
    # ------------------------------------------------------------------ #
    async def upsert_valuation(
        self,
        *,
        account_id: int,
        as_of_date: date,
        value: int,
        owner_user_id: int | None = None,
        source: str = "manual",
        source_ref: str | None = None,
        note: str | None = None,
    ) -> FinanceValuation:
        """Insert or update the (account, date, source) valuation, then set the
        account's ``current_balance`` to the latest-dated valuation.

        Idempotent on ``uq_finance_valuation (account_id, as_of_date, source)``:
        a repeat write updates in place rather than duplicating.
        """
        existing = (
            await self.db.exec(
                select(FinanceValuation).where(
                    FinanceValuation.account_id == account_id,
                    FinanceValuation.as_of_date == as_of_date,
                    FinanceValuation.source == source,
                )
            )
        ).first()
        if existing is not None:
            existing.value = value
            existing.source_ref = source_ref
            existing.note = note
            existing.updated_at = _utcnow()
            valuation = existing
        else:
            valuation = FinanceValuation(
                owner_user_id=owner_user_id,
                account_id=account_id,
                as_of_date=as_of_date,
                value=value,
                source=source,
                source_ref=source_ref,
                note=note,
            )
        self.db.add(valuation)
        await self.db.flush()

        # current_balance for a manual asset = its latest-dated valuation.
        latest_value = (
            await self.db.exec(
                select(FinanceValuation.value)
                .where(FinanceValuation.account_id == account_id)
                .order_by(FinanceValuation.as_of_date.desc())
                .limit(1)
            )
        ).first()
        account = await self.get_account(account_id, owner_user_id=owner_user_id)
        if account is not None and latest_value is not None:
            account.current_balance = int(latest_value)
            account.balance_as_of = _utcnow()
            self.db.add(account)
            await self.db.flush()
        return valuation

    async def list_valuations(
        self, account_id: int, *, owner_user_id: int | None = None
    ) -> list[FinanceValuation]:
        """Valuation series for an account, oldest first. Empty if not owned."""
        account = await self.get_account(account_id, owner_user_id=owner_user_id)
        if account is None:
            return []
        query = (
            select(FinanceValuation)
            .where(FinanceValuation.account_id == account_id)
            .order_by(FinanceValuation.as_of_date)
        )
        return list((await self.db.exec(query)).all())

    # ------------------------------------------------------------------ #
    # Import batches (review / audit; the ingest lives in import_service)
    # ------------------------------------------------------------------ #
    async def get_import_batch(
        self, batch_id: int, *, owner_user_id: int | None = None
    ) -> FinanceImportBatch | None:
        # finance_import_batch.owner_user_id is NOT NULL; standalone uses 0.
        batch_owner = 0 if owner_user_id is None else owner_user_id
        return (
            await self.db.exec(
                select(FinanceImportBatch).where(
                    FinanceImportBatch.id == batch_id,
                    FinanceImportBatch.owner_user_id == batch_owner,
                )
            )
        ).first()

    async def list_import_batches(
        self,
        *,
        owner_user_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[FinanceImportBatch]:
        batch_owner = 0 if owner_user_id is None else owner_user_id
        query = (
            select(FinanceImportBatch)
            .where(FinanceImportBatch.owner_user_id == batch_owner)
            .order_by(FinanceImportBatch.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list((await self.db.exec(query)).all())

    async def list_import_batch_rows(
        self, batch_id: int
    ) -> list[FinanceImportBatchRow]:
        query = (
            select(FinanceImportBatchRow)
            .where(FinanceImportBatchRow.import_batch_id == batch_id)
            .order_by(FinanceImportBatchRow.row_number)
        )
        return list((await self.db.exec(query)).all())

    # ------------------------------------------------------------------ #
    # Investments (manual securities + holdings)
    # ------------------------------------------------------------------ #
    async def get_or_create_security(
        self,
        *,
        ticker: str,
        name: str | None = None,
        security_type: str | None = None,
        currency: str = _DEFAULT_CURRENCY,
    ) -> FinanceSecurity:
        """Fetch a security by ticker (case-insensitive), else create it.

        Securities are global/un-owned — the catalog is shared across accounts.
        """
        normalized = ticker.strip().upper()
        existing = (
            await self.db.exec(
                select(FinanceSecurity).where(FinanceSecurity.ticker == normalized)
            )
        ).first()
        if existing is not None:
            return existing
        await self.get_or_create_currency(currency)  # security.currency FK
        security = FinanceSecurity(
            ticker=normalized,
            name=name or normalized,
            security_type=security_type,
            currency=currency,
            provider="manual",
        )
        self.db.add(security)
        await self.db.flush()
        return security

    async def upsert_security_price(
        self,
        *,
        security_id: int,
        price_date: date,
        close_price: int,
        price_scale: int = 2,
        currency: str = _DEFAULT_CURRENCY,
        source: str = "manual",
    ) -> FinanceSecurityPrice:
        """Insert/update the (security, date, source) price point."""
        existing = (
            await self.db.exec(
                select(FinanceSecurityPrice).where(
                    FinanceSecurityPrice.security_id == security_id,
                    FinanceSecurityPrice.price_date == price_date,
                    FinanceSecurityPrice.source == source,
                )
            )
        ).first()
        if existing is not None:
            existing.close_price = close_price
            existing.price_scale = price_scale
            existing.currency = currency
            self.db.add(existing)
            await self.db.flush()
            return existing
        await self.get_or_create_currency(currency)  # price.currency FK
        price = FinanceSecurityPrice(
            security_id=security_id,
            price_date=price_date,
            close_price=close_price,
            price_scale=price_scale,
            currency=currency,
            source=source,
        )
        self.db.add(price)
        await self.db.flush()
        return price

    async def upsert_holding(
        self,
        *,
        owner_user_id: int | None,
        account_id: int,
        security_id: int,
        as_of_date: date,
        quantity_e8: int,
        price: int | None = None,
        price_scale: int = 2,
        cost_basis: int | None = None,
        average_cost: int | None = None,
        currency: str = _DEFAULT_CURRENCY,
        source: str = "manual",
        sync_account_balance: bool = True,
    ) -> FinanceHolding:
        """Insert/update the (account, security, as_of_date) position snapshot.

        ``owner_user_id`` is NOT NULL on holdings, so standalone (no-auth) rows
        use the ``0`` sentinel — the same convention as import batches.

        ``sync_account_balance`` sets the account's ``current_balance`` to its
        holdings value (right for manual entry). Pass ``False`` when a provider
        already supplies an authoritative account balance (e.g. Plaid).
        """
        holding_owner = 0 if owner_user_id is None else owner_user_id
        existing = (
            await self.db.exec(
                select(FinanceHolding).where(
                    FinanceHolding.account_id == account_id,
                    FinanceHolding.security_id == security_id,
                    FinanceHolding.as_of_date == as_of_date,
                )
            )
        ).first()
        if existing is not None:
            existing.quantity_e8 = quantity_e8
            existing.price = price
            existing.price_scale = price_scale
            existing.cost_basis = cost_basis
            existing.average_cost = average_cost
            existing.currency = currency
            existing.source = source
            existing.deleted_at = None
            self.db.add(existing)
            result = existing
        else:
            await self.get_or_create_currency(currency)  # holding.currency FK
            result = FinanceHolding(
                owner_user_id=holding_owner,
                account_id=account_id,
                security_id=security_id,
                as_of_date=as_of_date,
                quantity_e8=quantity_e8,
                price=price,
                price_scale=price_scale,
                cost_basis=cost_basis,
                average_cost=average_cost,
                currency=currency,
                source=source,
            )
            self.db.add(result)
        await self.db.flush()
        # Reflect the position in net worth: an investment account's balance is
        # its holdings' market value (unless the provider supplies its own).
        if sync_account_balance:
            await self._sync_account_balance_from_holdings(
                account_id, owner_user_id=owner_user_id
            )
        return result

    async def upsert_trade(
        self,
        *,
        owner_user_id: int | None,
        account_id: int,
        trade_type: str,
        trade_date: date,
        amount: int,
        security_id: int | None = None,
        subtype: str | None = None,
        quantity_e8: int | None = None,
        price: int | None = None,
        price_scale: int = 2,
        fees: int | None = None,
        currency: str = _DEFAULT_CURRENCY,
        source: str = Provider.MANUAL,
        external_id: str | None = None,
        external_id_source: str | None = None,
        name: str | None = None,
        connection_id: int | None = None,
        raw_payload: dict[str, Any] | None = None,
    ) -> FinanceTrade:
        """Insert/update one investment trade (buy/sell/dividend/...).

        Provider rows dedup on the external-id lane ``(account, source,
        external_id)``; manual/imported rows without an ``external_id`` always
        insert (the import-hash lane is the importers' job, not this path).
        ``owner_user_id`` is NOT NULL, so standalone (no-auth) rows use the
        ``0`` sentinel — same convention as holdings and import batches.
        """
        trade_owner = 0 if owner_user_id is None else owner_user_id
        existing: FinanceTrade | None = None
        if external_id is not None:
            existing = (
                await self.db.exec(
                    select(FinanceTrade).where(
                        FinanceTrade.account_id == account_id,
                        FinanceTrade.source == source,
                        FinanceTrade.external_id == external_id,
                        FinanceTrade.deleted_at.is_(None),
                    )
                )
            ).first()
        await self.get_or_create_currency(currency)  # trade.currency FK
        if existing is not None:
            existing.security_id = security_id
            existing.type = trade_type
            existing.subtype = subtype
            existing.quantity_e8 = quantity_e8
            existing.price = price
            existing.price_scale = price_scale
            existing.amount = amount
            existing.fees = fees
            existing.currency = currency
            existing.trade_date = trade_date
            existing.name = name
            existing.connection_id = connection_id
            existing.raw_payload = raw_payload
            existing.deleted_at = None
            self.db.add(existing)
            await self.db.flush()
            return existing
        trade = FinanceTrade(
            owner_user_id=trade_owner,
            account_id=account_id,
            security_id=security_id,
            connection_id=connection_id,
            source=source,
            external_id=external_id,
            external_id_source=external_id_source,
            type=trade_type,
            subtype=subtype,
            quantity_e8=quantity_e8,
            price=price,
            price_scale=price_scale,
            amount=amount,
            fees=fees,
            currency=currency,
            trade_date=trade_date,
            name=name,
            raw_payload=raw_payload,
        )
        self.db.add(trade)
        await self.db.flush()
        return trade

    async def list_trades(
        self,
        *,
        owner_user_id: int | None,
        account_id: int | None = None,
        limit: int = 100,
    ) -> list[FinanceTrade]:
        """Recent trades for an owner (optionally one account), newest first."""
        trade_owner = 0 if owner_user_id is None else owner_user_id
        query = select(FinanceTrade).where(
            FinanceTrade.owner_user_id == trade_owner,
            FinanceTrade.deleted_at.is_(None),
        )
        if account_id is not None:
            query = query.where(FinanceTrade.account_id == account_id)
        query = query.order_by(
            FinanceTrade.trade_date.desc(), FinanceTrade.id.desc()
        ).limit(limit)
        return list((await self.db.exec(query)).all())

    async def _sync_account_balance_from_holdings(
        self, account_id: int, *, owner_user_id: int | None = None
    ) -> None:
        """Set an account's ``current_balance`` to its current holdings value.

        Keeps net worth (which sums ``current_balance``) in step with positions.
        """
        account = await self.get_account(account_id, owner_user_id=owner_user_id)
        if account is None:
            return
        account.current_balance = await self.get_portfolio_value(
            owner_user_id=owner_user_id, account_id=account_id
        )
        account.balance_as_of = _utcnow()
        account.updated_at = _utcnow()
        self.db.add(account)
        await self.db.flush()

    async def list_current_holdings(
        self, *, owner_user_id: int | None = None, account_id: int | None = None
    ) -> list[tuple[FinanceHolding, FinanceSecurity | None, int]]:
        """Current positions: the latest-dated holding per (account, security)
        with a non-zero quantity, each paired with its security and market
        value in cents (holding price, falling back to the security close).
        """
        # Exclude holdings whose account is soft-deleted (e.g. after
        # disconnecting a provider connection) so they don't leak into portfolio
        # totals — the account, not just the holding row, must be live.
        filters = [
            FinanceHolding.deleted_at.is_(None),
            FinanceAccount.deleted_at.is_(None),
        ]
        if owner_user_id is not None:
            filters.append(FinanceHolding.owner_user_id == owner_user_id)
        if account_id is not None:
            filters.append(FinanceHolding.account_id == account_id)
        rows = list(
            (
                await self.db.exec(
                    select(FinanceHolding)
                    .join(
                        FinanceAccount,
                        FinanceAccount.id == FinanceHolding.account_id,
                    )
                    .where(*filters)
                    .order_by(FinanceHolding.as_of_date)
                )
            ).all()
        )
        # Ascending date order -> the last write per (account, security) is the
        # current snapshot.
        latest: dict[tuple[int, int], FinanceHolding] = {}
        for holding in rows:
            latest[(holding.account_id, holding.security_id)] = holding
        current = [h for h in latest.values() if h.quantity_e8 != 0]
        if not current:
            return []
        security_ids = {h.security_id for h in current}
        securities = {
            s.id: s
            for s in (
                await self.db.exec(
                    select(FinanceSecurity).where(
                        FinanceSecurity.id.in_(security_ids)
                    )
                )
            ).all()
        }
        result: list[tuple[FinanceHolding, FinanceSecurity | None, int]] = []
        for holding in current:
            security = securities.get(holding.security_id)
            price = holding.price
            if price is None and security is not None:
                price = security.close_price
            value = market_value_cents(
                holding.quantity_e8, price, holding.price_scale
            )
            result.append((holding, security, value))
        result.sort(key=lambda item: item[2], reverse=True)
        return result

    async def get_portfolio_value(
        self, *, owner_user_id: int | None = None, account_id: int | None = None
    ) -> int:
        """Total market value (cents) of the current holdings."""
        holdings = await self.list_current_holdings(
            owner_user_id=owner_user_id, account_id=account_id
        )
        return sum(value for _holding, _security, value in holdings)
