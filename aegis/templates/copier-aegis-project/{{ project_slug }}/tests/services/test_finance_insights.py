"""Tests for recurring-stream detection + "wasting money" insights (FIN-27).

Covers the ticket's acceptance scenarios: a Netflix-style subscription with a
price bump → stream detected + a single price_hike (idempotent, mutable); a
bank fee → fee insight; a 2x category month → overspend insight; too little
history → no insight, no crash; dismissal survives a re-run.
"""

from datetime import date

import pytest
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.services.finance.categorize import detect_recurring, generate_insights
from app.services.finance.finance_service import FinanceService
from app.services.finance.models import (
    FinanceCategory,
    FinanceInsight,
    FinanceRecurringStream,
)

_MONTH_STARTS = [date(2026, m, 15) for m in range(1, 8)]  # Jan..Jul 15th


async def _account(svc):
    return await svc.create_manual_account(
        name="Checking", account_type="checking", classification="asset",
        owner_user_id=1,
    )


async def _txn(svc, account_id, amount, day, name, category_id=None):
    return await svc.create_transaction(
        account_id=account_id,
        amount=amount,
        txn_date=day,
        owner_user_id=1,
        name=name,
        category_id=category_id,
    )


class TestRecurringDetection:
    @pytest.mark.asyncio
    async def test_netflix_subscription_detected_with_price_hike(
        self, async_db_session: AsyncSession
    ) -> None:
        svc = FinanceService(async_db_session)
        account = await _account(svc)
        for day in _MONTH_STARTS[:6]:
            await _txn(svc, account.id, -1549, day, "NETFLIX")
        await _txn(svc, account.id, -1799, _MONTH_STARTS[6], "NETFLIX")

        detected = await detect_recurring(async_db_session, owner_user_id=1)
        assert detected.detected == 1
        stream = (await async_db_session.exec(select(FinanceRecurringStream))).one()
        assert stream.frequency == "monthly"
        assert stream.is_subscription is True
        assert stream.average_amount == 1549
        assert stream.last_amount == 1799

        first = await generate_insights(
            async_db_session, owner_user_id=1, today=date(2026, 7, 20)
        )
        assert first.created == 1
        hike = (
            await async_db_session.exec(
                select(FinanceInsight).where(
                    FinanceInsight.insight_type == "price_hike"
                )
            )
        ).one()
        assert hike.detected_amount == 1799

        # Idempotent: the same price does not re-alert.
        again = await generate_insights(
            async_db_session, owner_user_id=1, today=date(2026, 7, 20)
        )
        assert again.created == 0

    @pytest.mark.asyncio
    async def test_muting_suppresses_price_hike(
        self, async_db_session: AsyncSession
    ) -> None:
        svc = FinanceService(async_db_session)
        account = await _account(svc)
        for day in _MONTH_STARTS[:6]:
            await _txn(svc, account.id, -1549, day, "NETFLIX")
        await _txn(svc, account.id, -1799, _MONTH_STARTS[6], "NETFLIX")
        await detect_recurring(async_db_session, owner_user_id=1)
        stream = (await async_db_session.exec(select(FinanceRecurringStream))).one()

        await svc.mute_recurring(stream.id, owner_user_id=1)
        result = await generate_insights(
            async_db_session, owner_user_id=1, today=date(2026, 7, 20)
        )
        assert result.created == 0  # muted -> no hike

    @pytest.mark.asyncio
    async def test_irregular_payee_not_a_stream(
        self, async_db_session: AsyncSession
    ) -> None:
        svc = FinanceService(async_db_session)
        account = await _account(svc)
        # Three charges, but wildly irregular gaps -> no stable cadence.
        for day, amt in [
            (date(2026, 1, 1), -500),
            (date(2026, 1, 3), -500),
            (date(2026, 5, 20), -500),
        ]:
            await _txn(svc, account.id, amt, day, "RANDOM SHOP")
        result = await detect_recurring(async_db_session, owner_user_id=1)
        assert result.detected == 0


