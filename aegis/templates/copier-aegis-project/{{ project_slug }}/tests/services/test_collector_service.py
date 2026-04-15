"""
Tests for CollectorService orchestration layer.
"""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from app.services.insights.collector_service import CollectorService
from app.services.insights.collectors.base import CollectionResult
from app.services.insights.constants import MetricKeys, Periods, SourceKeys
from app.services.insights.models import (
    InsightMetric,
    InsightMetricType,
    InsightSource,
)
from sqlmodel.ext.asyncio.session import AsyncSession

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _seed_source(
    session: AsyncSession,
    key: str = SourceKeys.GITHUB_TRAFFIC,
    enabled: bool = True,
) -> InsightSource:
    source = InsightSource(
        key=key,
        display_name="Test Source",
        collection_interval_hours=6,
        enabled=enabled,
    )
    session.add(source)
    await session.flush()
    return source


async def _seed_metric_type(
    session: AsyncSession,
    source: InsightSource,
    key: str = MetricKeys.CLONES,
) -> InsightMetricType:
    mt = InsightMetricType(
        source_id=source.id,  # type: ignore[arg-type]
        key=key,
        display_name=key.replace("_", " ").title(),
        unit="count",
    )
    session.add(mt)
    await session.flush()
    return mt


# ---------------------------------------------------------------------------
# Tests: collect_source
# ---------------------------------------------------------------------------


class TestCollectSource:
    @pytest.mark.asyncio
    async def test_collect_unknown_source(self, async_db_session: AsyncSession) -> None:
        """Unknown source key returns error CollectionResult."""
        service = CollectorService(async_db_session)
        result = await service.collect_source("nonexistent_source")

        assert result.success is False
        assert "No collector registered" in (result.error or "")

    @pytest.mark.asyncio
    async def test_collect_source_not_in_db(
        self, async_db_session: AsyncSession
    ) -> None:
        """Source key registered but not seeded in DB returns error."""
        service = CollectorService(async_db_session)
        result = await service.collect_source(SourceKeys.GITHUB_TRAFFIC)

        assert result.success is False
        assert "not found in database" in (result.error or "")

    @pytest.mark.asyncio
    async def test_collect_disabled_source(
        self, async_db_session: AsyncSession
    ) -> None:
        """Disabled source returns error."""
        await _seed_source(async_db_session, SourceKeys.GITHUB_TRAFFIC, enabled=False)

        service = CollectorService(async_db_session)
        result = await service.collect_source(SourceKeys.GITHUB_TRAFFIC)

        assert result.success is False
        assert "disabled" in (result.error or "")

    @pytest.mark.asyncio
    @patch("app.services.insights.collectors.github_traffic.settings")
    async def test_collect_updates_last_collected_at(
        self, mock_settings: AsyncMock, async_db_session: AsyncSession
    ) -> None:
        """Successful collection updates source.last_collected_at."""
        mock_settings.INSIGHT_GITHUB_TOKEN = ""
        mock_settings.INSIGHT_GITHUB_OWNER = ""
        mock_settings.INSIGHT_GITHUB_REPO = ""

        source = await _seed_source(async_db_session, SourceKeys.GITHUB_TRAFFIC)
        assert source.last_collected_at is None

        # The collector will fail due to missing config, but that's a success=False path
        # so last_collected_at won't be updated. We need a success path.
        # Patch the collector's collect method directly for a clean test.
        with patch(
            "app.services.insights.collector_service.COLLECTOR_REGISTRY",
            {SourceKeys.GITHUB_TRAFFIC: _make_mock_collector_cls(success=True)},
        ):
            service = CollectorService(async_db_session)
            result = await service.collect_source(SourceKeys.GITHUB_TRAFFIC)

            assert result.success is True

            # Refresh the source from DB
            await async_db_session.refresh(source)
            assert source.last_collected_at is not None


# ---------------------------------------------------------------------------
# Tests: collect_all
# ---------------------------------------------------------------------------


class TestCollectAll:
    @pytest.mark.asyncio
    async def test_collect_all_runs_enabled_sources(
        self, async_db_session: AsyncSession
    ) -> None:
        """collect_all runs collectors for all enabled sources."""
        await _seed_source(async_db_session, SourceKeys.GITHUB_TRAFFIC, enabled=True)
        await _seed_source(async_db_session, SourceKeys.PYPI, enabled=True)
        await _seed_source(async_db_session, SourceKeys.REDDIT, enabled=False)

        mock_cls = _make_mock_collector_cls(success=True)
        registry = {
            SourceKeys.GITHUB_TRAFFIC: mock_cls,
            SourceKeys.PYPI: mock_cls,
            SourceKeys.REDDIT: mock_cls,
        }

        with patch(
            "app.services.insights.collector_service.COLLECTOR_REGISTRY", registry
        ):
            service = CollectorService(async_db_session)
            results = await service.collect_all()

        # Only enabled sources should have results
        assert SourceKeys.GITHUB_TRAFFIC in results
        assert SourceKeys.PYPI in results
        assert SourceKeys.REDDIT not in results

    @pytest.mark.asyncio
    async def test_collect_all_empty_db(self, async_db_session: AsyncSession) -> None:
        """collect_all with no sources returns empty dict."""
        service = CollectorService(async_db_session)
        results = await service.collect_all()
        assert results == {}


