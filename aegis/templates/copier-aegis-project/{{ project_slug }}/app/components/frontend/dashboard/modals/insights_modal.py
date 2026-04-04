"""
Insights Service Detail Modal

Tabbed modal showing adoption metrics across all data sources.
All tabs pull real data from the database via _load_db().
"""

from __future__ import annotations

from typing import Any

import flet as ft
from app.components.frontend.controls import (
    BodyText,
    H3Text,
    LabelText,
    SecondaryText,
)
from app.components.frontend.theme import AegisTheme as Theme
from app.services.system.models import ComponentStatus
from app.services.system.ui import get_component_subtitle, get_component_title

from ..cards.card_utils import get_status_detail
from .base_detail_popup import BaseDetailPopup
from .modal_sections import MetricCard, MilestoneCard, PieChartCard

# Event type → chip border/highlight color
EVENT_TYPE_COLORS: dict[str, str] = {
    "release": "#22C55E",
    "fork": "#A855F7",
    "star": "#F59E0B",
    "reddit_post": "#FF5722",
    "localization": "#3B82F6",
    "feature": "#06B6D4",
    "milestone_github": "#EC4899",
    "milestone_pypi": "#EC4899",
    "anomaly_github": "#EF4444",
    "external": "#9CA3AF",
}

# Shared date range options for all tabs
RANGE_OPTIONS = [
    ("7d", 7),
    ("14d", 14),
    ("1m", 30),
    ("3m", 90),
    ("6m", 180),
    ("1y", 365),
    ("All", 9999),
]

# Event types relevant to each tab
GITHUB_EVENT_TYPES = {
    "release",
    "fork",
    "star",
    "feature",
    "milestone_github",
    "anomaly_github",
    "localization",
    "external",
}
PYPI_EVENT_TYPES = {
    "release",
    "reddit_post",
    "star",
    "feature",
    "milestone_pypi",
    "localization",
    "external",
}
DOCS_EVENT_TYPES = {
    "release",
    "reddit_post",
    "star",
    "feature",
    "localization",
    "external",
}

# Milestone category config (for Overview trophy cards)
CATEGORY_CONFIG: dict[str, dict[str, str]] = {
    "daily_clones": {"label": "GitHub 1-Day Clones", "color": "#2563eb"},
    "daily_unique": {"label": "GitHub 1-Day Unique", "color": "#A855F7"},
    "daily_views": {"label": "GitHub 1-Day Views", "color": "#22C55E"},
    "daily_visitors": {"label": "GitHub 1-Day Visitors", "color": "#F59E0B"},
    "14d_clones": {"label": "GitHub 14-Day Clones", "color": "#06B6D4"},
    "14d_unique": {"label": "GitHub 14-Day Unique", "color": "#EC4899"},
    "14d_visitors": {"label": "GitHub 14-Day Visitors", "color": "#F97316"},
    "pypi_daily": {"label": "PyPI Best Single Day", "color": "#EF4444"},
    "plausible_daily_visitors": {"label": "Docs 1-Day Visitors", "color": "#6366F1"},
    "plausible_daily_pageviews": {"label": "Docs 1-Day Pageviews", "color": "#22C55E"},
}

# Event type to status mapping (for activity feed dot colors)
EVENT_STATUS_MAP: dict[str, str] = {
    "release": "success",
    "star": "warning",
    "reddit_post": "info",
    "milestone_github": "warning",
    "milestone_pypi": "warning",
    "feature": "info",
    "anomaly_github": "error",
    "external": "info",
}


def _pct(current: float, previous: float) -> float | None:
    """Compute period-over-period percentage change."""
    if previous > 0:
        return (current - previous) / previous * 100
    return 100.0 if current > 0 else None


