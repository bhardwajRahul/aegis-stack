"""
Plausible Analytics collector.

Collects docs visitor metrics, page engagement, and bounce rates.
Supports multiple sites via comma-separated INSIGHT_PLAUSIBLE_SITES.
Uses /stats/timeseries for daily breakdowns (supports backfill).
Per-day country + page breakdowns stored for range-aware display.
"""

from datetime import datetime, timedelta  # noqa: I001
import logging

import httpx
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings

from ..constants import MetricKeys, Periods, SourceKeys
from ..schemas import (
    PlausibleCountryEntry,
    PlausiblePageEntry,
    PlausibleSiteMetadata,
    PlausibleTopCountriesMetadata,
    PlausibleTopPagesMetadata,
)
from .base import BaseCollector, CollectionResult

logger = logging.getLogger(__name__)

PLAUSIBLE_API = "https://plausible.io/api/v1"


class PlausibleCollector(BaseCollector):
    """Collects analytics from the Plausible API."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    @property
    def source_key(self) -> str:
        return SourceKeys.PLAUSIBLE

    async def collect(self, lookback_days: int = 1) -> CollectionResult:
        """Collect visitor metrics and page engagement for all configured sites.

        Args:
            lookback_days: Number of days to fetch. 1 = today only (default).
                           Higher values for backfill (e.g., 365).
        """
        api_key = settings.INSIGHT_PLAUSIBLE_API_KEY
        sites_str = settings.INSIGHT_PLAUSIBLE_SITES

        if not api_key or not sites_str:
            return CollectionResult(
                source_key=self.source_key,
                success=False,
                error="Missing INSIGHT_PLAUSIBLE_API_KEY or INSIGHT_PLAUSIBLE_SITES",
            )

        sites = [s.strip() for s in sites_str.split(",") if s.strip()]
        headers = {"Authorization": f"Bearer {api_key}"}

        rows_written = 0
        rows_skipped = 0

        try:
            visitors_type = await self.get_metric_type(MetricKeys.VISITORS)
            pageviews_type = await self.get_metric_type(MetricKeys.PAGEVIEWS)
            duration_type = await self.get_metric_type(MetricKeys.AVG_DURATION)
            bounce_type = await self.get_metric_type(MetricKeys.BOUNCE_RATE)
            pages_type = await self.get_metric_type(MetricKeys.TOP_PAGES)
            countries_type = await self.get_metric_type(MetricKeys.TOP_COUNTRIES)

            today = _today()
            start_date = today - timedelta(days=lookback_days - 1)
            date_range = (
                f"{start_date.strftime('%Y-%m-%d')},{today.strftime('%Y-%m-%d')}"
            )

            async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
                for site in sites:
                    site_meta = PlausibleSiteMetadata(site=site).model_dump()

                    # Fetch daily timeseries for the date range
                    resp = await client.get(
                        f"{PLAUSIBLE_API}/stats/timeseries",
                        params={
                            "site_id": site,
                            "period": "custom",
                            "date": date_range,
                            "metrics": "visitors,pageviews,visit_duration,bounce_rate",
                        },
                    )
                    resp.raise_for_status()
                    timeseries = resp.json().get("results", [])

                    # Collect days that had visitors (for per-day breakdowns)
                    active_days: list[str] = []

                    for day_data in timeseries:
                        day_str = day_data.get("date", "")
                        if not day_str:
                            continue
                        day_dt = datetime.strptime(day_str, "%Y-%m-%d")

                        visitors = day_data.get("visitors") or 0
                        if visitors > 0:
                            active_days.append(day_str)

                        for mt, key in [
                            (visitors_type, "visitors"),
                            (pageviews_type, "pageviews"),
                            (duration_type, "visit_duration"),
                            (bounce_type, "bounce_rate"),
                        ]:
                            value = day_data.get(key) or 0
                            _, created = await self.upsert_metric(
                                metric_type=mt,
                                date=day_dt,
                                value=float(value),
                                period=Periods.DAILY,
                                metadata=site_meta,
                            )
                            rows_written += 1 if created else 0
                            rows_skipped += 0 if created else 1

                    # Per-day country + page breakdowns for active days
                    for day_str in active_days:
                        day_dt = datetime.strptime(day_str, "%Y-%m-%d")

                        # Pages
                        pages_resp = await client.get(
                            f"{PLAUSIBLE_API}/stats/breakdown",
                            params={
                                "site_id": site,
                                "period": "day",
                                "date": day_str,
                                "property": "event:page",
                                "metrics": "visitors,visit_duration",
                                "limit": 20,
                            },
                        )
                        pages_resp.raise_for_status()
                        page_results = pages_resp.json().get("results", [])

                        pages_metadata = PlausibleTopPagesMetadata(
                            site=site,
                            pages=[
                                PlausiblePageEntry(
                                    url=p.get("page", ""),
                                    visitors=p.get("visitors", 0),
                                    time_s=p.get("visit_duration"),
                                )
                                for p in page_results
                            ],
                        )
                        _, created = await self.upsert_metric(
                            metric_type=pages_type,
                            date=day_dt,
                            value=float(len(page_results)),
                            period=Periods.DAILY,
                            metadata=pages_metadata.model_dump(),
                        )
                        rows_written += 1 if created else 0
                        rows_skipped += 0 if created else 1

                        # Countries
                        countries_resp = await client.get(
                            f"{PLAUSIBLE_API}/stats/breakdown",
                            params={
                                "site_id": site,
                                "period": "day",
                                "date": day_str,
                                "property": "visit:country",
                                "metrics": "visitors",
                                "limit": 20,
                            },
                        )
                        countries_resp.raise_for_status()
                        country_results = countries_resp.json().get("results", [])

                        countries_metadata = PlausibleTopCountriesMetadata(
                            site=site,
                            countries=[
                                PlausibleCountryEntry(
                                    country=c.get("country", ""),
                                    visitors=c.get("visitors", 0),
                                )
                                for c in country_results
                            ],
                        )
                        _, created = await self.upsert_metric(
                            metric_type=countries_type,
                            date=day_dt,
                            value=float(len(country_results)),
                            period=Periods.DAILY,
                            metadata=countries_metadata.model_dump(),
                        )
                        rows_written += 1 if created else 0
                        rows_skipped += 0 if created else 1

            await self.db.commit()

            logger.info(
                "Plausible collected for %d sites (%d days, %d active): %d written, %d skipped",  # noqa: E501
                len(sites),
                lookback_days,
                len(active_days),
                rows_written,
                rows_skipped,
            )

            return CollectionResult(
                source_key=self.source_key,
                success=True,
                rows_written=rows_written,
                rows_skipped=rows_skipped,
            )

        except httpx.HTTPStatusError as e:
            error_msg = f"Plausible API error: {e.response.status_code}"
            logger.error(error_msg)
            return CollectionResult(
                source_key=self.source_key,
                success=False,
                rows_written=rows_written,
                rows_skipped=rows_skipped,
                error=error_msg,
            )
        except Exception as e:
            error_msg = f"Plausible collection failed: {e}"
            logger.error(error_msg)
            return CollectionResult(
                source_key=self.source_key,
                success=False,
                rows_written=rows_written,
                rows_skipped=rows_skipped,
                error=error_msg,
            )


def _today() -> datetime:
    """Get today as a midnight datetime (no timezone)."""
    return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
