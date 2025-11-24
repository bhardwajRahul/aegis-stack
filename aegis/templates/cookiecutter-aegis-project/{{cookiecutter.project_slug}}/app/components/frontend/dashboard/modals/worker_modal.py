"""
Worker Detail Modal

Displays comprehensive worker component information using component composition.
Each section is a self-contained Flet control that can be reused and tested independently.
"""

import flet as ft
from app.components.frontend.controls import (
    BodyText,
    H3Text,
    PrimaryText,
    SecondaryText,
)
from app.components.frontend.theme import AegisTheme as Theme
from app.services.system.models import ComponentStatus

from .base_detail_popup import BaseDetailPopup
from .modal_constants import ModalLayout
from .modal_sections import MetricCard

# Worker health status thresholds
FAILURE_RATE_CRITICAL_THRESHOLD = 20  # % - Red status (failing)
FAILURE_RATE_WARNING_THRESHOLD = 5  # % - Yellow status (degraded)
SUCCESS_RATE_HEALTHY_THRESHOLD = 95  # % - Green display
SUCCESS_RATE_WARNING_THRESHOLD = 80  # % - Yellow display

# Queue health table column widths (pixels)
COL_WIDTH_STATUS_ICON = 30
COL_WIDTH_QUEUED = 80
COL_WIDTH_PROCESSING = 80
COL_WIDTH_COMPLETED = 100
COL_WIDTH_FAILED = 80
COL_WIDTH_SUCCESS_RATE = 100
COL_WIDTH_STATUS = 80

# Statistics section layout
STAT_LABEL_WIDTH = 200  # Label column width

# Display formatting
MAX_REDIS_URL_DISPLAY_LENGTH = 50


