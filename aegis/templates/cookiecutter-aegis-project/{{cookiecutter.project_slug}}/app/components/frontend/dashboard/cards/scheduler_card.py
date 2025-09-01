"""
Stunning Scheduler Component Card

Modern, visually striking card component that displays scheduled jobs,
job statistics, and scheduling information using shared utility functions.
"""


import flet as ft

from app.components.frontend.controls import LabelText, PrimaryText
from app.services.system.models import ComponentStatus

from .card_utils import (
    create_hover_handler,
    create_responsive_3_section_layout,
    create_standard_card_container,
    create_stats_row,
    create_tech_badge,
    get_status_colors,
)


class SchedulerCard:
    """
    A visually stunning, wide component card for displaying Scheduler/APScheduler metrics.
    
    Features:
    - Modern Material Design 3 styling
    - Three-section layout (badge, jobs, stats)
    - Scheduled job indicators with next run times
    - Job statistics and scheduler status
    - Status-aware coloring and hover effects
    - 800px width for optimal content spacing
    """

    def __init__(self, component_data: ComponentStatus) -> None:
        """
        Initialize the Scheduler card with component data.
        
        Args:
            component_data: ComponentStatus containing scheduler health and metrics
        """
        self.component_data = component_data
        self._card_container: ft.Container | None = None

    def _create_job_indicator(self, job_name: str, next_run: str, job_type: str) -> ft.Container:
        """Create a job status indicator with next run information."""
        job_color = ft.Colors.TEAL if job_type == "recurring" else ft.Colors.BLUE
        job_icon = "🔄" if job_type == "recurring" else "⏱️"

        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text(job_icon, size=12),
                            LabelText(job_name.upper()),
                        ],
                        spacing=5,
                    ),
                    ft.Container(height=2, bgcolor=job_color, border_radius=1),
                    LabelText(next_run, size=10),
                ],
                spacing=2,
            ),
            padding=ft.padding.all(8),
            bgcolor=ft.Colors.SURFACE,
            border=ft.border.all(1, job_color),
            border_radius=8,
            width=120,
            height=70,
        )

    def _create_technology_badge(self) -> ft.Container:
        """Create the Scheduler technology badge section."""
        primary_color, _, _ = get_status_colors(self.component_data)

        return create_tech_badge(
            title="Scheduler",
            subtitle="APScheduler",
            icon="⏰",
            badge_text="JOBS",
            badge_color=ft.Colors.TEAL,
            primary_color=primary_color,
            width=160
        )

    def _create_jobs_section(self) -> ft.Container:
        """Create the scheduled jobs section with job indicators."""
        # Sample scheduled jobs (in real app, this would come from APScheduler)
        scheduled_jobs = [
            {"name": "backup", "next_run": "in 2h", "type": "recurring"},
            {"name": "cleanup", "next_run": "daily", "type": "recurring"},
            {"name": "report", "next_run": "weekly", "type": "recurring"},
        ]

        job_controls = []
        for job_data in scheduled_jobs:
            job_controls.append(
                self._create_job_indicator(
                    job_data["name"],
                    job_data["next_run"],
                    job_data["type"]
                )
            )

        # Add placeholder if no jobs
        if not job_controls:
            job_controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("📅", size=24),
                            LabelText("No Scheduled Jobs"),
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
                    PrimaryText("Scheduled Jobs"),
                    ft.Divider(height=1, color=ft.Colors.GREY_300),
                    ft.Container(
                        content=ft.Row(
                            job_controls,
                            spacing=12,
                            wrap=True,
                            alignment=ft.MainAxisAlignment.CENTER,
                        ),
                        width=360,  # Good width for job indicators
                        alignment=ft.alignment.center,
                    ),
                ],
                spacing=12,
                alignment=ft.MainAxisAlignment.START,
            ),
            width=400,  # Section width
            padding=ft.padding.all(16),
            alignment=ft.alignment.top_center,
        )

    def _create_stats_section(self) -> ft.Container:
        """Create the scheduler statistics section."""
        # Sample scheduler stats (in real app, this would come from APScheduler metrics)
        scheduler_stats = {
            "Total Jobs": "5",
            "Active Jobs": "3",
            "Completed Today": "127",
            "Failed Jobs": "2",
            "Next Job": "in 2h",
        }

        stats_content = [
            PrimaryText("Job Statistics"),
            ft.Divider(height=1, color=ft.Colors.GREY_300),
        ]

        # Add all stats using the utility function
        for stat_name, stat_value in scheduler_stats.items():
            stats_content.append(create_stats_row(stat_name, stat_value))

        # Add scheduler status
        stats_content.extend([
            ft.Divider(height=1, color=ft.Colors.GREY_300),
            create_stats_row(
                "Status",
                self.component_data.status.value.title(),
                get_status_colors(self.component_data)[0]
            ),
        ])

        return ft.Container(
            content=ft.Column(
                stats_content,
                spacing=8,
                alignment=ft.MainAxisAlignment.START,
            ),
            padding=ft.padding.all(16),
            width=240,  # Stats section width
            alignment=ft.alignment.top_left,
        )

    def build(self) -> ft.Container:
        """Build and return the complete Scheduler card with responsive layout."""
        primary_color, background_color, border_color = get_status_colors(self.component_data)

        # Use shared responsive 3-section layout prioritizing middle section
        content = create_responsive_3_section_layout(
            left_content=self._create_technology_badge(),
            middle_content=self._create_jobs_section(),
            right_content=self._create_stats_section()
        )

        self._card_container = create_standard_card_container(
            content=content,
            primary_color=primary_color,
            border_color=border_color,
            width=None,  # Let ResponsiveRow handle the width
            hover_handler=create_hover_handler(None)  # Will set after container creation
        )

        # Set the hover handler with the actual container
        self._card_container.on_hover = create_hover_handler(self._card_container)

        return self._card_container
