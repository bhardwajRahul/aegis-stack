"""Tests for finance API endpoints.

Plain ``.py`` (only generated in finance-selected stacks). Exercises the
mounted router end to end via the async test client, mirroring
``test_blog_endpoints.py``.
"""

import pytest
from app.services.finance.finance_service import FinanceService
from fastapi.testclient import TestClient
from sqlmodel.ext.asyncio.session import AsyncSession


@pytest.mark.asyncio
async def test_finance_health_returns_200_when_empty(
    async_client_with_db: TestClient,
) -> None:
    """FIN-11 acceptance: GET /api/v1/finance/health -> 200 with zero counts."""
    response = async_client_with_db.get("/api/v1/finance/health")
    assert response.status_code == 200
    body = response.json()
    assert body["accounts"] == 0
    assert body["connections"] == 0
    assert body["status"] == "ok"


@pytest.mark.asyncio
async def test_finance_health_reflects_accounts(
    async_client_with_db: TestClient, async_db_session: AsyncSession
) -> None:
    service = FinanceService(async_db_session)
    await service.create_manual_account(
        owner_user_id=1,
        name="Chase Checking",
        account_type="checking",
        classification="asset",
    )
    await async_db_session.commit()

    response = async_client_with_db.get("/api/v1/finance/health")
    assert response.status_code == 200
    assert response.json()["accounts"] == 1


@pytest.mark.asyncio
async def test_account_and_valuation_flow(
    async_client_with_db: TestClient,
) -> None:
    """FIN-12 acceptance: create My House, value it twice, read both back,
    current_balance follows the latest valuation."""
    created = async_client_with_db.post(
        "/api/v1/finance/accounts",
        json={
            "name": "My House",
            "account_type": "property",
            "classification": "asset",
        },
    )
    assert created.status_code == 201
    account_id = created.json()["id"]

    v1 = async_client_with_db.post(
        f"/api/v1/finance/accounts/{account_id}/valuations",
        json={"as_of_date": "2026-07-01", "value": 50_000_000},
    )
    assert v1.status_code == 201
    v2 = async_client_with_db.post(
        f"/api/v1/finance/accounts/{account_id}/valuations",
        json={"as_of_date": "2026-07-04", "value": 50_500_000},
    )
    assert v2.status_code == 201

    series = async_client_with_db.get(
        f"/api/v1/finance/accounts/{account_id}/valuations"
    )
    assert series.status_code == 200
    assert series.json()["total"] == 2

    accounts = async_client_with_db.get("/api/v1/finance/accounts")
    house = next(a for a in accounts.json()["items"] if a["id"] == account_id)
    assert house["current_balance"] == 50_500_000


@pytest.mark.asyncio
async def test_valuation_repost_updates_in_place(
    async_client_with_db: TestClient,
) -> None:
    created = async_client_with_db.post(
        "/api/v1/finance/accounts",
        json={
            "name": "House",
            "account_type": "property",
            "classification": "asset",
        },
    )
    account_id = created.json()["id"]
    for value in (100, 200):
        async_client_with_db.post(
            f"/api/v1/finance/accounts/{account_id}/valuations",
            json={"as_of_date": "2026-07-01", "value": value},
        )
    series = async_client_with_db.get(
        f"/api/v1/finance/accounts/{account_id}/valuations"
    )
    assert series.json()["total"] == 1  # upsert, not duplicate


@pytest.mark.asyncio
async def test_soft_delete_removes_from_listing(
    async_client_with_db: TestClient,
) -> None:
    created = async_client_with_db.post(
        "/api/v1/finance/accounts",
        json={
            "name": "Temp",
            "account_type": "checking",
            "classification": "asset",
        },
    )
    account_id = created.json()["id"]
    deleted = async_client_with_db.delete(
        f"/api/v1/finance/accounts/{account_id}"
    )
    assert deleted.status_code == 204
    accounts = async_client_with_db.get("/api/v1/finance/accounts")
    assert all(a["id"] != account_id for a in accounts.json()["items"])


