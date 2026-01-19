"""
Scheduler Card

Modern card component for displaying APScheduler job status.
Table layout matching the worker card pattern.
"""

import contextlib
from datetime import datetime

import flet as ft
from app.components.frontend.controls import SecondaryText
from app.components.frontend.theme import AegisTheme as Theme
from app.services.system.models import ComponentStatus

from .card_container import CardContainer
from .card_utils import (
    create_header_row,
    get_status_colors,
)


def simplify_schedule(schedule: str) -> str:
    """Simplify verbose schedule strings for display.

    Converts verbose cron strings like "Cron: hour=2, minute=0, second=0"
    to simpler formats like "Daily 2:00 AM".
    """
    if not schedule:
        return "—"

    # Already simple formats pass through
    if schedule.startswith("Every "):
        return schedule

    # Handle verbose cron format: "Cron: hour=2, minute=0, second=0"
    if schedule.startswith("Cron:"):
        parts = schedule.replace("Cron:", "").strip()
        params: dict[str, int] = {}
        for part in parts.split(","):
            part = part.strip()
            if "=" in part:
                key, value = part.split("=", 1)
                with contextlib.suppress(ValueError):
                    params[key.strip()] = int(value.strip())

        hour = params.get("hour")
        minute = params.get("minute", 0)

        if hour is not None:
            # Format as time
            period = "AM" if hour < 12 else "PM"
            display_hour = hour if hour <= 12 else hour - 12
            if display_hour == 0:
                display_hour = 12
            return f"Daily {display_hour}:{minute:02d} {period}"

    # Truncate long schedules
    if len(schedule) > 15:
        return schedule[:12] + "..."

    return schedule


def format_relative_future_time(iso_str: str) -> str:
    """Convert ISO datetime string to relative future time.

    Args:
        iso_str: ISO format datetime string

    Returns:
        Human-readable relative time like "in 2h", "in 30m"
    """
    try:
        # Parse ISO datetime string
        if "T" in iso_str:
            dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
            # Make naive for comparison if needed
            if dt.tzinfo is not None:
                dt = dt.replace(tzinfo=None)
        else:
            dt = datetime.fromisoformat(iso_str)

        now = datetime.now()
        diff = dt - now

        seconds = diff.total_seconds()
        if seconds < 0:
            return "now"
        elif seconds < 60:
            return f"in {int(seconds)}s"
        elif seconds < 3600:
            mins = int(seconds / 60)
            return f"in {mins}m"
        elif seconds < 86400:
            hours = seconds / 3600
            if hours == int(hours):
                return f"in {int(hours)}h"
            else:
                # Show hours and minutes for more precision
                h = int(hours)
                m = int((seconds % 3600) / 60)
                if m > 0:
                    return f"in {h}h {m}m"
                return f"in {h}h"
        else:
            days = int(seconds / 86400)
            return f"in {days}d"
    except Exception:
        return "—"


