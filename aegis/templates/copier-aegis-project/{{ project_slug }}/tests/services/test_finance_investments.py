"""Tests for the manual investments layer (securities, holdings, portfolio value).

Plain ``.py`` (the ``app.services.finance`` import only resolves in
finance-selected stacks). Runs against the in-memory SQLite async session from
conftest (FK enforcement ON), exercising the same ``FinanceService`` the API,
CLI, and dashboard use.
"""

from datetime import date

import pytest
from app.services.finance.finance_service import FinanceService, market_value_cents
from sqlmodel.ext.asyncio.session import AsyncSession

_E8 = 10**8  # quantity scale: shares stored as shares * 1e8


class TestMarketValue:
    def test_basic(self) -> None:
        # 10 shares @ $150.00 (price=15000, scale=2) -> $1,500.00 -> 150000 cents
        assert market_value_cents(10 * _E8, 15000, 2) == 150_000

    def test_fractional_shares(self) -> None:
        # 2.5 shares @ $10.00 -> $25.00
        assert market_value_cents(int(2.5 * _E8), 1000, 2) == 2_500

    def test_no_price_is_zero(self) -> None:
        assert market_value_cents(10 * _E8, None, 2) == 0

    def test_large_position_stays_exact(self) -> None:
        # 1,000,000 shares @ $1,234.5678 (scale 4). Float division of the
        # ~1e22 numerator would lose integer precision; integer math is exact.
        # value = 1_000_000 * 1234.5678 * 100 cents = 123_456_780_000
        assert (
            market_value_cents(1_000_000 * _E8, 12_345_678, 4) == 123_456_780_000
        )

    def test_negative_quantity_rounds_symmetrically(self) -> None:
        # Short position: 3 shares @ $10.005 (price=10005, scale=3) = $30.015.
        # Rounds half away from zero to -$30.02 -> -3002 cents.
        assert market_value_cents(-3 * _E8, 10_005, 3) == -3_002


class TestSecurities:
    @pytest.mark.asyncio
    async def test_get_or_create_is_idempotent_case_insensitive(
        self, async_db_session: AsyncSession
    ) -> None:
        svc = FinanceService(async_db_session)
        first = await svc.get_or_create_security(ticker="aapl", name="Apple Inc.")
        again = await svc.get_or_create_security(ticker="AAPL")
        assert again.id == first.id  # same catalog row, not a duplicate
        assert first.ticker == "AAPL"  # normalized to upper


class TestHoldings:
    @pytest.mark.asyncio
    async def test_upsert_creates_and_syncs_account_balance(
        self, async_db_session: AsyncSession
    ) -> None:
        svc = FinanceService(async_db_session)
        account = await svc.create_manual_account(
            owner_user_id=1,
            name="Brokerage",
            account_type="brokerage",
            classification="asset",
        )
        aapl = await svc.get_or_create_security(ticker="AAPL", name="Apple Inc.")
        await svc.upsert_holding(
            owner_user_id=1,
            account_id=account.id,
            security_id=aapl.id,
            as_of_date=date(2026, 7, 1),
            quantity_e8=10 * _E8,
            price=15000,
            price_scale=2,
            cost_basis=120_000,
        )
        # Manual holding -> account balance follows its holdings value ($1,500.00).
        refreshed = await svc.get_account(account.id, owner_user_id=1)
        assert refreshed is not None
        assert refreshed.current_balance == 150_000

    @pytest.mark.asyncio
    async def test_upsert_is_idempotent_on_date(
        self, async_db_session: AsyncSession
    ) -> None:
        svc = FinanceService(async_db_session)
        account = await svc.create_manual_account(
            owner_user_id=1,
            name="B",
            account_type="brokerage",
            classification="asset",
        )
        aapl = await svc.get_or_create_security(ticker="AAPL")
        for qty in (10, 12):  # same (account, security, date) -> update in place
            await svc.upsert_holding(
                owner_user_id=1,
                account_id=account.id,
                security_id=aapl.id,
                as_of_date=date(2026, 7, 1),
                quantity_e8=qty * _E8,
                price=15000,
            )
        holdings = await svc.list_current_holdings(
            owner_user_id=1, account_id=account.id
        )
        assert len(holdings) == 1  # updated, not duplicated
        holding, _security, value = holdings[0]
        assert holding.quantity_e8 == 12 * _E8
        assert value == 180_000  # 12 shares @ $150.00

    @pytest.mark.asyncio
    async def test_list_current_takes_latest_dated_snapshot(
        self, async_db_session: AsyncSession
    ) -> None:
        svc = FinanceService(async_db_session)
        account = await svc.create_manual_account(
            owner_user_id=1,
            name="B",
            account_type="brokerage",
            classification="asset",
        )
        aapl = await svc.get_or_create_security(ticker="AAPL")
        await svc.upsert_holding(
            owner_user_id=1,
            account_id=account.id,
            security_id=aapl.id,
            as_of_date=date(2026, 6, 1),
            quantity_e8=10 * _E8,
            price=14000,
        )
        await svc.upsert_holding(
            owner_user_id=1,
            account_id=account.id,
            security_id=aapl.id,
            as_of_date=date(2026, 7, 1),
            quantity_e8=15 * _E8,
            price=15000,
        )
        holdings = await svc.list_current_holdings(owner_user_id=1)
        assert len(holdings) == 1
        holding, _security, value = holdings[0]
        assert holding.quantity_e8 == 15 * _E8  # latest date wins
        assert value == 225_000  # 15 shares @ $150.00

    @pytest.mark.asyncio
    async def test_excludes_holdings_of_soft_deleted_account(
        self, async_db_session: AsyncSession
    ) -> None:
        # Disconnecting a provider soft-deletes the account but leaves its
        # holding rows; those must not leak into portfolio listings/totals.
        svc = FinanceService(async_db_session)
        account = await svc.create_manual_account(
            owner_user_id=1,
            name="Brokerage",
            account_type="brokerage",
            classification="asset",
        )
        aapl = await svc.get_or_create_security(ticker="AAPL")
        await svc.upsert_holding(
            owner_user_id=1,
            account_id=account.id,
            security_id=aapl.id,
            as_of_date=date(2026, 7, 1),
            quantity_e8=10 * _E8,
            price=15000,
        )
        assert len(await svc.list_current_holdings(owner_user_id=1)) == 1
        assert await svc.get_portfolio_value(owner_user_id=1) == 150_000

        await svc.soft_delete_account(account.id, owner_user_id=1)

        assert await svc.list_current_holdings(owner_user_id=1) == []
        assert await svc.get_portfolio_value(owner_user_id=1) == 0
