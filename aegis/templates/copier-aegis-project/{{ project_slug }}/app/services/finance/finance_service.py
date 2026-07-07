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

from datetime import UTC, date, datetime

from sqlalchemy import func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.services.finance.constants import Provider
from app.services.finance.models import (
    FinanceAccount,
    FinanceConnection,
    FinanceCurrency,
    FinanceImportBatch,
    FinanceImportBatchRow,
    FinanceInstitution,
    FinanceTransaction,
    FinanceValuation,
)
from app.services.finance.schemas import (
    FinanceHealth,
    FinanceStatusSummary,
    NetWorthResponse,
)

_DEFAULT_CURRENCY = "usd"


def _utcnow() -> datetime:
    """Naive-UTC timestamp (matches the models' convention)."""
    return datetime.now(UTC).replace(tzinfo=None)


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
        import_batch_id: int | None = None,
        raw_amount: int | None = None,
        raw_sign_convention: str | None = None,
        original_description: str | None = None,
        memo: str | None = None,
        check_number: str | None = None,
        currency: str = _DEFAULT_CURRENCY,
        category_id: int | None = None,
    ) -> FinanceTransaction:
        txn = FinanceTransaction(
            owner_user_id=owner_user_id,
            account_id=account_id,
            amount=amount,
            date_=txn_date,
            name=name,
            source=source,
            external_id=external_id,
            external_id_source=external_id_source,
            import_hash=import_hash,
            import_batch_id=import_batch_id,
            raw_amount=raw_amount,
            raw_sign_convention=raw_sign_convention,
            original_description=original_description,
            memo=memo,
            check_number=check_number,
            currency=currency,
            category_id=category_id,
        )
        self.db.add(txn)
        await self.db.flush()
        return txn

    async def list_transactions(
        self,
        *,
        owner_user_id: int | None = None,
        account_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[FinanceTransaction], int]:
        query = select(FinanceTransaction).where(
            FinanceTransaction.deleted_at.is_(None)
        )
        count_query = (
            select(func.count())
            .select_from(FinanceTransaction)
            .where(FinanceTransaction.deleted_at.is_(None))
        )
        if owner_user_id is not None:
            query = query.where(FinanceTransaction.owner_user_id == owner_user_id)
            count_query = count_query.where(
                FinanceTransaction.owner_user_id == owner_user_id
            )
        if account_id is not None:
            query = query.where(FinanceTransaction.account_id == account_id)
            count_query = count_query.where(
                FinanceTransaction.account_id == account_id
            )
        total = (await self.db.exec(count_query)).one()
        query = (
            query.order_by(
                FinanceTransaction.date_.desc(), FinanceTransaction.id.desc()
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list((await self.db.exec(query)).all()), total

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
    async def _asset_liability_totals(
        self, *, owner_user_id: int | None = None
    ) -> tuple[int, int]:
        """Live (assets, liabilities) totals summed across visible accounts."""
        query = (
            select(
                FinanceAccount.classification,
                func.coalesce(func.sum(FinanceAccount.current_balance), 0),
            )
            .where(FinanceAccount.deleted_at.is_(None), ~FinanceAccount.is_hidden)
            .group_by(FinanceAccount.classification)
        )
        if owner_user_id is not None:
            query = query.where(FinanceAccount.owner_user_id == owner_user_id)
        assets = liabilities = 0
        for classification, total in (await self.db.exec(query)).all():
            if classification == "asset":
                assets = int(total or 0)
            elif classification == "liability":
                liabilities = int(total or 0)
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
        assets, liabilities = await self._asset_liability_totals(
            owner_user_id=owner_user_id
        )
        account_q = (
            select(func.count())
            .select_from(FinanceAccount)
            .where(FinanceAccount.deleted_at.is_(None))
        )
        connection_q = (
            select(func.count())
            .select_from(FinanceConnection)
            .where(FinanceConnection.deleted_at.is_(None))
        )
        if owner_user_id is not None:
            account_q = account_q.where(FinanceAccount.owner_user_id == owner_user_id)
            connection_q = connection_q.where(
                FinanceConnection.owner_user_id == owner_user_id
            )
        account_count = int((await self.db.exec(account_q)).one())
        connection_count = int((await self.db.exec(connection_q)).one())
        return FinanceStatusSummary(
            net_worth_amount=assets - liabilities,
            total_assets_amount=assets,
            total_liabilities_amount=liabilities,
            account_count=account_count,
            connection_count=connection_count,
            currency=currency,
        )

    async def health(self, *, owner_user_id: int | None = None) -> FinanceHealth:
        """Liveness summary: account/connection counts + worst connection state.

        Backs ``GET /api/v1/finance/health``. ``status`` is ``"ok"`` unless a
        connection needs the user's attention (re-auth, consent expired, ...).
        """
        account_q = (
            select(func.count())
            .select_from(FinanceAccount)
            .where(FinanceAccount.deleted_at.is_(None))
        )
        connection_q = (
            select(func.count())
            .select_from(FinanceConnection)
            .where(FinanceConnection.deleted_at.is_(None))
        )
        needs_action_q = (
            select(func.count())
            .select_from(FinanceConnection)
            .where(
                FinanceConnection.deleted_at.is_(None),
                FinanceConnection.needs_user_action,
            )
        )
        if owner_user_id is not None:
            account_q = account_q.where(FinanceAccount.owner_user_id == owner_user_id)
            connection_q = connection_q.where(
                FinanceConnection.owner_user_id == owner_user_id
            )
            needs_action_q = needs_action_q.where(
                FinanceConnection.owner_user_id == owner_user_id
            )
        accounts = int((await self.db.exec(account_q)).one())
        connections = int((await self.db.exec(connection_q)).one())
        needs_action = int((await self.db.exec(needs_action_q)).one())
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

    async def list_import_batch_rows(
        self, batch_id: int
    ) -> list[FinanceImportBatchRow]:
        query = (
            select(FinanceImportBatchRow)
            .where(FinanceImportBatchRow.import_batch_id == batch_id)
            .order_by(FinanceImportBatchRow.row_number)
        )
        return list((await self.db.exec(query)).all())
