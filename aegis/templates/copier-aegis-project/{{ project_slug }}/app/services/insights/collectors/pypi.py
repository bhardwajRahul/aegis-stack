"""
PyPI downloads collector via ClickHouse public SQL endpoint.

Collects download stats with full dimensional breakdowns:
country, installer, version, distribution type, and human vs bot.
No authentication required.
"""

import logging
from datetime import datetime

import httpx
from app.core.config import settings
from sqlmodel.ext.asyncio.session import AsyncSession

from ..constants import MetricKeys, Periods, SourceKeys
from ..schemas import (
    PyPICountryBreakdown,
    PyPIDownloadMetadata,
    PyPIInstallerBreakdown,
    PyPITypeBreakdown,
    PyPIVersionDetail,
)
from .base import BaseCollector, CollectionResult

logger = logging.getLogger(__name__)

CLICKHOUSE_URL = "https://sql-clickhouse.clickhouse.com"
CLICKHOUSE_PARAMS = {"user": "play", "default_format": "JSONCompact"}

# Pre-aggregated table with all dimensions
FULL_TABLE = "pypi.pypi_downloads_per_day_by_version_by_installer_by_type_by_country"
DAILY_TABLE = "pypi.pypi_downloads_per_day"

# Known bot/mirror installers — these are NOT real humans installing your package
BOT_INSTALLERS = {
    "bandersnatch",
    "z3c.pypimirror",
    "Nexus",
    "devpi",
    "pep381client",
    "requests",
    "OS",
    "Artifactory",
    "",  # empty user-agent = automated
}


