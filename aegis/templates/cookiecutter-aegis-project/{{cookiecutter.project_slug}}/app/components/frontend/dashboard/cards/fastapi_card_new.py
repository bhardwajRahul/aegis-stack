"""
Stunning FastAPI Component Card

Modern, visually striking card component that displays rich FastAPI metrics
and system performance data using the BaseCard architecture.
"""

from typing import Any

import flet as ft

from app.components.frontend.controls import LabelText

from .base_card import BaseCard
from .card_factory import CardFactory


class FastAPICard(BaseCard):
    """
    A visually stunning, wide component card for displaying FastAPI metrics.

    Features:
    - Inherits common functionality from BaseCard
    - Three-section layout (badge, metrics, details)
    - Status-aware coloring and visual indicators
    - Progress bars for CPU, Memory, and Disk usage
    - API endpoint information
    """

    def _get_technology_info(self) -> dict[str, Any]:
        """Get FastAPI-specific technology badge information."""
        return {
            "title": "FastAPI",
            "subtitle": "Backend API",
            "badge_text": "ACTIVE",
            "icon": "🚀",
            "badge_color": ft.Colors.GREEN_100,
            "width": 140,
        }

    def _create_middle_section(self) -> ft.Container:
        """Create the system metrics section with progress indicators."""
        sub_components = self.component_data.sub_components
        progress_indicators = []

        # CPU metrics
        cpu_data = sub_components.get("cpu")
        if cpu_data and cpu_data.metadata:
            cpu_percent = cpu_data.metadata.get("percent_used", 0.0)
            cpu_color = (
                ft.Colors.GREEN
                if cpu_percent < 70
                else ft.Colors.ORANGE
                if cpu_percent < 85
                else ft.Colors.RED
            )
            progress_indicators.append(
                CardFactory.create_progress_indicator(
                    "CPU Usage",
                    cpu_percent,
                    f"{cpu_data.metadata.get('core_count', 'N/A')} cores",
                    cpu_color,
                )
            )

        # Memory metrics
        memory_data = sub_components.get("memory")
        if memory_data and memory_data.metadata:
            memory_percent = memory_data.metadata.get("percent_used", 0.0)
            total_gb = memory_data.metadata.get("total_gb", 0.0)
            available_gb = memory_data.metadata.get("available_gb", 0.0)
            used_gb = total_gb - available_gb
            memory_color = (
                ft.Colors.GREEN
                if memory_percent < 70
                else ft.Colors.ORANGE
                if memory_percent < 85
                else ft.Colors.RED
            )
            progress_indicators.append(
                CardFactory.create_progress_indicator(
                    "Memory Usage",
                    memory_percent,
                    f"{used_gb:.1f}GB / {total_gb:.1f}GB",
                    memory_color,
                )
            )

        # Disk metrics
        disk_data = sub_components.get("disk")
        if disk_data and disk_data.metadata:
            disk_percent = disk_data.metadata.get("percent_used", 0.0)
            total_gb = disk_data.metadata.get("total_gb", 0.0)
            free_gb = disk_data.metadata.get("free_gb", 0.0)
            disk_color = (
                ft.Colors.GREEN
                if disk_percent < 70
                else ft.Colors.ORANGE
                if disk_percent < 85
                else ft.Colors.RED
            )
            progress_indicators.append(
                CardFactory.create_progress_indicator(
                    "Disk Usage",
                    disk_percent,
                    f"{free_gb:.1f}GB / {total_gb:.1f}GB",
                    disk_color,
                )
            )

        return ft.Container(
            content=ft.Column(
                progress_indicators,
                spacing=12,
            ),
            width=260,  # Reduced width to prevent bleeding
            padding=ft.padding.all(16),
        )

    def _create_right_section(self) -> ft.Container:
        """Create the performance and API details section."""
        response_time = self.component_data.response_time_ms or 0.0

        # Sample API endpoints
        api_endpoints = [
            "GET /health/",
            "GET /docs",
            "POST /api/v1/users",
            "GET /api/v1/status",
        ]

        # Create stats using factory
        stats = [
            CardFactory.create_stats_row("Response Time", f"{response_time:.1f}ms"),
            CardFactory.create_stats_row(
                "Status",
                self.component_data.status.value.title(),
                self._get_status_colors()[0],
            ),
            CardFactory.create_stats_row("Endpoints", f"{len(api_endpoints)} routes"),
        ]

        # Add API endpoints
        endpoint_items = []
        for endpoint in api_endpoints[:3]:  # Show first 3
            endpoint_items.append(LabelText(f"• {endpoint}"))

        if len(api_endpoints) > 3:
            endpoint_items.append(LabelText(f"• +{len(api_endpoints) - 3} more..."))

        all_content = stats + endpoint_items

        return CardFactory.create_section_with_title(
            "Performance", all_content, width=240
        )

    def _get_card_width(self) -> int:
        """Get the total width for FastAPI cards."""
        return 600
