"""
Stunning Redis/Cache Component Card

Modern, visually striking card component that displays rich Redis metrics,
memory usage, connection statistics, and cache performance data.
"""


import flet as ft

from app.components.frontend.controls import (
    LabelText,
    MetricText,
    PrimaryText,
    SecondaryText,
    TitleText,
)
from app.services.system.models import ComponentStatus, ComponentStatusType

from .card_utils import create_responsive_3_section_layout


class RedisCard:
    """
    A visually stunning, wide component card for displaying Redis/Cache metrics.
    
    Features:
    - Modern Material Design 3 styling
    - Three-section layout (badge, metrics, performance)
    - Redis-specific statistics and cache hit/miss ratios
    - Memory usage and connection monitoring
    - Status-aware coloring and hover effects
    """

    def __init__(self, component_data: ComponentStatus) -> None:
        """
        Initialize the Redis card with component data.
        
        Args:
            component_data: ComponentStatus containing Redis health and metrics
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

    def _create_metric_gauge(self, label: str, value: float, unit: str, color: str) -> ft.Container:
        """Create a circular gauge-style metric indicator."""
        return ft.Container(
            content=ft.Column(
                [
                    LabelText(label),
                    ft.Container(
                        content=ft.Column(
                            [
                                MetricText(f"{value:.1f}"),
                                LabelText(unit),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=0,
                        ),
                        width=60,
                        height=60,
                        bgcolor=ft.Colors.with_opacity(0.1, color),
                        border=ft.border.all(2, color),
                        border_radius=30,
                        padding=ft.padding.all(4),
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=4,
            ),
            padding=ft.padding.all(8),
        )

    def _create_technology_badge(self) -> ft.Container:
        """Create the Redis technology badge section."""
        primary_color, _, _ = self._get_status_colors()

        return ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Text("🗄️", size=32),
                        padding=ft.padding.all(8),
                        bgcolor=primary_color,
                        border_radius=12,
                        margin=ft.margin.only(bottom=8),
                    ),
                    TitleText("Redis"),
                    SecondaryText("Cache + Pub/Sub"),
                    ft.Container(
                        content=LabelText(
                            "CACHE",
                            color=ft.Colors.WHITE,
                        ),
                        padding=ft.padding.symmetric(horizontal=8, vertical=2),
                        bgcolor=ft.Colors.RED,
                        border_radius=8,
                        margin=ft.margin.only(top=4),
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=4,
            ),
            padding=ft.padding.all(16),
            width=160,  # Expanded badge width to 160px
        )

    def _create_metrics_section(self) -> ft.Container:
        """Create the Redis metrics section with memory and connection stats."""
        # Sample Redis metrics (in real app, this would come from Redis INFO command)
        redis_metrics = {
            "memory": {"used": 45.2, "unit": "MB", "color": ft.Colors.BLUE},
            "connections": {"active": 12, "unit": "conn", "color": ft.Colors.GREEN},
            "hit_ratio": {"rate": 94.7, "unit": "%", "color": ft.Colors.PURPLE},
        }

        metrics_controls = []
        for metric_key, data in redis_metrics.items():
            label = metric_key.replace("_", " ").title()
            metrics_controls.append(
                self._create_metric_gauge(
                    label,
                    data["used"] if "used" in data else data.get("active", data.get("rate", 0)),
                    data["unit"],
                    data["color"]
                )
            )

        return ft.Column(
            [
                PrimaryText("Cache Metrics"),
                ft.Divider(height=1, color=ft.Colors.GREY_300),
                ft.Row(metrics_controls, spacing=15, alignment=ft.MainAxisAlignment.CENTER),
            ],
            spacing=8,
        )

    def _create_performance_section(self) -> ft.Container:
        """Create the Redis performance and statistics section."""
        response_time = self.component_data.response_time_ms or 0.0

        # Sample Redis performance stats
        performance_stats = {
            "Uptime": "7d 12h",
            "Commands/sec": "1,247",
            "Keys": "15,432",
            "Keyspace Hits": "94.7%",
            "Memory Peak": "67.2MB",
        }

        perf_content = [
            PrimaryText("Performance"),
            ft.Divider(height=1, color=ft.Colors.GREY_300),
        ]

        for stat_name, stat_value in performance_stats.items():
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
        perf_content.extend([
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
        ])

        return ft.Column(perf_content, spacing=6)

    def _on_card_hover(self, e: ft.ControlEvent) -> None:
        """Handle card hover effects."""
        print(f"Redis card hover: {e.data}")
        if e.data == "true":  # Mouse enter
            self._card_container.scale = 1.05
        else:  # Mouse leave
            self._card_container.scale = 1.0

        self._card_container.update()

    def build(self) -> ft.Container:
        """Build and return the complete Redis card with responsive layout."""
        primary_color, background_color, border_color = self._get_status_colors()

        # Use shared responsive 3-section layout prioritizing middle section
        content = create_responsive_3_section_layout(
            left_content=self._create_technology_badge(),
            middle_content=self._create_metrics_section(),
            right_content=self._create_performance_section()
        )

        self._card_container = ft.Container(
            content=content,
            bgcolor=ft.Colors.SURFACE,
            border=ft.border.all(1, border_color),
            border_radius=16,
            padding=0,
            scale=1,
            animate_scale=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
            on_hover=self._on_card_hover,
            width=None,  # Let ResponsiveRow handle the width
            height=280,
        )

        return self._card_container
