"""Tests for the finance service layer (manual accounts, transactions, net worth).

Plain ``.py`` (the ``app.services.finance`` import only resolves in
finance-selected stacks). Runs against the in-memory SQLite async session from
conftest (FK enforcement ON), exercising the same ``FinanceService`` the API,
CLI, and dashboard card use.
"""

from datetime import date

import pytest
from app.services.finance.finance_service import FinanceService
from sqlmodel.ext.asyncio.session import AsyncSession


class TestFinanceAccounts:
    @pytest.mark.asyncio
    async def test_create_manual_account_and_net_worth(
        self, async_db_session: AsyncSession
    ) -> None:
        svc = FinanceService(async_db_session)
        checking = await svc.create_manual_account(
            owner_user_id=1,
            name="Chase Checking",
            account_type="checking",
            classification="asset",
            current_balance=842_650,
        )
        await svc.create_manual_account(
            owner_user_id=1,
            name="Chase Sapphire",
            account_type="credit_card",
            classification="liability",
            current_balance=310_401,
        )
        assert checking.is_manual is True
        assert checking.provider == "manual"

        net_worth = await svc.get_net_worth(owner_user_id=1)
        assert net_worth.total_assets_amount == 842_650
        assert net_worth.total_liabilities_amount == 310_401
        assert net_worth.net_worth_amount == 532_249

    @pytest.mark.asyncio
    async def test_list_accounts_excludes_hidden(
        self, async_db_session: AsyncSession
    ) -> None:
        svc = FinanceService(async_db_session)
        await svc.create_manual_account(
            owner_user_id=1, name="A", account_type="checking", classification="asset"
        )
        hidden = await svc.create_manual_account(
            owner_user_id=1, name="B", account_type="savings", classification="asset"
        )
        hidden.is_hidden = True
        async_db_session.add(hidden)
        await async_db_session.flush()

        accounts, total = await svc.list_accounts(owner_user_id=1)
        assert total == 1
        assert [a.name for a in accounts] == ["A"]

        accounts, total = await svc.list_accounts(
            owner_user_id=1, include_hidden=True
        )
        assert total == 2

    @pytest.mark.asyncio
    async def test_net_worth_is_owner_scoped(
        self, async_db_session: AsyncSession
    ) -> None:
        svc = FinanceService(async_db_session)
        await svc.create_manual_account(
            owner_user_id=1,
            name="Mine",
            account_type="checking",
            classification="asset",
            current_balance=100,
        )
        await svc.create_manual_account(
            owner_user_id=2,
            name="Theirs",
            account_type="checking",
            classification="asset",
            current_balance=999,
        )
        assert (await svc.get_net_worth(owner_user_id=1)).total_assets_amount == 100
        assert (await svc.get_net_worth(owner_user_id=2)).total_assets_amount == 999

    @pytest.mark.asyncio
    async def test_update_account_balance(
        self, async_db_session: AsyncSession
    ) -> None:
        svc = FinanceService(async_db_session)
        acct = await svc.create_manual_account(
            owner_user_id=1,
            name="House",
            account_type="property",
            classification="asset",
            current_balance=500_000_00,
        )
        updated = await svc.update_account_balance(
            acct.id, current_balance=525_000_00, owner_user_id=1
        )
        assert updated is not None
        assert updated.current_balance == 525_000_00
        assert updated.balance_as_of is not None

    @pytest.mark.asyncio
    async def test_update_missing_account_returns_none(
        self, async_db_session: AsyncSession
    ) -> None:
        svc = FinanceService(async_db_session)
        assert (
            await svc.update_account_balance(999_999, current_balance=1) is None
        )


class TestFinanceTransactions:
    @pytest.mark.asyncio
    async def test_create_and_list_newest_first(
        self, async_db_session: AsyncSession
    ) -> None:
        svc = FinanceService(async_db_session)
        acct = await svc.create_manual_account(
            owner_user_id=1,
            name="Checking",
            account_type="checking",
            classification="asset",
        )
        await svc.create_transaction(
            owner_user_id=1,
            account_id=acct.id,
            amount=-4_599,
            txn_date=date(2026, 7, 1),
            name="Coffee",
        )
        await svc.create_transaction(
            owner_user_id=1,
            account_id=acct.id,
            amount=320_000,
            txn_date=date(2026, 7, 3),
            name="Payroll",
        )
        txns, total = await svc.list_transactions(owner_user_id=1)
        assert total == 2
        assert txns[0].name == "Payroll"  # newest first

    @pytest.mark.asyncio
    async def test_two_lane_dedup(self, async_db_session: AsyncSession) -> None:
        svc = FinanceService(async_db_session)
        acct = await svc.create_manual_account(
            owner_user_id=1,
            name="Checking",
            account_type="checking",
            classification="asset",
        )
        # LANE 1 — provider external_id.
        await svc.create_transaction(
            owner_user_id=1,
            account_id=acct.id,
            amount=-100,
            txn_date=date(2026, 7, 1),
            source="plaid",
            external_id="e1",
        )
        assert (
            await svc.transaction_exists(
                account_id=acct.id, source="plaid", external_id="e1"
            )
            is True
        )
        assert (
            await svc.transaction_exists(
                account_id=acct.id, source="plaid", external_id="e2"
            )
            is False
        )
        # LANE 2 — id-less file import hash.
        await svc.create_transaction(
            owner_user_id=1,
            account_id=acct.id,
            amount=-50,
            txn_date=date(2026, 7, 1),
            source="csv",
            import_hash="h1",
        )
        assert (
            await svc.transaction_exists(
                account_id=acct.id, source="csv", import_hash="h1"
            )
            is True
        )
        assert (
            await svc.transaction_exists(
                account_id=acct.id, source="csv", import_hash="h2"
            )
            is False
        )


