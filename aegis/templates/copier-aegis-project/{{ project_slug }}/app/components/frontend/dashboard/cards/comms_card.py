"""
Communications Service Card

Modern card component specifically designed for communications service monitoring.
Shows email (Resend), SMS (Twilio), and voice call status with a clean layout.
"""

import flet as ft
from app.components.frontend.controls import LabelText, PrimaryText, ServiceCard
from app.components.frontend.controls.tech_badge import TechBadge
from app.services.system.models import ComponentStatus

from .card_container import CardContainer
from .card_utils import (
    get_status_colors,
)


class CommsCard:
    """
    A clean communications service card with real metrics.

    Features:
    - Real provider configuration from health checks
    - Clean 2-column layout
    - Highlighted metric containers
    - Channel status indicators
    """

    def __init__(self, component_data: ComponentStatus):
        """Initialize with communications service data from health check."""
        self.component_data = component_data
        self.metadata = component_data.metadata or {}

    def _create_metric_container(
        self, label: str, value: str, color: str = ft.Colors.BLUE
    ) -> ft.Container:
        """Create a properly sized metric container."""
        return ft.Container(
            content=ft.Column(
                [
                    LabelText(label),
                    ft.Container(height=8),  # More spacing
                    PrimaryText(value),
                ],
                spacing=0,
                horizontal_alignment=ft.CrossAxisAlignment.START,
            ),
            padding=ft.padding.all(16),  # More padding
            bgcolor=ft.Colors.with_opacity(0.08, color),
            border_radius=8,
            border=ft.border.all(1, ft.Colors.with_opacity(0.15, color)),
            height=80,  # Taller containers
            expand=True,
        )

    def _create_technology_badge(self) -> ft.Container:
        """Create technology badge for communications service."""
        primary_color, _, _ = get_status_colors(self.component_data)

        return TechBadge(
            title="Resend + Twilio",
            subtitle="Communications",
            badge_text="Comms",
            badge_color=ft.Colors.PINK,
            primary_color=primary_color,
        )

    def _create_metrics_section(self) -> ft.Container:
        """Create the metrics section with a clean grid layout."""
        # Get real data from metadata
        email_configured = self.metadata.get("email_configured", False)
        sms_configured = self.metadata.get("sms_configured", False)
        voice_configured = self.metadata.get("voice_configured", False)
        channels_configured = self.metadata.get("channels_configured", 0)
        channels_total = self.metadata.get("channels_total", 3)
        response_time = self.component_data.response_time_ms

        # Get provider info
        email_provider = self.metadata.get("email_provider", "None")
        sms_provider = self.metadata.get("sms_provider", "None")

        # Create metrics grid (3 rows x 2 columns)
        return ft.Container(
            content=ft.Column(
                [
                    # Row 1: Email and SMS status
                    ft.Row(
                        [
                            self._create_metric_container(
                                "Email",
                                email_provider.title()
                                if email_configured
                                else "Not configured",
                                ft.Colors.GREEN if email_configured else ft.Colors.GREY,
                            ),
                            self._create_metric_container(
                                "SMS",
                                sms_provider.title()
                                if sms_configured
                                else "Not configured",
                                ft.Colors.GREEN if sms_configured else ft.Colors.GREY,
                            ),
                        ],
                        expand=True,
                    ),
                    ft.Container(height=12),  # Vertical spacing
                    # Row 2: Voice and Channels
                    ft.Row(
                        [
                            self._create_metric_container(
                                "Voice",
                                "Twilio" if voice_configured else "Not configured",
                                ft.Colors.GREEN if voice_configured else ft.Colors.GREY,
                            ),
                            self._create_metric_container(
                                "Channels",
                                f"{channels_configured}/{channels_total}",
                                (
                                    ft.Colors.GREEN
                                    if channels_configured == channels_total
                                    else ft.Colors.ORANGE
                                    if channels_configured > 0
                                    else ft.Colors.RED
                                ),
                            ),
                        ],
                        expand=True,
                    ),
                    ft.Container(height=12),  # Vertical spacing
                    # Row 3: Response time and Status
                    ft.Row(
                        [
                            self._create_metric_container(
                                "Response Time",
                                f"{response_time:.1f}ms" if response_time else "N/A",
                                (
                                    ft.Colors.GREEN
                                    if response_time and response_time < 100
                                    else ft.Colors.ORANGE
                                ),
                            ),
                            self._create_metric_container(
                                "Status",
                                (
                                    "Ready"
                                    if channels_configured > 0
                                    else "Configure providers"
                                ),
                                (
                                    ft.Colors.GREEN
                                    if channels_configured > 0
                                    else ft.Colors.ORANGE
                                ),
                            ),
                        ],
                        expand=True,
                    ),
                ],
                spacing=0,
            ),
            expand=True,
            padding=ft.padding.all(16),
        )

    def build(self) -> ft.Container:
        """Build and return the complete communications card."""
        # Get colors based on component status
        _, _, border_color = get_status_colors(self.component_data)

        # Use ServiceCard for consistent service card layout
        content = ServiceCard(
            left_content=self._create_technology_badge(),
            right_content=self._create_metrics_section(),
        )

        return CardContainer(
            content=content,
            border_color=border_color,
            component_data=self.component_data,
            component_name="comms",
        )
