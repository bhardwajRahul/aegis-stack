"""
Reusable Modal Section Components

Provides commonly used section patterns across component detail modals:
- MetricCardSection: Display key metrics in card grid
- StatRowsSection: Label/value pairs for detailed information
- EmptyStatePlaceholder: Consistent "no data" messaging
- PieChartCard: Donut chart with legend
- FlowConnector: Vertical arrow between flow sections
- LifecycleInspector: Right-side inspector panel for lifecycle details
- LifecycleCard: Clickable card for lifecycle items
- FlowSection: Labeled section in a lifecycle flow diagram
"""

from __future__ import annotations

import contextlib  # noqa: I001
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import flet as ft
from app.components.frontend.controls import (
    BodyText,
    H3Text,
    LabelText,
    PrimaryText,
    SecondaryText,
    Tag,
)
from app.components.frontend.theme import AegisTheme as Theme
from app.components.frontend.theme import DarkColorPalette


def format_duration_ms(duration_ms: int | float | str | None) -> str:
    """Format milliseconds to human-readable duration (e.g., '1.2s', '3m 45s')."""
    if not duration_ms:
        return "\u2014"
    try:
        ms = float(duration_ms)
        if ms < 1000:
            return f"{ms:.0f}ms"
        s = ms / 1000
        if s < 60:
            return f"{s:.1f}s"
        m = int(s // 60)
        s = s % 60
        return f"{m}m {s:.0f}s"
    except (ValueError, TypeError):
        return "\u2014"


def format_timestamp(iso_str: str | None) -> str:
    """Format ISO timestamp for display (HH:MM:SS)."""
    if not iso_str:
        return "\u2014"
    try:
        from datetime import datetime

        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%H:%M:%S")
    except (ValueError, TypeError):
        return "\u2014"


class InfoCard(ft.Container):
    """Info card displaying a label and value with consistent card styling."""

    def __init__(
        self,
        label: str,
        value: str = "",
        tags: list[tuple[str, str]] | None = None,
    ) -> None:
        """
        Initialize info card.

        Args:
            label: Card label text (shown at top)
            value: Value to display (used if no tags provided)
            tags: Optional list of (text, color) tuples to show as tags
        """
        super().__init__()

        content_items: list[ft.Control] = [
            LabelText(label),
            ft.Container(height=Theme.Spacing.XS),
        ]

        if tags:
            # Show tags (e.g., provider badges)
            tag_controls = [Tag(text=t, color=c) for t, c in tags]
            content_items.append(
                ft.Row(
                    tag_controls,
                    spacing=4,
                    wrap=True,
                    alignment=ft.MainAxisAlignment.CENTER,
                )
            )
        else:
            # Show value as body text
            content_items.append(BodyText(value))

        self.content = ft.Column(
            content_items,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=0,
        )
        self.padding = Theme.Spacing.MD
        self.bgcolor = ft.Colors.SURFACE_CONTAINER_HIGHEST
        self.border_radius = Theme.Components.CARD_RADIUS
        self.border = ft.border.all(0.5, ft.Colors.OUTLINE)
        self.expand = True


class MetricCard(ft.Container):
    """Reusable metric display card with icon, label, and colored value."""

    def __init__(
        self,
        label: str,
        value: str,
        color: str,
        icon: str | None = None,
        change_pct: float | None = None,
        invert: bool = False,
        prev_value: str | None = None,
        tooltip: str | None = None,
    ) -> None:
        """
        Initialize metric card.

        Args:
            label: Metric label text
            value: Metric value to display
            color: Color for the value text
            icon: Optional icon name (e.g., ft.Icons.TOKEN)
            change_pct: Optional period-over-period change percentage
            invert: If True, down is good (green) and up is bad (red) — e.g., bounce rate
            prev_value: Optional previous period value to display (e.g., "prev: 3,080")
        """  # noqa: E501
        super().__init__()

        # Header row with icon and label
        header_items: list[ft.Control] = []
        if icon:
            header_items.append(ft.Icon(icon, size=16, color=color))
        header_items.append(SecondaryText(label))

        header_row = ft.Row(
            header_items,
            spacing=6,
        )

        # Value text — stored as instance attribute for live updates
        self.value_text = ft.Text(
            value,
            size=24,
            weight=ft.FontWeight.W_600,
        )

        # Value row: number + optional change arrow inline
        value_items: list[ft.Control] = [self.value_text]
        if change_pct is not None:
            # When invert=True, up is bad (red) and down is good (green)
            if change_pct > 0:
                arrow_icon = ft.Icons.NORTH_EAST
                arrow_color = Theme.Colors.ERROR if invert else Theme.Colors.SUCCESS
            elif change_pct < 0:
                arrow_icon = ft.Icons.SOUTH_EAST
                arrow_color = Theme.Colors.SUCCESS if invert else Theme.Colors.ERROR
            else:
                arrow_icon = ft.Icons.EAST
                arrow_color = ft.Colors.ON_SURFACE_VARIANT
            value_items.append(
                ft.Row(
                    [
                        ft.Icon(arrow_icon, size=14, color=arrow_color),
                        ft.Text(
                            f"{abs(change_pct):.0f}%",
                            size=14,
                            color=arrow_color,
                            weight=ft.FontWeight.W_600,
                        ),
                    ],
                    spacing=2,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                )
            )

        value_row = ft.Row(
            value_items, spacing=6, vertical_alignment=ft.CrossAxisAlignment.END
        )

        column_items = [header_row, value_row]
        if prev_value is not None:
            column_items.append(
                SecondaryText(prev_value, size=Theme.Typography.BODY_SMALL)
            )

        self.content = ft.Column(
            column_items,
            spacing=Theme.Spacing.XS,
        )
        self.padding = Theme.Spacing.MD
        self.bgcolor = ft.Colors.SURFACE_CONTAINER_HIGHEST
        self.border_radius = Theme.Components.CARD_RADIUS
        self.border = ft.border.all(0.5, ft.Colors.OUTLINE)
        self.expand = True
        if tooltip:
            self.tooltip = tooltip

    def set_value(self, value: str, color: str | None = None) -> None:
        """Update the displayed value (and optionally its color) in place."""
        self.value_text.value = value
        if color is not None:
            self.value_text.color = color


class MilestoneCard(ft.Container):
    """Trophy-style card for key milestones with hero number."""

    def __init__(
        self,
        label: str,
        value: str,
        date: str,
        accent_color: str = "#9CA3AF",
    ) -> None:
        super().__init__()

        items: list[ft.Control] = [SecondaryText(label)]
        if value and value != "\u2014":
            items.append(
                ft.Text(
                    value,
                    size=28,
                    weight=ft.FontWeight.W_700,
                    color=accent_color,
                )
            )
        items.append(SecondaryText(date, size=Theme.Typography.BODY_SMALL))

        self.content = ft.Column(
            items,
            spacing=2,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
        )
        self.padding = Theme.Spacing.MD
        self.bgcolor = ft.Colors.SURFACE_CONTAINER_HIGHEST
        self.border_radius = Theme.Components.CARD_RADIUS
        self.border = ft.border.all(0.5, ft.Colors.OUTLINE)
        self.height = 130
        self.expand = True


class SectionHeader(ft.Row):
    """Section header with icon and title."""

    def __init__(
        self,
        title: str,
        icon: str | None = None,
        color: str | None = None,
    ) -> None:
        """
        Initialize section header.

        Args:
            title: Section title text
            icon: Optional icon name
            color: Optional icon color (defaults to secondary text color)
        """
        items: list[ft.Control] = []
        if icon:
            items.append(
                ft.Icon(icon, size=18, color=color or ft.Colors.ON_SURFACE_VARIANT)
            )
        items.append(H3Text(title))

        super().__init__(items, spacing=8)


class MetricCardSection(ft.Container):
    """
    Reusable section for displaying metric cards in a grid.

    Creates a titled section with metric cards displayed in a horizontal row.
    Each metric is rendered using the MetricCard component.
    """

    def __init__(self, title: str, metrics: list[dict[str, str]]) -> None:
        """
        Initialize metric card section.

        Args:
            title: Section title
            metrics: List of metric dicts with keys: label, value, color
                     Example: [{"label": "Total", "value": "42", "color": "#00ff00"}]
        """
        super().__init__()

        cards = []
        for metric in metrics:
            cards.append(
                MetricCard(
                    label=metric["label"],
                    value=metric["value"],
                    color=metric["color"],
                )
            )

        self.content = ft.Column(
            [
                H3Text(title),
                ft.Container(height=Theme.Spacing.SM),
                ft.Row(cards, spacing=Theme.Spacing.MD),
            ],
            spacing=0,
        )
        self.padding = Theme.Spacing.MD


class StatRowsSection(ft.Container):
    """
    Reusable section for displaying label/value pairs.

    Creates a titled section with statistics displayed as label: value rows.
    Common pattern for detailed component information.
    """

    def __init__(
        self,
        title: str,
        stats: dict[str, str],
        label_width: int = 150,
    ) -> None:
        """
        Initialize stat rows section.

        Args:
            title: Section title
            stats: Dictionary of label: value pairs
            label_width: Width for label column (default: 150px)
        """
        super().__init__()

        rows = []
        for label, value in stats.items():
            rows.append(
                ft.Row(
                    [
                        SecondaryText(
                            f"{label}:",
                            weight=Theme.Typography.WEIGHT_SEMIBOLD,
                            width=label_width,
                        ),
                        BodyText(value),
                    ],
                    spacing=Theme.Spacing.MD,
                )
            )

        self.content = ft.Column(
            [
                H3Text(title),
                ft.Container(height=Theme.Spacing.SM),
                ft.Column(rows, spacing=Theme.Spacing.SM),
            ],
            spacing=0,
        )
        self.padding = Theme.Spacing.MD


class EmptyStatePlaceholder(ft.Container):
    """
    Reusable placeholder for empty states.

    Displays a consistent message when no data is available,
    using theme colors and spacing.
    """

    def __init__(
        self,
        message: str,
    ) -> None:
        """
        Initialize empty state placeholder.

        Args:
            message: Message to display
        """
        super().__init__()

        self.content = ft.Row(
            [
                SecondaryText(
                    message,
                    size=Theme.Typography.BODY_LARGE,
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=Theme.Spacing.MD,
        )
        self.padding = Theme.Spacing.XL
        self.bgcolor = (
            ft.Colors.SURFACE_CONTAINER_HIGHEST
        )  # Elevated surface for contrast
        self.border_radius = Theme.Components.CARD_RADIUS
        self.border = ft.border.all(1, ft.Colors.OUTLINE)


# Color palette for pie chart segments (distinct, visually appealing colors)
PIE_CHART_COLORS = [
    DarkColorPalette.ACCENT,  # Teal
    "#22C55E",  # Green
    "#F5A623",  # Orange/Amber
    "#A855F7",  # Purple
    "#3B82F6",  # Blue
    "#EC4899",  # Pink
    "#6366F1",  # Indigo
    "#14B8A6",  # Cyan
]


class PieChartCard(ft.Container):
    """
    Reusable pie chart card with title, donut chart, and legend.

    Provides consistent styling matching the React reference design.
    Features interactive hover effects with segment expansion and tooltips.
    """

    # Segment radius constants (must fit within chart container)
    NORMAL_RADIUS = 45
    HOVER_RADIUS = 52

    def __init__(
        self,
        title: str,
        sections: list[dict[str, Any]],
    ) -> None:
        """
        Initialize pie chart card.

        Args:
            title: Card title
            sections: List of dicts with keys: value, label (color is auto-assigned)
                      Example: [{"value": 100, "label": "Input (50%)"}]
        """
        super().__init__()

        self._section_labels: list[str] = []
        self._section_values: list[float] = []
        self._hovered_index: int | None = None

        if not sections:
            self.content = ft.Column(
                [
                    SecondaryText(title),
                    ft.Container(
                        content=SecondaryText("No data", size=13),
                        expand=True,
                        alignment=ft.alignment.center,
                    ),
                ],
                spacing=0,
                expand=True,
            )
            self._setup_card_style()
            return

        # Build pie chart sections with auto-assigned colors
        self._pie_sections: list[ft.PieChartSection] = []
        legend_items: list[ft.Row] = []

        for i, section in enumerate(sections):
            value = float(section.get("value", 0))
            # Use provided color or auto-assign from palette
            color = section.get("color") or PIE_CHART_COLORS[i % len(PIE_CHART_COLORS)]
            label = str(section.get("label", ""))

            # Store for tooltips
            self._section_labels.append(label)
            self._section_values.append(value)

            self._pie_sections.append(
                ft.PieChartSection(
                    value=value,
                    title="",
                    color=color,
                    radius=self.NORMAL_RADIUS,
                )
            )
            legend_items.append(self._legend_item(label, color))

        # Donut chart with hover interaction
        self._pie_chart = ft.PieChart(
            sections=self._pie_sections,
            sections_space=2,
            center_space_radius=28,
            on_chart_event=self._on_chart_event,
        )

        # Legend column
        legend = ft.Column(
            legend_items,
            spacing=Theme.Spacing.XS,
            alignment=ft.MainAxisAlignment.CENTER,
        )

        # Layout: chart + legend horizontal, centered
        chart_row = ft.Row(
            [
                ft.Container(
                    content=self._pie_chart,
                    width=130,
                    height=130,
                ),
                legend,
            ],
            spacing=Theme.Spacing.LG,
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        # Column layout with chart pushed down to avoid overlap
        self.content = ft.Column(
            [
                SecondaryText(title),
                ft.Container(
                    content=chart_row,
                    expand=True,
                    alignment=ft.alignment.center,
                    margin=ft.margin.only(top=Theme.Spacing.MD),
                ),
            ],
            spacing=0,
            expand=True,
        )
        self._setup_card_style()

    def _setup_card_style(self) -> None:
        """Apply consistent card styling."""
        self.bgcolor = ft.Colors.SURFACE_CONTAINER_HIGHEST
        self.border = ft.border.all(0.5, ft.Colors.OUTLINE)
        self.border_radius = Theme.Components.CARD_RADIUS
        self.padding = ft.padding.only(
            left=Theme.Spacing.MD,
            right=Theme.Spacing.MD,
            top=Theme.Spacing.SM,
            bottom=Theme.Spacing.SM,
        )
        self.height = 210
        self.expand = True
        self.clip_behavior = ft.ClipBehavior.HARD_EDGE

    def _on_chart_event(self, e: ft.PieChartEvent) -> None:
        """Handle hover events - expand hovered segment."""
        # Reset all sections to normal radius
        for section in self._pie_sections:
            section.radius = self.NORMAL_RADIUS

        # Check if hovering over a section (section_index is -1 when not hovering)
        idx = e.section_index
        if idx is not None and idx >= 0 and idx < len(self._pie_sections):
            self._pie_sections[idx].radius = self.HOVER_RADIUS
            self._hovered_index = idx
        else:
            self._hovered_index = None

        self._pie_chart.update()

    def _legend_item(self, label: str, color: str) -> ft.Row:
        """Create a legend item with color dot and label."""
        return ft.Row(
            [
                ft.Container(width=10, height=10, bgcolor=color, border_radius=5),
                SecondaryText(label, size=Theme.Typography.BODY_SMALL),
            ],
            spacing=8,
        )


# ---------------------------------------------------------------------------
# Date range chip strip
# ---------------------------------------------------------------------------


class DateRangeChips(ft.Container):
    """Row of small selectable pills for picking a date-range window.

    Mirrors the aegis-pulse `alpine_date_range` macro: tightly-padded
    chips with a light teal-fill / teal-border on the selected pill and
    the standard MetricCard surface treatment on the others. Owns its
    own selection state so the parent tab only has to wire up an
    ``on_change(days)`` callback - the in-place restyle on click stays
    inside the control.

    Example:
        chips = DateRangeChips(
            options=[("7d", 7), ("14d", 14), ("1m", 30), ("All", 9999)],
            selected_days=14,
            on_change=lambda d: tab._on_range_change(d),
        )
    """

    _BORDER_RADIUS = 4

    def __init__(
        self,
        *,
        options: list[tuple[str, int]],
        selected_days: int,
        on_change: Callable[[int], None],
    ) -> None:
        super().__init__()
        self._options = options
        self._selected_days = selected_days
        self._on_change = on_change

        self._chips: list[ft.Container] = []
        for label, days in options:
            self._chips.append(
                ft.Container(
                    content=ft.Text(
                        label,
                        size=11,
                        weight=self._weight(days == selected_days),
                        color=self._text_color(days == selected_days),
                    ),
                    bgcolor=self._bgcolor(days == selected_days),
                    border=self._border(days == selected_days),
                    border_radius=self._BORDER_RADIUS,
                    padding=ft.padding.symmetric(horizontal=10, vertical=4),
                    on_click=lambda _e, d=days: self._handle_click(d),
                    ink=True,
                )
            )

        self.content = ft.Row(self._chips, spacing=6)

    def set_selected(self, days: int) -> None:
        """Update the active pill in place without rebuilding."""
        self._selected_days = days
        for (_label, d), chip in zip(self._options, self._chips, strict=False):
            is_active = d == days
            chip.bgcolor = self._bgcolor(is_active)
            chip.border = self._border(is_active)
            chip.content.weight = self._weight(is_active)
            chip.content.color = self._text_color(is_active)

    def _handle_click(self, days: int) -> None:
        self.set_selected(days)
        self._on_change(days)

    @staticmethod
    def _bgcolor(is_active: bool) -> str:
        # Inactive pills sit on the page background (transparent) so the
        # range strip reads as outlined controls rather than a row of
        # cards - matches the aegis-pulse htmx version. Active pill
        # gets the light teal fill to mark the selection.
        return (
            ft.Colors.with_opacity(0.10, ChartColors.TEAL)
            if is_active
            else ft.Colors.TRANSPARENT
        )

    @staticmethod
    def _border(is_active: bool) -> ft.Border:
        return ft.border.all(0.5, ChartColors.TEAL if is_active else ft.Colors.OUTLINE)

    @staticmethod
    def _weight(is_active: bool) -> ft.FontWeight:
        return ft.FontWeight.W_600 if is_active else ft.FontWeight.W_400

    @staticmethod
    def _text_color(is_active: bool) -> str:
        return ft.Colors.ON_SURFACE if is_active else ft.Colors.ON_SURFACE_VARIANT


# ---------------------------------------------------------------------------
# Chart palette - exact tokens lifted from the aegis-pulse `THEME`
# (web_frontend/static/js/charts.js). Any chart in this codebase pulls
# its colors from here so the visual language stays in lockstep with
# the SaaS frontend; if the brand teal changes there, it changes here.
# ---------------------------------------------------------------------------


class ChartColors:
    """Aegis chart palette.

    The cool ramp (teal -> sky) is the data palette - primary series gets
    teal, the second series picks the next ramp color that gives the most
    perceptual separation. Warm signals (amber, success, error) stay
    sparing, reserved for highlight / delta semantics.
    """

    # Brand / primary
    TEAL = "#17CCBF"

    # Cool ramp - used in this order for multi-series charts
    CYAN = "#06B6D4"
    BLUE = "#3B82F6"
    INDIGO = "#6366F1"
    VIOLET = "#8B5CF6"
    PURPLE = "#A855F7"
    SKY = "#0EA5E9"

    # Warm signals - highlight / delta only, never the default series color
    AMBER = "#F59E0B"
    SUCCESS = "#22C55E"
    ERROR = "#EF4444"

    # Legacy aliases - kept so any code that referenced the older pink
    # accent for releases keeps rendering
    PINK = "#EC4899"

    # Muted fallback (also used as the secondary surface text token in
    # the htmx side; reused here as the palette's "neutral" slot)
    MUTED = "#7E8A9A"


def chart_tooltip_kwargs() -> dict[str, Any]:
    """Shared tooltip styling for any chart control (LineChart, BarChart).

    Filled SURFACE_1 panel with the same outline-variant border used by
    every card surface in the modal. Use as ``**kwargs`` on the chart
    constructor; chart-specific extras (e.g. LineChart's
    ``tooltip_show_on_top_of_chart_box_area``) layer in alongside.
    """
    # NB: Flet's constructor kwarg is `tooltip_tooltip_border_side` even
    # though the runtime attribute is `tooltip_border_side`. Passing the
    # short form raises `TypeError: ... got an unexpected keyword argument
    # 'tooltip_border_side'` on Flet 0.28. Keep the doubled prefix.
    return {
        "tooltip_bgcolor": Theme.Colors.SURFACE_1,
        "tooltip_tooltip_border_side": ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
        "tooltip_rounded_radius": 8,
        "tooltip_padding": 10,
        "tooltip_max_content_width": 200,
        "tooltip_fit_inside_vertically": True,
        "tooltip_fit_inside_horizontally": True,
    }


class ChartPoint:
    """Standard chart-point shapes used by every chart in the modal.

    ``ft.ChartCirclePoint`` is a Flet value type, not a Control - it can't
    be subclassed via the component model - so this class is a namespace
    of factory methods rather than a real custom control. Compose them
    directly into ``ft.LineChartData(point=...)`` or
    ``ft.LineChartDataPoint(point=...)`` so every chart in the project
    uses the same point geometry without re-defining radii/strokes inline.
    """

    @staticmethod
    def dot(color: str = ft.Colors.ON_SURFACE) -> ft.ChartCirclePoint:
        """Small marker drawn at every data point on a visible series.

        Default color is the on-surface foreground so the dots read on
        any line color. Pass the line color (or any other) to bias the
        dot toward / away from the curve.
        """
        return ft.ChartCirclePoint(radius=3, color=color, stroke_width=0)

    @staticmethod
    def highlight(
        color: str = ChartColors.AMBER,
    ) -> ft.ChartCirclePoint:
        """Larger marker for points that match a selected event chip on
        the parent tab. Stroked in the on-surface color so it pops on
        any series color underneath."""
        return ft.ChartCirclePoint(
            radius=7,
            color=color,
            stroke_width=2,
            stroke_color=ft.Colors.ON_SURFACE,
        )


# ---------------------------------------------------------------------------
# Line chart card
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LineSeries:
    """One line on a `LineChartCard`.

    `points` is a list of (x_index, y_value) pairs - x is the position
    on the shared date axis owned by the parent card, y is whatever the
    metric is. `tooltips` is parallel to `points`; ``None`` means no
    per-point tooltip.

    `fill=True` paints a 15%-opacity area under the line - the
    star-history / hero-trend treatment. `stroke_width` defaults to 2;
    bump to 3 for headline series that should read above the others.
    `show_in_legend=False` hides the series from the legend (used for
    annotation overlays like release markers that aren't real data).

    `highlighted_indices` marks specific data points (by their index in
    `points`) for emphasis - typically driven by event-chip selection on
    the parent tab. Each marked point renders as a 7-px circle in
    `highlight_color` so the viewer's eye is drawn to dates that
    correspond to the currently selected event chip on the parent tab.
    """

    label: str
    color: str
    points: list[tuple[int, float]]
    fill: bool = False
    stroke_width: int = 2
    tooltips: list[str] | None = None
    show_in_legend: bool = True
    highlighted_indices: frozenset[int] = field(default_factory=frozenset)
    highlight_color: str = (
        "#F59E0B"  # ChartColors.AMBER - keep dataclass self-contained
    )


class LineChartCard(ft.Container):
    """Card-styled line chart with a title, optional subtitle, the chart
    body, and a legend. Owns its own surface treatment (matches
    `MetricCard`: SURFACE_CONTAINER_HIGHEST, 0.5px OUTLINE border, the
    standard CARD_RADIUS) so a tab composing this control doesn't have
    to wrap it again.

    Example:
        LineChartCard(
            title="Daily Cloners",
            subtitle="unique people / clones per day",
            x_labels=[d.date for d in daily],
            series=[
                LineSeries(
                    label="Clones",
                    color="#2563eb",
                    points=[(i, d.clones) for i, d in enumerate(daily)],
                    tooltips=[f"Clones: {d.clones:,}" for d in daily],
                ),
                LineSeries(
                    label="Unique Cloners",
                    color="#7c3aed",
                    points=[(i, d.unique_cloners) for i, d in enumerate(daily)],
                ),
            ],
        )
    """

    def __init__(
        self,
        *,
        title: str,
        series: list[LineSeries],
        x_labels: list[str],
        subtitle: str = "",
        height: int = 240,
        min_y: float = 0,
        event_annotations: list[list[str]] | None = None,
    ) -> None:
        super().__init__()

        chart_data: list[ft.LineChartData] = [self._make_series(s) for s in series]

        # Event-annotation overlay. When the parent tab passes a list of
        # event labels per x-position, we render a transparent series at
        # ``min_y`` whose only job is to surface a muted-grey tooltip
        # entry on dates that have events. Each event-bearing point gets
        # an invisible (transparent) ChartCirclePoint so Flet has a real
        # hover target - without it, a stroke_width=0 series sometimes
        # gets dropped from the multi-series tooltip stack on hover.
        if event_annotations is not None:
            overlay_points: list[ft.LineChartDataPoint] = []
            muted_style = ft.TextStyle(
                color=ft.Colors.ON_SURFACE_VARIANT,
                size=Theme.Typography.BODY_SMALL,
            )
            for i, evs in enumerate(event_annotations):
                if evs:
                    overlay_points.append(
                        ft.LineChartDataPoint(
                            i,
                            min_y,
                            tooltip="\n".join(evs),
                            show_tooltip=True,
                            tooltip_style=muted_style,
                            point=ft.ChartCirclePoint(
                                radius=2,
                                color=ft.Colors.TRANSPARENT,
                                stroke_width=0,
                            ),
                        )
                    )
                else:
                    overlay_points.append(
                        ft.LineChartDataPoint(i, min_y, show_tooltip=False)
                    )
            chart_data.append(
                ft.LineChartData(
                    data_points=overlay_points,
                    stroke_width=0,
                    color=ft.Colors.TRANSPARENT,
                )
            )

        # Y-axis range - driven by the visible (legend-shown) series so
        # annotation overlays at y=0 don't squash the scale.
        visible_values = [y for s in series if s.show_in_legend for _, y in s.points]
        max_val = max(visible_values) if visible_values else 1
        step = self._smart_step(max_val - min_y)
        max_y = int((max_val // step + 1) * step) if step else int(max_val + 1)

        # Bottom-axis labels: reuse just the date strings; the parent
        # owns the x-coordinate semantics.
        bottom_labels = [
            ft.ChartAxisLabel(
                value=i,
                label=ft.Text(label[-5:], size=9, color=ft.Colors.ON_SURFACE_VARIANT),
            )
            for i, label in enumerate(x_labels)
            # Show ~8 ticks evenly distributed plus the last day.
            if i % max(1, len(x_labels) // 8) == 0 or i == len(x_labels) - 1
        ]

        # Y-axis ticks rendered explicitly so they pick up the same
        # small + muted styling as the bottom axis. Without this, Flet
        # falls back to its default-styled auto-labels which are larger
        # and use the default text color.
        left_labels = []
        if step > 0:
            tick = int(min_y) + (step - (int(min_y) % step) if int(min_y) % step else 0)
            while tick <= max_y:
                left_labels.append(
                    ft.ChartAxisLabel(
                        value=tick,
                        label=ft.Text(
                            f"{int(tick):,}",
                            size=9,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                    )
                )
                tick += step

        chart = ft.LineChart(
            data_series=chart_data,
            left_axis=ft.ChartAxis(labels_size=50, labels=left_labels),
            bottom_axis=ft.ChartAxis(labels_size=50, labels=bottom_labels),
            horizontal_grid_lines=ft.ChartGridLines(
                interval=step,
                color=ft.Colors.with_opacity(0.08, ft.Colors.ON_SURFACE),
                width=1,
            ),
            **chart_tooltip_kwargs(),
            tooltip_show_on_top_of_chart_box_area=True,
            point_line_start=0,
            point_line_end=float("inf"),
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            interactive=True,
            min_y=min_y,
            max_y=max_y,
            min_x=0,
            max_x=max(0, len(x_labels) - 1),
            height=height,
            expand=True,
        )

        legend_items = [(s.color, s.label) for s in series if s.show_in_legend]
        legend = ft.Row(
            [
                ft.Row(
                    [
                        ft.Container(
                            width=10, height=10, bgcolor=color, border_radius=5
                        ),
                        SecondaryText(label, size=Theme.Typography.BODY_SMALL),
                    ],
                    spacing=4,
                )
                for color, label in legend_items
            ],
            spacing=16,
            alignment=ft.MainAxisAlignment.CENTER,
        )

        # Title row dropped - chart cards now lead with the chart
        # itself; the legend underneath labels each series. ``title``
        # / ``subtitle`` parameters stay on the constructor so callers
        # don't have to change, but they're not rendered.
        self.content = ft.Column(
            [chart, legend],
            spacing=Theme.Spacing.SM,
        )
        self.padding = Theme.Spacing.MD
        self.bgcolor = ft.Colors.SURFACE_CONTAINER_HIGHEST
        self.border = ft.border.all(0.5, ft.Colors.OUTLINE)
        self.border_radius = Theme.Components.CARD_RADIUS

    @staticmethod
    def _make_series(s: LineSeries) -> ft.LineChartData:
        """Build a `LineChartData` with the project's standard line
        styling - curved, radius-3 circle points, rounded stroke caps -
        plus an optional 15%-opacity below-line fill.

        Indices in ``s.highlighted_indices`` get a per-point ChartCirclePoint
        override (radius 7, ``s.highlight_color``, white stroke) so the
        viewer's eye is drawn to dates that correspond to the currently
        selected event chip on the parent tab.

        Two subtle behaviors that matter for annotation overlays (e.g. a
        release marker series rendered at y=0 with no visible line):
          * Per-point tooltips that are empty/None pass ``show_tooltip=False``
            so non-event dates don't surface a blank entry next to the
            real metric tooltip.
          * Series with ``stroke_width=0`` skip the series-level point dot
            so the overlay series stays truly invisible - only its
            tooltips matter.
        """
        highlight_point = ChartPoint.highlight(s.highlight_color)

        def _point_kwargs(i: int) -> dict[str, Any]:
            """Per-point overrides. ``show_tooltip`` is set explicitly in
            both branches because Flet treats the absence of a tooltip
            string differently from an opt-in `show_tooltip=True`; the
            OLD chart code relied on the explicit form and tooltips
            stopped surfacing when the refactor leaned on the default."""
            kw: dict[str, Any] = {}
            if i in s.highlighted_indices:
                kw["point"] = highlight_point
            tip = s.tooltips[i] if s.tooltips else None
            if tip:
                kw["tooltip"] = tip
                kw["show_tooltip"] = True
            else:
                kw["show_tooltip"] = False
            return kw

        data_points = [
            ft.LineChartDataPoint(x, y, **_point_kwargs(i))
            for i, (x, y) in enumerate(s.points)
        ]
        kwargs: dict[str, Any] = {
            "data_points": data_points,
            "stroke_width": s.stroke_width,
            "color": s.color,
        }
        # Visible-line styling only applies when the series actually
        # draws a stroke. For annotation overlays (stroke_width=0) this
        # block is intentionally skipped - they're invisible tooltip
        # carriers, and applying line styling can change how Flet
        # registers their points in the tooltip stack.
        if s.stroke_width > 0:
            kwargs["curved"] = True
            kwargs["stroke_cap_round"] = True
            kwargs["point"] = ChartPoint.dot(
                s.color if s.fill else ft.Colors.ON_SURFACE
            )
            if s.fill:
                kwargs["below_line_bgcolor"] = ft.Colors.with_opacity(0.15, s.color)
        return ft.LineChartData(**kwargs)

    @staticmethod
    def _smart_step(value_range: float) -> int:
        """Pick a nice y-axis interval based on the data magnitude."""
        if value_range <= 20:
            return 5
        if value_range <= 100:
            return 10
        if value_range <= 500:
            return 50
        return 100


class FlowConnector(ft.Container):
    """Vertical connector with arrow between flow sections."""

    def __init__(self) -> None:
        """Initialize flow connector."""
        super().__init__()
        self.content = ft.Column(
            [
                # Vertical line (thicker)
                ft.Container(
                    width=3,
                    height=30,
                    bgcolor=Theme.Colors.BORDER_DEFAULT,
                    border_radius=2,
                ),
                # Arrow icon
                ft.Icon(
                    ft.Icons.ARROW_DROP_DOWN,
                    size=20,
                    color=Theme.Colors.BORDER_DEFAULT,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=0,
        )
        self.padding = ft.padding.symmetric(vertical=Theme.Spacing.XS)


class LifecycleInspector(ft.Container):
    """Right-side inspector panel showing selected card details."""

    def __init__(self) -> None:
        """Initialize lifecycle inspector panel."""
        super().__init__()
        self._selected_card: LifecycleCard | None = None
        self._name_text = PrimaryText("")
        self._subtitle_text = SecondaryText("")
        self._badge_container = ft.Container(visible=False)
        self._details_column: ft.Column = ft.Column([], spacing=8)
        self._showing_empty_state = True

        # Main column that will swap between empty state and content
        self._main_column = ft.Column(
            [
                ft.Icon(
                    ft.Icons.TOUCH_APP, size=48, color=ft.Colors.ON_SURFACE_VARIANT
                ),
                SecondaryText("Select a lifecycle hook"),
                SecondaryText("to inspect configuration", size=12),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

        self.content = self._main_column
        self.bgcolor = ft.Colors.SURFACE_CONTAINER_HIGHEST
        self.border_radius = Theme.Components.CARD_RADIUS
        self.border = ft.border.all(1, ft.Colors.OUTLINE)
        self.padding = ft.padding.all(Theme.Spacing.MD)
        self.width = 300

    def clear_selection(self) -> None:
        """Reset inspector to empty state (e.g., on queue switch)."""
        if self._selected_card:
            with contextlib.suppress(Exception):
                self._selected_card.set_selected(False)
            self._selected_card = None

    def select_card(self, card: LifecycleCard) -> None:  # noqa: F821
        """Select a card and update inspector."""
        # Deselect previous (guard against unmounted cards)
        if self._selected_card:
            with contextlib.suppress(Exception):
                self._selected_card.set_selected(False)
        # Select new
        self._selected_card = card
        card.set_selected(True)
        # Show details
        self.show_details(
            card.name,
            card.subtitle,
            card._details,
            card._badge_text,
            card._badge_color,
            card.section,
        )

    def _create_code_block(self, text: str, copyable: bool = False) -> ft.Container:
        """Create styled code block for values."""
        content_items: list[ft.Control] = [
            ft.Text(
                text,
                font_family="monospace",
                size=12,
                color=ft.Colors.ON_SURFACE_VARIANT,
                selectable=True,
                expand=True,
            ),
        ]
        if copyable:
            content_items.append(
                ft.IconButton(
                    icon=ft.Icons.COPY,
                    icon_size=14,
                    tooltip="Copy",
                    on_click=lambda e: self._copy_to_clipboard(text),
                ),
            )
        return ft.Container(
            content=ft.Row(content_items, spacing=4),
            bgcolor=ft.Colors.SURFACE,
            border_radius=6,
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
        )

    def _copy_to_clipboard(self, text: str) -> None:
        """Copy text to clipboard with feedback."""
        if self.page:
            self.page.set_clipboard(text)
            self.page.open(ft.SnackBar(content=ft.Text("Copied to clipboard")))

    def show_details(
        self,
        name: str,
        subtitle: str,
        details: dict[str, object],
        badge_text: str | None = None,
        badge_color: str | None = None,
        section: str = "",
    ) -> None:
        """
        Update inspector with card data.

        Args:
            name: Card name to display
            subtitle: Card subtitle to display
            details: Dict of key-value pairs to show
            badge_text: Optional badge text (e.g., "Security")
            badge_color: Badge background color
            section: Section name for context header
        """
        self._name_text.value = name
        self._subtitle_text.value = subtitle

        # Update badge
        if badge_text:
            self._badge_container.content = LabelText(
                badge_text, color=Theme.Colors.BADGE_TEXT
            )
            self._badge_container.padding = ft.padding.symmetric(
                horizontal=6, vertical=2
            )
            self._badge_container.bgcolor = badge_color or ft.Colors.AMBER
            self._badge_container.border_radius = 4
            self._badge_container.visible = True
        else:
            self._badge_container.visible = False

        # Build details (skip Module - already shown as subtitle)
        detail_rows: list[ft.Control] = []
        for key, value in details.items():
            if key == "Module":
                continue

            detail_rows.append(SecondaryText(f"{key}:"))

            # Handle lists - join items with newlines in one block
            if isinstance(value, list):
                list_text = ",\n".join(str(item) for item in value)
                detail_rows.append(self._create_code_block(list_text))
            else:
                detail_rows.append(self._create_code_block(str(value)))

        self._details_column.controls = detail_rows

        # Build content with optional section header
        content_controls: list[ft.Control] = []

        # Section context header (e.g., "Startup Hooks")
        if section:
            content_controls.append(SecondaryText(section))

        # Card name + badge
        content_controls.append(
            ft.Row(
                [self._name_text, self._badge_container],
                spacing=Theme.Spacing.SM,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )
        content_controls.append(self._subtitle_text)
        content_controls.append(ft.Divider())
        content_controls.append(self._details_column)

        # Swap to content view
        self._main_column.controls = content_controls
        self._main_column.horizontal_alignment = ft.CrossAxisAlignment.START
        self._main_column.spacing = Theme.Spacing.SM
        self._showing_empty_state = False
        self.update()


class LifecycleCard(ft.Container):
    """Clickable card for lifecycle items (hooks or middleware)."""

    def __init__(
        self,
        name: str,
        subtitle: str,
        section: str = "",
        details: dict[str, object] | None = None,
        badge: str | None = None,
        badge_color: str | None = None,
        inspector: LifecycleInspector | None = None,
    ) -> None:
        """
        Initialize lifecycle card.

        Args:
            name: Function/class name (e.g., database_init, CORSMiddleware)
            subtitle: Module path for inspector
            section: Section name (e.g., "Startup Hooks") for inspector context
            details: Optional dict of key-value pairs for inspector view
            badge: Optional badge text (e.g., "Security")
            badge_color: Badge background color
            inspector: Shared inspector panel to update on click
        """
        super().__init__()
        # Auto-format: snake_case -> Title Case, preserve CamelCase
        if "_" in name:
            display_name = name.replace("_", " ").title()
        elif name.islower():
            display_name = name.capitalize()
        else:
            display_name = name  # Preserve CamelCase
        self.name = display_name
        self.subtitle = subtitle
        self.section = section
        self._raw_name = name  # Keep original for code reference
        self._details = details or {}
        self._badge_text = badge
        self._badge_color = badge_color or ft.Colors.AMBER
        self._inspector = inspector
        self._is_selected = False

        # Build card header: Title + Badge on top, code name below
        header_row_content: list[ft.Control] = [PrimaryText(display_name)]

        # Add badge if provided
        if self._badge_text:
            header_row_content.append(
                ft.Container(
                    content=LabelText(self._badge_text, color=Theme.Colors.BADGE_TEXT),
                    padding=ft.padding.symmetric(horizontal=6, vertical=2),
                    bgcolor=self._badge_color,
                    border_radius=4,
                    margin=ft.margin.only(left=Theme.Spacing.SM),
                )
            )

        self.card_header = ft.Container(
            content=ft.Row(
                header_row_content,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.all(Theme.Spacing.SM),
            on_hover=self._on_hover,
        )

        # Wrap header in gesture detector
        self.header_gesture = ft.GestureDetector(
            content=self.card_header,
            on_tap=self._handle_click,
            mouse_cursor=ft.MouseCursor.CLICK,
        )

        self.content = self.header_gesture
        self.bgcolor = ft.Colors.SURFACE_CONTAINER_HIGHEST
        self.border_radius = Theme.Components.CARD_RADIUS
        self.border = ft.border.all(1, ft.Colors.OUTLINE)

    def _on_hover(self, e: ft.ControlEvent) -> None:
        """Handle hover state change."""
        if self._is_selected:
            return  # Don't change hover state when selected
        if e.data == "true":
            self.card_header.bgcolor = ft.Colors.with_opacity(
                0.08, ft.Colors.ON_SURFACE
            )
        else:
            self.card_header.bgcolor = None
        if e.control.page:
            self.card_header.update()

    def _handle_click(self, e: ft.ControlEvent) -> None:
        """Handle card click to update inspector."""
        _ = e
        if self._inspector:
            self._inspector.select_card(self)

    def set_selected(self, selected: bool) -> None:
        """Update visual state for selection."""
        self._is_selected = selected
        if selected:
            self.border = ft.border.all(2, Theme.Colors.ACCENT)
            self.bgcolor = ft.Colors.with_opacity(0.12, ft.Colors.ON_SURFACE)
        else:
            self.border = ft.border.all(1, ft.Colors.OUTLINE)
            self.bgcolor = ft.Colors.SURFACE_CONTAINER_HIGHEST
        self.update()


class FlowSection(ft.Container):
    """A section in the lifecycle flow with label and cards."""

    def __init__(
        self, title: str, cards: list[LifecycleCard], icon: str, step_number: int
    ) -> None:
        """
        Initialize flow section.

        Args:
            title: Section title
            cards: List of LifecycleCard components
            icon: Icon name for the section header
            step_number: Execution order number (1, 2, 3...)
        """
        super().__init__()
        self.title = title
        self.cards_list = cards

        # Section header with step number and icon
        section_header = ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        content=SecondaryText(f"{step_number:02d}", size=10),
                        bgcolor=ft.Colors.with_opacity(0.08, ft.Colors.ON_SURFACE),
                        border_radius=4,
                        padding=ft.padding.symmetric(horizontal=6, vertical=2),
                    ),
                    ft.Icon(icon, size=18, color=Theme.Colors.TEXT_SECONDARY),
                    H3Text(title),
                    ft.Container(
                        content=SecondaryText(f"({len(cards)})"),
                        padding=ft.padding.only(left=Theme.Spacing.XS),
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=Theme.Spacing.SM,
            ),
            padding=ft.padding.only(bottom=Theme.Spacing.SM),
        )

        # Cards row (wraps if many items)
        if cards:
            cards_row = ft.Row(
                cards,
                wrap=True,
                spacing=Theme.Spacing.MD,
                run_spacing=Theme.Spacing.MD,
                alignment=ft.MainAxisAlignment.CENTER,
            )
        else:
            cards_row = ft.Container(
                content=SecondaryText("None configured"),
                padding=ft.padding.all(Theme.Spacing.MD),
                alignment=ft.alignment.center,
            )

        self.content = ft.Column(
            [section_header, cards_row],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=0,
        )
        self.padding = ft.padding.symmetric(vertical=Theme.Spacing.SM)
