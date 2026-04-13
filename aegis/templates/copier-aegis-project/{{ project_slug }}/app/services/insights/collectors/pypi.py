"""
PyPI downloads collector via ClickHouse public SQL endpoint.

Collects download stats with full dimensional breakdowns:
country, installer, version, distribution type, and human vs bot.
No authentication required.
"""

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
from .base import BaseCollector, CollectionResult, clickhouse_query, parse_date, today

# Pre-aggregated table with all dimensions
FULL_TABLE = "pypi.pypi_downloads_per_day_by_version_by_installer_by_type_by_country"
DAILY_TABLE = "pypi.pypi_downloads_per_day"

# Known bot/mirror/scanner installers — NOT real humans
# Real humans use: pip, uv. Everything else is automated.
BOT_INSTALLERS = {
    "bandersnatch",  # PyPI mirror tool
    "z3c.pypimirror",  # PyPI mirror tool
    "Nexus",  # Sonatype artifact proxy
    "devpi",  # PyPI cache/proxy
    "pep381client",  # PyPI mirror client
    "requests",  # Scripts/automation
    "OS",  # OS-level package managers
    "Artifactory",  # JFrog artifact proxy
    "Browser",  # Automated security scanners downloading every version
    "",  # Empty user-agent = automated
}


class PyPICollector(BaseCollector):
    """Collects PyPI download stats from ClickHouse public dataset."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    @property
    def source_key(self) -> str:
        return SourceKeys.PYPI

    async def collect(self, lookback_days: int = 14) -> CollectionResult:
        """Collect daily totals + per-day dimensional breakdowns."""
        package = settings.INSIGHT_PYPI_PACKAGE

        if err := self._validate_config(INSIGHT_PYPI_PACKAGE=package):
            return err

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
                total_data = await clickhouse_query(
                    client,
                    f"""
                    SELECT sum(count) FROM {DAILY_TABLE}
                    WHERE project = '{package}'
                """,
                )
                total = int(total_data[0][0]) if total_data else 0

                _, created = await self.upsert_metric(
                    metric_type=total_type,
                    date=today(),
                    value=float(total),
                    period=Periods.CUMULATIVE,
                )
                rows_written += 1 if created else 0
                rows_skipped += 0 if created else 1

                # Per-day data with installer for human/bot split
                daily_installer_data = await clickhouse_query(
                    client,
                    f"""
                    SELECT date, installer, sum(count) as downloads
                    FROM {FULL_TABLE}
                    WHERE project = '{package}' AND date >= today() - {lookback_days}
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
                    date = parse_date(day)

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
                    date = parse_date(day)
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
                country_data = await clickhouse_query(
                    client,
                    f"""
                    SELECT date, country_code, sum(count) as downloads
                    FROM {FULL_TABLE}
                    WHERE project = '{package}' AND date >= today() - {lookback_days}
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
                    date = parse_date(day)
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

                # Per-day version breakdown with human/bot split
                version_data = await clickhouse_query(
                    client,
                    f"""
                    SELECT date, version,
                        sum(count) as total,
                        sumIf(count, installer NOT IN ('bandersnatch','z3c.pypimirror','Nexus','devpi','pep381client','requests','OS','Artifactory','Browser','')) as human
                    FROM {FULL_TABLE}
                    WHERE project = '{package}' AND date >= today() - {lookback_days}
                    GROUP BY date, version
                    ORDER BY date
                """,
                )

                daily_versions: dict[str, dict[str, PyPIVersionDetail]] = {}
                for row in version_data:
                    day = row[0]
                    ver = row[1]
                    if day not in daily_versions:
                        daily_versions[day] = {}
                    daily_versions[day][ver] = PyPIVersionDetail(
                        total=int(row[2]), human=int(row[3])
                    )

                for day, versions in daily_versions.items():
                    date = parse_date(day)
                    metadata = PyPIDownloadMetadata(versions=versions)
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
                type_data = await clickhouse_query(
                    client,
                    f"""
                    SELECT date, type, sum(count) as downloads
                    FROM {FULL_TABLE}
                    WHERE project = '{package}' AND date >= today() - {lookback_days}
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
                    date = parse_date(day)
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
            return self._success(rows_written, rows_skipped)

        except Exception as e:
            return self._error(
                f"PyPI collection failed: {e}", rows_written, rows_skipped
            )