class TestFinanceStatusSummary:
    @pytest.mark.asyncio
    async def test_summary_counts_and_net_worth(
        self, async_db_session: AsyncSession
    ) -> None:
        svc = FinanceService(async_db_session)
        await svc.create_manual_account(
            owner_user_id=1,
            name="Checking",
            account_type="checking",
            classification="asset",
            current_balance=500_000,
        )
        await svc.create_manual_account(
            owner_user_id=1,
            name="Card",
            account_type="credit_card",
            classification="liability",
            current_balance=50_000,
        )
        summary = await svc.get_status_summary(owner_user_id=1)
        assert summary.net_worth_amount == 450_000
        assert summary.account_count == 2
        assert summary.connection_count == 0
        assert summary.currency == "usd"


class TestFinanceHealth:
    @pytest.mark.asyncio
    async def test_health_empty_then_with_account(
        self, async_db_session: AsyncSession
    ) -> None:
        svc = FinanceService(async_db_session)
        health = await svc.health(owner_user_id=1)
        assert health.status == "ok"
        assert health.accounts == 0
        assert health.connections == 0
        assert health.connections_needing_action == 0

        await svc.create_manual_account(
            owner_user_id=1,
            name="Checking",
            account_type="checking",
            classification="asset",
        )
        health = await svc.health(owner_user_id=1)
        assert health.accounts == 1


class TestFinanceAccountEdits:
    @pytest.mark.asyncio
    async def test_update_rename_hide(
        self, async_db_session: AsyncSession
    ) -> None:
        svc = FinanceService(async_db_session)
        acct = await svc.create_manual_account(
            owner_user_id=1,
            name="Old",
            account_type="checking",
            classification="asset",
        )
        updated = await svc.update_account(
            acct.id, owner_user_id=1, name="New", is_hidden=True
        )
        assert updated is not None
        assert updated.name == "New"
        assert updated.is_hidden is True

    @pytest.mark.asyncio
    async def test_soft_delete_hides_but_keeps_row(
        self, async_db_session: AsyncSession
    ) -> None:
        svc = FinanceService(async_db_session)
        acct = await svc.create_manual_account(
            owner_user_id=1,
            name="Temp",
            account_type="checking",
            classification="asset",
        )
        assert await svc.soft_delete_account(acct.id, owner_user_id=1) is True
        _, total = await svc.list_accounts(owner_user_id=1)
        assert total == 0
        assert await svc.get_account(acct.id, owner_user_id=1) is None
        # row survives (deleted_at set), just excluded from reads
        assert acct.deleted_at is not None

    @pytest.mark.asyncio
    async def test_missing_account_edits_are_noops(
        self, async_db_session: AsyncSession
    ) -> None:
        svc = FinanceService(async_db_session)
        assert await svc.update_account(999_999, name="x") is None
        assert await svc.soft_delete_account(999_999) is False

    @pytest.mark.asyncio
    async def test_owner_scoping_blocks_other_user(
        self, async_db_session: AsyncSession
    ) -> None:
        svc = FinanceService(async_db_session)
        acct = await svc.create_manual_account(
            owner_user_id=1,
            name="Mine",
            account_type="checking",
            classification="asset",
        )
        # user 2 sees nothing and can't edit — surfaces as 404 in the router.
        assert await svc.get_account(acct.id, owner_user_id=2) is None
        assert (
            await svc.update_account(acct.id, owner_user_id=2, name="hacked") is None
        )


