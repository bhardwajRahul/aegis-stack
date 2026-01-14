"""
Reusable Modal Section Components

Provides commonly used section patterns across component detail modals:
- MetricCardSection: Display key metrics in card grid
- StatRowsSection: Label/value pairs for detailed information
- EmptyStatePlaceholder: Consistent "no data" messaging
- PieChartCard: Donut chart with legend
"""

from typing import Any

import flet as ft
from app.components.frontend.controls import (
    BodyText,
    H3Text,
    LabelText,
    SecondaryText,
    Tag,
)
from app.components.frontend.theme import AegisTheme as Theme
from app.components.frontend.theme import DarkColorPalette


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
    ) -> None:
        """
        Initialize metric card.

        Args:
            label: Metric label text
            value: Metric value to display
            color: Color for the value text
            icon: Optional icon name (e.g., ft.Icons.TOKEN)
        """
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

        # Value text
        value_text = ft.Text(
            value,
            size=24,
            weight=ft.FontWeight.W_600,
        )

        self.content = ft.Column(
            [header_row, value_text],
            spacing=Theme.Spacing.XS,
        )
        self.padding = Theme.Spacing.MD
        self.bgcolor = ft.Colors.SURFACE_CONTAINER_HIGHEST
        self.border_radius = Theme.Components.CARD_RADIUS
        self.border = ft.border.all(0.5, ft.Colors.OUTLINE)
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

    # Segment radius constants
    NORMAL_RADIUS = 55
    HOVER_RADIUS = 65

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
            self.content = SecondaryText("No data available")
            self._setup_card_style()
            return

        # Build pie chart sections with auto-assigned colors
        self._pie_sections: list[ft.PieChartSection] = []
        legend_items: list[ft.Row] = []
        total = sum(float(s.get("value", 0)) for s in sections)

        for i, section in enumerate(sections):
            value = float(section.get("value", 0))
            # Use provided color or auto-assign from palette
            color = section.get("color") or PIE_CHART_COLORS[i % len(PIE_CHART_COLORS)]
            label = str(section.get("label", ""))

            # Store for tooltips
            self._section_labels.append(label)
            self._section_values.append(value)

            # Calculate percentage for title display (only show if >= 15%)
            pct = (value / total * 100) if total > 0 else 0

            self._pie_sections.append(
                ft.PieChartSection(
                    value=value,
                    title=f"{pct:.0f}%" if pct >= 15 else "",
                    color=color,
                    radius=self.NORMAL_RADIUS,
                    title_style=ft.TextStyle(
                        color=ft.Colors.WHITE,
                        size=11,
                        weight=ft.FontWeight.W_600,
                    ),
                )
            )
            legend_items.append(self._legend_item(label, color))

        # Tooltip text (shown on hover next to title)
        self._tooltip_text = ft.Text(
            "",
            size=12,
            color=ft.Colors.ON_SURFACE,
        )

        # Donut chart with hover interaction
        self._pie_chart = ft.PieChart(
            sections=self._pie_sections,
            sections_space=2,
            center_space_radius=30,
            expand=True,
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
                ft.Container(content=self._pie_chart, width=140, height=140),
                legend,
            ],
            spacing=Theme.Spacing.LG,
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        # Title row with hover info in top-right corner
        title_row = ft.Row(
            [
                ft.Text(title, size=14, weight=ft.FontWeight.W_600),
                ft.Container(expand=True),  # Spacer
                self._tooltip_text,
            ],
        )

        # Title at top, chart+legend centered in remaining space
        self.content = ft.Column(
            [
                title_row,
                ft.Container(
                    content=chart_row,
                    expand=True,
                    alignment=ft.alignment.center,
                ),
            ],
            spacing=Theme.Spacing.SM,
            expand=True,
        )
        self._setup_card_style()

    def _setup_card_style(self) -> None:
        """Apply consistent card styling."""
        self.bgcolor = ft.Colors.SURFACE_CONTAINER_HIGHEST
        self.border = ft.border.all(0.5, ft.Colors.OUTLINE)
        self.border_radius = Theme.Components.CARD_RADIUS
        self.padding = Theme.Spacing.LG
        self.height = 220
        self.expand = True
        self.clip_behavior = ft.ClipBehavior.HARD_EDGE

    def _on_chart_event(self, e: ft.PieChartEvent) -> None:
        """Handle hover events - expand segment and show tooltip."""
        # Reset all sections to normal radius
        for section in self._pie_sections:
            section.radius = self.NORMAL_RADIUS

        # Check if hovering over a section (section_index is -1 when not hovering)
        idx = e.section_index
        if idx is not None and idx >= 0 and idx < len(self._pie_sections):
            # Expand hovered section
            self._pie_sections[idx].radius = self.HOVER_RADIUS
            # Show tooltip with label
            self._tooltip_text.value = self._section_labels[idx]
            self._hovered_index = idx
        else:
            # Clear tooltip when not hovering
            self._tooltip_text.value = ""
            self._hovered_index = None

        self._pie_chart.update()
        self._tooltip_text.update()

    def _legend_item(self, label: str, color: str) -> ft.Row:
        """Create a legend item with color dot and label."""
        return ft.Row(
            [
                ft.Container(width=10, height=10, bgcolor=color, border_radius=5),
                ft.Text(label, size=12),
            ],
            spacing=8,
        )
