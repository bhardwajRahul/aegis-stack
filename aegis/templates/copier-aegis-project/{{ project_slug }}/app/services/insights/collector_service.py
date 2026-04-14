"""
Collector service — orchestrates data collection across all enabled sources.
"""

import logging
from typing import Any

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from .collectors.base import BaseCollector, CollectionResult
from .collectors.github_events import GitHubEventsCollector
from .collectors.github_stars import GitHubStarsCollector
from .collectors.github_traffic import GitHubTrafficCollector
from .collectors.plausible import PlausibleCollector
from .collectors.pypi import PyPICollector
from .collectors.reddit import RedditCollector
from .constants import SourceKeys
from .models import InsightSource

logger = logging.getLogger(__name__)

# Registry of source_key → collector class
COLLECTOR_REGISTRY: dict[str, type[BaseCollector]] = {
    SourceKeys.GITHUB_TRAFFIC: GitHubTrafficCollector,
    SourceKeys.GITHUB_STARS: GitHubStarsCollector,
    SourceKeys.GITHUB_EVENTS: GitHubEventsCollector,
    SourceKeys.PYPI: PyPICollector,
    SourceKeys.PLAUSIBLE: PlausibleCollector,
    SourceKeys.REDDIT: RedditCollector,
}


class CollectorService:
    """Orchestrates data collection across all enabled sources."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def collect_all(self) -> dict[str, CollectionResult]:
        """Run all enabled collectors. Returns results keyed by source key."""
        results: dict[str, CollectionResult] = {}

        # Get enabled sources that have a registered collector
        stmt = select(InsightSource).where(InsightSource.enabled == True)  # noqa: E712
        result = await self.db.exec(stmt)
        enabled_sources = result.all()

        for source in enabled_sources:
            if source.key in COLLECTOR_REGISTRY:
                results[source.key] = await self._run_collector(source.key)
            else:
                logger.debug("No collector registered for source '%s'", source.key)

        return results

    async def collect_source(self, source_key: str, **kwargs: Any) -> CollectionResult:
        """Run a specific collector by source key."""
        if source_key not in COLLECTOR_REGISTRY:
            return CollectionResult(
                source_key=source_key,
                success=False,
                error=f"No collector registered for source '{source_key}'",
            )

        # Check if source is enabled
        stmt = select(InsightSource).where(InsightSource.key == source_key)
        result = await self.db.exec(stmt)
        source = result.first()

        if source is None:
            return CollectionResult(
                source_key=source_key,
                success=False,
                error=f"Source '{source_key}' not found in database",
            )

        if not source.enabled:
            return CollectionResult(
                source_key=source_key,
                success=False,
                error=f"Source '{source_key}' is disabled",
            )

        return await self._run_collector(source_key, **kwargs)

    async def _run_collector(self, source_key: str, **kwargs: Any) -> CollectionResult:
        """Instantiate and run a collector."""
        collector_cls = COLLECTOR_REGISTRY[source_key]
        collector = collector_cls(self.db)

        logger.info("Running collector for '%s'", source_key)

        try:
            result = await collector.collect(**kwargs)
            if result.success:
                # Update last_collected_at on the source
                from datetime import datetime

                stmt = select(InsightSource).where(InsightSource.key == source_key)
                source = (await self.db.exec(stmt)).first()
                if source:
                    source.last_collected_at = datetime.now()
                    self.db.add(source)
                    await self.db.commit()

                # Invalidate cached insights data
                from app.core.cache import cache

                cache.invalidate("insights:all")

                # Check for new records
                new_records = await self._check_records(source_key)
                result.records_broken = new_records

                logger.info(
                    "Collector '%s' completed: %d written, %d skipped",
                    source_key,
                    result.rows_written,
                    result.rows_skipped,
                )
            else:
                logger.warning(
                    "Collector '%s' failed: %s",
                    source_key,
                    result.error,
                )
            return result
        except Exception as e:
            error_msg = f"Collector '{source_key}' raised exception: {e}"
            logger.error(error_msg, exc_info=True)
            return CollectionResult(
                source_key=source_key,
                success=False,
                error=error_msg,
            )

    async def _check_records(self, source_key: str) -> list[str]:
        """Check if any metrics set new all-time records after collection. Returns list of broken record descriptions."""
        from datetime import datetime, timedelta

        from .models import InsightEvent, InsightMetric, InsightMetricType

        broken: list[str] = []

        # Define which metrics to track records for, per source
        record_checks: dict[str, list[dict[str, str]]] = {
            SourceKeys.GITHUB_TRAFFIC: [
                {
                    "key": "clones",
                    "category": "daily_clones",
                    "label": "GitHub 1-Day Clones",
                    "event_type": "milestone_github",
                },
                {
                    "key": "unique_cloners",
                    "category": "daily_unique",
                    "label": "GitHub 1-Day Unique",
                    "event_type": "milestone_github",
                },
                {
                    "key": "views",
                    "category": "daily_views",
                    "label": "GitHub 1-Day Views",
                    "event_type": "milestone_github",
                },
                {
                    "key": "unique_visitors",
                    "category": "daily_visitors",
                    "label": "GitHub 1-Day Visitors",
                    "event_type": "milestone_github",
                },
            ],
            SourceKeys.PYPI: [
                {
                    "key": "downloads_daily",
                    "category": "pypi_daily",
                    "label": "PyPI Best Single Day",
                    "event_type": "milestone_pypi",
                },
            ],
            SourceKeys.PLAUSIBLE: [
                {
                    "key": "visitors",
                    "category": "plausible_daily_visitors",
                    "label": "Docs 1-Day Visitors",
                    "event_type": "milestone_pypi",
                },
                {
                    "key": "pageviews",
                    "category": "plausible_daily_pageviews",
                    "label": "Docs 1-Day Pageviews",
                    "event_type": "milestone_pypi",
                },
            ],
        }

        checks = record_checks.get(source_key, [])
        if not checks:
            return broken

        now = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        for check in checks:
            mt = (
                await self.db.exec(
                    select(InsightMetricType).where(
                        InsightMetricType.key == check["key"]
                    )
                )
            ).first()
            if not mt:
                continue

            # Find the all-time max daily value
            result = await self.db.exec(
                select(InsightMetric.date, InsightMetric.value)
                .where(
                    InsightMetric.metric_type_id == mt.id,
                    InsightMetric.period == "daily",
                )
                .order_by(InsightMetric.value.desc())
                .limit(1)
            )
            top_row = result.first()
            if not top_row:
                continue

            record_date = str(top_row[0])[:10]
            record_value = int(top_row[1])

            if record_value == 0:
                continue

            # Check if we already have a milestone for this value or higher
            existing = (
                await self.db.exec(
                    select(InsightEvent).where(
                        InsightEvent.event_type == check["event_type"],
                    )
                )
            ).all()

            current_record = 0
            for ev in existing:
                meta = ev.metadata_ if isinstance(ev.metadata_, dict) else {}
                if meta.get("category") == check["category"]:
                    # Extract number from description
                    import re

                    numbers = re.findall(r"\d[\d,]*", ev.description)
                    for n in numbers:
                        val = int(n.replace(",", ""))
                        current_record = max(current_record, val)

            if record_value > current_record:
                # New record!
                desc = f"{record_value:,} ({check['label']})"
                event = InsightEvent(
                    date=datetime.strptime(record_date, "%Y-%m-%d"),
                    event_type=check["event_type"],
                    description=desc,
                    metadata_={"category": check["category"]},
                )
                self.db.add(event)
                await self.db.commit()
                broken.append(
                    f"{check['label']}: {record_value:,} (was {current_record:,})"
                )
                logger.info(
                    "New record: %s = %s on %s (prev: %s)",
                    check["label"],
                    record_value,
                    record_date,
                    current_record,
                )

        # Also check 14-day rolling records for GitHub traffic
        if source_key == SourceKeys.GITHUB_TRAFFIC:
            d14 = now - timedelta(days=14)
            rolling_checks = [
                {
                    "key": "clones",
                    "category": "14d_clones",
                    "label": "GitHub 14-Day Clones",
                    "event_type": "milestone_github",
                },
                {
                    "key": "unique_cloners",
                    "category": "14d_unique",
                    "label": "GitHub 14-Day Unique",
                    "event_type": "milestone_github",
                },
            ]
            for check in rolling_checks:
                mt = (
                    await self.db.exec(
                        select(InsightMetricType).where(
                            InsightMetricType.key == check["key"]
                        )
                    )
                ).first()
                if not mt:
                    continue

                rows = (
                    await self.db.exec(
                        select(InsightMetric).where(
                            InsightMetric.metric_type_id == mt.id,
                            InsightMetric.period == "daily",
                            InsightMetric.date >= d14,
                        )
                    )
                ).all()
                rolling_total = sum(int(r.value) for r in rows)

                if rolling_total == 0:
                    continue

                # Check existing record
                existing = (
                    await self.db.exec(
                        select(InsightEvent).where(
                            InsightEvent.event_type == check["event_type"],
                        )
                    )
                ).all()

                current_record = 0
                for ev in existing:
                    meta = ev.metadata_ if isinstance(ev.metadata_, dict) else {}
                    if meta.get("category") == check["category"]:
                        import re

                        numbers = re.findall(r"\d[\d,]*", ev.description)
                        for n in numbers:
                            val = int(n.replace(",", ""))
                            current_record = max(current_record, val)

                if rolling_total > current_record:
                    desc = f"{rolling_total:,} ({check['label']})"
                    event = InsightEvent(
                        date=now,
                        event_type=check["event_type"],
                        description=desc,
                        metadata_={"category": check["category"]},
                    )
                    self.db.add(event)
                    await self.db.commit()
                    broken.append(
                        f"{check['label']}: {rolling_total:,} (was {current_record:,})"
                    )
                    logger.info(
                        "New 14-day record: %s = %s (prev: %s)",
                        check["label"],
                        rolling_total,
                        current_record,
                    )

        return broken

    def get_registered_sources(self) -> list[str]:
        """Get list of source keys that have registered collectors."""
        return list(COLLECTOR_REGISTRY.keys())
