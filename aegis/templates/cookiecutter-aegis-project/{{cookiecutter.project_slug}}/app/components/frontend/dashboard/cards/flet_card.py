"""
Flet Frontend Component Card

Modern card component that displays Flet frontend framework information,
UI settings, and frontend health status.
"""

import flet as ft
from app.components.frontend.controls import PrimaryText
from app.services.system.models import ComponentStatus

from .card_utils import (
    create_card_click_handler,
    create_clickable_hover_handler,
    create_responsive_3_section_layout,
    create_standard_card_container,
    create_stats_row,
    create_tech_badge,
    get_status_colors,
)


class FletCard:
    """
    Visually stunning component card for displaying Flet frontend metrics.

    Features:
    - Modern Material Design 3 styling
    - Three-section layout (badge, settings, stats)
    - Framework version and UI configuration
    - Theme settings and refresh rates
    - Status-aware coloring and hover effects
    """

    def __init__(self, component_data: ComponentStatus) -> None:
        """
        Initialize the Flet card with component data.

        Args:
            component_data: ComponentStatus containing frontend health and metrics
        """
        self.component_data = component_data
        self._card_container: ft.Container | None = None

    def _create_technology_badge(self) -> ft.Container:
        """Create the Flet technology badge section."""
        primary_color, _, _ = get_status_colors(self.component_data)

        return create_tech_badge(
            title="Frontend",
            subtitle="Flet",
            icon="🎨",
            badge_text="UI",
            badge_color=ft.Colors.PURPLE,
            primary_color=primary_color,
            width=160,
        )

    def _create_settings_section(self) -> ft.Container:
        """Create the frontend settings section."""
        # Get metadata
        metadata = self.component_data.metadata or {}

        settings_items = []

        # Add framework info
        settings_items.append(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Icon(ft.Icons.WEB, size=16, color=ft.Colors.GREY),
                                ft.Text(
                                    "Framework",
                                    size=14,
                                    weight=ft.FontWeight.W_500,
                                    color=ft.Colors.ON_SURFACE,
                                ),
                            ],
                            spacing=8,
                        ),
                        ft.Text(
                            f"Flet {ft.version.version}",
                            size=13,
                            color=ft.Colors.GREY,
                        ),
                    ],
                    spacing=4,
                ),
                padding=ft.padding.symmetric(vertical=8, horizontal=12),
            )
        )

        # Add integration type
        settings_items.append(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Icon(
                                    ft.Icons.INTEGRATION_INSTRUCTIONS,
                                    size=16,
                                    color=ft.Colors.GREY,
                                ),
                                ft.Text(
                                    "Integration",
                                    size=14,
                                    weight=ft.FontWeight.W_500,
                                    color=ft.Colors.ON_SURFACE,
                                ),
                            ],
                            spacing=8,
                        ),
                        ft.Text(
                            metadata.get("note", "FastAPI integrated"),
                            size=13,
                            color=ft.Colors.GREY,
                        ),
                    ],
                    spacing=4,
                ),
                padding=ft.padding.symmetric(vertical=8, horizontal=12),
            )
        )

        # Add theme capabilities
        settings_items.append(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Icon(
                                    ft.Icons.PALETTE, size=16, color=ft.Colors.GREY
                                ),
                                ft.Text(
                                    "Theme Support",
                                    size=14,
                                    weight=ft.FontWeight.W_500,
                                    color=ft.Colors.ON_SURFACE,
                                ),
                            ],
                            spacing=8,
                        ),
                        ft.Text(
                            "Light / Dark Mode",
                            size=13,
                            color=ft.Colors.GREY,
                        ),
                    ],
                    spacing=4,
                ),
                padding=ft.padding.symmetric(vertical=8, horizontal=12),
            )
        )

        # Add refresh rate
        settings_items.append(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Icon(
                                    ft.Icons.REFRESH, size=16, color=ft.Colors.GREY
                                ),
                                ft.Text(
                                    "Auto Refresh",
                                    size=14,
                                    weight=ft.FontWeight.W_500,
                                    color=ft.Colors.ON_SURFACE,
                                ),
                            ],
                            spacing=8,
                        ),
                        ft.Text(
                            "Every 30 seconds",
                            size=13,
                            color=ft.Colors.GREY,
                        ),
                    ],
                    spacing=4,
                ),
                padding=ft.padding.symmetric(vertical=8, horizontal=12),
            )
        )

        return ft.Container(
            content=ft.Column(
                settings_items,
                spacing=2,
                scroll=ft.ScrollMode.AUTO,
            ),
            width=400,
            height=250,
            padding=ft.padding.only(left=12, right=12, bottom=12, top=0),
            alignment=ft.alignment.top_left,
        )

    def _create_stats_section(self) -> ft.Container:
        """Create the frontend statistics section."""
        # Get metadata
        metadata = self.component_data.metadata or {}

        # Build stats
        frontend_stats = {
            "Framework": metadata.get("framework", "Flet").title(),
            "UI Type": "Reactive Web",
            "Platform": "Cross-platform",
            "Components": "Material 3",
        }

        stats_content = [
            PrimaryText("UI Configuration"),
            ft.Divider(height=1, color=ft.Colors.GREY_300),
        ]

        # Add all stats
        for stat_name, stat_value in frontend_stats.items():
            stats_content.append(create_stats_row(stat_name, stat_value))

        # Add status
        stats_content.extend(
            [
                ft.Divider(height=1, color=ft.Colors.GREY_300),
                create_stats_row(
                    "Status",
                    self.component_data.status.value.title(),
                    get_status_colors(self.component_data)[0],
                ),
            ]
        )

        return ft.Container(
            content=ft.Column(
                stats_content,
                spacing=8,
                alignment=ft.MainAxisAlignment.START,
            ),
            padding=ft.padding.all(16),
            width=240,
            alignment=ft.alignment.top_left,
        )

    def build(self) -> ft.Container:
        """Build and return the complete Flet card with responsive layout."""
        primary_color, background_color, border_color = get_status_colors(
            self.component_data
        )

        # Use shared responsive 3-section layout
        content = create_responsive_3_section_layout(
            left_content=self._create_technology_badge(),
            middle_content=self._create_settings_section(),
            right_content=self._create_stats_section(),
        )

        self._card_container = create_standard_card_container(
            content=content,
            primary_color=primary_color,
            border_color=border_color,
            width=None,  # Let ResponsiveRow handle the width
            hover_handler=None,
        )

        # Create clickable hover handler for the card (with scale animation)
        hover_handler = create_clickable_hover_handler(self._card_container)
        self._card_container.on_hover = hover_handler

        # Add click handler to open modal (standard pattern)
        self._card_container.on_click = create_card_click_handler(
            "frontend", self.component_data
        )
        self._card_container.cursor = ft.MouseCursor.CLICK

        return self._card_container
