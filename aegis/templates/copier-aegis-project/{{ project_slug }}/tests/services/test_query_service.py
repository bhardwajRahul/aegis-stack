"""
Tests for InsightQueryService sync query layer.
"""

from datetime import datetime, timedelta

from app.services.insights.constants import MetricKeys, Periods, SourceKeys
from app.services.insights.models import (
    InsightEvent,
    InsightMetric,
    InsightMetricType,
    InsightSource,
)
from app.services.insights.query_service import InsightQueryService
from sqlmodel import Session

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_source(
    session: Session, key: str = SourceKeys.GITHUB_TRAFFIC
) -> InsightSource:
    source = InsightSource(
        key=key, display_name="Test Source", collection_interval_hours=6, enabled=True
    )
    session.add(source)
    session.flush()
    return source


def _seed_metric_type(
    session: Session,
    source: InsightSource,
    key: str = MetricKeys.CLONES,
    unit: str = "count",
) -> InsightMetricType:
    mt = InsightMetricType(
        source_id=source.id,  # type: ignore[arg-type]
        key=key,
        display_name=key.replace("_", " ").title(),
        unit=unit,
    )
    session.add(mt)
    session.flush()
    return mt


def _seed_metric(
    session: Session,
    metric_type: InsightMetricType,
    date: datetime,
    value: float,
    period: str = Periods.DAILY,
    metadata: dict | None = None,
) -> InsightMetric:
    metric = InsightMetric(
        date=date,
        metric_type_id=metric_type.id,  # type: ignore[arg-type]
        value=value,
        period=period,
    )
    if metadata:
        metric.metadata_ = metadata
    session.add(metric)
    session.flush()
    return metric


def _seed_event(
    session: Session,
    event_type: str,
    description: str,
    date: datetime | None = None,
    metadata: dict | None = None,
) -> InsightEvent:
    event = InsightEvent(
        date=date or datetime.now(),
        event_type=event_type,
        description=description,
    )
    if metadata:
        event.metadata_ = metadata
    session.add(event)
    session.flush()
    return event


# ---------------------------------------------------------------------------
# Tests: get_daily
# ---------------------------------------------------------------------------


class TestGetDaily:
    def test_returns_rows_after_cutoff(self, db_session: Session) -> None:
        source = _seed_source(db_session)
        mt = _seed_metric_type(db_session, source)

        now = datetime(2026, 4, 10)
        for i in range(5):
            _seed_metric(db_session, mt, now - timedelta(days=i), float(10 + i))

        qs = InsightQueryService(session=db_session)
        cutoff = now - timedelta(days=2)
        rows = qs.get_daily(MetricKeys.CLONES, cutoff)

        assert len(rows) == 3
        assert all(r.date >= cutoff for r in rows)

    def test_returns_empty_for_unknown_key(self, db_session: Session) -> None:
        qs = InsightQueryService(session=db_session)
        rows = qs.get_daily("nonexistent_key", datetime(2020, 1, 1))
        assert rows == []

    def test_ordering_is_ascending(self, db_session: Session) -> None:
        source = _seed_source(db_session)
        mt = _seed_metric_type(db_session, source)

        dates = [datetime(2026, 4, d) for d in [3, 1, 5, 2, 4]]
        for d in dates:
            _seed_metric(db_session, mt, d, 10.0)

        qs = InsightQueryService(session=db_session)
        rows = qs.get_daily(MetricKeys.CLONES, datetime(2026, 4, 1))

        result_dates = [r.date for r in rows]
        assert result_dates == sorted(result_dates)


# ---------------------------------------------------------------------------
# Tests: get_daily_range
# ---------------------------------------------------------------------------


class TestGetDailyRange:
    def test_includes_start_excludes_end(self, db_session: Session) -> None:
        source = _seed_source(db_session)
        mt = _seed_metric_type(db_session, source)

        for day in range(1, 6):
            _seed_metric(db_session, mt, datetime(2026, 4, day), float(day))

        qs = InsightQueryService(session=db_session)
        rows = qs.get_daily_range(
            MetricKeys.CLONES, datetime(2026, 4, 2), datetime(2026, 4, 4)
        )

        dates = {r.date for r in rows}
        assert datetime(2026, 4, 2) in dates
        assert datetime(2026, 4, 3) in dates
        assert datetime(2026, 4, 4) not in dates

    def test_empty_range(self, db_session: Session) -> None:
        source = _seed_source(db_session)
        mt = _seed_metric_type(db_session, source)
        _seed_metric(db_session, mt, datetime(2026, 4, 1), 10.0)

        qs = InsightQueryService(session=db_session)
        rows = qs.get_daily_range(
            MetricKeys.CLONES, datetime(2026, 5, 1), datetime(2026, 5, 10)
        )
        assert rows == []