class SchedulerCard:
    """
    A clean scheduler card showing scheduled jobs in a table.

    Features:
    - Table layout with header and job rows (matching worker card)
    - Jobs sorted by next run time (soonest first)
    - Relative time display for next run
    - Active/Paused job counts
    - Responsive design
    """

    def __init__(self, component_data: ComponentStatus) -> None:
        """Initialize with scheduler data from health check."""
        self.component_data = component_data
        self.metadata = component_data.metadata or {}

    def _create_job_table(self) -> ft.Container:
        """Create the job status table."""
        upcoming_tasks = self.metadata.get("upcoming_tasks", [])

        # Table header
        header_style = ft.TextStyle(
            size=11,
            weight=ft.FontWeight.W_600,
            color=ft.Colors.ON_SURFACE_VARIANT,
        )

        header_row = ft.Container(
            content=ft.Row(
                [
                    ft.Container(width=16),  # Icon column
                    ft.Container(
                        content=ft.Text("Job", style=header_style),
                        expand=True,
                    ),
                    ft.Container(
                        content=ft.Text("Schedule", style=header_style),
                        width=100,
                        alignment=ft.alignment.center_right,
                    ),
                    ft.Container(
                        content=ft.Text("Next Run", style=header_style),
                        width=70,
                        alignment=ft.alignment.center_right,
                    ),
                ],
                spacing=4,
            ),
            padding=ft.padding.only(bottom=8),
            border=ft.border.only(bottom=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT)),
        )

        # Build job rows
        rows = []
        cell_style = ft.TextStyle(size=12, color=ft.Colors.ON_SURFACE)

        if upcoming_tasks:
            for task in upcoming_tasks:
                # Handle both dict and object formats
                if isinstance(task, dict):
                    name = task.get("name", task.get("id", "Unknown"))
                    schedule = task.get("schedule", "Unknown")
                    next_run = task.get("next_run", "")
                else:
                    name = getattr(task, "name", "Unknown")
                    schedule = getattr(task, "schedule", "Unknown")
                    next_run = getattr(task, "next_run", "")

                # Format schedule and next run time
                schedule_display = simplify_schedule(schedule)
                next_run_display = format_relative_future_time(next_run)

                # Active jobs have green status
                status_icon = "🟢"

                row = ft.Container(
                    content=ft.Row(
                        [
                            ft.Container(
                                content=ft.Text(status_icon, size=12),
                                width=16,
                            ),
                            ft.Container(
                                content=ft.Text(name, style=cell_style),
                                expand=True,
                            ),
                            ft.Container(
                                content=ft.Text(
                                    schedule_display,
                                    style=ft.TextStyle(
                                        size=12,
                                        color=ft.Colors.ON_SURFACE_VARIANT,
                                    ),
                                ),
                                width=100,
                                alignment=ft.alignment.center_right,
                            ),
                            ft.Container(
                                content=ft.Text(
                                    next_run_display,
                                    style=ft.TextStyle(
                                        size=12,
                                        color=Theme.Colors.TEXT_SECONDARY,
                                    ),
                                ),
                                width=70,
                                alignment=ft.alignment.center_right,
                            ),
                        ],
                        spacing=4,
                    ),
                    padding=ft.padding.symmetric(vertical=6),
                )
                rows.append(row)
        else:
            # No jobs placeholder
            rows.append(
                ft.Container(
                    content=ft.Text(
                        "No scheduled jobs",
                        size=12,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                        italic=True,
                    ),
                    padding=ft.padding.symmetric(vertical=12),
                )
            )

        return ft.Container(
            content=ft.Column(
                [header_row] + rows,
                spacing=0,
            ),
            bgcolor=ft.Colors.with_opacity(0.08, ft.Colors.GREY),
            border_radius=8,
            border=ft.border.all(1, ft.Colors.with_opacity(0.15, ft.Colors.GREY)),
            padding=ft.padding.all(12),
        )

    def _create_stats_row(self) -> ft.Container:
        """Create the stats summary row."""
        active_tasks = self.metadata.get("active_tasks", 0)
        paused_tasks = self.metadata.get("paused_tasks", 0)

        return ft.Container(
            content=ft.Row(
                [
                    SecondaryText(f"Active: {active_tasks}", size=11),
                    SecondaryText("|", size=11),
                    SecondaryText(f"Paused: {paused_tasks}", size=11),
                ],
                spacing=8,
            ),
            padding=ft.padding.only(top=12),
        )

    def _create_card_content(self) -> ft.Container:
        """Create the full card content with header, job table, and stats."""
        return ft.Container(
            content=ft.Column(
                [
                    create_header_row(
                        "Scheduler",
                        "APScheduler",
                        self.component_data,
                    ),
                    self._create_job_table(),
                    self._create_stats_row(),
                ],
                spacing=0,
            ),
            padding=ft.padding.all(16),
            expand=True,
        )

    def build(self) -> ft.Container:
        """Build and return the complete scheduler card."""
        _, _, border_color = get_status_colors(self.component_data)

        return CardContainer(
            content=self._create_card_content(),
            border_color=border_color,
            component_data=self.component_data,
            component_name="scheduler",
        )
