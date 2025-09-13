"""
Stunning Redis/Cache Component Card

Modern, visually striking card component that displays real Redis metrics
from Redis INFO command, including memory usage, cache hit rates, operations
per second, connection statistics, and comprehensive performance data.
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
    A visually stunning, wide component card for displaying real Redis metrics.

    Features:
    - Modern Material Design 3 styling with circular gauge indicators
    - Three-section layout (badge, real-time metrics, performance stats)
    - Real Redis INFO command data: hit rates, memory usage, ops/sec
    - Comprehensive statistics: uptime, keys, connections, evictions
    - Health-aware coloring based on cache performance thresholds
    - Graceful fallback for unavailable metrics
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

    def _create_metric_gauge(
        self, label: str, value: float, unit: str, color: str
    ) -> ft.Container:
        """Create a circular gauge-style metric indicator."""
        # Format value appropriately based on size
        if value >= 1000:
            formatted_value = f"{value / 1000:.1f}k"
        elif value >= 1000000:
            formatted_value = f"{value / 1000000:.1f}M"
        else:
            formatted_value = (
                f"{value:.1f}" if isinstance(value, float) else str(int(value))
            )

        return ft.Container(
            content=ft.Column(
                [
                    LabelText(label),
                    ft.Container(
                        content=ft.Column(
                            [
                                MetricText(formatted_value),
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
        # Extract real Redis metrics from component metadata
        metadata = self.component_data.metadata or {}

        # Calculate hit rate with proper color coding
        hit_rate = metadata.get("hit_rate_percent", 0)
        hit_rate_color = (
            ft.Colors.GREEN
            if hit_rate >= 90
            else ft.Colors.ORANGE
            if hit_rate >= 70
            else ft.Colors.RED
        )

        # Calculate memory usage percentage if maxmemory is set
        used_memory = metadata.get("used_memory", 0)
        max_memory = metadata.get("maxmemory", 0)

        if max_memory > 0:
            memory_percent = (used_memory / max_memory) * 100
            memory_value = memory_percent
            memory_unit = "%"
            # Set color based on memory usage percentage
            if memory_percent >= 90:
                memory_color = ft.Colors.RED
            elif memory_percent >= 70:
                memory_color = ft.Colors.ORANGE
            else:
                memory_color = ft.Colors.BLUE
        else:
            # Show absolute memory usage in MB
            memory_value = used_memory / (1024 * 1024) if used_memory > 0 else 0
            memory_unit = "MB"
            memory_color = ft.Colors.BLUE

        # Get operations per second
        ops_per_sec = metadata.get("instantaneous_ops_per_sec", 0)

        redis_metrics = {
            "hit_ratio": {
                "value": hit_rate,
                "unit": "%",
                "color": hit_rate_color,
            },
            "memory": {
                "value": memory_value,
                "unit": memory_unit,
                "color": memory_color,
            },
            "ops_sec": {
                "value": ops_per_sec,
                "unit": "/sec",
                "color": ft.Colors.PURPLE,
            },
        }

        metrics_controls = []
        for metric_key, data in redis_metrics.items():
            label = metric_key.replace("_", " ").replace("ops sec", "Ops").title()
            metrics_controls.append(
                self._create_metric_gauge(
                    label,
                    data["value"],
                    data["unit"],
                    data["color"],
                )
            )

        return ft.Column(
            [
                PrimaryText("Cache Metrics"),
                ft.Divider(height=1, color=ft.Colors.GREY_300),
                ft.Row(
                    metrics_controls, spacing=15, alignment=ft.MainAxisAlignment.CENTER
                ),
            ],
            spacing=8,
        )

    def _create_performance_section(self) -> ft.Container:
        """Create the Redis performance and statistics section."""

        # Extract real Redis performance stats from metadata
        metadata = self.component_data.metadata or {}

        # Format uptime from seconds to human readable
        uptime_seconds = metadata.get("uptime_in_seconds", 0)
        uptime_days = uptime_seconds // 86400
        uptime_hours = (uptime_seconds % 86400) // 3600
        uptime_str = (
            f"{uptime_days}d {uptime_hours}h" if uptime_days > 0 else f"{uptime_hours}h"
        )

        # Format numbers with commas
        def format_number(num: int | float) -> str:
            if isinstance(num, float):
                return f"{num:,.1f}"
            return f"{num:,}"

        performance_stats = {
            "Uptime": uptime_str,
            "Commands/sec": format_number(metadata.get("instantaneous_ops_per_sec", 0)),
            "Total Keys": format_number(metadata.get("total_keys", 0)),
            "Memory Peak": metadata.get("used_memory_peak_human", "unknown"),
            "Connected Clients": format_number(metadata.get("connected_clients", 0)),
            "Evicted Keys": format_number(metadata.get("evicted_keys", 0)),
            "Fragmentation": f"{metadata.get('mem_fragmentation_ratio', 1.0):.2f}",
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

        # Wrap in a scrollable container to handle overflow
        return ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Column(
                            perf_content,
                            spacing=6,
                            scroll=ft.ScrollMode.AUTO,
                        ),
                        height=240,  # Increased height to show more stats
                    )
                ]
            ),
            padding=ft.padding.only(right=4),  # Add padding for scrollbar space
        )

    def build(self) -> ft.Container:
        """Build and return the complete Redis card with responsive layout."""
        primary_color, background_color, border_color = self._get_status_colors()

        # Use shared responsive 3-section layout prioritizing middle section
        content = create_responsive_3_section_layout(
            left_content=self._create_technology_badge(),
            middle_content=self._create_metrics_section(),
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