# ---------------------------------------------------------------------------
# Tests: get_latest
# ---------------------------------------------------------------------------


class TestGetLatest:
    def test_returns_most_recent(self, db_session: Session) -> None:
        source = _seed_source(db_session)
        mt = _seed_metric_type(db_session, source)

        _seed_metric(db_session, mt, datetime(2026, 4, 1), 10.0)
        _seed_metric(db_session, mt, datetime(2026, 4, 5), 50.0)
        _seed_metric(db_session, mt, datetime(2026, 4, 3), 30.0)

        qs = InsightQueryService(session=db_session)
        latest = qs.get_latest(MetricKeys.CLONES)

        assert latest is not None
        assert latest.value == 50.0
        assert latest.date == datetime(2026, 4, 5)

    def test_returns_none_for_unknown(self, db_session: Session) -> None:
        qs = InsightQueryService(session=db_session)
        assert qs.get_latest("nonexistent") is None


# ---------------------------------------------------------------------------
# Tests: get_events / get_all_events / get_events_in_range
# ---------------------------------------------------------------------------


class TestGetEvents:
    def test_returns_event_period_rows(self, db_session: Session) -> None:
        source = _seed_source(db_session)
        mt = _seed_metric_type(db_session, source)

        _seed_metric(db_session, mt, datetime(2026, 4, 1), 10.0, Periods.DAILY)
        _seed_metric(db_session, mt, datetime(2026, 4, 1), 1.0, Periods.EVENT)
        _seed_metric(db_session, mt, datetime(2026, 4, 2), 2.0, Periods.EVENT)

        qs = InsightQueryService(session=db_session)
        events = qs.get_events(MetricKeys.CLONES, datetime(2026, 4, 1))

        assert len(events) == 2
        assert all(e.period == Periods.EVENT for e in events)

    def test_respects_cutoff(self, db_session: Session) -> None:
        source = _seed_source(db_session)
        mt = _seed_metric_type(db_session, source)

        _seed_metric(db_session, mt, datetime(2026, 3, 1), 1.0, Periods.EVENT)
        _seed_metric(db_session, mt, datetime(2026, 4, 5), 2.0, Periods.EVENT)

        qs = InsightQueryService(session=db_session)
        events = qs.get_events(MetricKeys.CLONES, datetime(2026, 4, 1))

        assert len(events) == 1
        assert events[0].date == datetime(2026, 4, 5)


class TestGetAllEvents:
    def test_returns_all_regardless_of_date(self, db_session: Session) -> None:
        source = _seed_source(db_session)
        mt = _seed_metric_type(db_session, source)

        _seed_metric(db_session, mt, datetime(2020, 1, 1), 1.0, Periods.EVENT)
        _seed_metric(db_session, mt, datetime(2026, 4, 1), 2.0, Periods.EVENT)

        qs = InsightQueryService(session=db_session)
        events = qs.get_all_events(MetricKeys.CLONES)

        assert len(events) == 2

    def test_ascending_order(self, db_session: Session) -> None:
        source = _seed_source(db_session)
        mt = _seed_metric_type(db_session, source)

        _seed_metric(db_session, mt, datetime(2026, 4, 5), 2.0, Periods.EVENT)
        _seed_metric(db_session, mt, datetime(2026, 4, 1), 1.0, Periods.EVENT)

        qs = InsightQueryService(session=db_session)
        events = qs.get_all_events(MetricKeys.CLONES)

        assert events[0].date < events[1].date


class TestGetEventsInRange:
    def test_includes_start_excludes_end(self, db_session: Session) -> None:
        source = _seed_source(db_session)
        mt = _seed_metric_type(db_session, source)

        _seed_metric(db_session, mt, datetime(2026, 4, 1), 1.0, Periods.EVENT)
        _seed_metric(db_session, mt, datetime(2026, 4, 3), 2.0, Periods.EVENT)
        _seed_metric(db_session, mt, datetime(2026, 4, 5), 3.0, Periods.EVENT)

        qs = InsightQueryService(session=db_session)
        events = qs.get_events_in_range(
            MetricKeys.CLONES, datetime(2026, 4, 1), datetime(2026, 4, 5)
        )

        assert len(events) == 2
        dates = {e.date for e in events}
        assert datetime(2026, 4, 1) in dates
        assert datetime(2026, 4, 3) in dates
        assert datetime(2026, 4, 5) not in dates


# ---------------------------------------------------------------------------
# Tests: get_all_metrics
# ---------------------------------------------------------------------------


