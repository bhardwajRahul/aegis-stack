"""
Query layer for insight metrics.

Centralizes all DB queries used by the Overseer dashboard and API endpoints.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from .constants import Periods
from .models import InsightEvent, InsightMetric, InsightMetricType, InsightSource
from .schemas import BulkInsightsResponse

# Metric keys grouped by query type
DAILY_KEYS = [
    "clones",
    "unique_cloners",
    "views",
    "unique_visitors",
    # GitHub's server-side 14-day rolling totals (one row per day).
    "clones_14d",
    "clones_14d_unique",
    "views_14d",
    "views_14d_unique",
    "star_events",
    "activity_summary",
    "downloads_daily",
    "downloads_daily_human",
    "downloads_by_installer",
    "downloads_by_country",
    "downloads_by_version",
    "downloads_by_type",
    "visitors",
    "pageviews",
    "avg_duration",
    "bounce_rate",
    "top_pages",
    "top_countries",
    "top_sources",
]
EVENT_KEYS = ["new_star", "forks", "releases", "post_stats"]
SNAPSHOT_KEYS = ["referrers", "popular_paths", "downloads_total"]


class InsightQueryService:
    """Async query service for insight metrics."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._type_cache: dict[str, InsightMetricType | None] = {}

    async def __aenter__(self) -> InsightQueryService:
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass  # Session lifecycle managed by caller (deps)

    # -- metric type lookup (cached) ------------------------------------------

    async def _get_type(self, key: str) -> InsightMetricType | None:
        if key not in self._type_cache:
            result = await self.session.exec(
                select(InsightMetricType).where(InsightMetricType.key == key)
            )
            self._type_cache[key] = result.first()
        return self._type_cache[key]

    # -- core queries ---------------------------------------------------------

    async def get_daily(self, key: str, cutoff: datetime) -> list[InsightMetric]:
        """Fetch daily metrics for a key from cutoff date onward."""
        mt = await self._get_type(key)
        if not mt:
            return []
        result = await self.session.exec(
            select(InsightMetric)
            .where(
                InsightMetric.metric_type_id == mt.id,
                InsightMetric.period == Periods.DAILY,
                InsightMetric.date >= cutoff,
            )
            .order_by(InsightMetric.date.asc())
        )
        return list(result.all())

    async def get_daily_range(
        self,
        key: str,
        start: datetime,
        end: datetime,
    ) -> list[InsightMetric]:
        """Fetch daily metrics between start (inclusive) and end (exclusive)."""
        mt = await self._get_type(key)
        if not mt:
            return []
        result = await self.session.exec(
            select(InsightMetric).where(
                InsightMetric.metric_type_id == mt.id,
                InsightMetric.period == Periods.DAILY,
                InsightMetric.date >= start,
                InsightMetric.date < end,
            )
        )
        return list(result.all())

    async def get_latest(self, key: str) -> InsightMetric | None:
        """Fetch the most recent metric row for a key."""
        mt = await self._get_type(key)
        if not mt:
            return None
        result = await self.session.exec(
            select(InsightMetric)
            .where(InsightMetric.metric_type_id == mt.id)
            .order_by(InsightMetric.date.desc())
            .limit(1)
        )
        return result.first()

    async def get_events(self, key: str, cutoff: datetime) -> list[InsightMetric]:
        """Fetch event-period metrics for a key from cutoff onward."""
        mt = await self._get_type(key)
        if not mt:
            return []
        result = await self.session.exec(
            select(InsightMetric)
            .where(
                InsightMetric.metric_type_id == mt.id,
                InsightMetric.period == Periods.EVENT,
                InsightMetric.date >= cutoff,
            )
            .order_by(InsightMetric.date.desc())
        )
        return list(result.all())

    async def get_all_events(self, key: str) -> list[InsightMetric]:
        """Fetch all event-period metrics for a key (no date filter)."""
        mt = await self._get_type(key)
        if not mt:
            return []
        result = await self.session.exec(
            select(InsightMetric)
            .where(
                InsightMetric.metric_type_id == mt.id,
                InsightMetric.period == Periods.EVENT,
            )
            .order_by(InsightMetric.date.asc())
        )
        return list(result.all())

    async def get_events_in_range(
        self,
        key: str,
        start: datetime,
        end: datetime,
    ) -> list[InsightMetric]:
        """Fetch event-period metrics between start (inclusive) and end (exclusive)."""
        mt = await self._get_type(key)
        if not mt:
            return []
        result = await self.session.exec(
            select(InsightMetric).where(
                InsightMetric.metric_type_id == mt.id,
                InsightMetric.period == Periods.EVENT,
                InsightMetric.date >= start,
                InsightMetric.date < end,
            )
        )
        return list(result.all())

    async def get_all_metrics(self, key: str) -> list[InsightMetric]:
        """Fetch all metrics for a key (any period, ordered by date desc)."""
        mt = await self._get_type(key)
        if not mt:
            return []
        result = await self.session.exec(
            select(InsightMetric)
            .where(InsightMetric.metric_type_id == mt.id)
            .order_by(InsightMetric.date.desc())
        )
        return list(result.all())

    async def sum_range(self, key: str, start: datetime, end: datetime) -> int:
        """Sum daily metric values between start and end."""
        rows = await self.get_daily_range(key, start, end)
        return sum(int(r.value) for r in rows)

    async def sum_daily(self, key: str, cutoff: datetime) -> int:
        """Sum all daily metric values from cutoff onward."""
        rows = await self.get_daily(key, cutoff)
        return sum(int(r.value) for r in rows)

    # -- insight events -------------------------------------------------------

    async def get_insight_events(
        self,
        cutoff: datetime | None = None,
        type_filter: set[str] | None = None,
    ) -> list[InsightEvent]:
        """Fetch InsightEvent rows with optional date and type filters."""
        result = await self.session.exec(
            select(InsightEvent).order_by(InsightEvent.date.asc())
        )
        events = list(result.all())

        if cutoff:
            cutoff_str = str(cutoff.date())
            events = [ev for ev in events if str(ev.date)[:10] >= cutoff_str]

        if type_filter:
            events = [ev for ev in events if ev.event_type in type_filter]

        return events

    async def get_recent_insight_events(self, limit: int = 15) -> list[InsightEvent]:
        """Fetch most recent InsightEvent rows."""
        result = await self.session.exec(
            select(InsightEvent).order_by(InsightEvent.date.desc()).limit(limit)
        )
        return list(result.all())

    async def get_milestone_events(self) -> list[InsightEvent]:
        """Fetch all milestone and feature events."""
        result = await self.session.exec(
            select(InsightEvent).where(
                InsightEvent.event_type.in_(
                    ["milestone_github", "milestone_pypi", "feature"]
                )
            )
        )
        return list(result.all())

    async def get_release_metrics(self) -> list[InsightMetric]:
        """Fetch release metric rows."""
        mt = await self._get_type("releases")
        if not mt:
            return []
        result = await self.session.exec(
            select(InsightMetric).where(InsightMetric.metric_type_id == mt.id)
        )
        return list(result.all())

    # -- sources --------------------------------------------------------------

    async def get_sources(self) -> list[InsightSource]:
        """Fetch all insight sources."""
        result = await self.session.exec(select(InsightSource))
        return list(result.all())

    # -- bulk loader ----------------------------------------------------------

    async def load_all(self) -> BulkInsightsResponse:
        """Bulk-load all insight data in the minimum number of queries.

        Previously this ran ~50 separate SELECTs (one per key to look up
        the metric_type, one per key to fetch its rows, plus `get_latest`
        for each snapshot). The fan-out was mechanical loop-iteration, not
        a data dependency — so we collapse it with `IN (...)` clauses:

            1. one SELECT for all metric_types we care about
            2. one SELECT for every daily metric across every daily key
            3. one SELECT for every event metric across every event key
            4. one SELECT for every snapshot metric; pick the latest per
               key in Python (portable across dialects, vs. DISTINCT ON)
            5. one SELECT for insight_events
            6. one SELECT for insight_sources

        Total: 6 round-trips regardless of how many keys the app tracks.
        """
        all_keys = DAILY_KEYS + EVENT_KEYS + SNAPSHOT_KEYS
        types_result = await self.session.exec(
            select(InsightMetricType).where(InsightMetricType.key.in_(all_keys))
        )
        types_by_key: dict[str, InsightMetricType] = {
            t.key: t for t in types_result.all()
        }
        # Warm the instance-level cache so subsequent `.get_daily()` / etc.
        # calls in this request skip the DB hit we just did.
        for k in all_keys:
            self._type_cache[k] = types_by_key.get(k)

        # Daily metrics — one query spanning every daily type.
        daily: dict[str, list[InsightMetric]] = {k: [] for k in DAILY_KEYS}
        daily_type_ids = [types_by_key[k].id for k in DAILY_KEYS if k in types_by_key]
        if daily_type_ids:
            result = await self.session.exec(
                select(InsightMetric)
                .where(
                    InsightMetric.metric_type_id.in_(daily_type_ids),
                    InsightMetric.period == Periods.DAILY,
                )
                .order_by(InsightMetric.date.asc())
            )
            id_to_key = {types_by_key[k].id: k for k in DAILY_KEYS if k in types_by_key}
            for m in result.all():
                daily[id_to_key[m.metric_type_id]].append(m)

        # Event metrics — one query.
        events: dict[str, list[InsightMetric]] = {k: [] for k in EVENT_KEYS}
        event_type_ids = [types_by_key[k].id for k in EVENT_KEYS if k in types_by_key]
        if event_type_ids:
            result = await self.session.exec(
                select(InsightMetric)
                .where(
                    InsightMetric.metric_type_id.in_(event_type_ids),
                    InsightMetric.period == Periods.EVENT,
                )
                .order_by(InsightMetric.date.asc())
            )
            id_to_key = {types_by_key[k].id: k for k in EVENT_KEYS if k in types_by_key}
            for m in result.all():
                events[id_to_key[m.metric_type_id]].append(m)

        # Snapshots — one query, desc by date, take the first row per key.
        latest: dict[str, InsightMetric | None] = dict.fromkeys(SNAPSHOT_KEYS)
        snapshot_type_ids = [
            types_by_key[k].id for k in SNAPSHOT_KEYS if k in types_by_key
        ]
        if snapshot_type_ids:
            result = await self.session.exec(
                select(InsightMetric)
                .where(InsightMetric.metric_type_id.in_(snapshot_type_ids))
                .order_by(InsightMetric.date.desc())
            )
            id_to_key = {
                types_by_key[k].id: k for k in SNAPSHOT_KEYS if k in types_by_key
            }
            for m in result.all():
                key = id_to_key[m.metric_type_id]
                if latest[key] is None:  # first iteration per key == latest date
                    latest[key] = m

        result = await self.session.exec(
            select(InsightEvent).order_by(InsightEvent.date.asc())
        )
        insight_events = list(result.all())

        result = await self.session.exec(select(InsightSource))
        sources = list(result.all())

        return BulkInsightsResponse(
            daily=daily,
            events=events,
            insight_events=insight_events,
            sources=sources,
            latest=latest,
        )

    # -- convenience: date helpers --------------------------------------------

    @staticmethod
    def compute_cutoffs(days: int) -> tuple[datetime, datetime]:
        """Compute current and previous period cutoff dates.

        Returns (cutoff, prev_cutoff) where:
        - cutoff = now - days
        - prev_cutoff = cutoff - days
        """
        now = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if days >= 9999:
            cutoff = datetime(2000, 1, 1)
            prev_cutoff = datetime(2000, 1, 1)
        else:
            cutoff = now - timedelta(days=days)
            prev_cutoff = cutoff - timedelta(days=days)
        return cutoff, prev_cutoff