# ---------------------------------------------------------------------------
# Tests: _check_records
# ---------------------------------------------------------------------------


class TestCheckRecords:
    @pytest.mark.asyncio
    async def test_detects_new_record(self, async_db_session: AsyncSession) -> None:
        """_check_records creates a milestone event when ATH is detected."""
        source = await _seed_source(async_db_session)
        mt = await _seed_metric_type(async_db_session, source, MetricKeys.CLONES)

        # Seed a daily metric that should trigger a record
        metric = InsightMetric(
            date=datetime(2026, 4, 10),
            metric_type_id=mt.id,  # type: ignore[arg-type]
            value=999.0,
            period=Periods.DAILY,
        )
        async_db_session.add(metric)
        await async_db_session.flush()

        service = CollectorService(async_db_session)
        broken = await service._check_records(SourceKeys.GITHUB_TRAFFIC)

        assert len(broken) > 0
        assert "999" in broken[0]

    @pytest.mark.asyncio
    async def test_no_record_when_lower(self, async_db_session: AsyncSession) -> None:
        """_check_records does not create event when value <= existing record."""
        from app.services.insights.models import InsightEvent

        source = await _seed_source(async_db_session)
        mt = await _seed_metric_type(async_db_session, source, MetricKeys.CLONES)

        # Seed an existing milestone
        event = InsightEvent(
            date=datetime(2026, 4, 1),
            event_type="milestone_github",
            description="1,000 (GitHub 1-Day Clones)",
            metadata_={"category": "daily_clones"},
        )
        async_db_session.add(event)
        await async_db_session.flush()

        # Seed a daily metric lower than existing record
        metric = InsightMetric(
            date=datetime(2026, 4, 10),
            metric_type_id=mt.id,  # type: ignore[arg-type]
            value=500.0,
            period=Periods.DAILY,
        )
        async_db_session.add(metric)
        await async_db_session.flush()

        service = CollectorService(async_db_session)
        broken = await service._check_records(SourceKeys.GITHUB_TRAFFIC)

        # Should not detect record for clones (500 < 1000)
        clone_records = [b for b in broken if "1-Day Clones" in b]
        assert len(clone_records) == 0

    @pytest.mark.asyncio
    async def test_no_records_for_untracked_source(
        self, async_db_session: AsyncSession
    ) -> None:
        """Sources without record checks return empty list."""
        service = CollectorService(async_db_session)
        broken = await service._check_records(SourceKeys.REDDIT)
        assert broken == []

    @pytest.mark.asyncio
    async def test_star_daily_record(self, async_db_session: AsyncSession) -> None:
        """_check_records detects new star daily ATH from new_star events."""
        source = await _seed_source(async_db_session, SourceKeys.GITHUB_STARS)
        mt = await _seed_metric_type(async_db_session, source, "new_star")

        # 6 stars on the same day
        for i in range(6):
            async_db_session.add(
                InsightMetric(
                    date=datetime(2026, 4, 10),
                    metric_type_id=mt.id,  # type: ignore[arg-type]
                    value=float(i + 1),
                    period=Periods.EVENT,
                )
            )
        await async_db_session.flush()

        service = CollectorService(async_db_session)
        broken = await service._check_records(SourceKeys.GITHUB_STARS)

        star_records = [b for b in broken if "Stars Best Day" in b]
        assert len(star_records) == 1
        assert "6" in star_records[0]

    @pytest.mark.asyncio
    async def test_star_monthly_record(self, async_db_session: AsyncSession) -> None:
        """_check_records detects new star monthly ATH from new_star events."""
        source = await _seed_source(async_db_session, SourceKeys.GITHUB_STARS)
        mt = await _seed_metric_type(async_db_session, source, "new_star")

        # Stars across multiple days in the same month: 3 + 2 + 5 = 10
        for day, count in [(1, 3), (5, 2), (10, 5)]:
            for i in range(count):
                async_db_session.add(
                    InsightMetric(
                        date=datetime(2026, 4, day),
                        metric_type_id=mt.id,  # type: ignore[arg-type]
                        value=float(i + 1),
                        period=Periods.EVENT,
                    )
                )
        await async_db_session.flush()

        service = CollectorService(async_db_session)
        broken = await service._check_records(SourceKeys.GITHUB_STARS)

        monthly_records = [b for b in broken if "Stars Best Month" in b]
        assert len(monthly_records) == 1
        assert "10" in monthly_records[0]


# ---------------------------------------------------------------------------
# Tests: get_registered_sources
# ---------------------------------------------------------------------------


class TestGetRegisteredSources:
    def test_returns_all_registered(self) -> None:
        service = CollectorService(AsyncMock())
        sources = service.get_registered_sources()

        assert SourceKeys.GITHUB_TRAFFIC in sources
        assert SourceKeys.PYPI in sources
        assert SourceKeys.PLAUSIBLE in sources
        assert SourceKeys.REDDIT in sources
        assert len(sources) == 6


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _make_mock_collector_cls(success: bool = True) -> type:
    """Create a mock collector class that returns a fixed result."""

    class MockCollector:
        def __init__(self, db: AsyncSession) -> None:
            self.db = db

        @property
        def source_key(self) -> str:
            return "mock"

        async def collect(self, **kwargs: object) -> CollectionResult:
            return CollectionResult(
                source_key=self.source_key,
                success=success,
                rows_written=5 if success else 0,
            )

    return MockCollector
