"""
Redis Detail Modal

Displays comprehensive Redis cache information including performance metrics,
slow query log, active client connections, and infrastructure details.
Each section is a self-contained Flet control for reusability and testing.
"""

from datetime import datetime

import flet as ft
from app.components.frontend.controls import (
    BodyText,
    H3Text,
    SecondaryText,
)
from app.components.frontend.theme import AegisTheme as Theme
from app.services.system.models import ComponentStatus

from .base_detail_popup import BaseDetailPopup
from .modal_sections import MetricCard

# Slow query thresholds
SLOWLOG_CRITICAL_MS = 1000  # 1 second - Critical (red)
SLOWLOG_WARNING_MS = 100  # 100ms - Warning (yellow)

# Client connection table column widths (pixels)
COL_WIDTH_CLIENT_ID = 100
COL_WIDTH_ADDRESS = 150
COL_WIDTH_AGE = 80
COL_WIDTH_IDLE = 80
COL_WIDTH_DB = 60
COL_WIDTH_COMMAND = 200

# Slow query table column widths (pixels)
COL_WIDTH_TIMESTAMP = 180
COL_WIDTH_DURATION = 100
COL_WIDTH_SLOWLOG_CMD = 400

# Statistics section layout
STAT_LABEL_WIDTH = 200

# URL display formatting
MAX_REDIS_URL_DISPLAY_LENGTH = 50


class OverviewSection(ft.Container):
    """Overview section showing key Redis metrics."""

    def __init__(self, redis_component: ComponentStatus, page: ft.Page) -> None:
        """
        Initialize overview section.

        Args:
            redis_component: Redis ComponentStatus with metadata
        """
        super().__init__()
        self.padding = Theme.Spacing.MD

        metadata = redis_component.metadata or {}

        total_keys = metadata.get("total_keys", 0)
        connected_clients = metadata.get("connected_clients", 0)
        hit_rate = metadata.get("hit_rate_percent", 0.0)

        # Determine hit rate color
        if hit_rate >= 90:
            hit_rate_color = Theme.Colors.SUCCESS
        elif hit_rate >= 70:
            hit_rate_color = Theme.Colors.WARNING
        else:
            hit_rate_color = Theme.Colors.ERROR

        self.content = ft.Row(
            [
                MetricCard(
                    "Total Keys",
                    str(total_keys),
                    Theme.Colors.INFO,
                ),
                MetricCard(
                    "Connected Clients",
                    str(connected_clients),
                    Theme.Colors.SUCCESS,
                ),
                MetricCard(
                    "Cache Hit Rate",
                    f"{hit_rate:.1f}%",
                    hit_rate_color,
                ),
            ],
            spacing=Theme.Spacing.MD,
        )


class PerformanceSection(ft.Container):
    """Performance metrics section showing memory, ops, and cache stats."""

    def __init__(self, redis_component: ComponentStatus, page: ft.Page) -> None:
        """
        Initialize performance section.

        Args:
            redis_component: Redis ComponentStatus with metadata
        """
        super().__init__()
        self.padding = Theme.Spacing.MD

        metadata = redis_component.metadata or {}

        # Memory metrics
        used_memory_human = metadata.get("used_memory_human", "0B")
        maxmemory_human = metadata.get("maxmemory_human", "0B")
        mem_fragmentation = metadata.get("mem_fragmentation_ratio", 1.0)

        # Performance metrics
        ops_per_sec = metadata.get("instantaneous_ops_per_sec", 0)
        keyspace_hits = metadata.get("keyspace_hits", 0)
        keyspace_misses = metadata.get("keyspace_misses", 0)
        evicted_keys = metadata.get("evicted_keys", 0)
        expired_keys = metadata.get("expired_keys", 0)

        def metric_row(label: str, value: str) -> ft.Row:
            """Create a performance metric row."""
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
                H3Text("Performance Metrics"),
                ft.Container(height=Theme.Spacing.SM),
                metric_row("Memory Usage", f"{used_memory_human} / {maxmemory_human}"),
                metric_row("Memory Fragmentation", f"{mem_fragmentation:.2f}"),
                metric_row("Operations/Sec", str(ops_per_sec)),
                ft.Divider(height=20, color=ft.Colors.OUTLINE_VARIANT),
                metric_row("Cache Hits", str(keyspace_hits)),
                metric_row("Cache Misses", str(keyspace_misses)),
                metric_row("Evicted Keys", str(evicted_keys)),
                metric_row("Expired Keys", str(expired_keys)),
            ],
            spacing=Theme.Spacing.XS,
        )


