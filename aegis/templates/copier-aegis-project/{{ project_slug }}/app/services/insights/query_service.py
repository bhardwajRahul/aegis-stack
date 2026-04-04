"""
Sync query layer for insight metrics.

Centralizes all DB queries used by the Overseer dashboard tabs.
This will become the API endpoint layer when we migrate from direct DB access.
"""

from datetime import datetime, timedelta
from typing import Any

from app.core.db import SessionLocal
from sqlmodel import Session, select

from .constants import Periods
from .models import InsightEvent, InsightMetric, InsightMetricType, InsightSource


class InsightQueryService:
    """Sync query service for insight metrics. One session per service lifetime."""

    def __init__(self, session: Session | None = None) -> None:
        self.session = session or SessionLocal()
        self._owns_session = session is None
        self._type_cache: dict[str, InsightMetricType | None] = {}

    def close(self) -> None:
        if self._owns_session:
            self.session.close()

    def __enter__(self) -> "InsightQueryService":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    # -- metric type lookup (cached) ------------------------------------------

    def _get_type(self, key: str) -> InsightMetricType | None:
        if key not in self._type_cache:
            self._type_cache[key] = self.session.exec(
                select(InsightMetricType).where(InsightMetricType.key == key)
            ).first()
        return self._type_cache[key]

    # -- core queries ---------------------------------------------------------

    def get_daily(self, key: str, cutoff: datetime) -> list[InsightMetric]:
        """Fetch daily metrics for a key from cutoff date onward."""
        mt = self._get_type(key)
        if not mt:
            return []
        return list(
            self.session.exec(
                select(InsightMetric)
                .where(
                    InsightMetric.metric_type_id == mt.id,
                    InsightMetric.period == Periods.DAILY,
                    InsightMetric.date >= cutoff,
                )
                .order_by(InsightMetric.date.asc())
            ).all()
        )

    def get_daily_range(
        self, key: str, start: datetime, end: datetime
    ) -> list[InsightMetric]:
        """Fetch daily metrics between start (inclusive) and end (exclusive)."""
        mt = self._get_type(key)
        if not mt:
            return []
        return list(
            self.session.exec(
                select(InsightMetric).where(
                    InsightMetric.metric_type_id == mt.id,
                    InsightMetric.period == Periods.DAILY,
                    InsightMetric.date >= start,
                    InsightMetric.date < end,
                )
            ).all()
        )

    def get_latest(self, key: str) -> InsightMetric | None:
        """Fetch the most recent metric row for a key."""
        mt = self._get_type(key)
        if not mt:
            return None
        return self.session.exec(
            select(InsightMetric)
            .where(InsightMetric.metric_type_id == mt.id)
            .order_by(InsightMetric.date.desc())
            .limit(1)
        ).first()

    def get_events(self, key: str, cutoff: datetime) -> list[InsightMetric]:
        """Fetch event-period metrics for a key from cutoff onward."""
        mt = self._get_type(key)
        if not mt:
            return []
        return list(
            self.session.exec(
                select(InsightMetric)
                .where(
                    InsightMetric.metric_type_id == mt.id,
                    InsightMetric.period == Periods.EVENT,
                    InsightMetric.date >= cutoff,
                )
                .order_by(InsightMetric.date.desc())
            ).all()
        )

    def get_all_events(self, key: str) -> list[InsightMetric]:
        """Fetch all event-period metrics for a key (no date filter)."""
        mt = self._get_type(key)
        if not mt:
            return []
        return list(
            self.session.exec(
                select(InsightMetric)
                .where(
                    InsightMetric.metric_type_id == mt.id,
                    InsightMetric.period == Periods.EVENT,
                )
                .order_by(InsightMetric.date.asc())
            ).all()
        )

    def get_events_in_range(
        self, key: str, start: datetime, end: datetime
    ) -> list[InsightMetric]:
        """Fetch event-period metrics between start (inclusive) and end (exclusive)."""
        mt = self._get_type(key)
        if not mt:
            return []
        return list(
            self.session.exec(
                select(InsightMetric).where(
                    InsightMetric.metric_type_id == mt.id,
                    InsightMetric.period == Periods.EVENT,
                    InsightMetric.date >= start,
                    InsightMetric.date < end,
                )
            ).all()
        )

    def get_all_metrics(self, key: str) -> list[InsightMetric]:
        """Fetch all metrics for a key (any period, ordered by date desc)."""
        mt = self._get_type(key)
        if not mt:
            return []
        return list(
            self.session.exec(
                select(InsightMetric)
                .where(InsightMetric.metric_type_id == mt.id)
                .order_by(InsightMetric.date.desc())
            ).all()
        )

    def sum_range(self, key: str, start: datetime, end: datetime) -> int:
        """Sum daily metric values between start and end."""
        rows = self.get_daily_range(key, start, end)
        return sum(int(r.value) for r in rows)

    def sum_daily(self, key: str, cutoff: datetime) -> int:
        """Sum all daily metric values from cutoff onward."""
        rows = self.get_daily(key, cutoff)
        return sum(int(r.value) for r in rows)

    # -- insight events -------------------------------------------------------

    def get_insight_events(
        self,
        cutoff: datetime | None = None,
        type_filter: set[str] | None = None,
    ) -> list[InsightEvent]:
        """Fetch InsightEvent rows with optional date and type filters."""
        q = select(InsightEvent).order_by(InsightEvent.date.asc())
        events = list(self.session.exec(q).all())

        if cutoff:
            cutoff_str = str(cutoff.date())
            events = [ev for ev in events if str(ev.date)[:10] >= cutoff_str]

        if type_filter:
            events = [ev for ev in events if ev.event_type in type_filter]

        return events

    def get_recent_insight_events(self, limit: int = 15) -> list[InsightEvent]:
        """Fetch most recent InsightEvent rows."""
        return list(
            self.session.exec(
                select(InsightEvent).order_by(InsightEvent.date.desc()).limit(limit)
            ).all()
        )

    def get_milestone_events(self) -> list[InsightEvent]:
        """Fetch all milestone and feature events."""
        return list(
            self.session.exec(
                select(InsightEvent).where(
                    InsightEvent.event_type.in_(
                        ["milestone_github", "milestone_pypi", "feature"]
                    )
                )
            ).all()
        )

    def get_release_metrics(self) -> list[InsightMetric]:
        """Fetch release metric rows."""
        mt = self._get_type("releases")
        if not mt:
            return []
        q = select(InsightMetric).where(InsightMetric.metric_type_id == mt.id)
        return list(self.session.exec(q).all())

    # -- sources --------------------------------------------------------------

    def get_sources(self) -> list[InsightSource]:
        """Fetch all insight sources."""
        return list(self.session.exec(select(InsightSource)).all())

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