class PyPICollector(BaseCollector):
    """Collects PyPI download stats from ClickHouse public dataset."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    @property
    def source_key(self) -> str:
        return SourceKeys.PYPI

    async def collect(self, lookback_days: int = 14) -> CollectionResult:  # noqa: ARG002
        """Collect daily totals + per-day dimensional breakdowns.

        ``lookback_days`` is accepted for API parity with other collectors but
        currently ignored — pypi pulls a fixed 14-day window.
        """
        package = settings.INSIGHT_PYPI_PACKAGE

        if not package:
            return CollectionResult(
                source_key=self.source_key,
                success=False,
                error="Missing INSIGHT_PYPI_PACKAGE",
            )

        rows_written = 0
        rows_skipped = 0

        try:
            daily_type = await self.get_metric_type(MetricKeys.DOWNLOADS_DAILY)
            daily_human_type = await self.get_metric_type(
                MetricKeys.DOWNLOADS_DAILY_HUMAN
            )
            total_type = await self.get_metric_type(MetricKeys.DOWNLOADS_TOTAL)
            country_type = await self.get_metric_type(MetricKeys.DOWNLOADS_BY_COUNTRY)
            installer_type = await self.get_metric_type(
                MetricKeys.DOWNLOADS_BY_INSTALLER
            )
            version_type = await self.get_metric_type(MetricKeys.DOWNLOADS_BY_VERSION)
            dist_type = await self.get_metric_type(MetricKeys.DOWNLOADS_BY_TYPE)

            async with httpx.AsyncClient(timeout=30.0) as client:
                # All-time cumulative total
                total_data = await self._query(
                    client,
                    f"""
                    SELECT sum(count) FROM {DAILY_TABLE}
                    WHERE project = '{package}'
                """,
                )
                total = int(total_data[0][0]) if total_data else 0
                today = _today()

                _, created = await self.upsert_metric(
                    metric_type=total_type,
                    date=today,
                    value=float(total),
                    period=Periods.CUMULATIVE,
                )
                rows_written += 1 if created else 0
                rows_skipped += 0 if created else 1

                # Per-day data with installer for human/bot split
                daily_installer_data = await self._query(
                    client,
                    f"""
                    SELECT date, installer, sum(count) as downloads
                    FROM {FULL_TABLE}
                    WHERE project = '{package}' AND date >= today() - 14
                    GROUP BY date, installer
                    ORDER BY date
                """,
                )

                # Aggregate per day: total and human-only
                daily_totals: dict[str, int] = {}
                daily_humans: dict[str, int] = {}
                daily_installers: dict[str, dict[str, int]] = {}

                for row in daily_installer_data:
                    day = row[0]
                    installer = row[1] or "(unknown)"
                    count = int(row[2])

                    daily_totals[day] = daily_totals.get(day, 0) + count

                    if row[1] not in BOT_INSTALLERS:
                        daily_humans[day] = daily_humans.get(day, 0) + count

                    if day not in daily_installers:
                        daily_installers[day] = {}
                    daily_installers[day][installer] = count

                # Write daily total + human rows
                for day, total_count in daily_totals.items():
                    date = _parse_date(day)

                    _, created = await self.upsert_metric(
                        metric_type=daily_type,
                        date=date,
                        value=float(total_count),
                        period=Periods.DAILY,
                    )
                    rows_written += 1 if created else 0
                    rows_skipped += 0 if created else 1

                    human_count = daily_humans.get(day, 0)
                    _, created = await self.upsert_metric(
                        metric_type=daily_human_type,
                        date=date,
                        value=float(human_count),
                        period=Periods.DAILY,
                    )
                    rows_written += 1 if created else 0
                    rows_skipped += 0 if created else 1

                # Write per-day installer breakdown
                for day, installers in daily_installers.items():
                    date = _parse_date(day)
                    metadata = PyPIInstallerBreakdown(installers=installers)
                    _, created = await self.upsert_metric(
                        metric_type=installer_type,
                        date=date,
                        value=float(len(installers)),
                        period=Periods.DAILY,
                        metadata=metadata.model_dump(),
                    )
                    rows_written += 1 if created else 0
                    rows_skipped += 0 if created else 1

                # Per-day country breakdown
                country_data = await self._query(
                    client,
                    f"""
                    SELECT date, country_code, sum(count) as downloads
                    FROM {FULL_TABLE}
                    WHERE project = '{package}' AND date >= today() - 14
                    GROUP BY date, country_code
                    ORDER BY date
                """,
                )

                daily_countries: dict[str, dict[str, int]] = {}
                for row in country_data:
                    day = row[0]
                    country = row[1] or "XX"
                    if day not in daily_countries:
                        daily_countries[day] = {}
                    daily_countries[day][country] = int(row[2])

                for day, countries in daily_countries.items():
                    date = _parse_date(day)
                    metadata = PyPICountryBreakdown(countries=countries)
                    _, created = await self.upsert_metric(
                        metric_type=country_type,
                        date=date,
                        value=float(len(countries)),
                        period=Periods.DAILY,
                        metadata=metadata.model_dump(),
                    )
                    rows_written += 1 if created else 0
                    rows_skipped += 0 if created else 1

                # Per-day version breakdown
                version_data = await self._query(
                    client,
                    f"""
                    SELECT date, version, sum(count) as downloads
                    FROM {FULL_TABLE}
                    WHERE project = '{package}' AND date >= today() - 14
                    GROUP BY date, version
                    ORDER BY date
                """,
                )

                daily_versions: dict[str, dict[str, int]] = {}
                for row in version_data:
                    day = row[0]
                    if day not in daily_versions:
                        daily_versions[day] = {}
                    daily_versions[day][row[1]] = int(row[2])

                for day, versions in daily_versions.items():
                    date = _parse_date(day)
                    metadata = PyPIDownloadMetadata(
                        versions={
                            v: PyPIVersionDetail(total=c) for v, c in versions.items()
                        }
                    )
                    _, created = await self.upsert_metric(
                        metric_type=version_type,
                        date=date,
                        value=float(len(versions)),
                        period=Periods.DAILY,
                        metadata=metadata.model_dump(),
                    )
                    rows_written += 1 if created else 0
                    rows_skipped += 0 if created else 1

                # Per-day distribution type breakdown
                type_data = await self._query(
                    client,
                    f"""
                    SELECT date, type, sum(count) as downloads
                    FROM {FULL_TABLE}
                    WHERE project = '{package}' AND date >= today() - 14
                    GROUP BY date, type
                    ORDER BY date
                """,
                )

                daily_types: dict[str, dict[str, int]] = {}
                for row in type_data:
                    day = row[0]
                    if day not in daily_types:
                        daily_types[day] = {}
                    daily_types[day][row[1]] = int(row[2])

                for day, types in daily_types.items():
                    date = _parse_date(day)
                    metadata = PyPITypeBreakdown(types=types)
                    _, created = await self.upsert_metric(
                        metric_type=dist_type,
                        date=date,
                        value=float(len(types)),
                        period=Periods.DAILY,
                        metadata=metadata.model_dump(),
                    )
                    rows_written += 1 if created else 0
                    rows_skipped += 0 if created else 1

            await self.db.commit()

            logger.info(
                "PyPI collected via ClickHouse: %d written, %d skipped, total=%d",
                rows_written,
                rows_skipped,
                total,
            )

            return CollectionResult(
                source_key=self.source_key,
                success=True,
                rows_written=rows_written,
                rows_skipped=rows_skipped,
            )

        except Exception as e:
            error_msg = f"PyPI collection failed: {e}"
            logger.error(error_msg, exc_info=True)
            return CollectionResult(
                source_key=self.source_key,
                success=False,
                rows_written=rows_written,
                rows_skipped=rows_skipped,
                error=error_msg,
            )

    async def _query(self, client: httpx.AsyncClient, sql: str) -> list[list]:
        """Execute a ClickHouse SQL query and return rows."""
        resp = await client.post(
            CLICKHOUSE_URL,
            params=CLICKHOUSE_PARAMS,
            content=sql.strip(),
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", [])


def _parse_date(date_str: str) -> datetime:
    """Parse YYYY-MM-DD date string to datetime."""
    return datetime.strptime(date_str, "%Y-%m-%d")


def _today() -> datetime:
    """Get today as a midnight datetime."""
    return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