class SlowQueryRow(ft.Container):
    """Single slow query display row."""

    def __init__(self, entry: dict) -> None:
        """
        Initialize slow query row.

        Args:
            entry: Slow query entry from SLOWLOG
        """
        super().__init__()

        timestamp = entry.get("timestamp", 0)
        duration_ms = entry.get("duration_ms", 0)
        command = entry.get("command", "")

        # Format timestamp
        try:
            dt = datetime.fromtimestamp(timestamp)
            timestamp_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, OSError, OverflowError, TypeError):
            timestamp_str = str(timestamp)

        # Color code by duration
        if duration_ms >= SLOWLOG_CRITICAL_MS:
            duration_color = Theme.Colors.ERROR
        elif duration_ms >= SLOWLOG_WARNING_MS:
            duration_color = Theme.Colors.WARNING
        else:
            duration_color = Theme.Colors.SUCCESS

        self.content = ft.Row(
            [
                ft.Container(
                    content=BodyText(timestamp_str),
                    width=COL_WIDTH_TIMESTAMP,
                ),
                ft.Container(
                    content=SecondaryText(
                        f"{duration_ms:.2f}ms",
                        color=duration_color,
                        weight=Theme.Typography.WEIGHT_SEMIBOLD,
                    ),
                    width=COL_WIDTH_DURATION,
                ),
                ft.Container(
                    content=BodyText(command),
                    width=COL_WIDTH_SLOWLOG_CMD,
                ),
            ],
            spacing=Theme.Spacing.SM,
        )
        self.padding = ft.padding.symmetric(vertical=Theme.Spacing.XS)