class TestGetAllMetrics:
    def test_returns_all_periods(self, db_session: Session) -> None:
        source = _seed_source(db_session)
        mt = _seed_metric_type(db_session, source)

        _seed_metric(db_session, mt, datetime(2026, 4, 1), 10.0, Periods.DAILY)
        _seed_metric(db_session, mt, datetime(2026, 4, 1), 1.0, Periods.EVENT)

        qs = InsightQueryService(session=db_session)
        metrics = qs.get_all_metrics(MetricKeys.CLONES)

        assert len(metrics) == 2
        periods = {m.period for m in metrics}
        assert Periods.DAILY in periods
        assert Periods.EVENT in periods

    def test_descending_order(self, db_session: Session) -> None:
        source = _seed_source(db_session)
        mt = _seed_metric_type(db_session, source)

        _seed_metric(db_session, mt, datetime(2026, 4, 1), 1.0)
        _seed_metric(db_session, mt, datetime(2026, 4, 5), 5.0)

        qs = InsightQueryService(session=db_session)
        metrics = qs.get_all_metrics(MetricKeys.CLONES)

        assert metrics[0].date > metrics[1].date


# ---------------------------------------------------------------------------
# Tests: sum_range / sum_daily
# ---------------------------------------------------------------------------


class TestSumRange:
    def test_sums_values_in_range(self, db_session: Session) -> None:
        source = _seed_source(db_session)
        mt = _seed_metric_type(db_session, source)

        _seed_metric(db_session, mt, datetime(2026, 4, 1), 10.0)
        _seed_metric(db_session, mt, datetime(2026, 4, 2), 20.0)
        _seed_metric(db_session, mt, datetime(2026, 4, 3), 30.0)
        _seed_metric(db_session, mt, datetime(2026, 4, 4), 40.0)

        qs = InsightQueryService(session=db_session)
        total = qs.sum_range(
            MetricKeys.CLONES, datetime(2026, 4, 2), datetime(2026, 4, 4)
        )

        assert total == 50  # 20 + 30

    def test_zero_for_empty_range(self, db_session: Session) -> None:
        qs = InsightQueryService(session=db_session)
        total = qs.sum_range("nonexistent", datetime(2026, 1, 1), datetime(2026, 1, 2))
        assert total == 0


class TestSumDaily:
    def test_sums_from_cutoff(self, db_session: Session) -> None:
        source = _seed_source(db_session)
        mt = _seed_metric_type(db_session, source)

        _seed_metric(db_session, mt, datetime(2026, 3, 1), 100.0)  # before cutoff
        _seed_metric(db_session, mt, datetime(2026, 4, 1), 10.0)
        _seed_metric(db_session, mt, datetime(2026, 4, 2), 20.0)
        _seed_metric(db_session, mt, datetime(2026, 4, 3), 30.0)

        qs = InsightQueryService(session=db_session)
        total = qs.sum_daily(MetricKeys.CLONES, datetime(2026, 4, 1))

        assert total == 60  # 10 + 20 + 30 (excludes 100)


# ---------------------------------------------------------------------------
# Tests: InsightEvent queries
# ---------------------------------------------------------------------------


class TestInsightEvents:
    def test_returns_all_when_no_filters(self, db_session: Session) -> None:
        _seed_event(db_session, "release", "v1.0", datetime(2026, 4, 1))
        _seed_event(db_session, "star", "Star #50", datetime(2026, 4, 2))
        _seed_event(db_session, "reddit_post", "NWN post", datetime(2026, 4, 3))

        qs = InsightQueryService(session=db_session)
        events = qs.get_insight_events()

        assert len(events) == 3

    def test_filters_by_type(self, db_session: Session) -> None:
        _seed_event(db_session, "release", "v1.0", datetime(2026, 4, 1))
        _seed_event(db_session, "star", "Star #50", datetime(2026, 4, 2))
        _seed_event(db_session, "reddit_post", "NWN post", datetime(2026, 4, 3))

        qs = InsightQueryService(session=db_session)
        events = qs.get_insight_events(type_filter={"release", "star"})

        assert len(events) == 2
        types = {e.event_type for e in events}
        assert types == {"release", "star"}

    def test_filters_by_cutoff(self, db_session: Session) -> None:
        _seed_event(db_session, "release", "old", datetime(2026, 3, 1))
        _seed_event(db_session, "release", "new", datetime(2026, 4, 5))

        qs = InsightQueryService(session=db_session)
        events = qs.get_insight_events(cutoff=datetime(2026, 4, 1))

        assert len(events) == 1
        assert events[0].description == "new"

    def test_combined_filters(self, db_session: Session) -> None:
        _seed_event(db_session, "release", "old release", datetime(2026, 3, 1))
        _seed_event(db_session, "release", "new release", datetime(2026, 4, 5))
        _seed_event(db_session, "star", "new star", datetime(2026, 4, 5))

        qs = InsightQueryService(session=db_session)
        events = qs.get_insight_events(
            cutoff=datetime(2026, 4, 1), type_filter={"release"}
        )

        assert len(events) == 1
        assert events[0].description == "new release"


