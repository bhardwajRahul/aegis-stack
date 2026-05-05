"""
Tests for insights API endpoints.
"""

import pytest
from app.services.insights.constants import MetricKeys, Periods, SourceKeys
from app.services.insights.models import (
    InsightEvent,
    InsightMetric,
    InsightMetricType,
    InsightSource,
)
from sqlmodel.ext.asyncio.session import AsyncSession


async def _seed_full(session: AsyncSession) -> None:
    """Seed a source, metric type, metric, and event for testing."""
    source = InsightSource(
        key=SourceKeys.GITHUB_TRAFFIC,
        display_name="GitHub Traffic",
        collection_interval_hours=6,
        enabled=True,
    )
    session.add(source)
    await session.flush()

    mt = InsightMetricType(
        source_id=source.id,  # type: ignore[arg-type]
        key=MetricKeys.CLONES,
        display_name="Clones",
        unit="count",
    )
    session.add(mt)
    await session.flush()

    from datetime import datetime

    project = await _ensure_project(session)
    project_kwargs = {"project_id": project.id} if project is not None else {}

    metric = InsightMetric(
        date=datetime(2026, 4, 10),
        metric_type_id=mt.id,  # type: ignore[arg-type]
        value=42.0,
        period=Periods.DAILY,
        **project_kwargs,
    )
    session.add(metric)

    event = InsightEvent(
        date=datetime(2026, 4, 10),
        event_type="release",
        description="v0.6.9",
        **project_kwargs,
    )
    session.add(event)
    await session.flush()


async def _ensure_project(session: AsyncSession) -> object | None:
    """Lazily create (or reuse) a Project for this test session.

    Returns ``None`` in auth=off builds (no Project model exists), so
    rows can be inserted without ``project_id`` in single-tenant mode.
    """
    try:
        from sqlmodel import select

        from app.models.user import User
        from app.services.insights.models import Project
    except ImportError:
        return None
    result = await session.exec(select(Project).limit(1))
    existing = result.first()
    if existing is not None:
        return existing
    user = User(
        email="insights-endpoints-test@example.com",
        full_name="Insights API Test",
        hashed_password="x",
    )
    session.add(user)
    await session.flush()
    project = Project(
        slug="iep",
        name="iep",
        owner_user_id=user.id,  # type: ignore[arg-type]
    )
    session.add(project)
    await session.flush()
    return project


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    """Clear the cache before each test."""
    from app.core.cache import cache

    cache.clear()


class TestGetAllInsights:
    @pytest.mark.asyncio
    async def test_returns_bulk_data(
        self,
        async_client_with_db: object,
        async_db_session: AsyncSession,
        auth_headers: dict[str, str],
    ) -> None:
        """GET /api/v1/insights/all returns bulk insight data."""
        await _seed_full(async_db_session)

        response = async_client_with_db.get(  # type: ignore[union-attr]
            "/api/v1/insights/all", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert "daily" in data
        assert "events" in data
        assert "insight_events" in data
        assert "sources" in data
        assert "latest" in data

    @pytest.mark.asyncio
    async def test_daily_contains_seeded_metric(
        self,
        async_client_with_db: object,
        async_db_session: AsyncSession,
        auth_headers: dict[str, str],
    ) -> None:
        """Seeded daily metric appears in response."""
        await _seed_full(async_db_session)

        response = async_client_with_db.get(  # type: ignore[union-attr]
            "/api/v1/insights/all", headers=auth_headers
        )
        data = response.json()

        clones = data["daily"].get("clones", [])
        assert len(clones) == 1
        assert clones[0]["value"] == 42.0
        assert clones[0]["date"].startswith("2026-04-10")
        assert clones[0]["period"] == "daily"

    @pytest.mark.asyncio
    async def test_insight_events_in_response(
        self,
        async_client_with_db: object,
        async_db_session: AsyncSession,
        auth_headers: dict[str, str],
    ) -> None:
        """Seeded InsightEvent appears in response."""
        await _seed_full(async_db_session)

        response = async_client_with_db.get(  # type: ignore[union-attr]
            "/api/v1/insights/all", headers=auth_headers
        )
        data = response.json()

        assert len(data["insight_events"]) == 1
        assert data["insight_events"][0]["event_type"] == "release"
        assert data["insight_events"][0]["description"] == "v0.6.9"

    @pytest.mark.asyncio
    async def test_empty_db_returns_empty_lists(
        self, async_client_with_db: object, auth_headers: dict[str, str]
    ) -> None:
        """Empty database returns structure with empty lists."""
        response = async_client_with_db.get(  # type: ignore[union-attr]
            "/api/v1/insights/all", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["insight_events"] == []
        assert data["sources"] == []
