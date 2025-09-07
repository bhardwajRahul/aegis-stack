"""
Stunning Database/SQLite Component Card

Modern, visually striking card component that displays rich database metrics,
connection statistics, query performance, and table information.
"""

import flet as ft

from app.components.frontend.controls import (
    LabelText,
    PrimaryText,
    SecondaryText,
    TitleText,
)
from app.services.system.models import ComponentStatus, ComponentStatusType

from .card_utils import create_responsive_3_section_layout


class DatabaseCard:
    """
    A visually stunning, wide component card for displaying Database/SQLite metrics.

    Features:
    - Modern Material Design 3 styling
    - Three-section layout (badge, metrics, performance)
    - Database-specific statistics and query performance
    - Table counts and connection monitoring
    - Status-aware coloring and hover effects
    """

    def __init__(self, component_data: ComponentStatus) -> None:
        """
        Initialize the Database card with component data.

        Args:
            component_data: ComponentStatus containing database health and metrics
        """
        self.component_data = component_data
        self._card_container: ft.Container | None = None

    def _get_status_colors(self) -> tuple[str, str, str]:
        """
        Get status-aware colors for the card.

        Returns:
            Tuple of (primary_color, background_color, border_color)
        """
        status = self.component_data.status

        if status == ComponentStatusType.HEALTHY:
            return (ft.Colors.GREEN, ft.Colors.SURFACE, ft.Colors.GREEN)
        elif status == ComponentStatusType.INFO:
            return (ft.Colors.BLUE, ft.Colors.SURFACE, ft.Colors.BLUE)
        elif status == ComponentStatusType.WARNING:
            return (ft.Colors.ORANGE, ft.Colors.SURFACE, ft.Colors.ORANGE)
        else:  # UNHEALTHY
            return (ft.Colors.RED, ft.Colors.SURFACE, ft.Colors.RED)

    def _create_table_indicator(
        self, table_name: str, record_count: int
    ) -> ft.Container:
        """Create a table status indicator with record count."""
        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text("🗂️", size=12),
                            LabelText(table_name.upper()),
                        ],
                        spacing=5,
                    ),
                    ft.Container(height=2, bgcolor=ft.Colors.BLUE, border_radius=1),
                    LabelText(f"{record_count:,} rows"),
                ],
                spacing=2,
            ),
            padding=ft.padding.all(8),
            bgcolor=ft.Colors.SURFACE,
            border=ft.border.all(1, ft.Colors.BLUE),
            border_radius=8,
            width=120,
            height=70,
        )

    def _create_technology_badge(self) -> ft.Container:
        """Create the Database/SQLite technology badge section."""
        primary_color, _, _ = self._get_status_colors()

        return ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Text("🗃️", size=32),
                        padding=ft.padding.all(8),
                        bgcolor=primary_color,
                        border_radius=12,
                        margin=ft.margin.only(bottom=8),
                    ),
                    TitleText("Database"),
                    SecondaryText("SQLite + SQLModel"),
                    ft.Container(
                        content=LabelText(
                            "STORAGE",
                            color=ft.Colors.WHITE,
                        ),
                        padding=ft.padding.symmetric(horizontal=8, vertical=2),
                        bgcolor=ft.Colors.INDIGO,
                        border_radius=8,
                        margin=ft.margin.only(top=4),
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=2,
            ),
            padding=ft.padding.all(16),
            width=160,  # Wider badge section
        )

    def _create_tables_section(self) -> ft.Container:
        """Create the database tables section with table indicators."""
        # Sample table data (in real app, this would come from database introspection)
        tables_data = [
            {"name": "users", "records": 1247},
            {"name": "sessions", "records": 342},
            {"name": "logs", "records": 15432},
        ]

        table_controls = []
        for table_data in tables_data:
            table_controls.append(
                self._create_table_indicator(
                    str(table_data["name"]), 
                    (
                        int(table_data["records"]) 
                        if isinstance(table_data["records"], int | str) 
                        else 0
                    )
                )
            )

        return ft.Container(
            content=ft.Column(
                [
                    PrimaryText("Database Tables"),
                    ft.Divider(height=1, color=ft.Colors.GREY_300),
                    ft.Container(
                        content=ft.Row(table_controls, spacing=10, wrap=True),
                        width=320,  # Reduced width to prevent cutting off right section
                    ),
                ],
                spacing=8,
            ),
            width=360,  # Reduced overall width to give more room to performance section
            padding=ft.padding.all(16),
        )

    def _create_performance_section(self) -> ft.Container:
        """Create the database performance and statistics section."""

        # Sample database performance stats
        db_stats = {
            "File Size": "45.2 MB",
            "Connections": "5 active",
            "Avg Query Time": "12.3ms",
            "Total Queries": "8,947",
            "Cache Hit Rate": "94.7%",
            "Last Backup": "2h ago",
        }

        perf_content = [
            PrimaryText("Performance"),
            ft.Divider(height=1, color=ft.Colors.GREY_300),
        ]

        for stat_name, stat_value in db_stats.items():
            perf_content.append(
                ft.Row(
                    [
                        SecondaryText(f"{stat_name}:"),
                        LabelText(stat_value),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                )
            )

        # Add status info
        perf_content.extend(
            [
                ft.Divider(height=1, color=ft.Colors.GREY_300),
                ft.Row(
                    [
                        SecondaryText("Status:"),
                        LabelText(
                            self.component_data.status.value.title(),
                            color=self._get_status_colors()[0],
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
            ]
        )

        return ft.Container(
            content=ft.Column(perf_content, spacing=6),
            padding=ft.padding.all(16),
            width=260,  # Wider stats section
        )

    def build(self) -> ft.Container:
        """Build and return the complete Database card with responsive layout."""
        primary_color, background_color, border_color = self._get_status_colors()

        # Use shared responsive 3-section layout prioritizing middle section
        content = create_responsive_3_section_layout(
            left_content=self._create_technology_badge(),
            middle_content=self._create_tables_section(),
            right_content=self._create_performance_section(),
        )

        self._card_container = ft.Container(
            content=content,
            bgcolor=ft.Colors.SURFACE,
            border=ft.border.all(1, border_color),
            border_radius=16,
            padding=0,
            width=None,  # Let ResponsiveRow handle the width
            height=280,
        )

        return self._card_container