class SlowQueriesSection(ft.Container):
    """Slow queries log section displaying recent slow commands from Redis SLOWLOG."""

    def __init__(self, redis_component: ComponentStatus, page: ft.Page) -> None:
        """
        Initialize slow queries section.

        Args:
            redis_component: Redis ComponentStatus with slowlog_entries
        """
        super().__init__()
        self.padding = Theme.Spacing.MD

        metadata = redis_component.metadata or {}
        slowlog_entries = metadata.get("slowlog_entries", [])

        # Sort by duration descending
        sorted_entries = sorted(
            slowlog_entries, key=lambda x: x.get("duration_ms", 0), reverse=True
        )

        # Column headers
        header_row = ft.Row(
            [
                ft.Container(
                    content=SecondaryText(
                        "Timestamp", weight=Theme.Typography.WEIGHT_SEMIBOLD
                    ),
                    width=COL_WIDTH_TIMESTAMP,
                ),
                ft.Container(
                    content=SecondaryText(
                        "Duration",
                        weight=Theme.Typography.WEIGHT_SEMIBOLD,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    width=COL_WIDTH_DURATION,
                ),
                ft.Container(
                    content=SecondaryText(
                        "Command", weight=Theme.Typography.WEIGHT_SEMIBOLD
                    ),
                    width=COL_WIDTH_SLOWLOG_CMD,
                ),
            ],
            spacing=Theme.Spacing.SM,
        )

        # Query rows
        query_rows = [SlowQueryRow(entry) for entry in sorted_entries]

        self.content = ft.Column(
            [
                H3Text("Slow Query Log"),
                ft.Container(height=Theme.Spacing.SM),
                header_row,
                ft.Divider(height=1, color=ft.Colors.OUTLINE_VARIANT),
                ft.Column(
                    query_rows
                    if query_rows
                    else [BodyText("No slow queries recorded")],
                    spacing=0,
                ),
            ],
            spacing=0,
        )


class ClientConnectionRow(ft.Container):
    """Single client connection display row."""

    def __init__(self, client: dict) -> None:
        """
        Initialize client connection row.

        Args:
            client: Client info from CLIENT LIST
        """
        super().__init__()

        client_id = client.get("id", "")
        addr = client.get("addr", "")
        age = client.get("age", "0")
        idle = client.get("idle", "0")
        db = client.get("db", "0")
        cmd = client.get("cmd", "")

        self.content = ft.Row(
            [
                ft.Container(
                    content=BodyText(client_id, text_align=ft.TextAlign.CENTER),
                    width=COL_WIDTH_CLIENT_ID,
                ),
                ft.Container(
                    content=BodyText(addr),
                    width=COL_WIDTH_ADDRESS,
                ),
                ft.Container(
                    content=BodyText(age, text_align=ft.TextAlign.CENTER),
                    width=COL_WIDTH_AGE,
                ),
                ft.Container(
                    content=BodyText(idle, text_align=ft.TextAlign.CENTER),
                    width=COL_WIDTH_IDLE,
                ),
                ft.Container(
                    content=BodyText(db, text_align=ft.TextAlign.CENTER),
                    width=COL_WIDTH_DB,
                ),
                ft.Container(
                    content=BodyText(cmd),
                    width=COL_WIDTH_COMMAND,
                ),
            ],
            spacing=Theme.Spacing.SM,
        )
        self.padding = ft.padding.symmetric(vertical=Theme.Spacing.XS)


class ActiveConnectionsSection(ft.Container):
    """Active client connections section."""

    def __init__(self, redis_component: ComponentStatus, page: ft.Page) -> None:
        """
        Initialize active connections section.

        Args:
            redis_component: Redis ComponentStatus with active_clients
        """
        super().__init__()
        self.padding = Theme.Spacing.MD

        metadata = redis_component.metadata or {}
        active_clients = metadata.get("active_clients", [])

        # Column headers
        header_row = ft.Row(
            [
                ft.Container(
                    content=SecondaryText(
                        "Client ID",
                        weight=Theme.Typography.WEIGHT_SEMIBOLD,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    width=COL_WIDTH_CLIENT_ID,
                ),
                ft.Container(
                    content=SecondaryText(
                        "Address", weight=Theme.Typography.WEIGHT_SEMIBOLD
                    ),
                    width=COL_WIDTH_ADDRESS,
                ),
                ft.Container(
                    content=SecondaryText(
                        "Age (s)",
                        weight=Theme.Typography.WEIGHT_SEMIBOLD,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    width=COL_WIDTH_AGE,
                ),
                ft.Container(
                    content=SecondaryText(
                        "Idle (s)",
                        weight=Theme.Typography.WEIGHT_SEMIBOLD,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    width=COL_WIDTH_IDLE,
                ),
                ft.Container(
                    content=SecondaryText(
                        "DB",
                        weight=Theme.Typography.WEIGHT_SEMIBOLD,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    width=COL_WIDTH_DB,
                ),
                ft.Container(
                    content=SecondaryText(
                        "Command", weight=Theme.Typography.WEIGHT_SEMIBOLD
                    ),
                    width=COL_WIDTH_COMMAND,
                ),
            ],
            spacing=Theme.Spacing.SM,
        )

        # Client rows
        client_rows = [ClientConnectionRow(client) for client in active_clients]

        self.content = ft.Column(
            [
                H3Text("Active Connections"),
                ft.Container(height=Theme.Spacing.SM),
                header_row,
                ft.Divider(height=1, color=ft.Colors.OUTLINE_VARIANT),
                ft.Column(
                    client_rows if client_rows else [BodyText("No active connections")],
                    spacing=0,
                ),
            ],
            spacing=0,
        )


class StatisticsSection(ft.Container):
    """Statistics section showing Redis infrastructure information."""

    def __init__(self, component_data: ComponentStatus, page: ft.Page) -> None:
        """
        Initialize statistics section.

        Args:
            component_data: Redis ComponentStatus with full health information
        """
        super().__init__()
        self.padding = Theme.Spacing.MD

        status = component_data.status
        message = component_data.message
        response_time = component_data.response_time_ms or 0
        metadata = component_data.metadata or {}

        version = metadata.get("version", "unknown")
        uptime_seconds = metadata.get("uptime_in_seconds", 0)
        total_commands = metadata.get("total_commands_processed", 0)
        total_connections = metadata.get("total_connections_received", 0)
        used_memory_peak = metadata.get("used_memory_peak_human", "unknown")
        redis_url = metadata.get("url", "Not configured")

        # Format uptime
        days = uptime_seconds // 86400
        hours = (uptime_seconds % 86400) // 3600
        minutes = (uptime_seconds % 3600) // 60
        uptime_str = f"{days}d {hours}h {minutes}m"

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
                H3Text("Redis Information"),
                ft.Container(height=Theme.Spacing.SM),
                stat_row("Component Status", status.value.upper()),
                stat_row("Health Message", message),
                stat_row("Response Time", f"{response_time}ms"),
                ft.Divider(height=20, color=ft.Colors.OUTLINE_VARIANT),
                stat_row("Redis Version", version),
                stat_row("Server Uptime", uptime_str),
                stat_row("Total Commands", str(total_commands)),
                stat_row("Total Connections", str(total_connections)),
                stat_row("Peak Memory", used_memory_peak),
                ft.Divider(height=20, color=ft.Colors.OUTLINE_VARIANT),
                stat_row("Redis URL", redis_url),
            ],
            spacing=Theme.Spacing.XS,
        )


class RedisDetailDialog(BaseDetailPopup):
    """
    Redis cache detail popup dialog.

    Displays comprehensive Redis information including performance metrics,
    slow query log, active client connections, and infrastructure details.
    """

    def __init__(self, component_data: ComponentStatus, page: ft.Page) -> None:
        """
        Initialize the redis details popup.

        Args:
            component_data: ComponentStatus containing component health and metrics
        """
        # Build sections
        sections = [
            OverviewSection(component_data, page),
            PerformanceSection(component_data, page),
            ft.Divider(height=20, color=ft.Colors.OUTLINE_VARIANT),
            SlowQueriesSection(component_data, page),
            ft.Divider(height=20, color=ft.Colors.OUTLINE_VARIANT),
            ActiveConnectionsSection(component_data, page),
            ft.Divider(height=20, color=ft.Colors.OUTLINE_VARIANT),
            StatisticsSection(component_data, page),
        ]

        # Initialize base popup with custom sections
        super().__init__(
            page=page,
            component_data=component_data,
            title_text="Redis",
            sections=sections,
        )