def _make_line_chart(
    data_series: list,
    max_y: float,
    daily: list[dict],
    step: int,
    min_y: float = 0,
    height: int = 350,
) -> ft.LineChart:
    """Build a standard line chart with shared tooltip/grid/border config."""
    return ft.LineChart(
        data_series=data_series,
        left_axis=ft.ChartAxis(labels_size=50, labels_interval=step),
        bottom_axis=ft.ChartAxis(
            labels_size=50,
            labels=[
                ft.ChartAxisLabel(
                    value=i,
                    label=ft.Text(
                        d["date"][-5:], size=9, color=ft.Colors.ON_SURFACE_VARIANT
                    ),
                )
                for i, d in enumerate(daily)
                if i % max(1, len(daily) // 8) == 0 or i == len(daily) - 1
            ],
        ),
        horizontal_grid_lines=ft.ChartGridLines(
            interval=step,
            color=ft.Colors.with_opacity(0.08, ft.Colors.ON_SURFACE),
            width=1,
        ),
        tooltip_bgcolor=Theme.Colors.SURFACE_1,
        tooltip_rounded_radius=8,
        tooltip_padding=10,
        tooltip_max_content_width=200,
        tooltip_tooltip_border_side=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
        tooltip_fit_inside_vertically=True,
        tooltip_fit_inside_horizontally=True,
        tooltip_show_on_top_of_chart_box_area=True,
        point_line_start=0,
        point_line_end=float("inf"),
        border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
        interactive=True,
        min_y=min_y,
        max_y=max_y,
        min_x=0,
        max_x=len(daily) - 1,
        height=height,
        expand=True,
    )


def _make_legend(items: list[tuple[str, str]]) -> ft.Row:
    """Build chart legend. items = [(color, label), ...]"""
    return ft.Row(
        [
            ft.Row(
                [
                    ft.Container(width=10, height=10, bgcolor=color, border_radius=5),
                    SecondaryText(label, size=Theme.Typography.BODY_SMALL),
                ],
                spacing=4,
            )
            for color, label in items
        ],
        spacing=16,
        alignment=ft.MainAxisAlignment.CENTER,
    )


# ---------------------------------------------------------------------------
# Base class for interactive insight tabs
# ---------------------------------------------------------------------------


class InsightsTab(ft.Container):
    """Base class for insight tabs with date range chips, events toggle, and rebuild pattern."""

    _default_days: int = 7  # Override in subclass

    def __init__(self) -> None:
        super().__init__()

        self._days = self._default_days
        self._data = self._load_data(self._days)
        self._show_events = False
        self._highlighted_dates: set[str] = set()
        self._content_column = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO)

        self._events_toggle = ft.Switch(
            label="Show events",
            value=False,
            on_change=self._on_events_toggle,
            label_style=ft.TextStyle(size=12, color=ft.Colors.ON_SURFACE_VARIANT),
        )

        self._range_chips = ft.Row(
            [
                ft.Container(
                    content=ft.Text(
                        label,
                        size=11,
                        weight=ft.FontWeight.W_600
                        if days == self._days
                        else ft.FontWeight.W_400,
                        color=ft.Colors.ON_SURFACE
                        if days == self._days
                        else ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    bgcolor=Theme.Colors.SURFACE_2 if days == self._days else None,
                    border=ft.border.all(1, ft.Colors.ON_SURFACE)
                    if days == self._days
                    else ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
                    border_radius=12,
                    padding=ft.padding.symmetric(horizontal=10, vertical=4),
                    on_click=lambda e, d=days: self._on_range_change(d),
                    ink=True,
                )
                for label, days in RANGE_OPTIONS
            ],
            spacing=6,
        )

        self._build_content()

        self.content = self._content_column
        self.padding = ft.padding.only(
            left=Theme.Spacing.MD,
            top=Theme.Spacing.MD,
            bottom=Theme.Spacing.MD,
            right=Theme.Spacing.LG + 8,
        )
        self.expand = True

    def _on_events_toggle(self, e: ft.ControlEvent) -> None:
        self._show_events = e.control.value
        self._highlighted_dates = set()
        self._build_content()
        self._content_column.update()

    def _on_event_click(self, dates: set[str]) -> None:
        if self._highlighted_dates == dates:
            self._highlighted_dates = set()
        else:
            self._highlighted_dates = dates
        self._build_content()
        self._content_column.update()

    def _on_range_change(self, days: int) -> None:
        self._days = days
        self._data = self._load_data(days)

        for i, (_label, d) in enumerate(RANGE_OPTIONS):
            chip = self._range_chips.controls[i]
            is_active = d == days
            chip.bgcolor = Theme.Colors.SURFACE_2 if is_active else None
            chip.border = (
                ft.border.all(1, ft.Colors.ON_SURFACE)
                if is_active
                else ft.border.all(1, ft.Colors.OUTLINE_VARIANT)
            )
            chip.content.weight = (
                ft.FontWeight.W_600 if is_active else ft.FontWeight.W_400
            )
            chip.content.color = (
                ft.Colors.ON_SURFACE if is_active else ft.Colors.ON_SURFACE_VARIANT
            )

        self._build_content()
        self._content_column.update()

    def _build_content(self) -> None:
        """Override in subclass to build tab-specific content."""
        raise NotImplementedError

    @staticmethod
    def _load_data(days: int = 14) -> dict[str, Any]:
        """Override in subclass to load tab-specific data."""
        raise NotImplementedError

    def _make_filter_bar(
        self, last_updated: str = "", extra_controls: list[ft.Control] | None = None
    ) -> ft.Row:
        """Build the standard filter bar with range chips, last updated, and events toggle."""
        right_items: list[ft.Control] = []
        if last_updated:
            right_items.append(
                SecondaryText(
                    f"Last updated: {last_updated}", size=Theme.Typography.BODY_SMALL
                )
            )
        right_items.append(self._events_toggle)
        if extra_controls:
            right_items.extend(extra_controls)
        return ft.Row(
            [self._range_chips, ft.Row(right_items, spacing=Theme.Spacing.MD)],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

    def _render_event_chips(
        self,
        all_events: list[tuple[str, str, str]],
        valid_dates: set[str] | None = None,
        exclude_types: set[str] | None = None,
    ) -> ft.Control | None:
        """Render grouped event chips. Returns Row control or None."""
        if not self._show_events:
            return None

        if exclude_types:
            all_events = [
                (d, lbl, t) for d, lbl, t in all_events if t not in exclude_types
            ]
        if valid_dates is not None:
            all_events = [(d, lbl, t) for d, lbl, t in all_events if d in valid_dates]

        grouped = _group_events(all_events, self._days)
        if not grouped:
            return None

        highlighted = self._highlighted_dates
        return ft.Row(
            [
                ft.Container(
                    content=ft.Text(
                        f"{label}  {date[-5:]}",
                        size=Theme.Typography.BODY_SMALL,
                        weight=ft.FontWeight.W_600,
                        selectable=False,
                    ),
                    bgcolor=EVENT_TYPE_COLORS.get(etype, Theme.Colors.SURFACE_2)
                    if dates_set & highlighted
                    else Theme.Colors.SURFACE_2,
                    border=ft.border.all(
                        2 if dates_set & highlighted else 1,
                        EVENT_TYPE_COLORS.get(etype, ft.Colors.OUTLINE_VARIANT),
                    ),
                    border_radius=10,
                    padding=ft.padding.symmetric(horizontal=8, vertical=3),
                    on_click=lambda e, ds=dates_set: self._on_event_click(ds),
                    ink=True,
                )
                for date, label, etype, dates_set in grouped
            ],
            spacing=6,
            wrap=True,
        )


# ---------------------------------------------------------------------------
# Shared DB loader
# ---------------------------------------------------------------------------


def _load_db() -> dict[str, Any]:
    """Load all insight data from the database in one session.

    Returns a dict with keys consumed by every tab:
        traffic_daily   - list[dict] with keys date, clones, unique_cloners, views, unique_visitors
        referrers       - list[dict] with keys domain, views, uniques
        popular_paths   - list[dict] with keys path, views, uniques
        stars_total     - int
        stars_recent    - list[dict] latest 10 new_star events (username, location, company, date)
        star_countries  - dict[str, int] country -> count
        sources         - list[dict] enabled source statuses
        pypi_total      - int
    """
    from app.services.insights.query_service import InsightQueryService

    with InsightQueryService() as qs:
        cutoff_14d, _ = qs.compute_cutoffs(14)

        # -- github_traffic ---------------------------------------------------

        clones_rows = qs.get_daily("clones", cutoff_14d)
        unique_rows = qs.get_daily("unique_cloners", cutoff_14d)
        views_rows = qs.get_daily("views", cutoff_14d)
        visitors_rows = qs.get_daily("unique_visitors", cutoff_14d)

        unique_map = {str(r.date)[:10]: int(r.value) for r in unique_rows}
        views_map = {str(r.date)[:10]: int(r.value) for r in views_rows}
        visitors_map = {str(r.date)[:10]: int(r.value) for r in visitors_rows}

        traffic_daily: list[dict[str, Any]] = []
        for r in clones_rows:
            day = str(r.date)[:10]
            traffic_daily.append(
                {
                    "date": day,
                    "clones": int(r.value),
                    "unique_cloners": unique_map.get(day, 0),
                    "views": views_map.get(day, 0),
                    "unique_visitors": visitors_map.get(day, 0),
                }
            )

        # Referrers from latest referrers metric
        referrers_row = qs.get_latest("referrers")
        referrers: list[dict[str, Any]] = []
        if referrers_row and referrers_row.metadata_:
            meta = referrers_row.metadata_
            if isinstance(meta, dict) and not meta.get("referrers"):
                for domain, counts in meta.items():
                    if isinstance(counts, dict):
                        referrers.append(
                            {
                                "domain": domain,
                                "views": counts.get("views", 0),
                                "uniques": counts.get("uniques", 0),
                            }
                        )
            else:
                for ref in meta.get("referrers", []):
                    referrers.append(
                        {
                            "domain": ref.get("referrer", ref.get("domain", "unknown")),
                            "views": ref.get("count", ref.get("views", 0)),
                            "uniques": ref.get("uniques", 0),
                        }
                    )
            referrers.sort(key=lambda x: -x["views"])

        # Popular paths from latest popular_paths metric
        paths_row = qs.get_latest("popular_paths")
        popular_paths: list[dict[str, Any]] = []
        if paths_row and paths_row.metadata_:
            for p in paths_row.metadata_.get("popular_paths", []):
                popular_paths.append(
                    {
                        "path": p.get("path", "unknown"),
                        "views": p.get("count", p.get("views", 0)),
                        "uniques": p.get("uniques", 0),
                    }
                )

        # -- github_stars -----------------------------------------------------

        star_events = qs.get_all_events("new_star")
        stars_total = len(star_events)

        stars_recent: list[dict[str, Any]] = []
        star_countries: dict[str, int] = {}
        for ev in star_events:
            meta = ev.metadata_ or {}
            country = meta.get("location", "Unknown")
            if country and country != "Unknown":
                parts = [p.strip() for p in country.split(",")]
                country_key = parts[-1] if parts else "Unknown"
            else:
                country_key = "Unknown"
            star_countries[country_key] = star_countries.get(country_key, 0) + 1

            if len(stars_recent) < 10:
                stars_recent.append(
                    {
                        "username": meta.get("username", "unknown"),
                        "location": meta.get("location", ""),
                        "company": meta.get("company", ""),
                        "date": str(ev.date)[:10],
                    }
                )

        star_countries = dict(sorted(star_countries.items(), key=lambda x: -x[1]))

        # -- sources ----------------------------------------------------------

        sources = [
            {
                "key": s.key,
                "display_name": s.display_name,
                "enabled": s.enabled,
            }
            for s in qs.get_sources()
        ]

        # -- pypi_total -------------------------------------------------------

        pypi_total_row = qs.get_latest("downloads_total")
        pypi_total = int(pypi_total_row.value) if pypi_total_row else 0

        return {
            "traffic_daily": traffic_daily,
            "referrers": referrers,
            "popular_paths": popular_paths,
            "stars_total": stars_total,
            "stars_recent": stars_recent,
            "star_countries": star_countries,
            "sources": sources,
            "pypi_total": pypi_total,
        }


# ---------------------------------------------------------------------------
# Tab 1: Overview
# ---------------------------------------------------------------------------


class OverviewTab(ft.Container):
    """Overview: key metrics, milestones, recent events, source status."""

    def __init__(self, metadata: dict[str, Any], db: dict[str, Any]) -> None:
        super().__init__()

        daily = db["traffic_daily"]

        # Compute rolling 14d totals
        total_clones = sum(d["clones"] for d in daily)
        total_unique = sum(d["unique_cloners"] for d in daily)
        total_views = sum(d["views"] for d in daily)

        # Compute previous 14d for change arrows + load milestones/events
        from datetime import datetime, timedelta

        from app.services.insights.query_service import InsightQueryService

        stars_total = db["stars_total"]

        with InsightQueryService() as qs:
            now = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            d14 = now - timedelta(days=14)
            d28 = now - timedelta(days=28)

            prev_clones = qs.sum_range("clones", d28, d14)
            prev_unique = qs.sum_range("unique_cloners", d28, d14)
            prev_views = qs.sum_range("views", d28, d14)

            pypi_14d = qs.sum_range("downloads_daily", d14, now + timedelta(days=1))
            pypi_prev14d = qs.sum_range("downloads_daily", d28, d14)

            recent_stars = len(qs.get_events("new_star", d14))
            prev_star_count = len(qs.get_events_in_range("new_star", d28, d14))

            # Milestones - highest value per category (ATH per record type)
            best_per_category: dict[str, dict[str, Any]] = {}
            for ev in qs.get_milestone_events():
                meta = ev.metadata_ if isinstance(ev.metadata_, dict) else {}
                category = meta.get("category", ev.description)

                hero_str = (
                    _extract_max_number(ev.description)
                    if ev.event_type != "feature"
                    else ""
                )
                value = int(hero_str.replace(",", "")) if hero_str else 0

                existing = best_per_category.get(category)
                if existing is None or value > existing.get("_value", 0):
                    best_per_category[category] = {
                        "date": str(ev.date)[:10],
                        "description": ev.description,
                        "type": ev.event_type,
                        "metadata": meta,
                        "_value": value,
                    }

            milestones = sorted(
                best_per_category.values(), key=lambda m: m["date"], reverse=True
            )

            # Recent events of all types
            recent_events: list[dict[str, Any]] = []
            for ev in qs.get_insight_events():
                meta = ev.metadata_ if isinstance(ev.metadata_, dict) else {}
                recent_events.append(
                    {
                        "date": str(ev.date)[:10],
                        "description": ev.description,
                        "type": ev.event_type,
                        "metadata": meta,
                    }
                )

            # Also add releases from metric rows
            for r in qs.get_release_metrics():
                meta = r.metadata_ or {}
                tag = meta.get("tag", "")
                if tag:
                    recent_events.append(
                        {
                            "date": str(r.date)[:10],
                            "description": tag,
                            "type": "release",
                            "metadata": meta,
                        }
                    )

            # Enrich reddit posts with upvote/comment data from post_stats
            reddit_stats: dict[str, dict] = {}
            for r in qs.get_all_metrics("post_stats"):
                meta = r.metadata_ or {}
                pid = meta.get("post_id", "")
                if pid:
                    reddit_stats[pid] = {
                        "upvotes": int(r.value),
                        "comments": meta.get("comments", 0),
                        "subreddit": meta.get("subreddit", ""),
                    }

            # Sort by date desc, take 15
            recent_events.sort(key=lambda x: x["date"], reverse=True)
            recent_events = recent_events[:15]

        # Top-level metrics with change arrows + previous values
        metrics_row = ft.Row(
            [
                MetricCard(
                    "Stars",
                    str(stars_total),
                    "#FFD700",
                    change_pct=_pct(recent_stars, prev_star_count),
                    prev_value=f"+{recent_stars} last 14d",
                ),
                MetricCard(
                    "PyPI Downloads",
                    f"{db['pypi_total']:,}",
                    "#FF69B4",
                    change_pct=_pct(pypi_14d, pypi_prev14d),
                    prev_value=f"14d: {pypi_14d:,} (prev: {pypi_prev14d:,})",
                ),
                MetricCard(
                    "14d Clones",
                    f"{total_clones:,}",
                    Theme.Colors.PRIMARY,
                    change_pct=_pct(total_clones, prev_clones),
                    prev_value=f"{prev_clones:,}",
                ),
                MetricCard(
                    "14d Unique",
                    f"{total_unique:,}",
                    Theme.Colors.INFO,
                    change_pct=_pct(total_unique, prev_unique),
                    prev_value=f"{prev_unique:,}",
                ),
                MetricCard(
                    "14d Views",
                    f"{total_views:,}",
                    Theme.Colors.SUCCESS,
                    change_pct=_pct(total_views, prev_views),
                    prev_value=f"{prev_views:,}" if prev_views else None,
                ),
            ],
            spacing=Theme.Spacing.MD,
        )

        # Recent activity (left) — reuse ExpandableActivityRow
        from datetime import datetime as _dt

        from app.components.frontend.controls.data_table import (
            DataTableColumn,
            DataTableRow,
        )
        from app.services.system.activity import ActivityEvent

        from ..activity_feed import ExpandableActivityRow

        _row_col = [DataTableColumn("Activity")]

        activity_items: list[ft.Control] = []
        for ev in recent_events:
            status = EVENT_STATUS_MAP.get(ev["type"], "info")
            try:
                ts = _dt.strptime(ev["date"], "%Y-%m-%d")
            except (ValueError, TypeError):
                ts = _dt.now()

            # Build details from metadata
            meta = ev.get("metadata", {})
            details = None
            reddit_url = None
            if ev["type"] == "reddit_post":
                pid = meta.get("post_id", "")
                stats = reddit_stats.get(pid, {})
                parts = []
                sub = meta.get("subreddit") or stats.get("subreddit", "")
                if sub:
                    parts.append(f"r/{sub}")
                if stats.get("upvotes"):
                    parts.append(f"{stats['upvotes']} upvotes")
                if stats.get("comments"):
                    parts.append(f"{stats['comments']} comments")
                details = " \u2022 ".join(parts) if parts else None
                reddit_url = meta.get("url", "")
            elif ev["type"] == "star":
                usernames = meta.get("usernames", [])
                if usernames:
                    details = ", ".join(usernames[:10])
                    if len(usernames) > 10:
                        details += f" +{len(usernames) - 10} more"
            release_url = None
            if ev["type"] == "release":
                tag = meta.get("tag", ev["description"])
                release_url = (
                    f"https://github.com/lbedner/aegis-stack/releases/tag/{tag}"
                )
                details = tag
            elif ev["type"] in ("milestone_github", "milestone_pypi"):
                cat = meta.get("category", "")
                if cat:
                    details = cat.replace("_", " ").title()

            # For stars, show just the number in the title, name in details
            message = ev["description"][:80]
            if ev["type"] == "star" and " \u2014 " in message:
                message = message.split(" \u2014 ")[0]  # "⭐ #99 — ncthuc" → "⭐ #99"

            event_obj = ActivityEvent(
                component="insights",
                event_type=ev["type"],
                message=message,
                status=status,
                timestamp=ts,
                details=details or (reddit_url if reddit_url else None),
            )
            row = ExpandableActivityRow(event_obj)
            # Hide the status dot — not needed in insights feed
            row.content.controls[0].controls[0].visible = False

            # For reddit posts, replace details with stats + clickable link
            if reddit_url and details:
                row._details_container.content = ft.Column(
                    [
                        SecondaryText(details),
                        ft.Container(
                            content=ft.Text(
                                reddit_url,
                                size=Theme.Typography.BODY_SMALL,
                                style=ft.TextStyle(
                                    color=Theme.Colors.INFO,
                                    decoration=ft.TextDecoration.UNDERLINE,
                                ),
                                selectable=False,
                            ),
                            on_click=lambda e, u=reddit_url: e.page.launch_url(u),
                            ink=True,
                        ),
                    ],
                    spacing=4,
                )
            elif release_url:
                row._details_container.content = ft.Container(
                    content=ft.Text(
                        release_url,
                        size=Theme.Typography.BODY_SMALL,
                        style=ft.TextStyle(
                            color=Theme.Colors.INFO,
                            decoration=ft.TextDecoration.UNDERLINE,
                        ),
                        selectable=False,
                    ),
                    on_click=lambda e, u=release_url: e.page.launch_url(u),
                    ink=True,
                )

            activity_items.append(
                DataTableRow(columns=_row_col, row_data=[row], padding=4)
            )

        # Parse milestone data into trophy cards
        milestone_cards: list[ft.Control] = []
        for m in milestones:
            meta = m.get("metadata", {})
            category = meta.get("category", "")
            config = CATEGORY_CONFIG.get(category, {})
            label = config.get("label", m["description"])
            accent = config.get("color", "#9CA3AF")

            # Extract hero number — only for milestone types, not features
            hero = (
                _extract_max_number(m["description"]) if m["type"] != "feature" else ""
            )

            milestone_cards.append(
                MilestoneCard(
                    label=label,
                    value=hero or "\u2014",
                    date=_pretty_date(m["date"]),
                    accent_color=accent,
                )
            )

        # Arrange milestones in a 2x2 grid
        milestone_grid: list[ft.Control] = [
            H3Text("Key Milestones"),
            ft.Divider(height=1, color=ft.Colors.OUTLINE_VARIANT),
        ]
        row_items: list[ft.Control] = []
        for card in milestone_cards:
            row_items.append(card)
            if len(row_items) == 2:
                milestone_grid.append(ft.Row(row_items, spacing=Theme.Spacing.MD))
                row_items = []
        if row_items:
            milestone_grid.append(ft.Row(row_items, spacing=Theme.Spacing.MD))

        side_by_side = ft.Row(
            [
                ft.Column(
                    [
                        H3Text("Recent Activity"),
                        ft.Divider(height=1, color=ft.Colors.OUTLINE_VARIANT),
                        *activity_items,
                    ],
                    spacing=6,
                    expand=2,
                ),
                ft.Column(
                    milestone_grid,
                    spacing=6,
                    expand=1,
                ),
            ],
            spacing=Theme.Spacing.LG,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

        # Intelligence Report — collapsible analysis
        self.content = ft.Column(
            [
                metrics_row,
                ft.Container(height=4),
                side_by_side,
            ],
            spacing=8,
            scroll=ft.ScrollMode.AUTO,
        )
        self.padding = Theme.Spacing.MD
        self.expand = True


# ---------------------------------------------------------------------------
# Tab 2: GitHub
# ---------------------------------------------------------------------------


class GitHubTrafficTab(InsightsTab):
    """GitHub traffic, events, and activity with date range and event annotations."""

    _default_days = 7

    # -- build content --------------------------------------------------------

    def _build_content(self) -> None:  # noqa: C901
        """Build or rebuild all content based on state."""
        data = self._data
        daily = data["daily"]

        last_date = daily[-1]["date"] if daily else ""
        content: list[ft.Control] = [
            self._make_filter_bar(last_updated=last_date),
            ft.Container(height=8),
        ]

        if not daily:
            content.append(SecondaryText("No GitHub traffic data collected yet."))
            self._content_column.controls = content
            return

        # Range-level aggregates
        total_clones = sum(d["clones"] for d in daily)
        total_unique = sum(d["unique_cloners"] for d in daily)
        total_views = sum(d["views"] for d in daily)
        total_visitors = sum(d["unique_visitors"] for d in daily)
        clone_ratio = total_clones / total_unique if total_unique > 0 else 0
        num_days = len(daily)
        range_label = next(
            (label for label, days in RANGE_OPTIONS if days == self._days),
            f"{self._days}d",
        )

        # Period-over-period change

        prev_c = data.get("prev_clones", 0)
        prev_u = data.get("prev_unique", 0)
        prev_v = data.get("prev_views", 0)
        prev_vis = data.get("prev_visitors", 0)

        # Metric cards — all on one row, always visible
        forks = data.get("forks", [])
        releases = data.get("releases", {})
        star_daily = data.get("star_events_daily", [])
        avg_stars = (
            sum(d["stars"] for d in star_daily) / len(star_daily) if star_daily else 0
        )

        content.append(
            ft.Row(
                [
                    MetricCard(
                        "Clones",
                        f"{total_clones:,}",
                        Theme.Colors.PRIMARY,
                        change_pct=_pct(total_clones, prev_c),
                    ),
                    MetricCard(
                        "Unique",
                        f"{total_unique:,}",
                        Theme.Colors.INFO,
                        change_pct=_pct(total_unique, prev_u),
                    ),
                    MetricCard(
                        "Views",
                        f"{total_views:,}",
                        Theme.Colors.SUCCESS,
                        change_pct=_pct(total_views, prev_v),
                    ),
                    MetricCard(
                        "Visitors",
                        f"{total_visitors:,}",
                        Theme.Colors.WARNING,
                        change_pct=_pct(total_visitors, prev_vis),
                    ),
                    MetricCard("Clone Ratio", f"{clone_ratio:.1f}:1", "#E91E63"),
                    MetricCard("Forks", str(len(forks)), "#A855F7"),
                    MetricCard("Releases", str(len(releases)), "#22C55E"),
                    MetricCard("Avg Stars/Day", f"{avg_stars:.1f}", "#F59E0B"),
                ],
                spacing=Theme.Spacing.MD,
            )
        )

        # Date range text
        date_range = (
            f"{_pretty_date(daily[0]['date'])} \u2014 {_pretty_date(daily[-1]['date'])}"
        )
        content.append(SecondaryText(date_range, size=Theme.Typography.BODY_SMALL))

        # Event chips
        first_date = daily[0]["date"]
        last_date = daily[-1]["date"]
        window_events = [
            (date, label, etype)
            for date, label, etype in data.get("all_events", [])
            if first_date <= date <= last_date
        ]
        chips = self._render_event_chips(window_events)
        if chips:
            content.append(chips)

        content.append(ft.Container(height=4))

        # -- Clones + Unique chart with event annotations ---------------------

        releases_map = data.get("releases", {}) if self._show_events else {}
        highlighted = self._highlighted_dates

        max_clone = max(d["clones"] for d in daily) if daily else 1
        clone_step = _smart_step(max_clone)
        clone_max_y = int((max_clone // clone_step + 1) * clone_step)

        clone_points: list[ft.LineChartDataPoint] = []
        unique_points: list[ft.LineChartDataPoint] = []
        release_anno_points: list[ft.LineChartDataPoint] = []

        for i, d in enumerate(daily):
            is_hl = d["date"] in highlighted
            hl_point = (
                ft.ChartCirclePoint(
                    radius=7, color="#FF5722", stroke_width=2, stroke_color="#FFFFFF"
                )
                if is_hl
                else None
            )

            clone_points.append(
                ft.LineChartDataPoint(
                    i,
                    d["clones"],
                    tooltip=f"Clones: {d['clones']:,}",
                    point=hl_point,
                )
            )
            unique_points.append(
                ft.LineChartDataPoint(
                    i,
                    d["unique_cloners"],
                    tooltip=f"Unique: {d['unique_cloners']:,}",
                )
            )

            rel = releases_map.get(d["date"])
            if rel:
                release_anno_points.append(
                    ft.LineChartDataPoint(i, 0, tooltip=rel, show_tooltip=True)
                )
            else:
                release_anno_points.append(
                    ft.LineChartDataPoint(i, 0, show_tooltip=False)
                )

        clone_series = [
            ft.LineChartData(
                data_points=clone_points,
                stroke_width=2,
                color="#2563eb",
                curved=True,
                point=ft.ChartCirclePoint(
                    radius=3, color=ft.Colors.ON_SURFACE, stroke_width=0
                ),
                stroke_cap_round=True,
            ),
            ft.LineChartData(
                data_points=unique_points,
                stroke_width=2,
                color="#7c3aed",
                curved=True,
                point=ft.ChartCirclePoint(
                    radius=3, color=ft.Colors.ON_SURFACE, stroke_width=0
                ),
                stroke_cap_round=True,
            ),
        ]
        if any(p.show_tooltip for p in release_anno_points):
            clone_series.append(
                ft.LineChartData(
                    data_points=release_anno_points,
                    stroke_width=0,
                    color="#9CA3AF",
                )
            )

        clone_chart = _make_line_chart(clone_series, clone_max_y, daily, clone_step)
        content.append(
            ft.Container(content=clone_chart, margin=ft.margin.only(right=20))
        )
        content.append(
            _make_legend([("#2563eb", "Clones"), ("#7c3aed", "Unique Cloners")])
        )

        content.append(ft.Container(height=12))

        # -- Views + Visitors chart -------------------------------------------

        max_view = max(d["views"] for d in daily) if daily else 1
        view_step = _smart_step(max_view)
        view_max_y = int((max_view // view_step + 1) * view_step)

        view_points: list[ft.LineChartDataPoint] = []
        visitor_points: list[ft.LineChartDataPoint] = []
        release_anno2: list[ft.LineChartDataPoint] = []

        for i, d in enumerate(daily):
            is_hl = d["date"] in highlighted
            hl_point = (
                ft.ChartCirclePoint(
                    radius=7, color="#FF5722", stroke_width=2, stroke_color="#FFFFFF"
                )
                if is_hl
                else None
            )

            view_points.append(
                ft.LineChartDataPoint(
                    i,
                    d["views"],
                    tooltip=f"Views: {d['views']:,}",
                    point=hl_point,
                )
            )
            visitor_points.append(
                ft.LineChartDataPoint(
                    i,
                    d["unique_visitors"],
                    tooltip=f"Visitors: {d['unique_visitors']:,}",
                )
            )

            rel = releases_map.get(d["date"])
            if rel:
                release_anno2.append(
                    ft.LineChartDataPoint(i, 0, tooltip=rel, show_tooltip=True)
                )
            else:
                release_anno2.append(ft.LineChartDataPoint(i, 0, show_tooltip=False))

        view_series = [
            ft.LineChartData(
                data_points=view_points,
                stroke_width=2,
                color="#22C55E",
                curved=True,
                point=ft.ChartCirclePoint(
                    radius=3, color=ft.Colors.ON_SURFACE, stroke_width=0
                ),
                stroke_cap_round=True,
            ),
            ft.LineChartData(
                data_points=visitor_points,
                stroke_width=2,
                color="#F59E0B",
                curved=True,
                point=ft.ChartCirclePoint(
                    radius=3, color=ft.Colors.ON_SURFACE, stroke_width=0
                ),
                stroke_cap_round=True,
            ),
        ]
        if any(p.show_tooltip for p in release_anno2):
            view_series.append(
                ft.LineChartData(
                    data_points=release_anno2,
                    stroke_width=0,
                    color="#9CA3AF",
                )
            )

        views_chart = _make_line_chart(view_series, view_max_y, daily, view_step)
        content.append(
            ft.Container(content=views_chart, margin=ft.margin.only(right=20))
        )
        content.append(_make_legend([("#22C55E", "Views"), ("#F59E0B", "Visitors")]))

        # Interpretation
        content.append(
            ft.Container(
                content=SecondaryText(
                    f"{range_label} clone ratio of {clone_ratio:.1f}:1 across {total_clones:,} clones "
                    f"from {total_unique:,} unique cloners. "
                    f"Traffic data covers {num_days} days.",
                    size=Theme.Typography.BODY_SMALL,
                ),
                padding=ft.padding.symmetric(horizontal=4, vertical=8),
            )
        )

        # -- Activity Summary stacked bar chart -------------------------------

        activity = data.get("activity_summary", [])
        if activity:
            content.append(ft.Container(height=12))
            content.append(H3Text("Activity Summary"))

            # Group into 5 categories
            act_categories = [
                ("Code", "#3B82F6", ["push", "creates", "deletes"]),
                ("Issues", "#F59E0B", ["issues", "issue_comments"]),
                ("PRs", "#A855F7", ["pull_requests", "pull_request_reviews"]),
                ("Community", "#22C55E", ["forks", "stars"]),
                ("Releases", "#EC4899", ["releases"]),
            ]

            bar_groups: list[ft.BarChartGroup] = []
            act_max = 0

            bar_width = max(8, 400 // max(len(activity), 1))

            for i, day in enumerate(activity):
                stack_items: list[ft.BarChartRodStackItem] = []
                running_y = 0.0
                for _cat_name, color, fields in act_categories:
                    val = sum(day.get(f, 0) for f in fields)
                    if val > 0:
                        stack_items.append(
                            ft.BarChartRodStackItem(
                                from_y=running_y,
                                to_y=running_y + val,
                                color=color,
                            )
                        )
                    running_y += val
                act_max = max(act_max, running_y)
                bar_groups.append(
                    ft.BarChartGroup(
                        x=i,
                        bar_rods=[
                            ft.BarChartRod(
                                to_y=running_y,
                                width=bar_width,
                                rod_stack_items=stack_items,
                                color=ft.Colors.TRANSPARENT,
                                border_radius=2,
                            ),
                        ],
                    )
                )

            act_step = _smart_step(act_max) if act_max > 0 else 5
            act_max_y = int((act_max // act_step + 1) * act_step) if act_max > 0 else 10

            activity_chart = ft.BarChart(
                bar_groups=bar_groups,
                left_axis=ft.ChartAxis(labels_size=50, labels_interval=act_step),
                bottom_axis=ft.ChartAxis(
                    labels_size=50,
                    labels=[
                        ft.ChartAxisLabel(
                            value=i,
                            label=ft.Text(
                                day["date"][-5:],
                                size=9,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                        )
                        for i, day in enumerate(activity)
                        if i % 3 == 0 or i == len(activity) - 1
                    ],
                ),
                horizontal_grid_lines=ft.ChartGridLines(
                    interval=act_step,
                    color=ft.Colors.with_opacity(0.08, ft.Colors.ON_SURFACE),
                    width=1,
                ),
                border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
                interactive=False,
                max_y=act_max_y,
                height=300,
                expand=True,
            )

            content.append(
                ft.Container(content=activity_chart, margin=ft.margin.only(right=20))
            )
            content.append(
                ft.Row(
                    [
                        ft.Row(
                            [
                                ft.Container(
                                    width=10, height=10, bgcolor=color, border_radius=5
                                ),
                                SecondaryText(name, size=Theme.Typography.BODY_SMALL),
                            ],
                            spacing=4,
                        )
                        for name, color, _fields in act_categories
                    ],
                    spacing=16,
                    alignment=ft.MainAxisAlignment.CENTER,
                )
            )

        # -- Referrers --------------------------------------------------------

        referrers = data.get("referrers", [])
        content.append(ft.Container(height=8))
        content.append(H3Text("Referrers"))
        content.append(ft.Divider(height=1, color=ft.Colors.OUTLINE_VARIANT))

        if referrers:
            for ref in referrers:
                domain = ref["domain"]
                # Build URL — search engines get their URL, others get https://
                url = (
                    f"https://{domain}"
                    if "." in domain
                    else f"https://www.google.com/search?q={domain}"
                )
                content.append(
                    ft.Row(
                        [
                            ft.Container(
                                content=ft.Text(
                                    domain,
                                    size=Theme.Typography.BODY_SMALL,
                                    style=ft.TextStyle(
                                        color=Theme.Colors.INFO,
                                        decoration=ft.TextDecoration.UNDERLINE,
                                    ),
                                    selectable=False,
                                ),
                                width=200,
                                on_click=lambda e, u=url: e.page.launch_url(u),
                                ink=True,
                            ),
                            SecondaryText(
                                f"{ref['views']} views",
                                size=Theme.Typography.BODY_SMALL,
                            ),
                            SecondaryText(
                                f"{ref['uniques']} unique",
                                size=Theme.Typography.BODY_SMALL,
                            ),
                        ],
                        spacing=8,
                    )
                )
        else:
            content.append(
                SecondaryText(
                    "No referrer data available.", size=Theme.Typography.BODY_SMALL
                )
            )

        # -- Popular Paths ----------------------------------------------------

        paths = data.get("popular_paths", [])
        if paths:
            content.append(ft.Container(height=8))
            content.append(H3Text("Popular Paths"))
            content.append(ft.Divider(height=1, color=ft.Colors.OUTLINE_VARIANT))
            for p in paths:
                path_url = f"https://github.com{p['path']}"
                content.append(
                    ft.Row(
                        [
                            ft.Container(
                                content=ft.Text(
                                    p["path"],
                                    size=Theme.Typography.BODY_SMALL,
                                    style=ft.TextStyle(
                                        color=Theme.Colors.INFO,
                                        decoration=ft.TextDecoration.UNDERLINE,
                                    ),
                                    selectable=False,
                                ),
                                expand=True,
                                on_click=lambda e, u=path_url: e.page.launch_url(u),
                                ink=True,
                            ),
                            SecondaryText(
                                f"{p['views']} views", size=Theme.Typography.BODY_SMALL
                            ),
                            SecondaryText(
                                f"{p['uniques']} unique",
                                size=Theme.Typography.BODY_SMALL,
                            ),
                        ],
                        spacing=8,
                    )
                )

        self._content_column.controls = content

    # -- data loader ----------------------------------------------------------

    @staticmethod
    def _load_data(days: int = 14) -> dict[str, Any]:
        """Load GitHub data from database with date cutoff."""
        from app.services.insights.query_service import InsightQueryService

        with InsightQueryService() as qs:
            cutoff, prev_cutoff = qs.compute_cutoffs(days)

            # Traffic daily
            clones_rows = qs.get_daily("clones", cutoff)
            unique_rows = qs.get_daily("unique_cloners", cutoff)
            views_rows = qs.get_daily("views", cutoff)
            visitors_rows = qs.get_daily("unique_visitors", cutoff)

            unique_map = {str(r.date)[:10]: int(r.value) for r in unique_rows}
            views_map = {str(r.date)[:10]: int(r.value) for r in views_rows}
            visitors_map = {str(r.date)[:10]: int(r.value) for r in visitors_rows}

            daily: list[dict[str, Any]] = []
            for r in clones_rows:
                day = str(r.date)[:10]
                daily.append(
                    {
                        "date": day,
                        "clones": int(r.value),
                        "unique_cloners": unique_map.get(day, 0),
                        "views": views_map.get(day, 0),
                        "unique_visitors": visitors_map.get(day, 0),
                    }
                )

            # Referrers (latest snapshot)
            referrers_row = qs.get_latest("referrers")
            referrers: list[dict[str, Any]] = []
            if referrers_row and referrers_row.metadata_:
                meta = referrers_row.metadata_
                if isinstance(meta, dict) and not meta.get("referrers"):
                    for domain, counts in meta.items():
                        if isinstance(counts, dict):
                            referrers.append(
                                {
                                    "domain": domain,
                                    "views": counts.get("views", 0),
                                    "uniques": counts.get("uniques", 0),
                                }
                            )
                else:
                    for ref in meta.get("referrers", []):
                        referrers.append(
                            {
                                "domain": ref.get(
                                    "referrer", ref.get("domain", "unknown")
                                ),
                                "views": ref.get("count", ref.get("views", 0)),
                                "uniques": ref.get("uniques", 0),
                            }
                        )
                referrers.sort(key=lambda x: -x["views"])

            # Popular paths (latest snapshot)
            paths_row = qs.get_latest("popular_paths")
            popular_paths: list[dict[str, Any]] = []
            if paths_row and paths_row.metadata_:
                for p in paths_row.metadata_.get(
                    "paths", paths_row.metadata_.get("popular_paths", [])
                ):
                    popular_paths.append(
                        {
                            "path": p.get("path", "unknown"),
                            "title": p.get("title", ""),
                            "views": p.get("count", p.get("views", 0)),
                            "uniques": p.get("uniques", 0),
                        }
                    )

            # Fork events
            fork_rows = qs.get_events("forks", cutoff)
            forks: list[dict[str, str]] = []
            for r in fork_rows:
                meta = r.metadata_ or {}
                forks.append(
                    {"actor": meta.get("actor", "unknown"), "date": str(r.date)[:10]}
                )

            # Star events daily
            star_rows = qs.get_daily("star_events", cutoff)
            star_events_daily: list[dict[str, Any]] = []
            for r in star_rows:
                star_events_daily.append(
                    {"date": str(r.date)[:10], "stars": int(r.value)}
                )

            # Activity summary daily
            activity_rows = qs.get_daily("activity_summary", cutoff)
            activity_summary: list[dict[str, Any]] = []
            for r in activity_rows:
                meta = r.metadata_ or {}
                entry: dict[str, Any] = {"date": str(r.date)[:10]}
                for field in (
                    "push",
                    "issues",
                    "pull_requests",
                    "pull_request_reviews",
                    "issue_comments",
                    "forks",
                    "stars",
                    "releases",
                    "creates",
                    "deletes",
                ):
                    entry[field] = meta.get(field, 0)
                activity_summary.append(entry)

            # Build all_events list for chips
            all_events: list[tuple[str, str, str]] = []

            # Release events from metrics
            release_rows = qs.get_events("releases", cutoff)
            releases: dict[str, str] = {}
            for r in release_rows:
                meta = r.metadata_ or {}
                tag = meta.get("tag", "")
                day = str(r.date)[:10]
                if tag:
                    all_events.append((day, tag, "release"))
                    if day in releases:
                        releases[day] += f"\n{tag}"
                    else:
                        releases[day] = tag

            for f in forks:
                all_events.append((f["date"], f"Fork: {f['actor']}", "fork"))

            # InsightEvent rows filtered to GitHub-relevant types
            for ev in qs.get_insight_events(
                cutoff=cutoff, type_filter=GITHUB_EVENT_TYPES
            ):
                day = str(ev.date)[:10]
                all_events.append((day, ev.description[:60], ev.event_type))
                if day in releases:
                    releases[day] += f"\n{ev.description[:60]}"
                else:
                    releases[day] = ev.description[:60]

            all_events.sort(key=lambda x: x[0])

            return {
                "daily": daily,
                "referrers": referrers,
                "popular_paths": popular_paths,
                "forks": forks,
                "releases": releases,
                "all_events": all_events,
                "activity_summary": activity_summary,
                "star_events_daily": star_events_daily,
                "prev_clones": qs.sum_range("clones", prev_cutoff, cutoff),
                "prev_unique": qs.sum_range("unique_cloners", prev_cutoff, cutoff),
                "prev_views": qs.sum_range("views", prev_cutoff, cutoff),
                "prev_visitors": qs.sum_range("unique_visitors", prev_cutoff, cutoff),
            }


# ---------------------------------------------------------------------------
# Tab 3: Stars
# ---------------------------------------------------------------------------


class StarsTab(InsightsTab):
    """Stars: cumulative chart, recent list, event chips — with date range."""

    _default_days = 7

    def _build_content(self) -> None:
        """Build or rebuild all content based on state."""
        data = self._data
        star_history = data["star_history"]
        total_stars = data["total_stars"]
        range_stars = data["range_stars"]

        last_date = star_history[-1]["date"] if star_history else ""
        content: list[ft.Control] = [
            self._make_filter_bar(last_updated=last_date),
            ft.Container(height=8),
        ]

        # Metric cards
        num_days = len(star_history) if star_history else 1
        avg_per_day = range_stars / num_days if num_days else 0

        content.append(
            ft.Row(
                [
                    MetricCard("Total Stars", str(total_stars), "#FFD700"),
                    MetricCard("In Range", str(range_stars), Theme.Colors.INFO),
                    MetricCard("Avg / Day", f"{avg_per_day:.1f}", Theme.Colors.SUCCESS),
                ],
                spacing=Theme.Spacing.MD,
            )
        )

        if not star_history:
            content.append(SecondaryText("No star events in this range."))
            self._content_column.controls = content
            return

        # Date range text
        date_range = f"{_pretty_date(star_history[0]['date'])} \u2014 {_pretty_date(star_history[-1]['date'])}"
        content.append(SecondaryText(date_range, size=Theme.Typography.BODY_SMALL))

        # Event chips — only on dates with stars, exclude star type
        star_dates = {d["date"] for d in star_history}
        chips = self._render_event_chips(
            data.get("all_events", []),
            valid_dates=star_dates,
            exclude_types={"star"},
        )
        if chips:
            content.append(chips)

        # Star History cumulative chart
        max_stars = star_history[-1]["stars"]
        min_stars = star_history[0]["stars"]
        padding = max(1, (max_stars - min_stars) // 4)
        star_min_y = max(0, min_stars - padding)
        star_range = max_stars - star_min_y
        star_step = _smart_step(star_range)
        star_max_y = int((max_stars // star_step + 1) * star_step)
        highlighted = self._highlighted_dates
        # Filter releases: exclude star events, only dates that have chart points
        releases_map = data.get("releases", {}) if self._show_events else {}
        non_star_releases: dict[str, str] = {}
        for day, label in releases_map.items():
            if day not in star_dates:
                continue
            lines = [ln for ln in label.split("\n") if not ln.startswith("\u2b50")]
            if lines:
                non_star_releases[day] = "\n".join(lines)

        history_points: list[ft.LineChartDataPoint] = []
        release_anno: list[ft.LineChartDataPoint] = []

        for i, d in enumerate(star_history):
            is_hl = d["date"] in highlighted
            hl_point = (
                ft.ChartCirclePoint(
                    radius=7, color="#FF5722", stroke_width=2, stroke_color="#FFFFFF"
                )
                if is_hl
                else None
            )
            count = d.get("count", 1)
            names = d.get("usernames", [])
            if count == 1:
                tip = f"#{d['stars']} — {names[0] if names else ''}\n{_pretty_date(d['date'])}"
            else:
                first_num = d["stars"] - count + 1
                tip = f"#{first_num}-#{d['stars']} ({count} stars)\n{_pretty_date(d['date'])}"
            history_points.append(
                ft.LineChartDataPoint(
                    i,
                    d["stars"],
                    tooltip=tip,
                    point=hl_point,
                )
            )

            rel = non_star_releases.get(d["date"])
            if rel:
                release_anno.append(
                    ft.LineChartDataPoint(i, 0, tooltip=rel, show_tooltip=True)
                )
            else:
                release_anno.append(ft.LineChartDataPoint(i, 0, show_tooltip=False))

        chart_series = [
            ft.LineChartData(
                data_points=history_points,
                stroke_width=3,
                color="#FFD700",
                curved=True,
                below_line_bgcolor=ft.Colors.with_opacity(0.15, "#FFD700"),
                point=ft.ChartCirclePoint(radius=3, color="#FFD700", stroke_width=0),
                stroke_cap_round=True,
            ),
        ]
        if any(p.show_tooltip for p in release_anno):
            chart_series.append(
                ft.LineChartData(
                    data_points=release_anno,
                    stroke_width=0,
                    color="#9CA3AF",
                )
            )

        history_chart = _make_line_chart(
            chart_series, star_max_y, star_history, star_step, min_y=star_min_y
        )
        content.append(
            ft.Container(content=history_chart, margin=ft.margin.only(right=20))
        )
        content.append(_make_legend([("#FFD700", "Cumulative Stars")]))

        self._content_column.controls = content

    @staticmethod
    def _load_data(days: int = 9999) -> dict[str, Any]:
        """Load star data from database with date cutoff."""
        from app.services.insights.query_service import InsightQueryService

        with InsightQueryService() as qs:
            cutoff, _ = qs.compute_cutoffs(days)

            # All stars (for total count)
            all_rows = qs.get_all_events("new_star")
            total_stars = len(all_rows)

            if not all_rows:
                return {
                    "star_history": [],
                    "stars_recent": [],
                    "total_stars": 0,
                    "range_stars": 0,
                    "all_events": [],
                    "releases": {},
                }

            # Stars in range
            range_rows = [r for r in all_rows if r.date >= cutoff]
            range_stars = len(range_rows)

            # Cumulative history - only days with stars, within range
            by_date: dict[str, dict[str, Any]] = {}
            for r in range_rows:
                day = str(r.date)[:10]
                meta = r.metadata_ if isinstance(r.metadata_, dict) else {}
                if day not in by_date:
                    by_date[day] = {"max_num": 0, "count": 0, "usernames": []}
                by_date[day]["max_num"] = max(by_date[day]["max_num"], int(r.value))
                by_date[day]["count"] += 1
                by_date[day]["usernames"].append(meta.get("username", "unknown"))
            star_history = [
                {
                    "date": d,
                    "stars": info["max_num"],
                    "count": info["count"],
                    "usernames": info["usernames"],
                }
                for d, info in sorted(by_date.items())
            ]

            # Recent stars (last 20 in range)
            stars_recent: list[dict[str, Any]] = []
            for r in reversed(range_rows[-20:]):
                meta = r.metadata_ if isinstance(r.metadata_, dict) else {}
                stars_recent.append(
                    {
                        "number": int(r.value),
                        "username": meta.get("username", "unknown"),
                        "location": meta.get("location", ""),
                        "company": meta.get("company", ""),
                        "date": str(r.date)[:10],
                    }
                )

            # Events for chips + chart annotations
            all_events: list[tuple[str, str, str]] = []
            for r in qs.get_release_metrics():
                tag = (r.metadata_ or {}).get("tag", "")
                if tag:
                    all_events.append((str(r.date)[:10], tag, "release"))
            for ev in qs.get_insight_events(
                cutoff=cutoff, type_filter=GITHUB_EVENT_TYPES
            ):
                all_events.append(
                    (str(ev.date)[:10], ev.description[:60], ev.event_type)
                )

            release_map: dict[str, str] = {}
            for date, label, _ in all_events:
                if date in release_map:
                    release_map[date] += f"\n{label}"
                else:
                    release_map[date] = label

            all_events.sort(key=lambda x: x[0])

            return {
                "star_history": star_history,
                "stars_recent": stars_recent,
                "total_stars": total_stars,
                "range_stars": range_stars,
                "all_events": all_events,
                "releases": release_map,
            }


# ---------------------------------------------------------------------------
# Tab 4: PyPI (unchanged -- already uses real data)
# ---------------------------------------------------------------------------


class PyPITab(InsightsTab):
    """PyPI: real data from database with CI/mirror toggle and date range filter."""

    _default_days = 7

    def __init__(self) -> None:
        self._include_ci = False
        self._toggle = ft.Switch(
            label="Include CI/Mirror downloads",
            value=False,
            on_change=self._on_toggle,
            label_style=ft.TextStyle(size=12, color=ft.Colors.ON_SURFACE_VARIANT),
        )
        super().__init__()

    def _on_toggle(self, e: ft.ControlEvent) -> None:
        self._include_ci = e.control.value
        self._build_content()
        self._content_column.update()

    def _build_content(self) -> None:
        """Build or rebuild all content based on toggle state and date range."""
        data = self._data
        include_ci = self._include_ci
        daily = data["daily"]

        # Compute averages from daily data
        bot_pct = data["bot_percent"]
        num_days = len(daily) if daily else 1
        range_label = next(
            (label for label, days in RANGE_OPTIONS if days == self._days),
            f"{self._days}d",
        )

        range_all = sum(d["total"] for d in daily) if daily else 0
        range_human = sum(d["human"] for d in daily) if daily else 0

        if include_ci:
            total_display = f"{range_all:,}"
            avg_day = range_all // num_days if num_days else 0
        else:
            total_display = f"{range_human:,}"
            avg_day = range_human // num_days if num_days else 0

        avg_week = avg_day * 7
        avg_month = avg_day * 30

        last_date = daily[-1]["date"] if daily else ""
        content: list[ft.Control] = [
            self._make_filter_bar(
                last_updated=last_date, extra_controls=[self._toggle]
            ),
            ft.Container(height=8),
        ]

        # Period-over-period change
        prev_total = data.get("prev_total", 0)
        prev_human = data.get("prev_human", 0)
        prev_val = prev_total if include_ci else prev_human
        cur_val = range_all if include_ci else range_human

        # Metric cards
        metrics_row = ft.Row(
            [
                MetricCard(
                    "Total Downloads",
                    total_display,
                    "#FF69B4",
                    change_pct=_pct(cur_val, prev_val),
                ),
                MetricCard("Avg / Day", f"{avg_day:,}", Theme.Colors.INFO),
                MetricCard("Avg / Week", f"{avg_week:,}", Theme.Colors.SUCCESS),
                MetricCard("Avg / Month", f"{avg_month:,}", Theme.Colors.PRIMARY),
                MetricCard(
                    "Bot %",
                    f"{bot_pct:.0f}%",
                    Theme.Colors.WARNING if bot_pct > 50 else Theme.Colors.INFO,
                ),
            ],
            spacing=Theme.Spacing.MD,
        )
        content.append(metrics_row)

        # Date range + events in window
        releases = data.get("releases", {})
        if daily:
            date_range = f"{_pretty_date(daily[0]['date'])} \u2014 {_pretty_date(daily[-1]['date'])}"
            content.append(ft.Container(height=8))
            content.append(SecondaryText(date_range, size=Theme.Typography.BODY_SMALL))

            # Event chips
            first_date = daily[0]["date"] if daily else ""
            last_date = daily[-1]["date"] if daily else ""
            window_events = [
                (date, label, etype)
                for date, label, etype in data.get("all_events", [])
                if first_date <= date <= last_date
            ]
            chips = self._render_event_chips(window_events)
            if chips:
                content.append(chips)

        # Chart 1: Downloads — toggle controls which lines show
        if daily:
            if include_ci:
                max_val = max(d["total"] for d in daily)
            else:
                max_val = (
                    max(d["human"] for d in daily)
                    if any(d["human"] for d in daily)
                    else 1
                )

            # Smart rounding: small values round to nearest 5, medium to 25, large to 100
            if max_val <= 20:
                step = 5
            elif max_val <= 100:
                step = 10
            elif max_val <= 500:
                step = 50
            else:
                step = 100
            rounded_max = int((max_val // step + 1) * step)

            releases = data.get("releases", {}) if self._show_events else {}

            chart1_series = []
            if include_ci:
                # Stacked: total (pink filled) on top, human (green filled) below
                total_points = []
                human_points_ci = []
                release_points_ci = []
                highlighted = self._highlighted_dates
                for i, d in enumerate(daily):
                    is_hl = d["date"] in highlighted
                    point_style = (
                        ft.ChartCirclePoint(
                            radius=7,
                            color="#FF5722",
                            stroke_width=2,
                            stroke_color="#FFFFFF",
                        )
                        if is_hl
                        else None
                    )
                    total_points.append(
                        ft.LineChartDataPoint(
                            i,
                            d["total"],
                            tooltip=f"Total: {d['total']:,}  Bot: {d['total'] - d['human']:,}",
                            point=point_style,
                        )
                    )
                    human_points_ci.append(
                        ft.LineChartDataPoint(
                            i, d["human"], tooltip=f"Human: {d['human']:,}"
                        )
                    )

                    rel = releases.get(d["date"])
                    if rel:
                        release_points_ci.append(
                            ft.LineChartDataPoint(
                                i, 0, tooltip=f"{rel}", show_tooltip=True
                            )
                        )
                    else:
                        release_points_ci.append(
                            ft.LineChartDataPoint(i, 0, show_tooltip=False)
                        )

                chart1_series.append(
                    ft.LineChartData(
                        data_points=total_points,
                        stroke_width=1,
                        color="#FF69B4",
                        below_line_bgcolor=ft.Colors.with_opacity(0.5, "#FF69B4"),
                    )
                )
                chart1_series.append(
                    ft.LineChartData(
                        data_points=human_points_ci,
                        stroke_width=2,
                        color="#22C55E",
                        below_line_bgcolor=ft.Colors.with_opacity(0.6, "#22C55E"),
                        point=ft.ChartCirclePoint(
                            radius=3, color=ft.Colors.ON_SURFACE, stroke_width=0
                        ),
                    )
                )
                chart1_series.append(
                    ft.LineChartData(
                        data_points=release_points_ci,
                        stroke_width=0,
                        color="#9CA3AF",
                    )
                )
            else:
                # Just human as filled area
                human_points = []
                release_points = []
                highlighted = self._highlighted_dates
                for i, d in enumerate(daily):
                    tip = f"{d['human']:,} downloads"
                    is_hl = d["date"] in highlighted
                    point_style = (
                        ft.ChartCirclePoint(
                            radius=7,
                            color="#FF5722",
                            stroke_width=2,
                            stroke_color="#FFFFFF",
                        )
                        if is_hl
                        else ft.ChartCirclePoint(
                            radius=3, color=ft.Colors.ON_SURFACE, stroke_width=0
                        )
                    )
                    human_points.append(
                        ft.LineChartDataPoint(
                            i, d["human"], tooltip=tip, point=point_style
                        )
                    )

                    rel = releases.get(d["date"])
                    if rel:
                        release_points.append(
                            ft.LineChartDataPoint(
                                i, 0, tooltip=f"{rel}", show_tooltip=True
                            )
                        )
                    else:
                        release_points.append(
                            ft.LineChartDataPoint(i, 0, show_tooltip=False)
                        )

                chart1_series.append(
                    ft.LineChartData(
                        data_points=human_points,
                        stroke_width=2,
                        color="#22C55E",
                        below_line_bgcolor=ft.Colors.with_opacity(0.4, "#22C55E"),
                        point=ft.ChartCirclePoint(
                            radius=3, color=ft.Colors.ON_SURFACE, stroke_width=0
                        ),
                    )
                )
                # Release annotation series — invisible line, tooltip in secondary color
                chart1_series.append(
                    ft.LineChartData(
                        data_points=release_points,
                        stroke_width=0,
                        color="#9CA3AF",
                    )
                )

            chart1 = _make_line_chart(chart1_series, rounded_max, daily, step)

            if include_ci:
                legend1 = _make_legend(
                    [
                        (ft.Colors.with_opacity(0.5, "#FF69B4"), "Bot / Mirror"),
                        (ft.Colors.with_opacity(0.6, "#22C55E"), "Human"),
                    ]
                )
            else:
                legend1 = _make_legend(
                    [(ft.Colors.with_opacity(0.4, "#22C55E"), "Human Downloads")]
                )

            chart1_wrapped = ft.Container(
                content=chart1,
                margin=ft.margin.only(right=20),
            )
            content.extend([ft.Container(height=8), chart1_wrapped, legend1])

        # Bar chart: downloads by version
        versions = data["versions"]
        if versions:
            # Sort by version number (semantic sort)
            def _version_sort_key(ver: str) -> tuple:
                parts = (
                    ver.replace("rc", ".")
                    .replace("a", ".")
                    .replace("b", ".")
                    .split(".")
                )
                return tuple(int(p) if p.isdigit() else 0 for p in parts)

            all_sorted = sorted(versions.keys(), key=_version_sort_key)

            # Filter out versions with 0 downloads for the current mode
            sorted_versions = []
            for ver in all_sorted:
                info = versions[ver]
                if isinstance(info, dict):
                    t, h = info.get("total", 0), info.get("human", 0)
                else:
                    t, h = info, 0
                val = t if include_ci else h
                if val > 0:
                    sorted_versions.append(ver)

            bar_groups = []
            bar_max = 0
            for i, ver in enumerate(sorted_versions):
                info = versions[ver]
                if isinstance(info, dict):
                    t, h = info.get("total", 0), info.get("human", 0)
                else:
                    t, h = info, 0

                val = t if include_ci else h
                bar_max = max(bar_max, val)

                bar_groups.append(
                    ft.BarChartGroup(
                        x=i,
                        bar_rods=[
                            ft.BarChartRod(
                                from_y=0,
                                to_y=val,
                                width=max(8, 400 // len(sorted_versions)),
                                color="#FF69B4" if include_ci else "#22C55E",
                                border_radius=ft.border_radius.only(
                                    top_left=3, top_right=3
                                ),
                                tooltip=f"{ver}: {val:,}",
                            )
                        ],
                    )
                )

            bar_rounded_max = int(bar_max * 1.15) + 1 if bar_max > 0 else 10

            # Show every Nth label to avoid overlap
            label_step = max(1, len(sorted_versions) // 12)

            version_bar = ft.BarChart(
                bar_groups=bar_groups,
                left_axis=ft.ChartAxis(
                    labels_size=50, labels_interval=max(1, bar_rounded_max // 4)
                ),
                bottom_axis=ft.ChartAxis(
                    labels_size=50,
                    labels=[
                        ft.ChartAxisLabel(
                            value=i,
                            label=ft.Text(
                                ver, size=8, color=ft.Colors.ON_SURFACE_VARIANT
                            ),
                        )
                        for i, ver in enumerate(sorted_versions)
                        if i % label_step == 0 or i == len(sorted_versions) - 1
                    ],
                ),
                horizontal_grid_lines=ft.ChartGridLines(
                    interval=bar_rounded_max // 4 or 1,
                    color=ft.Colors.with_opacity(0.08, ft.Colors.ON_SURFACE),
                    width=1,
                ),
                tooltip_bgcolor=Theme.Colors.SURFACE_1,
                tooltip_rounded_radius=8,
                tooltip_padding=10,
                tooltip_tooltip_border_side=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
                border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
                max_y=bar_rounded_max,
                height=250,
                expand=True,
            )

            bar_wrapped = ft.Container(
                content=version_bar, margin=ft.margin.only(right=20)
            )
            bar_legend = ft.Row(
                [
                    ft.Row(
                        [
                            ft.Container(
                                width=10,
                                height=10,
                                bgcolor="#FF69B4" if include_ci else "#22C55E",
                                border_radius=5,
                            ),
                            SecondaryText(
                                f"Downloads by Version ({'incl. CI' if include_ci else 'human only'})",
                                size=Theme.Typography.BODY_SMALL,
                            ),
                        ],
                        spacing=4,
                    )
                ],
                alignment=ft.MainAxisAlignment.CENTER,
            )

            content.extend([ft.Container(height=12), bar_wrapped, bar_legend])

        # Three pie charts in one row
        pie_charts: list[ft.Control] = []

        installers = data["installers"]
        if installers:
            total_inst = sum(installers.values())
            pie_charts.append(
                PieChartCard(
                    title=f"By Installer ({range_label})",
                    sections=[
                        {"value": count, "label": f"{name} ({count / total_inst:.0%})"}
                        for name, count in list(installers.items())[:8]
                    ],
                )
            )

        countries = data["countries"]
        if countries:
            total_c = sum(countries.values())
            pie_charts.append(
                PieChartCard(
                    title=f"By Country ({range_label})",
                    sections=[
                        {"value": count, "label": f"{code} ({count / total_c:.0%})"}
                        for code, count in list(countries.items())[:10]
                    ],
                )
            )

        dist_types = data.get("types", {})
        if dist_types:
            total_t = sum(dist_types.values())
            pie_charts.append(
                PieChartCard(
                    title=f"Dist Type ({range_label})",
                    sections=[
                        {"value": count, "label": f"{name} ({count / total_t:.0%})"}
                        for name, count in dist_types.items()
                    ],
                )
            )

        if pie_charts:
            content.extend(
                [
                    ft.Container(height=8),
                    ft.Row(pie_charts, spacing=Theme.Spacing.MD),
                ]
            )

        # Version table
        versions = data["versions"]
        if versions:
            from app.components.frontend.controls.data_table import (
                DataTable,
                DataTableColumn,
            )

            version_columns = [
                DataTableColumn(header="Version", width=100, style="primary"),
                DataTableColumn(header="Total", width=80, alignment="right"),
                DataTableColumn(header="Human", width=80, alignment="right"),
                DataTableColumn(header="Bot", width=80, alignment="right"),
                DataTableColumn(header="Bot %", width=70, alignment="right"),
            ]

            version_rows_data = []
            for ver, info in list(versions.items())[:10]:
                if isinstance(info, dict):
                    t, h = info.get("total", 0), info.get("human", 0)
                else:
                    t, h = info, 0
                b = t - h
                pct = f"{(b / t * 100):.0f}%" if t > 0 else "\u2014"
                pct_color = "#EF4444" if t > 0 and b / t > 0.8 else "#22C55E"
                version_rows_data.append(
                    [
                        ver,
                        f"{t:,}",
                        ft.Text(f"{h:,}", color="#22C55E", size=12),
                        ft.Text(f"{b:,}", color="#EF4444", size=12),
                        ft.Text(
                            pct, color=pct_color, size=12, weight=ft.FontWeight.W_600
                        ),
                    ]
                )

            # Totals row
            total_t = sum(
                info.get("total", 0) if isinstance(info, dict) else info
                for info in versions.values()
            )
            total_h = sum(
                info.get("human", 0) if isinstance(info, dict) else 0
                for info in versions.values()
            )
            total_b = total_t - total_h
            total_pct = f"{(total_b / total_t * 100):.0f}%" if total_t > 0 else "\u2014"

            version_rows_data.append(
                [
                    ft.Text("TOTAL", size=12, weight=ft.FontWeight.W_700),
                    ft.Text(f"{total_t:,}", size=12, weight=ft.FontWeight.W_700),
                    ft.Text(
                        f"{total_h:,}",
                        size=12,
                        weight=ft.FontWeight.W_700,
                        color="#22C55E",
                    ),
                    ft.Text(
                        f"{total_b:,}",
                        size=12,
                        weight=ft.FontWeight.W_700,
                        color="#EF4444",
                    ),
                    ft.Text(
                        total_pct,
                        size=12,
                        weight=ft.FontWeight.W_700,
                        color="#EF4444"
                        if total_t > 0 and total_b / total_t > 0.8
                        else "#22C55E",
                    ),
                ]
            )

            version_table = DataTable(
                columns=version_columns,
                rows=version_rows_data,
            )

            # Daily downloads table (sorted by highest day)
            daily_columns = [
                DataTableColumn(header="Date", width=80, style="primary"),
                DataTableColumn(header="Total", width=70, alignment="right"),
                DataTableColumn(header="Human", width=70, alignment="right"),
                DataTableColumn(header="Bot", width=70, alignment="right"),
            ]

            sorted_days = sorted(daily, key=lambda d: d["date"], reverse=True)
            daily_rows_data = []
            for d in sorted_days:
                bot = d["total"] - d["human"]
                daily_rows_data.append(
                    [
                        d["date"][-5:],
                        f"{d['total']:,}",
                        ft.Text(f"{d['human']:,}", color="#22C55E", size=12),
                        ft.Text(f"{bot:,}", color="#EF4444", size=12),
                    ]
                )

            daily_table = DataTable(
                columns=daily_columns,
                rows=daily_rows_data,
                scroll_height=400,
            )

            content.extend(
                [
                    ft.Container(height=12),
                    ft.Row(
                        [
                            ft.Column(
                                [
                                    H3Text(f"Downloads by Version ({range_label})"),
                                    version_table,
                                ],
                                expand=True,
                            ),
                            ft.Column(
                                [
                                    H3Text(f"Daily Downloads ({range_label})"),
                                    daily_table,
                                ],
                                expand=True,
                            ),
                        ],
                        spacing=Theme.Spacing.LG,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    ),
                ]
            )

        self._content_column.controls = content

    @staticmethod
    def _load_data(days: int = 14) -> dict:
        """Load PyPI data from database (sync)."""
        from app.services.insights.query_service import InsightQueryService

        with InsightQueryService() as qs:
            cutoff, prev_cutoff = qs.compute_cutoffs(days)

            # Total
            total_row = qs.get_latest("downloads_total")
            total = int(total_row.value) if total_row else 0

            # Daily total + human
            daily_rows = qs.get_daily("downloads_daily", cutoff)
            human_rows = qs.get_daily("downloads_daily_human", cutoff)
            human_map = {str(r.date)[:10]: int(r.value) for r in human_rows}

            daily = []
            for r in daily_rows:
                day = str(r.date)[:10]
                t = int(r.value)
                h = human_map.get(day, 0)
                daily.append({"date": day, "total": t, "human": h})

            today_total = daily[-1]["total"] if daily else 0
            today_human = daily[-1]["human"] if daily else 0

            # Bot % computed over entire selected range
            range_total = sum(d["total"] for d in daily)
            range_human = sum(d["human"] for d in daily)
            bot_pct = (
                ((range_total - range_human) / range_total * 100)
                if range_total > 0
                else 0
            )

            # Latest installer breakdown (aggregate from all days)
            all_installers: dict[str, int] = {}
            for r in qs.get_daily("downloads_by_installer", cutoff):
                meta = r.metadata_ or {}
                for name, count in meta.get("installers", {}).items():
                    all_installers[name] = all_installers.get(name, 0) + count
            installers = dict(sorted(all_installers.items(), key=lambda x: -x[1]))

            # Latest country breakdown (aggregate)
            all_countries: dict[str, int] = {}
            for r in qs.get_daily("downloads_by_country", cutoff):
                meta = r.metadata_ or {}
                for code, count in meta.get("countries", {}).items():
                    all_countries[code] = all_countries.get(code, 0) + count
            countries = dict(sorted(all_countries.items(), key=lambda x: -x[1]))

            # Per-day per-version data
            version_daily_rows = qs.get_daily("downloads_by_version", cutoff)
            version_daily: dict[str, dict[str, int]] = {}
            for r in version_daily_rows:
                day = str(r.date)[:10]
                meta = r.metadata_ or {}
                day_versions = meta.get("versions", {})
                version_daily[day] = {}
                for ver, info in day_versions.items():
                    if isinstance(info, dict):
                        version_daily[day][ver] = info.get("total", 0)
                    else:
                        version_daily[day][ver] = info

            # Version breakdown with real human/bot
            versions: dict[str, dict[str, int]] = {}
            for r in version_daily_rows:
                meta = r.metadata_ or {}
                for ver, info in meta.get("versions", {}).items():
                    if ver not in versions:
                        versions[ver] = {"total": 0, "human": 0}
                    if isinstance(info, dict):
                        versions[ver]["total"] += info.get("total", 0)
                        versions[ver]["human"] += info.get("human", 0)
                    else:
                        versions[ver]["total"] += info
            versions = dict(sorted(versions.items(), key=lambda x: -x[1]["total"]))

            # Distribution type breakdown
            all_types: dict[str, int] = {}
            for r in qs.get_daily("downloads_by_type", cutoff):
                meta = r.metadata_ or {}
                for t, count in meta.get("types", {}).items():
                    all_types[t] = all_types.get(t, 0) + count
            dist_types = dict(sorted(all_types.items(), key=lambda x: -x[1]))

            # Events for chart annotations
            all_events: list[tuple[str, str, str]] = []
            for r in qs.get_release_metrics():
                tag = (r.metadata_ or {}).get("tag", "")
                if tag:
                    all_events.append((str(r.date)[:10], tag, "release"))
            for ev in qs.get_insight_events(type_filter=PYPI_EVENT_TYPES):
                all_events.append(
                    (str(ev.date)[:10], ev.description[:60], ev.event_type)
                )

            release_map: dict[str, str] = {}
            for date, label, _ in all_events:
                if date in release_map:
                    release_map[date] += f"\n{label}"
                else:
                    release_map[date] = label

            return {
                "total": total,
                "today_total": today_total,
                "today_human": today_human,
                "bot_percent": bot_pct,
                "prev_total": qs.sum_range("downloads_daily", prev_cutoff, cutoff),
                "prev_human": qs.sum_range(
                    "downloads_daily_human", prev_cutoff, cutoff
                ),
                "daily": daily,
                "version_daily": version_daily,
                "installers": installers,
                "countries": countries,
                "versions": versions,
                "types": dist_types,
                "releases": release_map,
                "all_events": all_events,
            }


# ---------------------------------------------------------------------------
# Tab 5: Docs (Plausible)
# ---------------------------------------------------------------------------


class DocsTab(InsightsTab):
    """Docs analytics from Plausible with date range and event annotations."""

    _default_days = 7

    def _build_content(self) -> None:
        """Build or rebuild all content."""
        data = self._data
        daily = data["daily"]

        last_collected = data.get("last_collected", "")
        content: list[ft.Control] = [
            self._make_filter_bar(last_updated=last_collected),
            ft.Container(height=8),
        ]

        if not daily:
            content.append(
                SecondaryText(
                    "No Plausible data collected yet. Run: my-app insights collect plausible"
                )
            )
            self._content_column.controls = content
            return

        # Aggregates over range
        total_visitors = sum(d["visitors"] for d in daily)
        total_pageviews = sum(d["pageviews"] for d in daily)
        num_days = len(daily)
        avg_bounce = sum(d["bounce_rate"] for d in daily) / num_days if num_days else 0
        avg_duration = (
            sum(d["avg_duration"] for d in daily) / num_days if num_days else 0
        )
        views_per_visit = total_pageviews / total_visitors if total_visitors else 0
        duration_min = int(avg_duration // 60)
        duration_sec = int(avg_duration % 60)

        # Period-over-period change
        prev_v = data.get("prev_visitors", 0)
        prev_pv = data.get("prev_pageviews", 0)
        prev_b = data.get("prev_bounce", 0)
        prev_d = data.get("prev_duration", 0)

        # Metric cards with change arrows
        content.append(
            ft.Row(
                [
                    MetricCard(
                        "Visitors",
                        f"{total_visitors:,}",
                        Theme.Colors.PRIMARY,
                        change_pct=_pct(total_visitors, prev_v),
                    ),
                    MetricCard(
                        "Pageviews",
                        f"{total_pageviews:,}",
                        Theme.Colors.INFO,
                        change_pct=_pct(total_pageviews, prev_pv),
                    ),
                    MetricCard(
                        "Views/Visit", f"{views_per_visit:.1f}", Theme.Colors.SUCCESS
                    ),
                    MetricCard(
                        "Bounce Rate",
                        f"{avg_bounce:.0f}%",
                        Theme.Colors.WARNING if avg_bounce > 50 else Theme.Colors.INFO,
                        change_pct=_pct(avg_bounce, prev_b),
                        invert=True,
                    ),
                    MetricCard(
                        "Avg Duration",
                        f"{duration_min}m {duration_sec}s",
                        "#A855F7",
                        change_pct=_pct(avg_duration, prev_d),
                    ),
                ],
                spacing=Theme.Spacing.MD,
            )
        )

        # Date range
        date_range = (
            f"{_pretty_date(daily[0]['date'])} \u2014 {_pretty_date(daily[-1]['date'])}"
        )
        content.append(SecondaryText(date_range, size=Theme.Typography.BODY_SMALL))

        # Event chips — only on days with visitor activity
        active_dates = {d["date"] for d in daily}
        chips = self._render_event_chips(
            data.get("all_events", []), valid_dates=active_dates
        )
        if chips:
            content.append(chips)

        content.append(ft.Container(height=4))

        # Visitors + Pageviews chart
        highlighted = self._highlighted_dates
        releases_map = {
            day: label
            for day, label in (
                data.get("releases", {}) if self._show_events else {}
            ).items()
            if day in active_dates
        }

        max_val = max(
            max(d["pageviews"] for d in daily), max(d["visitors"] for d in daily)
        )
        step = _smart_step(max_val)
        max_y = int((max_val // step + 1) * step)

        visitor_points: list[ft.LineChartDataPoint] = []
        pageview_points: list[ft.LineChartDataPoint] = []
        release_anno: list[ft.LineChartDataPoint] = []

        for i, d in enumerate(daily):
            is_hl = d["date"] in highlighted
            hl_point = (
                ft.ChartCirclePoint(
                    radius=7, color="#FF5722", stroke_width=2, stroke_color="#FFFFFF"
                )
                if is_hl
                else None
            )

            visitor_points.append(
                ft.LineChartDataPoint(
                    i,
                    d["visitors"],
                    tooltip=f"Visitors: {d['visitors']}",
                    point=hl_point,
                )
            )
            pageview_points.append(
                ft.LineChartDataPoint(
                    i,
                    d["pageviews"],
                    tooltip=f"Pageviews: {d['pageviews']}",
                )
            )

            rel = releases_map.get(d["date"])
            if rel:
                release_anno.append(
                    ft.LineChartDataPoint(i, 0, tooltip=rel, show_tooltip=True)
                )
            else:
                release_anno.append(ft.LineChartDataPoint(i, 0, show_tooltip=False))

        chart_series = [
            ft.LineChartData(
                data_points=visitor_points,
                stroke_width=2,
                color="#6366F1",
                curved=True,
                below_line_bgcolor=ft.Colors.with_opacity(0.15, "#6366F1"),
                point=ft.ChartCirclePoint(
                    radius=3, color=ft.Colors.ON_SURFACE, stroke_width=0
                ),
                stroke_cap_round=True,
            ),
            ft.LineChartData(
                data_points=pageview_points,
                stroke_width=2,
                color="#22C55E",
                curved=True,
                point=ft.ChartCirclePoint(
                    radius=3, color=ft.Colors.ON_SURFACE, stroke_width=0
                ),
                stroke_cap_round=True,
            ),
        ]
        if any(p.show_tooltip for p in release_anno):
            chart_series.append(
                ft.LineChartData(
                    data_points=release_anno,
                    stroke_width=0,
                    color="#9CA3AF",
                )
            )

        chart = _make_line_chart(chart_series, max_y, daily, step)
        content.append(ft.Container(content=chart, margin=ft.margin.only(right=20)))
        content.append(
            _make_legend([("#6366F1", "Visitors"), ("#22C55E", "Pageviews")])
        )

        # Country breakdown — horizontal bar chart
        countries = data.get("countries", [])
        if countries:
            content.append(ft.Container(height=12))
            content.append(H3Text("Countries"))

            max_visitors = countries[0]["visitors"] if countries else 1
            country_bar_groups = []
            country_labels = []
            for i, c in enumerate(countries):
                country_bar_groups.append(
                    ft.BarChartGroup(
                        x=i,
                        bar_rods=[
                            ft.BarChartRod(
                                from_y=0,
                                to_y=c["visitors"],
                                width=max(12, 300 // max(len(countries), 1)),
                                color="#6366F1",
                                border_radius=ft.border_radius.only(
                                    top_left=3, top_right=3
                                ),
                                tooltip=f"{c['country']}: {c['visitors']}",
                            )
                        ],
                    )
                )
                country_labels.append(c["country"])

            country_step = _smart_step(max_visitors)
            country_max_y = int((max_visitors // country_step + 1) * country_step)

            country_chart = ft.BarChart(
                bar_groups=country_bar_groups,
                left_axis=ft.ChartAxis(labels_size=50, labels_interval=country_step),
                bottom_axis=ft.ChartAxis(
                    labels_size=50,
                    labels=[
                        ft.ChartAxisLabel(
                            value=i,
                            label=ft.Text(
                                lbl, size=9, color=ft.Colors.ON_SURFACE_VARIANT
                            ),
                        )
                        for i, lbl in enumerate(country_labels)
                    ],
                ),
                horizontal_grid_lines=ft.ChartGridLines(
                    interval=country_step,
                    color=ft.Colors.with_opacity(0.08, ft.Colors.ON_SURFACE),
                    width=1,
                ),
                tooltip_bgcolor=Theme.Colors.SURFACE_1,
                tooltip_rounded_radius=8,
                tooltip_padding=10,
                tooltip_tooltip_border_side=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
                border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
                max_y=country_max_y,
                height=250,
                expand=True,
            )

            content.append(
                ft.Container(content=country_chart, margin=ft.margin.only(right=20))
            )

        # Top Pages table
        top_pages = data.get("top_pages", [])
        if top_pages:
            content.append(ft.Container(height=12))
            content.append(H3Text("Top Pages"))
            content.append(ft.Divider(height=1, color=ft.Colors.OUTLINE_VARIANT))
            for p in top_pages:
                page_url = f"https://lbedner.github.io{p['url']}"
                duration = p.get("time_s") or 0
                d_min = int(duration // 60)
                d_sec = int(duration % 60)
                content.append(
                    ft.Row(
                        [
                            ft.Container(
                                content=ft.Text(
                                    p["url"],
                                    size=Theme.Typography.BODY_SMALL,
                                    style=ft.TextStyle(
                                        color=Theme.Colors.INFO,
                                        decoration=ft.TextDecoration.UNDERLINE,
                                    ),
                                    selectable=False,
                                ),
                                expand=True,
                                on_click=lambda e, u=page_url: e.page.launch_url(u),
                                ink=True,
                            ),
                            SecondaryText(
                                f"{p['visitors']} visitors",
                                size=Theme.Typography.BODY_SMALL,
                            ),
                            SecondaryText(
                                f"{d_min}m {d_sec}s", size=Theme.Typography.BODY_SMALL
                            ),
                        ],
                        spacing=8,
                    )
                )

        self._content_column.controls = content

    @staticmethod
    def _load_data(days: int = 30) -> dict[str, Any]:
        """Load Plausible data from database."""
        from app.services.insights.query_service import InsightQueryService

        with InsightQueryService() as qs:
            cutoff, prev_cutoff = qs.compute_cutoffs(days)

            # Daily metrics - current period
            visitors_rows = qs.get_daily("visitors", cutoff)
            pageviews_rows = qs.get_daily("pageviews", cutoff)
            duration_rows = qs.get_daily("avg_duration", cutoff)
            bounce_rows = qs.get_daily("bounce_rate", cutoff)

            # Previous period totals for comparison
            prev_visitors = qs.sum_range("visitors", prev_cutoff, cutoff)
            prev_pageviews = qs.sum_range("pageviews", prev_cutoff, cutoff)
            prev_dur_rows = qs.get_daily_range("avg_duration", prev_cutoff, cutoff)
            prev_duration = (
                sum(float(r.value) for r in prev_dur_rows) / len(prev_dur_rows)
                if prev_dur_rows
                else 0
            )
            prev_bounce_rows = qs.get_daily_range("bounce_rate", prev_cutoff, cutoff)
            prev_bounce = (
                sum(float(r.value) for r in prev_bounce_rows) / len(prev_bounce_rows)
                if prev_bounce_rows
                else 0
            )

            pv_map = {str(r.date)[:10]: int(r.value) for r in pageviews_rows}
            dur_map = {str(r.date)[:10]: float(r.value) for r in duration_rows}
            bounce_map = {str(r.date)[:10]: float(r.value) for r in bounce_rows}

            daily: list[dict[str, Any]] = []
            last_collected = ""
            for r in visitors_rows:
                day = str(r.date)[:10]
                last_collected = day
                daily.append(
                    {
                        "date": day,
                        "visitors": int(r.value),
                        "pageviews": pv_map.get(day, 0),
                        "avg_duration": dur_map.get(day, 0),
                        "bounce_rate": bounce_map.get(day, 0),
                    }
                )

            # Top pages - aggregate per-day snapshots across selected range
            all_pages: dict[str, dict[str, Any]] = {}
            for r in qs.get_daily("top_pages", cutoff):
                meta = r.metadata_ if isinstance(r.metadata_, dict) else {}
                for p in meta.get("pages", []):
                    url = p.get("url", "")
                    if url not in all_pages:
                        all_pages[url] = {"url": url, "visitors": 0, "time_s": 0}
                    all_pages[url]["visitors"] += p.get("visitors", 0)
                    all_pages[url]["time_s"] += p.get("time_s") or 0
            top_pages = sorted(all_pages.values(), key=lambda x: -x["visitors"])[:20]

            # Countries - aggregate per-day snapshots across selected range
            all_countries: dict[str, int] = {}
            for r in qs.get_daily("top_countries", cutoff):
                meta = r.metadata_ if isinstance(r.metadata_, dict) else {}
                for c in meta.get("countries", []):
                    code = c.get("country", "")
                    all_countries[code] = all_countries.get(code, 0) + c.get(
                        "visitors", 0
                    )
            countries = [
                {"country": code, "visitors": count}
                for code, count in sorted(all_countries.items(), key=lambda x: -x[1])
            ][:20]

            # Events
            all_events: list[tuple[str, str, str]] = []
            for r in qs.get_release_metrics():
                tag = (r.metadata_ or {}).get("tag", "")
                if tag:
                    all_events.append((str(r.date)[:10], tag, "release"))
            for ev in qs.get_insight_events(
                cutoff=cutoff, type_filter=DOCS_EVENT_TYPES
            ):
                all_events.append(
                    (str(ev.date)[:10], ev.description[:60], ev.event_type)
                )

            release_map: dict[str, str] = {}
            for date, label, _ in all_events:
                if date in release_map:
                    release_map[date] += f"\n{label}"
                else:
                    release_map[date] = label

            all_events.sort(key=lambda x: x[0])

            return {
                "daily": daily,
                "top_pages": top_pages,
                "countries": countries,
                "all_events": all_events,
                "releases": release_map,
                "prev_visitors": prev_visitors,
                "prev_pageviews": prev_pageviews,
                "prev_bounce": prev_bounce,
                "prev_duration": prev_duration,
                "last_collected": last_collected,
            }


# ---------------------------------------------------------------------------
# Tab 6: Reddit
# ---------------------------------------------------------------------------


class RedditTab(ft.Container):
    """Reddit: tracked post stats from database."""

    def __init__(self) -> None:
        super().__init__()

        posts = self._load_posts()

        if not posts:
            self.content = ft.Column(
                [
                    SecondaryText(
                        "No Reddit posts tracked. Use: my-app insights reddit add <url>"
                    )
                ],
                scroll=ft.ScrollMode.AUTO,
            )
            self.padding = Theme.Spacing.MD
            self.expand = True
            return

        last_date = posts[0]["date"] if posts else ""
        content: list[ft.Control] = [
            SecondaryText(
                f"Last updated: {last_date}" if last_date else "",
                size=Theme.Typography.BODY_SMALL,
            ),
            ft.Container(height=4),
        ]

        for post in posts:
            meta = post.get("metadata", {})
            subreddit = meta.get("subreddit", "")
            title = meta.get("title", "")
            comments = meta.get("comments", 0)
            upvote_ratio = meta.get("upvote_ratio", 0)
            url = meta.get("url", "")
            upvotes = post.get("upvotes", 0)
            date = post.get("date", "")

            # Post card — compact layout
            post_card = ft.Container(
                content=ft.Column(
                    [
                        # Row 1: subreddit + date + stats
                        ft.Row(
                            [
                                ft.Container(
                                    content=LabelText(
                                        f"r/{subreddit}", color=Theme.Colors.BADGE_TEXT
                                    ),
                                    bgcolor="#FF5722",
                                    padding=ft.padding.symmetric(
                                        horizontal=6, vertical=2
                                    ),
                                    border_radius=4,
                                ),
                                SecondaryText(
                                    _pretty_date(date), size=Theme.Typography.BODY_SMALL
                                ),
                                ft.Container(expand=True),
                                ft.Text(
                                    f"{upvotes:,}",
                                    size=13,
                                    weight=ft.FontWeight.W_700,
                                    color="#FF5722",
                                ),
                                SecondaryText("upvotes", size=Theme.Typography.CAPTION),
                                ft.Container(width=8),
                                ft.Text(
                                    str(comments),
                                    size=13,
                                    weight=ft.FontWeight.W_700,
                                    color=Theme.Colors.INFO,
                                ),
                                SecondaryText(
                                    "comments", size=Theme.Typography.CAPTION
                                ),
                                ft.Container(width=8),
                                ft.Text(
                                    f"{upvote_ratio:.0%}",
                                    size=13,
                                    weight=ft.FontWeight.W_700,
                                    color=Theme.Colors.SUCCESS
                                    if upvote_ratio and upvote_ratio > 0.9
                                    else Theme.Colors.WARNING,
                                ),
                            ],
                            spacing=4,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        # Row 2: title as hyperlink
                        ft.Text(
                            spans=[
                                ft.TextSpan(
                                    title,
                                    style=ft.TextStyle(
                                        size=13,
                                        decoration=ft.TextDecoration.UNDERLINE,
                                        color=Theme.Colors.PRIMARY,
                                    ),
                                    url=url,
                                ),
                            ],
                        )
                        if url
                        else BodyText(title),
                    ],
                    spacing=6,
                ),
                padding=ft.padding.all(10),
                border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
                border_radius=8,
            )

            content.append(post_card)

        self.content = ft.Column(
            content,
            spacing=12,
            scroll=ft.ScrollMode.AUTO,
        )
        self.padding = Theme.Spacing.MD
        self.expand = True

    @staticmethod
    def _load_posts() -> list[dict]:
        """Load Reddit posts from database (sync)."""
        from app.services.insights.query_service import InsightQueryService

        with InsightQueryService() as qs:
            rows = qs.get_all_metrics("post_stats")
            if not rows:
                return []

            # Get original post dates from events
            event_dates: dict[str, str] = {}
            for ev in qs.get_insight_events(type_filter={"reddit_post"}):
                pid = (ev.metadata_ or {}).get("post_id", "")
                if pid and pid not in event_dates:
                    event_dates[pid] = str(ev.date)[:10]

            # Group by post_id, take latest snapshot per post
            seen: set[str] = set()
            posts = []
            for r in rows:
                meta = r.metadata_ or {}
                post_id = meta.get("post_id", "")
                if post_id in seen:
                    continue
                seen.add(post_id)
                original_date = event_dates.get(post_id, str(r.date)[:10])
                posts.append(
                    {
                        "upvotes": int(r.value),
                        "date": original_date,
                        "metadata": meta,
                    }
                )

            return posts


# ---------------------------------------------------------------------------
# Modal
# ---------------------------------------------------------------------------


def _group_events(
    events: list[tuple[str, str, str]],
    days: int,
) -> list[tuple[str, str, str, set[str]]]:
    """Group same-type events by time bucket for cleaner display.

    Returns list of (display_date, label, type, dates_set).
    At small ranges (<=30d), no grouping — each event gets its own chip.
    """
    import re
    from datetime import datetime as dt

    # Always return with dates_set for consistent interface
    if days <= 30 or not events:
        return [(date, label, etype, {date}) for date, label, etype in events]

    # Determine bucket size
    if days <= 90:

        def bucket_key(date_str: str) -> str:
            d = dt.strptime(date_str, "%Y-%m-%d")
            # ISO week: YYYY-WNN
            return f"{d.isocalendar()[0]}-W{d.isocalendar()[1]:02d}"
    else:

        def bucket_key(date_str: str) -> str:
            return date_str[:7]  # YYYY-MM

    # Group by (bucket, type)
    buckets: dict[tuple[str, str], list[tuple[str, str]]] = {}
    for date, label, etype in events:
        key = (bucket_key(date), etype)
        buckets.setdefault(key, []).append((date, label))

    result: list[tuple[str, str, str, set[str]]] = []
    for (_, etype), items in buckets.items():
        dates = {d for d, _ in items}
        first_date = min(dates)

        if len(items) == 1:
            result.append((items[0][0], items[0][1], etype, dates))
            continue

        if etype == "release":
            tags = [lbl for _, lbl in sorted(items)]
            label = f"{tags[0]}\u2013{tags[-1]}" if len(tags) > 1 else tags[0]
        elif etype == "star":
            # Extract star numbers from labels like "⭐ #80-#85 (6 stars)" or "⭐ #99 — user"
            nums: list[int] = []
            for _, lbl in items:
                for m in re.findall(r"#(\d+)", lbl):
                    nums.append(int(m))
            if nums:
                label = f"\u2b50 #{min(nums)}-#{max(nums)} ({len(items)} events)"
            else:
                label = f"\u2b50 ({len(items)} stars)"
        elif etype == "reddit_post":
            # Keep individual reddit posts — don't group
            for date, lbl in items:
                result.append((date, lbl, etype, {date}))
            continue
        else:
            label = f"{etype} ({len(items)})"

        result.append((first_date, label, etype, dates))

    result.sort(key=lambda x: x[0])
    return result


def _extract_max_number(text: str) -> str:
    """Extract the largest number from a text string (e.g., '5,292 clones' -> '5,292')."""
    import re

    numbers = re.findall(r"\d[\d,]*", text)
    if not numbers:
        return ""
    return max(numbers, key=lambda n: int(n.replace(",", "")))


def _smart_step(max_val: float) -> int:
    """Pick a nice y-axis interval based on magnitude."""
    if max_val <= 20:
        return 5
    if max_val <= 100:
        return 10
    if max_val <= 500:
        return 50
    return 100


def _pretty_date(date_str: str) -> str:
    """Format '2026-04-03' as 'April 3rd, 2026'."""
    from datetime import datetime as dt

    try:
        d = dt.strptime(date_str, "%Y-%m-%d")
    except (ValueError, TypeError):
        return date_str

    day = d.day
    if 11 <= day <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    return d.strftime(f"%B {day}{suffix}, %Y")


class SettingsTab(ft.Container):
    """Settings: data sources, collection status, metric counts."""

    def __init__(self, metadata: dict[str, Any], db: dict[str, Any]) -> None:
        super().__init__()

        total_metrics = metadata.get("total_metrics", 0)
        enabled_sources = metadata.get("enabled_sources", 0)
        stale_sources = metadata.get("stale_sources", [])
        sources_meta = metadata.get("sources", {})

        content: list[ft.Control] = [
            ft.Row(
                [
                    MetricCard(
                        "Total Metrics", f"{total_metrics:,}", Theme.Colors.PRIMARY
                    ),
                    MetricCard(
                        "Active Sources", str(enabled_sources), Theme.Colors.SUCCESS
                    ),
                ],
                spacing=Theme.Spacing.MD,
            ),
            ft.Container(height=8),
            H3Text("Data Sources"),
            ft.Divider(height=1, color=ft.Colors.OUTLINE_VARIANT),
        ]

        for src in db["sources"]:
            is_stale = src["key"] in stale_sources
            if src["enabled"]:
                status_text = "Stale" if is_stale else "Active"
                status_color = "#F59E0B" if is_stale else "#22C55E"
            else:
                status_text = "Disabled"
                status_color = ft.Colors.ON_SURFACE_VARIANT

            # Last collected time from health metadata
            src_meta = sources_meta.get(src["key"], {})
            last_collected = src_meta.get("last_collected", "")
            if last_collected:
                last_collected = last_collected[:16].replace("T", " ")

            content.append(
                ft.Row(
                    [
                        ft.Container(
                            content=BodyText(
                                src["display_name"], size=Theme.Typography.BODY_SMALL
                            ),
                            width=140,
                        ),
                        ft.Container(
                            content=LabelText(
                                status_text, color=Theme.Colors.BADGE_TEXT
                            ),
                            bgcolor=status_color,
                            padding=ft.padding.symmetric(horizontal=6, vertical=2),
                            border_radius=4,
                        ),
                        SecondaryText(
                            f"Last: {last_collected}" if last_collected else "",
                            size=Theme.Typography.BODY_SMALL,
                        ),
                    ],
                    spacing=8,
                )
            )

        self.content = ft.Column(
            content,
            spacing=8,
            scroll=ft.ScrollMode.AUTO,
        )
        self.padding = Theme.Spacing.MD
        self.expand = True


class InsightsDetailDialog(BaseDetailPopup):
    """Insights service detail modal with tabbed interface."""

    def __init__(self, component_data: ComponentStatus, page: ft.Page) -> None:
        metadata: dict[str, Any] = component_data.metadata or {}

        # Single DB load shared by Overview, GitHub, and Stars tabs
        db = _load_db()

        tabs_list = [
            ft.Tab(text="Overview", content=OverviewTab(metadata, db)),
            ft.Tab(text="GitHub", content=GitHubTrafficTab()),
            ft.Tab(text="Stars", content=StarsTab()),
            ft.Tab(text="PyPI", content=PyPITab()),
            ft.Tab(text="Docs", content=DocsTab()),
            ft.Tab(text="Reddit", content=RedditTab()),
            ft.Tab(text="Settings", content=SettingsTab(metadata, db)),
        ]

        tabs = ft.Tabs(
            selected_index=0,
            animation_duration=200,
            tabs=tabs_list,
            expand=True,
            label_color=ft.Colors.ON_SURFACE,
            unselected_label_color=ft.Colors.ON_SURFACE_VARIANT,
            indicator_color=ft.Colors.ON_SURFACE_VARIANT,
        )

        super().__init__(
            page=page,
            component_data=component_data,
            title_text=get_component_title("service_insights"),
            subtitle_text=get_component_subtitle("service_insights", metadata),
            sections=[
                ft.Container(
                    content=tabs,
                    padding=ft.padding.symmetric(horizontal=60),
                    expand=True,
                )
            ],
            scrollable=False,
            status_detail=get_status_detail(component_data),
            width=1500,
            height=850,
        )