@pytest.mark.asyncio
async def test_unknown_account_returns_404(
    async_client_with_db: TestClient,
) -> None:
    response = async_client_with_db.patch(
        "/api/v1/finance/accounts/999999", json={"name": "x"}
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_spending_summary_bad_month_returns_422(
    async_client_with_db: TestClient,
) -> None:
    """A malformed or out-of-range ``month`` is a client error, not a 500."""
    for bad in ("not-a-month", "2026-13"):
        response = async_client_with_db.get(
            "/api/v1/finance/spending/summary", params={"month": bad}
        )
        assert response.status_code == 422, bad


@pytest.mark.asyncio
async def test_net_worth_series_after_recompute(
    async_client_with_db: TestClient, async_db_session: AsyncSession
) -> None:
    """FIN-13 acceptance: House ($505k) + Mortgage ($300k) → net worth $205k."""
    from datetime import UTC, datetime, timedelta

    from app.services.finance import networth_service

    today = datetime.now(UTC).date()
    # House with two valuations; Mortgage as a liability.
    house = async_client_with_db.post(
        "/api/v1/finance/accounts",
        json={
            "name": "My House",
            "account_type": "property",
            "classification": "asset",
        },
    ).json()
    for offset, value in ((5, 50_000_000), (2, 50_500_000)):
        async_client_with_db.post(
            f"/api/v1/finance/accounts/{house['id']}/valuations",
            json={
                "as_of_date": (today - timedelta(days=offset)).isoformat(),
                "value": value,
            },
        )
    async_client_with_db.post(
        "/api/v1/finance/accounts",
        json={
            "name": "Mortgage",
            "account_type": "loan",
            "classification": "liability",
            "current_balance": 30_000_000,
        },
    )

    # Materialize snapshots (the nightly job's work), then read the series.
    await networth_service.recompute_snapshots(async_db_session, owner_user_id=None)
    await async_db_session.commit()

    response = async_client_with_db.get("/api/v1/finance/net-worth?days=90")
    assert response.status_code == 200
    series = response.json()
    assert series, "expected a net-worth series"
    assert series[-1]["net_worth_amount"] == 20_500_000


@pytest.mark.asyncio
async def test_import_batch_report(
    async_client_with_db: TestClient, async_db_session: AsyncSession
) -> None:
    """FIN-14: GET /import/batches/{id} shows per-row outcomes."""
    from pathlib import Path

    from app.services.finance import import_service
    from app.services.finance.importers.ofx import parse_ofx

    fixture = (
        Path(__file__).parent.parent
        / "services"
        / "finance"
        / "fixtures"
        / "sample_chase.qfx"
    )
    data = fixture.read_bytes()

    account = await FinanceService(async_db_session).create_manual_account(
        name="Chase Checking", account_type="checking", classification="asset"
    )
    result = await import_service.ingest_transactions(
        async_db_session,
        owner_user_id=None,
        source_type="qfx",
        file_name="sample_chase.qfx",
        file_bytes=data,
        parsed=parse_ofx(data, source="qfx"),
        default_account_id=account.id,
    )
    await async_db_session.commit()

    response = async_client_with_db.get(
        f"/api/v1/finance/import/batches/{result.batch_id}"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["rows_total"] == 6
    assert body["rows_inserted"] == 6
    assert len(body["rows"]) == 6
    assert all(r["parsed_status"] == "inserted" for r in body["rows"])


# ---------------------------------------------------------------------------
# FIN-17 — upload front door + read APIs
# ---------------------------------------------------------------------------

from pathlib import Path  # noqa: E402

_FIXTURES = (
    Path(__file__).parent.parent / "services" / "finance" / "fixtures"
)


async def _checking_account(session: AsyncSession) -> int:
    account = await FinanceService(session).create_manual_account(
        name="Chase Checking", account_type="checking", classification="asset"
    )
    await session.commit()
    return account.id


@pytest.mark.asyncio
async def test_upload_qif(
    async_client_with_db: TestClient, async_db_session: AsyncSession
) -> None:
    account_id = await _checking_account(async_db_session)
    data = (_FIXTURES / "sample_quicken.qif").read_bytes()
    response = async_client_with_db.post(
        "/api/v1/finance/import",
        files={"file": ("sample_quicken.qif", data, "text/plain")},
        params={"account_id": account_id},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["rows_inserted"] == 8

    # transactions read API returns them, newest first, deduped rows excluded
    txns = async_client_with_db.get(
        f"/api/v1/finance/transactions?account_id={account_id}"
    )
    assert txns.status_code == 200
    items = txns.json()["items"]
    assert len(items) == 8
    assert items[0]["date"] >= items[-1]["date"]


@pytest.mark.asyncio
async def test_upload_reupload_short_circuits(
    async_client_with_db: TestClient, async_db_session: AsyncSession
) -> None:
    account_id = await _checking_account(async_db_session)
    data = (_FIXTURES / "sample_chase.qfx").read_bytes()
    files = {"file": ("sample_chase.qfx", data, "application/octet-stream")}
    first = async_client_with_db.post(
        "/api/v1/finance/import", files=files, params={"account_id": account_id}
    )
    assert first.json()["rows_inserted"] == 6
    second = async_client_with_db.post(
        "/api/v1/finance/import",
        files={"file": ("sample_chase.qfx", data, "application/octet-stream")},
        params={"account_id": account_id},
    )
    body = second.json()
    assert body["rows_inserted"] == 0
    assert body["rows_duplicate"] == body["rows_total"] == 6

    batches = async_client_with_db.get("/api/v1/finance/import/batches")
    assert batches.status_code == 200
    assert len(batches.json()) >= 1


@pytest.mark.asyncio
async def test_upload_unknown_extension_415(
    async_client_with_db: TestClient, async_db_session: AsyncSession
) -> None:
    account_id = await _checking_account(async_db_session)
    response = async_client_with_db.post(
        "/api/v1/finance/import",
        files={"file": ("statement.pdf", b"%PDF-1.4", "application/pdf")},
        params={"account_id": account_id},
    )
    assert response.status_code == 415


@pytest.mark.asyncio
async def test_upload_missing_account_404(
    async_client_with_db: TestClient,
) -> None:
    response = async_client_with_db.post(
        "/api/v1/finance/import",
        files={"file": ("x.qif", b"!Type:Bank\n^\n", "text/plain")},
        params={"account_id": 999_999},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_upload_oversized_413(
    async_client_with_db: TestClient, async_db_session: AsyncSession
) -> None:
    account_id = await _checking_account(async_db_session)
    oversized = b"x" * (10 * 1024 * 1024 + 1)
    response = async_client_with_db.post(
        "/api/v1/finance/import",
        files={"file": ("big.csv", oversized, "text/csv")},
        params={"account_id": account_id},
    )
    assert response.status_code == 413
