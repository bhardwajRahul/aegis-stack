"""
Worker Detail Modal

Displays comprehensive worker component information using component composition.
Each section is a self-contained Flet control that can be reused and tested.
"""

import flet as ft
from app.components.frontend.controls import (
    BodyText,
    DataTableColumn,
    ExpandableDataTable,
    ExpandableRow,
    PrimaryText,
    SecondaryText,
)
from app.components.frontend.theme import AegisTheme as Theme
from app.components.worker.registry import get_queue_metadata
from app.services.system.models import ComponentStatus

from .base_detail_popup import BaseDetailPopup
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


def _build_queue_expanded_content(queue_name: str) -> ft.Control:
    """Build expanded content showing registered functions for a queue.

    Args:
        queue_name: Name of the queue (e.g., 'system', 'load_test')

    Returns:
        Column with queue description and registered functions
    """
    try:
        metadata = get_queue_metadata(queue_name)
        description = metadata.get("description", "")
        functions = metadata.get("functions", [])
        max_jobs = metadata.get("max_jobs", 10)
        timeout = metadata.get("timeout", 300)
    except Exception:
        description = f"Queue: {queue_name}"
        functions = []
        max_jobs = 10
        timeout = 300

    content: list[ft.Control] = []

    # Description on top with italic styling
    if description:
        content.append(
            ft.Text(
                description,
                size=Theme.Typography.BODY,
                italic=True,
                color=ft.Colors.ON_SURFACE_VARIANT,
            )
        )
        content.append(ft.Container(height=Theme.Spacing.SM))

    # Registered functions
    if functions:
        # Tasks header
        content.append(SecondaryText("Tasks:", size=Theme.Typography.BODY_SMALL))
        # Each task on its own line with bullet
        for func in functions:
            content.append(
                ft.Container(
                    content=SecondaryText(
                        f"  • {func}",
                        size=Theme.Typography.BODY_SMALL,
                    ),
                    padding=ft.padding.only(left=Theme.Spacing.SM),
                )
            )
    else:
        content.append(
            SecondaryText("No tasks registered", size=Theme.Typography.BODY_SMALL)
        )

    # Config info
    content.append(
        ft.Row(
            [
                SecondaryText(
                    f"max_jobs={max_jobs}, timeout={timeout}s",
                    size=Theme.Typography.BODY_SMALL,
                ),
            ],
            spacing=Theme.Spacing.SM,
        )
    )

    return ft.Column(content, spacing=0)