class QueueHealthRow(ft.Container):
    """Single queue health status display."""

    def __init__(self, queue_component: ComponentStatus, page: ft.Page) -> None:
        """
        Initialize queue health row.

        Args:
            queue_component: ComponentStatus for a single queue
        """
        super().__init__()

        queue_name = queue_component.name
        metadata = queue_component.metadata or {}
        worker_alive = metadata.get("worker_alive", False)
        queued_jobs = metadata.get("queued_jobs", 0)
        jobs_ongoing = metadata.get("jobs_ongoing", 0)
        jobs_completed = metadata.get("jobs_completed", 0)
        jobs_failed = metadata.get("jobs_failed", 0)
        failure_rate = metadata.get("failure_rate_percent", 0.0)

        # Determine status icon and color
        if not worker_alive:
            status_icon = "⚫"  # Offline
            status_color = ft.Colors.ON_SURFACE_VARIANT
        elif failure_rate > FAILURE_RATE_CRITICAL_THRESHOLD:
            status_icon = "🔴"  # Failing
            status_color = Theme.Colors.ERROR
        elif failure_rate > FAILURE_RATE_WARNING_THRESHOLD:
            status_icon = "🟡"  # Degraded
            status_color = Theme.Colors.WARNING
        else:
            status_icon = "🟢"  # Healthy
            status_color = Theme.Colors.SUCCESS

        # Success rate display with color coding
        success_rate = 100 - failure_rate if worker_alive else 0
        if success_rate >= SUCCESS_RATE_HEALTHY_THRESHOLD:
            rate_color = Theme.Colors.SUCCESS
        elif success_rate >= SUCCESS_RATE_WARNING_THRESHOLD:
            rate_color = Theme.Colors.WARNING
        else:
            rate_color = Theme.Colors.ERROR

        self.content = ft.Row(
            [
                ft.Container(
                    content=ft.Text(status_icon, size=16),
                    width=COL_WIDTH_STATUS_ICON,
                ),
                ft.Container(
                    content=PrimaryText(queue_name, size=Theme.Typography.BODY),
                    expand=2,
                ),
                ft.Container(
                    content=BodyText(str(queued_jobs), text_align=ft.TextAlign.CENTER),
                    width=COL_WIDTH_QUEUED,
                ),
                ft.Container(
                    content=BodyText(str(jobs_ongoing), text_align=ft.TextAlign.CENTER),
                    width=COL_WIDTH_PROCESSING,
                ),
                ft.Container(
                    content=BodyText(
                        str(jobs_completed), text_align=ft.TextAlign.CENTER
                    ),
                    width=COL_WIDTH_COMPLETED,
                ),
                ft.Container(
                    content=BodyText(str(jobs_failed), text_align=ft.TextAlign.CENTER),
                    width=COL_WIDTH_FAILED,
                ),
                ft.Container(
                    content=SecondaryText(
                        f"{success_rate:.1f}%",
                        color=rate_color,
                        weight=Theme.Typography.WEIGHT_SEMIBOLD,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    width=COL_WIDTH_SUCCESS_RATE,
                ),
                ft.Container(
                    content=SecondaryText(
                        "Online" if worker_alive else "Offline",
                        color=status_color,
                        weight=Theme.Typography.WEIGHT_SEMIBOLD,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    width=COL_WIDTH_STATUS,
                ),
            ],
            spacing=Theme.Spacing.SM,
        )
        self.padding = ft.padding.symmetric(vertical=Theme.Spacing.XS)


class OverviewSection(ft.Container):
    """Overview section showing key worker metrics."""

    def __init__(self, worker_component: ComponentStatus, page: ft.Page) -> None:
        """
        Initialize overview section.

        Args:
            worker_component: Worker ComponentStatus with metadata and sub_components
        """
        super().__init__()
        self.padding = Theme.Spacing.MD

        metadata = worker_component.metadata or {}

        # Get queue sub-components
        queues_component = worker_component.sub_components.get("queues")
        if queues_component and queues_component.sub_components:
            total_queues = len(queues_component.sub_components)
        else:
            total_queues = 0

        active_workers = metadata.get("active_workers", 0)
        total_ongoing = metadata.get("total_ongoing", 0)

        self.content = ft.Row(
            [
                MetricCard(
                    "Total Queues",
                    str(total_queues),
                    Theme.Colors.INFO,
                ),
                MetricCard(
                    "Active Workers",
                    str(active_workers),
                    Theme.Colors.SUCCESS,
                ),
                MetricCard(
                    "Jobs Processing",
                    str(total_ongoing),
                    Theme.Colors.INFO,
                ),
            ],
            spacing=Theme.Spacing.MD,
        )


class QueueHealthSection(ft.Container):
    """Queue health status table section."""

    def __init__(self, worker_component: ComponentStatus, page: ft.Page) -> None:
        """
        Initialize queue health section.

        Args:
            worker_component: Worker ComponentStatus with queue sub-components
        """
        super().__init__()
        self.padding = Theme.Spacing.MD

        # Extract queue sub-components
        queues_component = worker_component.sub_components.get("queues")
        queue_components = []
        if queues_component and queues_component.sub_components:
            queue_components = list(queues_component.sub_components.values())

        # Column headers
        header_row = ft.Row(
            [
                ft.Container(width=COL_WIDTH_STATUS_ICON),  # Status icon column
                ft.Container(
                    content=SecondaryText(
                        "Queue Name", weight=Theme.Typography.WEIGHT_SEMIBOLD
                    ),
                    expand=2,
                ),
                ft.Container(
                    content=SecondaryText(
                        "Queued",
                        weight=Theme.Typography.WEIGHT_SEMIBOLD,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    width=COL_WIDTH_QUEUED,
                ),
                ft.Container(
                    content=SecondaryText(
                        "Processing",
                        weight=Theme.Typography.WEIGHT_SEMIBOLD,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    width=COL_WIDTH_PROCESSING,
                ),
                ft.Container(
                    content=SecondaryText(
                        "Completed",
                        weight=Theme.Typography.WEIGHT_SEMIBOLD,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    width=COL_WIDTH_COMPLETED,
                ),
                ft.Container(
                    content=SecondaryText(
                        "Failed",
                        weight=Theme.Typography.WEIGHT_SEMIBOLD,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    width=COL_WIDTH_FAILED,
                ),
                ft.Container(
                    content=SecondaryText(
                        "Success Rate",
                        weight=Theme.Typography.WEIGHT_SEMIBOLD,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    width=COL_WIDTH_SUCCESS_RATE,
                ),
                ft.Container(
                    content=SecondaryText(
                        "Status",
                        weight=Theme.Typography.WEIGHT_SEMIBOLD,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    width=COL_WIDTH_STATUS,
                ),
            ],
            spacing=Theme.Spacing.SM,
        )

        # Queue rows
        queue_rows = [QueueHealthRow(queue, page) for queue in queue_components]

        self.content = ft.Column(
            [
                H3Text("Queue Status"),
                ft.Container(height=Theme.Spacing.SM),
                header_row,
                ft.Divider(height=1, color=ft.Colors.OUTLINE),
                ft.Column(
                    queue_rows if queue_rows else [BodyText("No queues configured")],
                    spacing=0,
                ),
            ],
            spacing=0,
        )


class StatisticsSection(ft.Container):
    """Statistics section showing worker infrastructure information."""

    def __init__(self, component_data: ComponentStatus, page: ft.Page) -> None:
        """
        Initialize statistics section.

        Args:
            component_data: Worker ComponentStatus with full health information
        """
        super().__init__()
        self.padding = Theme.Spacing.MD

        status = component_data.status
        message = component_data.message
        response_time = component_data.response_time_ms or 0
        metadata = component_data.metadata or {}

        total_queued = metadata.get("total_queued", 0)
        total_completed = metadata.get("total_completed", 0)
        total_failed = metadata.get("total_failed", 0)
        total_retried = metadata.get("total_retried", 0)
        overall_failure_rate = metadata.get("overall_failure_rate_percent", 0.0)
        redis_url = metadata.get("redis_url", "Not configured")

        # Truncate Redis URL for display
        if len(redis_url) > MAX_REDIS_URL_DISPLAY_LENGTH:
            redis_url = redis_url[: MAX_REDIS_URL_DISPLAY_LENGTH - 3] + "..."

        def stat_row(label: str, value: str) -> ft.Row:
            """Create a statistics row with label and value."""
            return ft.Row(
                [
                    SecondaryText(
                        f"{label}:",
                        weight=Theme.Typography.WEIGHT_SEMIBOLD,
                        width=STAT_LABEL_WIDTH,
                    ),
                    BodyText(value),
                ],
                spacing=Theme.Spacing.MD,
            )

        self.content = ft.Column(
            [
                H3Text("Worker Information"),
                ft.Container(height=Theme.Spacing.SM),
                stat_row("Component Status", status.value.upper()),
                stat_row("Health Message", message),
                stat_row("Response Time", f"{response_time}ms"),
                ft.Divider(height=20, color=ft.Colors.OUTLINE),
                stat_row("Total Queued", str(total_queued)),
                stat_row("Total Completed", str(total_completed)),
                stat_row("Total Failed", str(total_failed)),
                stat_row("Total Retried", str(total_retried)),
                stat_row("Overall Failure Rate", f"{overall_failure_rate:.1f}%"),
                ft.Divider(height=20, color=ft.Colors.OUTLINE),
                stat_row("Redis URL", redis_url),
            ],
            spacing=Theme.Spacing.XS,
        )


class WorkerDetailDialog(BaseDetailPopup):
    """
    Worker component detail popup dialog.

    Displays comprehensive worker information including queue health,
    job statistics, and infrastructure details.
    """

    def __init__(self, component_data: ComponentStatus, page: ft.Page) -> None:
        """
        Initialize worker detail popup.

        Args:
            component_data: Worker ComponentStatus from health check
        """
        # Build sections
        sections = [
            OverviewSection(component_data, page),
            QueueHealthSection(component_data, page),
            ft.Divider(
                height=ModalLayout.SECTION_DIVIDER_HEIGHT, color=ft.Colors.OUTLINE
            ),
            StatisticsSection(component_data, page),
        ]

        # Initialize base popup with custom sections
        super().__init__(
            page=page,
            component_data=component_data,
            title_text="Worker",
            sections=sections,
        )