class TestInsights:
    @pytest.mark.asyncio
    async def test_fee_insight(self, async_db_session: AsyncSession) -> None:
        svc = FinanceService(async_db_session)
        account = await _account(svc)
        await _txn(svc, account.id, -3500, date(2026, 7, 3), "MONTHLY SERVICE FEE")
        result = await generate_insights(
            async_db_session, owner_user_id=1, today=date(2026, 7, 20)
        )
        assert result.created == 1
        fee = (
            await async_db_session.exec(
                select(FinanceInsight).where(
                    FinanceInsight.insight_type == "fee_charged"
                )
            )
        ).one()
        assert fee.detected_amount == -3500

    @pytest.mark.asyncio
    async def test_overspend_insight(self, async_db_session: AsyncSession) -> None:
        svc = FinanceService(async_db_session)
        account = await _account(svc)
        category = FinanceCategory(
            owner_user_id=1, name="Dining", slug="dining", classification="expense"
        )
        async_db_session.add(category)
        await async_db_session.flush()
        # 3 prior full months at ~$100, current month at $250 (> 1.5x).
        for month in (4, 5, 6):
            await _txn(
                svc, account.id, -10000, date(2026, month, 10), "DINING",
                category_id=category.id,
            )
        await _txn(
            svc, account.id, -25000, date(2026, 7, 10), "DINING",
            category_id=category.id,
        )
        await generate_insights(
            async_db_session, owner_user_id=1, today=date(2026, 7, 20)
        )
        overspend = (
            await async_db_session.exec(
                select(FinanceInsight).where(
                    FinanceInsight.insight_type == "overspend_category"
                )
            )
        ).all()
        assert len(overspend) == 1
        assert overspend[0].detected_amount == 25000

    @pytest.mark.asyncio
    async def test_insufficient_history_no_overspend(
        self, async_db_session: AsyncSession
    ) -> None:
        svc = FinanceService(async_db_session)
        account = await _account(svc)
        category = FinanceCategory(
            owner_user_id=1, name="Dining", slug="dining", classification="expense"
        )
        async_db_session.add(category)
        await async_db_session.flush()
        # Only 1 prior month + current -> not enough history, no crash.
        await _txn(
            svc, account.id, -10000, date(2026, 6, 10), "DINING",
            category_id=category.id,
        )
        await _txn(
            svc, account.id, -25000, date(2026, 7, 10), "DINING",
            category_id=category.id,
        )
        await generate_insights(
            async_db_session, owner_user_id=1, today=date(2026, 7, 20)
        )
        overspend = (
            await async_db_session.exec(
                select(FinanceInsight).where(
                    FinanceInsight.insight_type == "overspend_category"
                )
            )
        ).all()
        assert overspend == []

    @pytest.mark.asyncio
    async def test_dismiss_survives_rerun(
        self, async_db_session: AsyncSession
    ) -> None:
        svc = FinanceService(async_db_session)
        account = await _account(svc)
        await _txn(svc, account.id, -3500, date(2026, 7, 3), "SERVICE FEE")
        await generate_insights(
            async_db_session, owner_user_id=1, today=date(2026, 7, 20)
        )
        fee = (
            await async_db_session.exec(
                select(FinanceInsight).where(
                    FinanceInsight.insight_type == "fee_charged"
                )
            )
        ).one()
        dismissed = await svc.dismiss_insight(fee.id, owner_user_id=1)
        assert dismissed is not None and dismissed.status == "dismissed"

        # Re-running must not resurrect the dismissed insight.
        await generate_insights(
            async_db_session, owner_user_id=1, today=date(2026, 7, 20)
        )
        rows = (
            await async_db_session.exec(
                select(FinanceInsight).where(
                    FinanceInsight.insight_type == "fee_charged"
                )
            )
        ).all()
        assert len(rows) == 1
        assert rows[0].status == "dismissed"