class TestFinanceValuations:
    @pytest.mark.asyncio
    async def test_upsert_tracks_latest_as_current_balance(
        self, async_db_session: AsyncSession
    ) -> None:
        svc = FinanceService(async_db_session)
        acct = await svc.create_manual_account(
            owner_user_id=1,
            name="My House",
            account_type="property",
            classification="asset",
        )
        await svc.upsert_valuation(
            account_id=acct.id,
            owner_user_id=1,
            as_of_date=date(2026, 7, 1),
            value=50_000_000,
        )
        await svc.upsert_valuation(
            account_id=acct.id,
            owner_user_id=1,
            as_of_date=date(2026, 7, 4),
            value=50_500_000,
        )
        series = await svc.list_valuations(acct.id, owner_user_id=1)
        assert len(series) == 2
        refreshed = await svc.get_account(acct.id, owner_user_id=1)
        assert refreshed is not None
        assert refreshed.current_balance == 50_500_000  # latest-dated value

    @pytest.mark.asyncio
    async def test_upsert_same_date_source_is_idempotent(
        self, async_db_session: AsyncSession
    ) -> None:
        svc = FinanceService(async_db_session)
        acct = await svc.create_manual_account(
            owner_user_id=1,
            name="House",
            account_type="property",
            classification="asset",
        )
        await svc.upsert_valuation(
            account_id=acct.id,
            owner_user_id=1,
            as_of_date=date(2026, 7, 1),
            value=50_000_000,
        )
        await svc.upsert_valuation(
            account_id=acct.id,
            owner_user_id=1,
            as_of_date=date(2026, 7, 1),
            value=51_000_000,
        )
        series = await svc.list_valuations(acct.id, owner_user_id=1)
        assert len(series) == 1  # updated in place, not duplicated
        assert series[0].value == 51_000_000


class TestFinanceNetWorth:
    @staticmethod
    def _days_ago(n: int) -> date:
        from datetime import UTC, datetime, timedelta

        return datetime.now(UTC).date() - timedelta(days=n)

    @pytest.mark.asyncio
    async def test_recompute_series_liability_sign(
        self, async_db_session: AsyncSession
    ) -> None:
        from app.services.finance import networth_service

        svc = FinanceService(async_db_session)
        house = await svc.create_manual_account(
            owner_user_id=1,
            name="My House",
            account_type="property",
            classification="asset",
        )
        await svc.upsert_valuation(
            account_id=house.id,
            owner_user_id=1,
            as_of_date=self._days_ago(5),
            value=50_000_000,
        )
        await svc.upsert_valuation(
            account_id=house.id,
            owner_user_id=1,
            as_of_date=self._days_ago(2),
            value=50_500_000,
        )
        await svc.create_manual_account(
            owner_user_id=1,
            name="Mortgage",
            account_type="loan",
            classification="liability",
            current_balance=30_000_000,
        )

        await networth_service.recompute_snapshots(
            async_db_session, owner_user_id=1
        )
        series = await networth_service.get_net_worth_series(
            async_db_session, owner_user_id=1, days=90
        )
        assert series, "expected net-worth snapshots"
        latest = series[-1]  # today
        assert latest.total_assets_amount == 50_500_000
        assert latest.total_liabilities_amount == 30_000_000
        assert latest.net_worth_amount == 20_500_000  # 50.5M - 30M

    @pytest.mark.asyncio
    async def test_recompute_is_idempotent(
        self, async_db_session: AsyncSession
    ) -> None:
        from sqlmodel import func, select

        from app.services.finance import networth_service
        from app.services.finance.models import FinanceNetWorthSnapshot

        svc = FinanceService(async_db_session)
        await svc.create_manual_account(
            owner_user_id=1,
            name="Cash",
            account_type="cash",
            classification="asset",
            current_balance=100_000,
        )
        await networth_service.recompute_snapshots(
            async_db_session, owner_user_id=1
        )
        count_q = select(func.count()).select_from(FinanceNetWorthSnapshot)
        first = (await async_db_session.exec(count_q)).one()
        await networth_service.recompute_snapshots(
            async_db_session, owner_user_id=1
        )
        second = (await async_db_session.exec(count_q)).one()
        assert first == second and first > 0  # upsert, no duplicate rows

    @pytest.mark.asyncio
    async def test_gap_days_carry_forward_estimated(
        self, async_db_session: AsyncSession
    ) -> None:
        from sqlmodel import select

        from app.services.finance import networth_service
        from app.services.finance.models import FinanceBalanceSnapshot

        svc = FinanceService(async_db_session)
        house = await svc.create_manual_account(
            owner_user_id=1,
            name="House",
            account_type="property",
            classification="asset",
        )
        valued_on = self._days_ago(3)
        await svc.upsert_valuation(
            account_id=house.id,
            owner_user_id=1,
            as_of_date=valued_on,
            value=50_000_000,
        )
        await networth_service.recompute_snapshots(
            async_db_session, owner_user_id=1
        )
        snaps = (
            await async_db_session.exec(
                select(FinanceBalanceSnapshot).where(
                    FinanceBalanceSnapshot.account_id == house.id
                )
            )
        ).all()
        exact = [s for s in snaps if s.balance_date == valued_on]
        carried = [s for s in snaps if s.balance_date > valued_on]
        assert exact and exact[0].is_estimated is False
        assert carried  # days after the valuation
        assert all(
            s.is_estimated and s.source == "carried_forward" for s in carried
        )
        assert all(s.balance == 50_000_000 for s in snaps)  # value carried
