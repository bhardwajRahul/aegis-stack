"""Tests for the OFX/QFX importer + import pipeline (FIN-14).

Plain ``.py`` (finance-only stacks). Uses the hand-crafted
``finance/fixtures/sample_chase.qfx`` (6 transactions covering debit, credit,
a check, a same-day/same-amount pair with distinct FITIDs, and a messy payee).
"""

from pathlib import Path

import pytest
from app.services.finance import import_service
from app.services.finance.finance_service import FinanceService
from app.services.finance.importers.base import normalize_payee
from app.services.finance.importers.ofx import parse_ofx
from app.services.finance.models import FinanceAccount
from sqlmodel.ext.asyncio.session import AsyncSession

_FIXTURE = Path(__file__).parent / "finance" / "fixtures" / "sample_chase.qfx"


def _qfx() -> bytes:
    return _FIXTURE.read_bytes()


async def _account(session: AsyncSession) -> FinanceAccount:
    return await FinanceService(session).create_manual_account(
        owner_user_id=1,
        name="Chase Checking",
        account_type="checking",
        classification="asset",
    )


class TestNormalizePayee:
    def test_normalizes(self) -> None:
        # NFKD fold: accented and plain spellings collapse to one key.
        assert normalize_payee("  Café   Münchén!! ") == "CAFE MUNCHEN"
        assert normalize_payee("Cafe Munchen") == "CAFE MUNCHEN"
        assert normalize_payee("WHOLE FOODS MKT #123") == "WHOLE FOODS MKT 123"
        assert normalize_payee(None) == ""


class TestParseOfx:
    def test_parses_six_with_correct_signs_and_cents(self) -> None:
        parsed = parse_ofx(_qfx(), source="qfx")
        assert len(parsed) == 6
        by_id = {p.external_id: p for p in parsed}
        assert by_id["F001"].amount == -14230  # debit -> negative
        assert by_id["F002"].amount == 320000  # credit -> positive
        assert by_id["F003"].amount == -8999
        assert by_id["F003"].check_number == "1042"
        assert by_id["F004"].amount == -650
        assert all(p.external_id_source == "fitid" for p in parsed)
        assert by_id["F001"].account_key == "1234567890"


class TestImportPipeline:
    @pytest.mark.asyncio
    async def test_import_inserts_with_correct_signs(
        self, async_db_session: AsyncSession
    ) -> None:
        account = await _account(async_db_session)
        result = await import_service.ingest_transactions(
            async_db_session,
            owner_user_id=1,
            source_type="qfx",
            file_name="sample_chase.qfx",
            file_bytes=_qfx(),
            parsed=parse_ofx(_qfx(), source="qfx"),
            default_account_id=account.id,
        )
        assert result.rows_total == 6
        assert result.rows_inserted == 6
        assert result.rows_duplicate == 0

        txns, total = await FinanceService(async_db_session).list_transactions(
            owner_user_id=1, account_id=account.id
        )
        assert total == 6
        amounts = {t.external_id: t.amount for t in txns}
        assert amounts["F001"] == -14230
        assert amounts["F002"] == 320000

    @pytest.mark.asyncio
    async def test_same_file_reimport_short_circuits(
        self, async_db_session: AsyncSession
    ) -> None:
        account = await _account(async_db_session)
        data = _qfx()
        first = await import_service.ingest_transactions(
            async_db_session,
            owner_user_id=1,
            source_type="qfx",
            file_name="c.qfx",
            file_bytes=data,
            parsed=parse_ofx(data, source="qfx"),
            default_account_id=account.id,
        )
        assert first.rows_inserted == 6

        second = await import_service.ingest_transactions(
            async_db_session,
            owner_user_id=1,
            source_type="qfx",
            file_name="c.qfx",
            file_bytes=data,
            parsed=parse_ofx(data, source="qfx"),
            default_account_id=account.id,
        )
        assert second.rows_inserted == 0
        assert second.rows_duplicate == 6
        assert second.batch_id == first.batch_id  # short-circuited to prior

        _, total = await FinanceService(async_db_session).list_transactions(
            owner_user_id=1, account_id=account.id
        )
        assert total == 6  # unchanged

    @pytest.mark.asyncio
    async def test_overlapping_file_inserts_only_new_row(
        self, async_db_session: AsyncSession
    ) -> None:
        account = await _account(async_db_session)
        data = _qfx()
        await import_service.ingest_transactions(
            async_db_session,
            owner_user_id=1,
            source_type="qfx",
            file_name="c.qfx",
            file_bytes=data,
            parsed=parse_ofx(data, source="qfx"),
            default_account_id=account.id,
        )
        # Same FITIDs F001-F005, but F006 becomes a brand-new F007 (diff bytes).
        overlapping = data.replace(b"<FITID>F006", b"<FITID>F007")
        result = await import_service.ingest_transactions(
            async_db_session,
            owner_user_id=1,
            source_type="qfx",
            file_name="c2.qfx",
            file_bytes=overlapping,
            parsed=parse_ofx(overlapping, source="qfx"),
            default_account_id=account.id,
        )
        assert result.rows_inserted == 1
        assert result.rows_duplicate == 5

        _, total = await FinanceService(async_db_session).list_transactions(
            owner_user_id=1, account_id=account.id
        )
        assert total == 7  # 6 original + 1 new
