"""
Insight service database models.

Five tables:
- InsightSource: Lookup table for data sources (GitHub, PyPI, Plausible, Reddit)
- InsightMetricType: Lookup table for metric types, FK to source
- InsightMetric: Time-series data, FK to metric type, JSONB metadata
- InsightRecord: All-time records/milestones per metric type
- InsightEvent: Contextual markers (releases, posts, external events)
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Column, Index, String, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

# ---------------------------------------------------------------------------
# Lookup: InsightSource
# ---------------------------------------------------------------------------


class InsightSource(SQLModel, table=True):
    """Data source for insight collection (e.g., GitHub, PyPI, Plausible)."""

    __tablename__ = "insight_source"

    id: int | None = Field(default=None, primary_key=True)
    key: str = Field(unique=True, index=True, max_length=64)
    display_name: str = Field(max_length=128)
    collection_interval_hours: int | None = Field(default=None)
    requires_auth: bool = Field(default=False)
    enabled: bool = Field(default=True)
    last_collected_at: datetime | None = Field(default=None)
    metadata_: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column("metadata", JSON)
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None)
    )

    # Relationships
    metric_types: list["InsightMetricType"] = Relationship(back_populates="source")


# ---------------------------------------------------------------------------
# Lookup: InsightMetricType
# ---------------------------------------------------------------------------


class InsightMetricType(SQLModel, table=True):
    """Type of metric collected by a source (e.g., clones, unique_cloners)."""

    __tablename__ = "insight_metric_type"
    __table_args__ = (
        UniqueConstraint("source_id", "key", name="uq_metric_type_source_key"),
    )

    id: int | None = Field(default=None, primary_key=True)
    source_id: int = Field(foreign_key="insight_source.id", index=True)
    key: str = Field(index=True, max_length=64)
    display_name: str = Field(max_length=128)
    unit: str = Field(max_length=32)  # count, seconds, percentage, ratio, json
    metadata_: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column("metadata", JSON)
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None)
    )

    # Relationships
    source: InsightSource = Relationship(back_populates="metric_types")
    metrics: list["InsightMetric"] = Relationship(back_populates="metric_type")
    records: list["InsightRecord"] = Relationship(back_populates="metric_type")


# ---------------------------------------------------------------------------
# Time-series: InsightMetric
# ---------------------------------------------------------------------------


class InsightMetric(SQLModel, table=True):
    """Single metric data point. The core time-series table."""

    __tablename__ = "insight_metric"
    __table_args__ = (
        # THE primary query pattern: "get clones for last 14 days"
        Index("ix_insight_metric_type_date", "metric_type_id", "date"),
        # Secondary: "all metrics for this date"
        Index("ix_insight_metric_date", "date"),
    )

    id: int | None = Field(default=None, primary_key=True)
    date: datetime = Field(index=False)  # Covered by compound indexes above
    metric_type_id: int = Field(foreign_key="insight_metric_type.id", index=True)
    value: float = Field(default=0.0)
    period: str = Field(max_length=32)  # daily, cumulative, snapshot, event
    metadata_: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column("metadata", JSON)
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None)
    )

    # Relationships
    metric_type: InsightMetricType = Relationship(back_populates="metrics")


# ---------------------------------------------------------------------------
# Records: InsightRecord
# ---------------------------------------------------------------------------


class InsightRecord(SQLModel, table=True):
    """All-time record for a metric type. Updated in place when broken."""

    __tablename__ = "insight_record"

    id: int | None = Field(default=None, primary_key=True)
    metric_type_id: int = Field(
        foreign_key="insight_metric_type.id", unique=True, index=True
    )
    value: float = Field(default=0.0)
    date_achieved: datetime
    previous_value: float | None = Field(default=None)
    previous_date: datetime | None = Field(default=None)
    context: str | None = Field(default=None, max_length=512)
    metadata_: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column("metadata", JSON)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None)
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None)
    )

    # Relationships
    metric_type: InsightMetricType = Relationship(back_populates="records")


# ---------------------------------------------------------------------------
# Events: InsightEvent
# ---------------------------------------------------------------------------


class InsightEvent(SQLModel, table=True):
    """Contextual marker explaining why a metric changed."""

    __tablename__ = "insight_event"
    __table_args__ = (
        Index("ix_insight_event_date", "date"),
        Index("ix_insight_event_type_date", "event_type", "date"),
    )

    id: int | None = Field(default=None, primary_key=True)
    date: datetime
    event_type: str = Field(
        max_length=64, sa_column=Column("event_type", String(64), nullable=False)
    )  # reddit_post, release, localization, external
    description: str = Field(max_length=1024)
    metadata_: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column("metadata", JSON)
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None)
    )