def _build_queue_health_row(queue_component: ComponentStatus) -> ExpandableRow:
    """Build row cells for a single queue health status.

    Args:
        queue_component: ComponentStatus for a single queue

    Returns:
        List of controls for each column in the row
    """
    queue_name = queue_component.name
    metadata = queue_component.metadata or {}
    worker_alive = metadata.get("worker_alive", False)
    queued_jobs = metadata.get("queued_jobs", 0)
    jobs_ongoing = metadata.get("jobs_ongoing", 0)
    jobs_completed = metadata.get("jobs_completed", 0)
    jobs_failed = metadata.get("jobs_failed", 0)
    failure_rate = metadata.get("failure_rate_percent", 0.0)
    has_job_history = (jobs_completed + jobs_failed) > 0

    # Determine status icon and color (matching card behavior)
    message = queue_component.message or ""
    if not worker_alive:
        if "no functions" in message.lower():
            status_icon = "⚪"  # No tasks defined
            status_color = ft.Colors.GREY_600
            status_text = "No Tasks"
        else:
            status_icon = "🔴"  # Offline - problem
            status_color = Theme.Colors.ERROR
            status_text = "Offline"
    elif failure_rate > FAILURE_RATE_CRITICAL_THRESHOLD:
        status_icon = "🔴"  # Failing
        status_color = Theme.Colors.ERROR
        status_text = "Failing"
    elif failure_rate > FAILURE_RATE_WARNING_THRESHOLD:
        status_icon = "🟠"  # Degraded
        status_color = Theme.Colors.WARNING
        status_text = "Degraded"
    elif jobs_ongoing > 0:
        status_icon = "🔵"  # Active - processing
        status_color = Theme.Colors.INFO
        status_text = "Active"
    else:
        status_icon = "🟢"  # Healthy
        status_color = Theme.Colors.SUCCESS
        status_text = "Online"

    # Success rate display with color coding
    # Show N/A when no jobs have been processed yet
    success_rate: float | None = (
        (100 - failure_rate) if (worker_alive and has_job_history) else None
    )
    if success_rate is None:
        rate_color = ft.Colors.ON_SURFACE_VARIANT
    elif success_rate >= SUCCESS_RATE_HEALTHY_THRESHOLD:
        rate_color = Theme.Colors.SUCCESS
    elif success_rate >= SUCCESS_RATE_WARNING_THRESHOLD:
        rate_color = Theme.Colors.WARNING
    else:
        rate_color = Theme.Colors.ERROR

    cells = [
        ft.Text(status_icon, size=16),
        PrimaryText(queue_name, size=Theme.Typography.BODY),
        BodyText(str(queued_jobs), text_align=ft.TextAlign.CENTER),
        BodyText(str(jobs_ongoing), text_align=ft.TextAlign.CENTER),
        BodyText(str(jobs_completed), text_align=ft.TextAlign.CENTER),
        BodyText(str(jobs_failed), text_align=ft.TextAlign.CENTER),
        SecondaryText(
            f"{success_rate:.1f}%" if success_rate is not None else "N/A",
            color=rate_color,
            weight=Theme.Typography.WEIGHT_SEMIBOLD,
            text_align=ft.TextAlign.CENTER,
        ),
        SecondaryText(
            status_text,
            color=status_color,
            weight=Theme.Typography.WEIGHT_SEMIBOLD,
            text_align=ft.TextAlign.CENTER,
        ),
    ]

    return ExpandableRow(
        cells=cells,
        expanded_content=_build_queue_expanded_content(queue_name),
    )


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
        total_queued = metadata.get("total_queued", 0)
        total_completed = metadata.get("total_completed", 0)
        total_failed = metadata.get("total_failed", 0)

        # Color for failed jobs - red if any failures
        failed_color = Theme.Colors.ERROR if total_failed > 0 else Theme.Colors.SUCCESS

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
                    "Processing",
                    str(total_ongoing),
                    Theme.Colors.INFO,
                ),
                MetricCard(
                    "Queued",
                    str(total_queued),
                    Theme.Colors.WARNING,
                ),
                MetricCard(
                    "Completed",
                    str(total_completed),
                    Theme.Colors.SUCCESS,
                ),
                MetricCard(
                    "Failed",
                    str(total_failed),
                    failed_color,
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

        # Define columns
        columns = [
            DataTableColumn("", width=COL_WIDTH_STATUS_ICON),  # Status icon
            DataTableColumn("Queue Name"),  # expands
            DataTableColumn("Queued", width=COL_WIDTH_QUEUED, alignment="center"),
            DataTableColumn(
                "Processing", width=COL_WIDTH_PROCESSING, alignment="center"
            ),
            DataTableColumn("Completed", width=COL_WIDTH_COMPLETED, alignment="center"),
            DataTableColumn("Failed", width=COL_WIDTH_FAILED, alignment="center"),
            DataTableColumn(
                "Success Rate", width=COL_WIDTH_SUCCESS_RATE, alignment="center"
            ),
            DataTableColumn("Status", width=COL_WIDTH_STATUS, alignment="center"),
        ]

        # Build row data
        rows = [_build_queue_health_row(queue) for queue in queue_components]

        # Build table
        table = ExpandableDataTable(
            columns=columns,
            rows=rows,
            row_padding=6,
            empty_message="No queues configured",
        )

        self.content = table


class BrokerSection(ft.Container):
    """Visual broker connection diagram showing Redis as the message broker."""

    def __init__(self, component_data: ComponentStatus, page: ft.Page) -> None:
        """
        Initialize broker section.

        Args:
            component_data: Worker ComponentStatus with Redis URL in metadata
        """
        super().__init__()

        metadata = component_data.metadata or {}
        redis_url = metadata.get("redis_url", "redis://localhost:6379")

        # Parse URL for display (just host:port)
        display_url = redis_url.replace("redis://", "")

        # Arrow pointing down from table to broker
        arrow = ft.Container(
            content=ft.Text("▼", size=24, color=ft.Colors.OUTLINE),
            alignment=ft.alignment.center,
        )

        # Redis broker box
        broker_box = ft.Container(
            content=ft.Column(
                [
                    ft.Text("Redis", size=16, weight=ft.FontWeight.W_600),
                    SecondaryText("Message Broker", size=12),
                    ft.Container(height=4),
                    BodyText(display_url, size=11),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=2,
            ),
            padding=ft.padding.all(16),
            border=ft.border.all(1, ft.Colors.OUTLINE),
            border_radius=12,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            width=160,
        )

        self.content = ft.Column(
            [arrow, broker_box],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
        )
        self.padding = Theme.Spacing.MD


class WorkerDetailDialog(BaseDetailPopup):
    """
    Worker component detail popup dialog.

    Displays comprehensive worker information including queue health,
    job statistics, and broker connection diagram.
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
            BrokerSection(component_data, page),
        ]

        # Initialize base popup with custom sections
        super().__init__(
            page=page,
            component_data=component_data,
            title_text="Worker",
            sections=sections,
        )