class TestGetRecentInsightEvents:
    def test_returns_limited_results(self, db_session: Session) -> None:
        for i in range(20):
            _seed_event(
                db_session,
                "star",
                f"Star #{i}",
                datetime(2026, 4, 1) + timedelta(hours=i),
            )

        qs = InsightQueryService(session=db_session)
        events = qs.get_recent_insight_events(limit=5)

        assert len(events) == 5


class TestGetMilestoneEvents:
    def test_returns_milestones_and_features(self, db_session: Session) -> None:
        _seed_event(
            db_session, "milestone_github", "New ATH: 100 clones", datetime(2026, 4, 1)
        )
        _seed_event(
            db_session, "milestone_pypi", "New ATH: 50 downloads", datetime(2026, 4, 2)
        )
        _seed_event(db_session, "feature", "Added Mandarin CLI", datetime(2026, 4, 3))
        _seed_event(db_session, "release", "v0.6.9", datetime(2026, 4, 4))
        _seed_event(db_session, "star", "Star #100", datetime(2026, 4, 5))

        qs = InsightQueryService(session=db_session)
        milestones = qs.get_milestone_events()

        assert len(milestones) == 3
        types = {m.event_type for m in milestones}
        assert types == {"milestone_github", "milestone_pypi", "feature"}


# ---------------------------------------------------------------------------
# Tests: get_release_metrics / get_sources
# ---------------------------------------------------------------------------


class TestGetReleaseMetrics:
    def test_returns_release_rows(self, db_session: Session) -> None:
        source = _seed_source(db_session)
        releases_mt = _seed_metric_type(db_session, source, "releases")
        other_mt = _seed_metric_type(db_session, source, MetricKeys.CLONES)

        _seed_metric(
            db_session,
            releases_mt,
            datetime(2026, 4, 1),
            1.0,
            metadata={"tag": "v0.6.9"},
        )
        _seed_metric(db_session, other_mt, datetime(2026, 4, 1), 100.0)

        qs = InsightQueryService(session=db_session)
        releases = qs.get_release_metrics()

        assert len(releases) == 1
        assert releases[0].metadata_.get("tag") == "v0.6.9"


class TestGetSources:
    def test_returns_all_sources(self, db_session: Session) -> None:
        _seed_source(db_session, SourceKeys.GITHUB_TRAFFIC)
        _seed_source(db_session, SourceKeys.PYPI)

        qs = InsightQueryService(session=db_session)
        sources = qs.get_sources()

        assert len(sources) == 2
        keys = {s.key for s in sources}
        assert SourceKeys.GITHUB_TRAFFIC in keys
        assert SourceKeys.PYPI in keys


# ---------------------------------------------------------------------------
# Tests: compute_cutoffs
# ---------------------------------------------------------------------------


class TestComputeCutoffs:
    def test_normal_days(self) -> None:
        cutoff, prev_cutoff = InsightQueryService.compute_cutoffs(14)

        now = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        expected_cutoff = now - timedelta(days=14)
        expected_prev = expected_cutoff - timedelta(days=14)

        assert cutoff == expected_cutoff
        assert prev_cutoff == expected_prev

    def test_all_time(self) -> None:
        cutoff, prev_cutoff = InsightQueryService.compute_cutoffs(9999)

        assert cutoff == datetime(2000, 1, 1)
        assert prev_cutoff == datetime(2000, 1, 1)


# ---------------------------------------------------------------------------
# Tests: Type caching
# ---------------------------------------------------------------------------


class TestTypeCaching:
    def test_caches_type_lookups(self, db_session: Session) -> None:
        source = _seed_source(db_session)
        _seed_metric_type(db_session, source)

        qs = InsightQueryService(session=db_session)

        # First call populates cache
        result1 = qs._get_type(MetricKeys.CLONES)
        assert result1 is not None

        # Second call returns cached value
        result2 = qs._get_type(MetricKeys.CLONES)
        assert result2 is result1  # Same object (from cache, not re-queried)

        # Cache stores None for missing keys too
        result3 = qs._get_type("nonexistent")
        assert result3 is None
        assert "nonexistent" in qs._type_cache
