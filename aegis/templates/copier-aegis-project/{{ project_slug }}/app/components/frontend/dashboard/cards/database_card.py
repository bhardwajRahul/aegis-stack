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
    TableCellText,
    TableHeaderText,
    TableNameText,
    TitleText,
)
from app.components.frontend.theme import AegisTheme as Theme
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

    def _create_table_row(self, table_name: str, row_count: int) -> ft.Container:
        """Create a single table row with metrics (consistent with worker card)."""
        # Estimate size (rough: assume avg 1KB per row for SQLite)
        size_kb = max(1, row_count)  # At least 1KB for existing tables
        if size_kb < 1024:
            size_str = f"{size_kb} KB" if size_kb > 0 else "-"
        elif size_kb < 1024 * 1024:
            size_str = f"{size_kb / 1024:.1f} MB"
        else:
            size_str = f"{size_kb / (1024 * 1024):.1f} GB"

        return ft.Container(
            content=ft.Row(
                [
                    # Table name (no icon, consistent with worker card)
                    ft.Container(
                        content=TableNameText(table_name),
                        width=120,
                    ),
                    # Row count
                    ft.Container(
                        content=TableCellText(f"{row_count:,}"),
                        width=60,
                        alignment=ft.alignment.center_right,
                    ),
                    # Estimated size
                    ft.Container(
                        content=TableCellText(size_str),
                        width=60,
                        alignment=ft.alignment.center_right,
                    ),
                ],
                alignment=ft.MainAxisAlignment.START,
            ),
            padding=ft.padding.symmetric(horizontal=10, vertical=6),
            border_radius=8,
        )

    def _create_technology_badge(self) -> ft.Container:
        """Create the Database/SQLite technology badge section."""
        primary_color, _, _ = self._get_status_colors()
        metadata = self.component_data.metadata or {}

        # Determine badge text based on database state
        if self.component_data.status == ComponentStatusType.WARNING:
            badge_text = "NOT INIT"
            badge_color = ft.Colors.ORANGE
            icon = "⚠️"
        else:
            table_count = metadata.get("table_count", 0)
            if table_count == 0:
                badge_text = "EMPTY"
                badge_color = ft.Colors.BLUE
                icon = "🗃️"
            else:
                badge_text = "STORAGE"
                badge_color = ft.Colors.INDIGO
                icon = "🗃️"

        return ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Text(icon, size=32),
                        padding=ft.padding.all(8),
                        bgcolor=primary_color,
                        border_radius=12,
                        margin=ft.margin.only(bottom=8),
                    ),
                    TitleText("Database"),
                    SecondaryText("SQLite + SQLModel"),
                    ft.Container(
                        content=LabelText(
                            badge_text,
                            color=Theme.Colors.BADGE_TEXT,
                        ),
                        padding=ft.padding.symmetric(horizontal=8, vertical=2),
                        bgcolor=badge_color,
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
        # Get real table data from metadata, with fallback for no tables
        metadata = self.component_data.metadata or {}
        tables_data = metadata.get("tables", [])

        # If no tables or database not initialized, show appropriate message
        if not tables_data:
            if self.component_data.status == ComponentStatusType.WARNING:
                # Database not initialized
                # Database Tables header (matches worker card's Queue Status header)
                database_tables_header = ft.Container(
                    content=ft.Text(
                        "Database Tables",
                        size=16,
                        weight=ft.FontWeight.W_600,
                        color=ft.Colors.ON_SURFACE,
                    ),
                    padding=ft.padding.only(top=10, bottom=10),
                )

                return ft.Container(
                    content=ft.Column(
                        [
                            database_tables_header,
                            ft.Container(
                                content=ft.Column(
                                    [
                                        ft.Icon(
                                            ft.Icons.WARNING_OUTLINED,
                                            size=32,
                                            color=ft.Colors.ORANGE,
                                        ),
                                        SecondaryText("Database not initialized"),
                                        LabelText("No tables found"),
                                    ],
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                    spacing=8,
                                ),
                                padding=ft.padding.all(16),
                            ),
                        ],
                        spacing=0,
                    ),
                    width=360,
                    padding=ft.padding.all(16),
                )
            else:
                # Database exists but no tables
                # Database Tables header (matches worker card's Queue Status header)
                database_tables_header = ft.Container(
                    content=ft.Text(
                        "Database Tables",
                        size=16,
                        weight=ft.FontWeight.W_600,
                        color=ft.Colors.ON_SURFACE,
                    ),
                    padding=ft.padding.only(top=10, bottom=10),
                )

                return ft.Container(
                    content=ft.Column(
                        [
                            database_tables_header,
                            ft.Container(
                                content=ft.Column(
                                    [
                                        ft.Icon(
                                            ft.Icons.TABLE_VIEW_OUTLINED,
                                            size=32,
                                            color=ft.Colors.BLUE,
                                        ),
                                        SecondaryText("Empty database"),
                                        LabelText("No tables created yet"),
                                    ],
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                    spacing=8,
                                ),
                                padding=ft.padding.all(16),
                            ),
                        ],
                        spacing=0,
                    ),
                    width=360,
                    padding=ft.padding.all(16),
                )

        # Header for table list (consistent with worker card)
        header_row = ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        TableHeaderText("Table"),
                        width=120,
                    ),
                    ft.Container(
                        TableHeaderText("Rows"),
                        width=60,
                        alignment=ft.alignment.center_right,
                    ),
                    ft.Container(
                        TableHeaderText("Size"),
                        width=60,
                        alignment=ft.alignment.center_right,
                    ),
                ],
                alignment=ft.MainAxisAlignment.START,
            ),
            padding=ft.padding.symmetric(horizontal=10, vertical=6),
            border=ft.border.only(bottom=ft.BorderSide(1, ft.Colors.GREY_300)),
        )

        # Table rows
        table_rows = []
        for table_data in tables_data:
            table_rows.append(
                self._create_table_row(
                    str(table_data["name"]), int(table_data.get("rows", 0))
                )
            )

        # Database Tables header (consistent with worker card's Queue Status header)
        database_tables_header = ft.Container(
            content=ft.Text(
                "Database Tables",
                size=16,
                weight=ft.FontWeight.W_600,
                color=ft.Colors.ON_SURFACE,
            ),
            padding=ft.padding.only(top=10, bottom=10),
        )

        # Table content with header and rows
        table_content = ft.Column(
            [
                database_tables_header,
                header_row,
                *table_rows,
            ],
            spacing=0,
        )

        return ft.Container(
            content=table_content,
            width=360,
            padding=ft.padding.all(16),
        )

    def _create_performance_section(self) -> ft.Container:
        """Create the database performance and statistics section."""
        metadata = self.component_data.metadata or {}

        # Get real database stats from metadata
        db_stats = {}

        # File size
        if "file_size_human" in metadata:
            db_stats["File Size"] = metadata["file_size_human"]
        elif "file_size_bytes" in metadata:
            # Format bytes if we have raw bytes but not human readable
            size_bytes = metadata["file_size_bytes"]
            if size_bytes == 0:
                db_stats["File Size"] = "0 B"
            elif size_bytes < 1024:
                db_stats["File Size"] = f"{size_bytes} B"
            elif size_bytes < 1024**2:
                db_stats["File Size"] = f"{size_bytes / 1024:.1f} KB"
            elif size_bytes < 1024**3:
                db_stats["File Size"] = f"{size_bytes / (1024**2):.1f} MB"
            else:
                db_stats["File Size"] = f"{size_bytes / (1024**3):.1f} GB"

        # Database version
        if "version" in metadata:
            db_stats["SQLite Version"] = metadata["version"]

        # Connection pool size
        if "connection_pool_size" in metadata:
            db_stats["Pool Size"] = str(metadata["connection_pool_size"])

        # Table count
        table_count = metadata.get("table_count", 0)
        if table_count > 0:
            db_stats["Tables"] = str(table_count)

        # Journal mode
        pragma_settings = metadata.get("pragma_settings", {})
        if "journal_mode" in pragma_settings:
            db_stats["Journal Mode"] = pragma_settings["journal_mode"].upper()

        # WAL enabled
        if metadata.get("wal_enabled"):
            db_stats["WAL"] = "Enabled"

        # Foreign keys
        if "foreign_keys" in pragma_settings:
            db_stats["Foreign Keys"] = (
                "On" if pragma_settings["foreign_keys"] else "Off"
            )

        # If database not initialized, show different stats
        if self.component_data.status == ComponentStatusType.WARNING:
            db_stats = {
                "Status": "Not Initialized",
                "Action": "Create database file",
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
