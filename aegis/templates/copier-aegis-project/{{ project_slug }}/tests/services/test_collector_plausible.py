"""
Tests for PlausibleCollector -- Plausible Analytics collection.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.services.insights.collectors.plausible import PlausibleCollector
from app.services.insights.constants import MetricKeys, Periods, SourceKeys
from app.services.insights.models import InsightMetric, InsightMetricType, InsightSource
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _seed_plausible(
    session: AsyncSession,
) -> tuple[InsightSource, dict[str, InsightMetricType]]:
    """Seed plausible source with all metric types."""
    source = InsightSource(
        key=SourceKeys.PLAUSIBLE,
        display_name="Plausible Analytics",
        collection_interval_hours=24,
        enabled=True,
    )
    session.add(source)
    await session.flush()

    metric_types: dict[str, InsightMetricType] = {}
    for key in [
        MetricKeys.VISITORS,
        MetricKeys.PAGEVIEWS,
        MetricKeys.AVG_DURATION,
        MetricKeys.BOUNCE_RATE,
        MetricKeys.TOP_PAGES,
        MetricKeys.TOP_COUNTRIES,
    ]:
        mt = InsightMetricType(
            source_id=source.id,  # type: ignore[arg-type]
            key=key,
            display_name=key.replace("_", " ").title(),
            unit="json" if "top_" in key else "count",
        )
        session.add(mt)
        await session.flush()
        metric_types[key] = mt

    return source, metric_types


# ---------------------------------------------------------------------------
# Tests: PlausibleCollector
# ---------------------------------------------------------------------------


class TestPlausibleCollectorSuccess:
    """Test successful collection."""

    @pytest.mark.asyncio
    async def test_collect_success(self, async_db_session: AsyncSession) -> None:
        """Happy path: collect visitor metrics and page engagement."""
        await _seed_plausible(async_db_session)

        mock_client = AsyncMock()

        async def mock_get(url: str, **kwargs):
            """Mock Plausible API responses."""
            if "timeseries" in url:
                # Daily timeseries metrics
                return MagicMock(
                    json=lambda: {
                        "results": [
                            {
                                "date": "2026-04-11",
                                "visitors": 100,
                                "pageviews": 250,
                                "visit_duration": 45.5,
                                "bounce_rate": 35.0,
                            },
                            {
                                "date": "2026-04-10",
                                "visitors": 80,
                                "pageviews": 200,
                                "visit_duration": 42.0,
                                "bounce_rate": 40.0,
                            },
                        ]
                    },
                    raise_for_status=lambda: None,
                )
            elif "breakdown" in url:
                params = kwargs.get("params", {})
                if "event:page" in params.get("property", ""):
                    # Top pages
                    return MagicMock(
                        json=lambda: {
                            "results": [
                                {
                                    "page": "/docs",
                                    "visitors": 60,
                                    "visit_duration": 120,
                                },
                                {"page": "/", "visitors": 40, "visit_duration": 30},
                            ]
                        },
                        raise_for_status=lambda: None,
                    )
                else:
                    # Top countries
                    return MagicMock(
                        json=lambda: {
                            "results": [
                                {"country": "United States", "visitors": 70},
                                {"country": "Canada", "visitors": 30},
                            ]
                        },
                        raise_for_status=lambda: None,
                    )

        mock_client.get = mock_get

        with patch(
            "app.services.insights.collectors.plausible.httpx.AsyncClient"
        ) as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client

            with patch(
                "app.services.insights.collectors.plausible.settings"
            ) as mock_settings:
                mock_settings.INSIGHT_PLAUSIBLE_API_KEY = "apikey123"
                mock_settings.INSIGHT_PLAUSIBLE_SITES = "docs.example.com"

                collector = PlausibleCollector(async_db_session)
                result = await collector.collect(lookback_days=1)

        assert result.success is True
        assert result.source_key == SourceKeys.PLAUSIBLE
        assert result.rows_written > 0

        # Verify metrics were written
        metrics = await async_db_session.exec(select(InsightMetric))
        metric_list = metrics.all()
        assert len(metric_list) > 0

    @pytest.mark.asyncio
    async def test_collect_missing_config(self, async_db_session: AsyncSession) -> None:
        """Missing API key or sites returns error."""
        await _seed_plausible(async_db_session)

        with patch(
            "app.services.insights.collectors.plausible.settings"
        ) as mock_settings:
            mock_settings.INSIGHT_PLAUSIBLE_API_KEY = None
            mock_settings.INSIGHT_PLAUSIBLE_SITES = "docs.example.com"

            collector = PlausibleCollector(async_db_session)
            result = await collector.collect()

        assert result.success is False
        assert "Missing" in result.error

    @pytest.mark.asyncio
    async def test_collect_api_error(self, async_db_session: AsyncSession) -> None:
        """HTTP error from Plausible is handled gracefully."""
        import httpx

        await _seed_plausible(async_db_session)

        mock_response = MagicMock(status_code=401)
        error = httpx.HTTPStatusError(
            "401", request=MagicMock(), response=mock_response
        )

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=error)

        with patch(
            "app.services.insights.collectors.plausible.httpx.AsyncClient"
        ) as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client

            with patch(
                "app.services.insights.collectors.plausible.settings"
            ) as mock_settings:
                mock_settings.INSIGHT_PLAUSIBLE_API_KEY = "apikey123"
                mock_settings.INSIGHT_PLAUSIBLE_SITES = "docs.example.com"

                collector = PlausibleCollector(async_db_session)
                result = await collector.collect()

        assert result.success is False
        assert "Plausible API error" in result.error

    @pytest.mark.asyncio
    async def test_deduplication(self, async_db_session: AsyncSession) -> None:
        """Second collect doesn't duplicate existing daily rows."""
        source, metric_types = await _seed_plausible(async_db_session)
        visitors_type = metric_types[MetricKeys.VISITORS]

        # Pre-populate a visitors row
        existing_visitors = InsightMetric(
            date=datetime(2026, 4, 11),
            metric_type_id=visitors_type.id,  # type: ignore[arg-type]
            value=100.0,
            period=Periods.DAILY,
            metadata_={"site": "docs.example.com"},
        )
        async_db_session.add(existing_visitors)
        await async_db_session.commit()

        mock_client = AsyncMock()

        async def mock_get(url: str, **kwargs):
            if "timeseries" in url:
                return MagicMock(
                    json=lambda: {
                        "results": [
                            {
                                "date": "2026-04-11",
                                "visitors": 100,
                                "pageviews": 250,
                                "visit_duration": 45.5,
                                "bounce_rate": 35.0,
                            },
                        ]
                    },
                    raise_for_status=lambda: None,
                )
            elif "breakdown" in url:
                return MagicMock(
                    json=lambda: {"results": []},
                    raise_for_status=lambda: None,
                )

        mock_client.get = mock_get

        with patch(
            "app.services.insights.collectors.plausible.httpx.AsyncClient"
        ) as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client

            with patch(
                "app.services.insights.collectors.plausible.settings"
            ) as mock_settings:
                mock_settings.INSIGHT_PLAUSIBLE_API_KEY = "apikey123"
                mock_settings.INSIGHT_PLAUSIBLE_SITES = "docs.example.com"

                collector = PlausibleCollector(async_db_session)
                result = await collector.collect(lookback_days=1)

        assert result.success is True
        # The visitors row for 2026-04-11 should be skipped (already exists)
        assert result.rows_skipped > 0

    @pytest.mark.asyncio
    async def test_lookback_days(self, async_db_session: AsyncSession) -> None:
        """Lookback parameter affects query date range."""
        await _seed_plausible(async_db_session)

        captured_requests: list[dict] = []

        mock_client = AsyncMock()

        async def mock_get(url: str, **kwargs):
            captured_requests.append(kwargs)
            if "timeseries" in url:
                return MagicMock(
                    json=lambda: {"results": []},
                    raise_for_status=lambda: None,
                )
            else:
                return MagicMock(
                    json=lambda: {"results": []},
                    raise_for_status=lambda: None,
                )

        mock_client.get = mock_get

        with patch(
            "app.services.insights.collectors.plausible.httpx.AsyncClient"
        ) as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client

            with patch(
                "app.services.insights.collectors.plausible.settings"
            ) as mock_settings:
                mock_settings.INSIGHT_PLAUSIBLE_API_KEY = "apikey123"
                mock_settings.INSIGHT_PLAUSIBLE_SITES = "docs.example.com"

                collector = PlausibleCollector(async_db_session)
                await collector.collect(lookback_days=30)

        # Check that timeseries request has date range parameter
        timeseries_requests = [
            r
            for r in captured_requests
            if r.get("params", {}).get("period") == "custom"
        ]
        assert len(timeseries_requests) > 0
        # The date parameter should have a range
        date_param = timeseries_requests[0].get("params", {}).get("date", "")
        assert "," in date_param, (
            f"Expected date range like 'YYYY-MM-DD,YYYY-MM-DD', got {date_param}"
        )
