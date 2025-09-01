"""
Stunning Worker Component Card

Modern, visually striking card component that displays rich Worker/arq metrics,
queue statistics, and job processing data using ee-toolset design standards.
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


class WorkerCard:
    """
    A visually stunning, wide component card for displaying Worker/arq metrics.

    Features:
    - Modern Material Design 3 styling
    - Three-section layout (badge, queues, stats)
    - Queue-specific information and job statistics
    - Status-aware coloring and visual indicators
    - Hover effects and proper scaling
    """

    def __init__(self, component_data: ComponentStatus) -> None:
        """
        Initialize the Worker card with component data.

        Args:
            component_data: ComponentStatus containing Worker health and queue metrics
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

    def _create_queue_indicator(
        self, queue_name: str, queue_data: ComponentStatus
    ) -> ft.Container:
        """Create a queue status indicator with job statistics."""
        is_healthy = queue_data.healthy if queue_data else True
        queue_color = ft.Colors.GREEN if is_healthy else ft.Colors.RED

        # Extract job statistics from message
        message = queue_data.message if queue_data else "No data"
        jobs_info = "0 jobs"
        if "completed" in message.lower():
            # Parse something like "Queue healthy: 0 completed, 0 failed, 0 ongoing"
            parts = message.split(":")
            if len(parts) > 1:
                jobs_info = parts[1].strip()

        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text("📥", size=12),
                            LabelText(queue_name.upper()),
                        ],
                        spacing=5,
                    ),
                    ft.Container(height=2, bgcolor=queue_color, border_radius=1),
                    LabelText(jobs_info, size=10),
                ],
                spacing=2,
            ),
            padding=ft.padding.all(8),
            bgcolor=ft.Colors.SURFACE,
            border=ft.border.all(1, queue_color),
            border_radius=8,
            width=100,
            height=70,
        )

    def _create_technology_badge(self) -> ft.Container:
        """Create the Worker/arq technology badge section."""
        primary_color, _, _ = self._get_status_colors()

        return ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Text("⚡", size=32),
                        padding=ft.padding.all(8),
                        bgcolor=primary_color,
                        border_radius=12,
                        margin=ft.margin.only(bottom=8),
                    ),
                    TitleText("Worker"),
                    SecondaryText("arq + Redis"),
                    ft.Container(
                        content=LabelText(
                            "QUEUES",
                            color=ft.Colors.WHITE,
                        ),
                        padding=ft.padding.symmetric(horizontal=8, vertical=2),
                        bgcolor=ft.Colors.PURPLE,
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
            alignment=ft.alignment.center,
        )

    def _create_queues_section(self) -> ft.Container:
        """Create the queues section with individual queue indicators."""
        queues_data = {}
        if (
            self.component_data.sub_components
            and "queues" in self.component_data.sub_components
        ):
            queues_comp = self.component_data.sub_components["queues"]
            if queues_comp.sub_components:
                queues_data = queues_comp.sub_components

        queue_controls = []

        if queues_data:
            # Show max 3 queues
            for queue_name, queue_data in list(queues_data.items())[:3]:
                queue_controls.append(
                    self._create_queue_indicator(queue_name, queue_data)
                )
        else:
            # Show placeholder when no queue data
            queue_controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("📭", size=24),
                            LabelText("No Active Queues"),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=ft.padding.all(16),
                    bgcolor=ft.Colors.GREY_200,
                    border=ft.border.all(1, ft.Colors.GREY_300),
                    border_radius=8,
                    height=80,
                )
            )

        return ft.Container(
            content=ft.Column(
                [
                    PrimaryText("Queue Status"),
                    ft.Divider(height=1, color=ft.Colors.GREY_300),
                    ft.Container(
                        content=ft.Row(
                            queue_controls,
                            spacing=12,
                            wrap=True,
                            alignment=ft.MainAxisAlignment.CENTER,
                        ),
                        width=360,  # Expanded width for better queue spacing
                        alignment=ft.alignment.center,
                    ),
                ],
                spacing=12,
                alignment=ft.MainAxisAlignment.START,
            ),
            alignment=ft.alignment.top_center,
        )

    def _create_stats_section(self) -> ft.Container:
        """Create the worker statistics section."""
        # Sample worker stats (in real app, this would come from arq/Redis metrics)
        worker_stats = {
            "Active Workers": "2",
            "Total Jobs": "1,247",
            "Failed Jobs": "12",
            "Avg Process Time": "1.2s",
        }

        stats_content = [
            PrimaryText("Worker Stats"),
            ft.Divider(height=1, color=ft.Colors.GREY_300),
        ]

        for stat_name, stat_value in worker_stats.items():
            stats_content.append(
                ft.Row(
                    [
                        SecondaryText(f"{stat_name}:"),
                        LabelText(stat_value),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                )
            )

        # Add status info
        stats_content.extend([
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

        return ft.Container(
            content=ft.Column(
                stats_content,
                spacing=8,  # Increased spacing for better vertical distribution
                alignment=ft.MainAxisAlignment.START,
            ),
            alignment=ft.alignment.top_left,  # Ensure proper alignment
        )

    def _on_card_hover(self, e: ft.ControlEvent) -> None:
        """Handle card hover effects."""
        print(f"Worker card hover: {e.data}")
        if e.data == "true":  # Mouse enter
            self._card_container.scale = 1.05
        else:  # Mouse leave
            self._card_container.scale = 1.0

        self._card_container.update()

    def build(self) -> ft.Container:
        """Build and return the complete Worker card with responsive layout."""
        primary_color, background_color, border_color = self._get_status_colors()

        # Use shared responsive 3-section layout prioritizing middle section
        content = create_responsive_3_section_layout(
            left_content=self._create_technology_badge(),
            middle_content=self._create_queues_section(),
            right_content=self._create_stats_section()
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
