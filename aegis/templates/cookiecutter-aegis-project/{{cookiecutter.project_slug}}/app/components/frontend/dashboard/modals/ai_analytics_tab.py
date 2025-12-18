"""
AI Analytics Tab Component

Displays LLM usage statistics including token counts, costs, model breakdown,
and recent activity. Fetches real data from the /ai/usage/stats API endpoint.
"""

from typing import Any

import flet as ft
import httpx
from app.components.frontend.controls import (
    H3Text,
    LabelText,
    SecondaryText,
    Tag,
)
from app.components.frontend.theme import AegisTheme as Theme
from app.core.config import settings
from app.core.formatting import format_cost, format_number

from ..cards.card_utils import PROVIDER_COLORS, create_progress_indicator
from .modal_sections import EmptyStatePlaceholder, MetricCard


def _get_success_rate_color(rate: float) -> str:
    """Get color based on success rate percentage."""
    if rate >= 95:
        return Theme.Colors.SUCCESS
    elif rate >= 80:
        return ft.Colors.ORANGE
    else:
        return Theme.Colors.ERROR


def _transform_api_response(api_data: dict[str, Any]) -> dict[str, Any]:
    """Transform API response to UI-expected format.

    API field names differ slightly from what the UI components expect:
    - models[].model_id -> models[].name
    - models[].percentage -> models[].pct
    - recent_activity -> recent
    - recent_activity[].timestamp -> recent[].time (time portion only)
    """
    # Transform models
    models = []
    for m in api_data.get("models", []):
        models.append(
            {
                "name": m.get("model_id", "Unknown"),
                "vendor": m.get("vendor", "unknown"),
                "requests": m.get("requests", 0),
                "tokens": m.get("tokens", 0),
                "cost": m.get("cost", 0.0),
                "pct": m.get("percentage", 0),
            }
        )

    # Transform recent activity
    recent = []
    for r in api_data.get("recent_activity", []):
        # Extract time from timestamp (e.g., "2024-01-01T12:34:56" -> "12:34:56")
        timestamp = r.get("timestamp", "")
        time_part = timestamp.split("T")[-1][:8] if "T" in timestamp else timestamp

        recent.append(
            {
                "time": time_part,
                "model": r.get("model", "Unknown"),
                "tokens": r.get("tokens", 0),
                "cost": r.get("cost", 0.0),
                "success": r.get("success", True),
            }
        )

    return {
        "total_tokens": api_data.get("total_tokens", 0),
        "input_tokens": api_data.get("input_tokens", 0),
        "output_tokens": api_data.get("output_tokens", 0),
        "total_cost": api_data.get("total_cost", 0.0),
        "total_requests": api_data.get("total_requests", 0),
        "success_rate": api_data.get("success_rate", 100.0),
        "models": models,
        "recent": recent,
    }


class HeroStatsSection(ft.Container):
    """Hero stats section showing key metrics in cards."""

    def __init__(self, stats: dict[str, Any]) -> None:
        """
        Initialize hero stats section.

        Args:
            stats: Dictionary with usage statistics
        """
        super().__init__()

        total_tokens = stats.get("total_tokens", 0)
        total_cost = stats.get("total_cost", 0.0)
        success_rate = stats.get("success_rate", 0.0)
        total_requests = stats.get("total_requests", 0)

        self.content = ft.Column(
            [
                H3Text("Usage Overview"),
                ft.Container(height=Theme.Spacing.SM),
                ft.Row(
                    [
                        MetricCard(
                            "Total Tokens",
                            format_number(total_tokens),
                            ft.Colors.PURPLE,
                        ),
                        MetricCard(
                            "Total Cost",
                            format_cost(total_cost),
                            Theme.Colors.PRIMARY,
                        ),
                        MetricCard(
                            "Success Rate",
                            f"{success_rate:.1f}%",
                            _get_success_rate_color(success_rate),
                        ),
                        MetricCard(
                            "Requests",
                            format_number(total_requests),
                            ft.Colors.CYAN,
                        ),
                    ],
                    spacing=Theme.Spacing.MD,
                ),
            ],
            spacing=0,
        )
        self.padding = Theme.Spacing.MD


class TokenBreakdownSection(ft.Container):
    """Token breakdown section showing input vs output distribution."""

    def __init__(self, stats: dict[str, Any]) -> None:
        """
        Initialize token breakdown section.

        Args:
            stats: Dictionary with token statistics
        """
        super().__init__()

        input_tokens = stats.get("input_tokens", 0)
        output_tokens = stats.get("output_tokens", 0)
        total = input_tokens + output_tokens

        input_pct = (input_tokens / total * 100) if total > 0 else 0
        output_pct = (output_tokens / total * 100) if total > 0 else 0

        self.content = ft.Column(
            [
                H3Text("Token Breakdown"),
                ft.Container(height=Theme.Spacing.SM),
                create_progress_indicator(
                    label="Input Tokens",
                    value=input_pct,
                    details=f"{format_number(input_tokens)} tokens ({input_pct:.0f}%)",
                    color=ft.Colors.PURPLE,
                ),
                ft.Container(height=Theme.Spacing.SM),
                create_progress_indicator(
                    label="Output Tokens",
                    value=output_pct,
                    details=f"{format_number(output_tokens)} tokens ({output_pct:.0f}%)",
                    color=ft.Colors.PURPLE_200,
                ),
            ],
            spacing=0,
        )
        self.padding = Theme.Spacing.MD


class ModelUsageSection(ft.Container):
    """Model usage section showing breakdown by model."""

    def __init__(self, stats: dict[str, Any]) -> None:
        """
        Initialize model usage section.

        Args:
            stats: Dictionary with model usage data
        """
        super().__init__()

        models = stats.get("models", [])

        if not models:
            self.content = ft.Column(
                [
                    H3Text("Model Usage"),
                    ft.Container(height=Theme.Spacing.SM),
                    EmptyStatePlaceholder("No model usage data available"),
                ],
                spacing=0,
            )
        else:
            model_rows = []
            for model in models:
                vendor = model.get("vendor", "unknown")
                color = PROVIDER_COLORS.get(vendor, ft.Colors.GREY)
                model_rows.append(
                    create_progress_indicator(
                        label=model.get("name", "Unknown"),
                        value=float(model.get("pct", 0)),
                        details=f"{model.get('requests', 0)} req • {format_cost(model.get('cost', 0))}",
                        color=color,
                    )
                )
                model_rows.append(ft.Container(height=Theme.Spacing.XS))

            self.content = ft.Column(
                [
                    H3Text("Model Usage"),
                    ft.Container(height=Theme.Spacing.SM),
                    *model_rows,
                ],
                spacing=0,
            )
        self.padding = Theme.Spacing.MD


class RecentActivitySection(ft.Container):
    """Recent activity section showing last N requests."""

    def __init__(self, stats: dict[str, Any]) -> None:
        """
        Initialize recent activity section.

        Args:
            stats: Dictionary with recent activity data
        """
        super().__init__()

        recent = stats.get("recent", [])

        if not recent:
            self.content = ft.Column(
                [
                    H3Text("Recent Activity"),
                    ft.Container(height=Theme.Spacing.SM),
                    EmptyStatePlaceholder("No recent activity"),
                ],
                spacing=0,
            )
        else:
            # Table header
            header = ft.Row(
                [
                    ft.Container(LabelText("Time"), width=80),
                    ft.Container(LabelText("Model"), width=120),
                    ft.Container(LabelText("Tokens"), width=80),
                    ft.Container(LabelText("Cost"), width=100),
                    ft.Container(LabelText("Status"), width=60),
                ],
                spacing=Theme.Spacing.SM,
            )

            # Table rows
            rows = [header]
            for activity in recent:
                success = activity.get("success", True)
                status_text = "OK" if success else "FAIL"
                status_color = Theme.Colors.SUCCESS if success else Theme.Colors.ERROR

                row = ft.Row(
                    [
                        ft.Container(
                            SecondaryText(activity.get("time", "")),
                            width=80,
                        ),
                        ft.Container(
                            SecondaryText(activity.get("model", "")),
                            width=120,
                        ),
                        ft.Container(
                            SecondaryText(format_number(activity.get("tokens", 0))),
                            width=80,
                        ),
                        ft.Container(
                            SecondaryText(format_cost(activity.get("cost", 0))),
                            width=100,
                        ),
                        ft.Container(
                            Tag(text=status_text, color=status_color),
                            width=60,
                        ),
                    ],
                    spacing=Theme.Spacing.SM,
                )
                rows.append(row)

            self.content = ft.Column(
                [
                    H3Text("Recent Activity"),
                    ft.Container(height=Theme.Spacing.SM),
                    ft.Container(
                        content=ft.Column(rows, spacing=Theme.Spacing.XS),
                        bgcolor=ft.Colors.SURFACE,
                        border_radius=Theme.Components.CARD_RADIUS,
                        border=ft.border.all(1, ft.Colors.OUTLINE),
                        padding=Theme.Spacing.MD,
                    ),
                ],
                spacing=0,
            )
        self.padding = Theme.Spacing.MD


class AIAnalyticsTab(ft.Container):
    """
    Analytics tab content for the AI Service modal.

    Fetches and displays comprehensive LLM usage statistics from the API.
    Gracefully handles memory-only mode where analytics are unavailable.
    """

    def __init__(self, metadata: dict[str, Any] | None = None) -> None:
        """
        Initialize analytics tab.

        Args:
            metadata: Component metadata from health check, used to detect
                     if analytics are available (persistence != "memory")
        """
        super().__init__()

        self._metadata = metadata or {}

        # Content container that will be updated after data loads
        self._content_column = ft.Column(
            [
                ft.Container(
                    content=ft.ProgressRing(width=32, height=32),
                    alignment=ft.alignment.center,
                    padding=Theme.Spacing.XL,
                ),
                ft.Container(
                    content=SecondaryText("Loading usage statistics..."),
                    alignment=ft.alignment.center,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=Theme.Spacing.MD,
        )

        self.content = self._content_column

    def did_mount(self) -> None:
        """Called when the control is added to the page. Fetches data."""
        # Check if analytics are available (requires database backend)
        if self._metadata.get("persistence") == "memory":
            self._render_unavailable()
        else:
            self.page.run_task(self._load_stats)

    async def _load_stats(self) -> None:
        """Fetch usage stats from API and update the UI."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://localhost:{settings.PORT}/ai/usage/stats",
                    params={"recent_limit": 10},
                    timeout=10.0,
                )

                if response.status_code == 200:
                    api_data = response.json()
                    stats = _transform_api_response(api_data)
                    self._render_stats(stats)
                else:
                    self._render_error(f"API returned status {response.status_code}")

        except httpx.TimeoutException:
            self._render_error("Request timed out")
        except httpx.ConnectError:
            self._render_error("Could not connect to backend API")
        except Exception as e:
            self._render_error(str(e))

    def _render_stats(self, stats: dict[str, Any]) -> None:
        """Render the stats sections with loaded data."""
        # Refresh button row
        refresh_row = ft.Row(
            [
                ft.Container(expand=True),  # Spacer
                ft.IconButton(
                    icon=ft.Icons.REFRESH,
                    icon_color=Theme.Colors.PRIMARY,
                    tooltip="Refresh analytics",
                    on_click=self._on_refresh_click,
                ),
            ],
            alignment=ft.MainAxisAlignment.END,
        )

        self._content_column.controls = [
            refresh_row,
            HeroStatsSection(stats),
            ft.Divider(height=20, color=ft.Colors.OUTLINE_VARIANT),
            TokenBreakdownSection(stats),
            ft.Divider(height=20, color=ft.Colors.OUTLINE_VARIANT),
            ModelUsageSection(stats),
            ft.Divider(height=20, color=ft.Colors.OUTLINE_VARIANT),
            RecentActivitySection(stats),
        ]
        self._content_column.scroll = ft.ScrollMode.AUTO
        self._content_column.spacing = 0
        self.update()

    def _render_error(self, message: str) -> None:
        """Render an error state."""
        self._content_column.controls = [
            ft.Container(
                content=ft.Icon(
                    ft.Icons.ERROR_OUTLINE,
                    size=48,
                    color=Theme.Colors.ERROR,
                ),
                alignment=ft.alignment.center,
                padding=Theme.Spacing.MD,
            ),
            ft.Container(
                content=H3Text("Failed to load usage statistics"),
                alignment=ft.alignment.center,
            ),
            ft.Container(
                content=SecondaryText(message),
                alignment=ft.alignment.center,
            ),
        ]
        self._content_column.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        self.update()

    def _render_unavailable(self) -> None:
        """Render an unavailable state when analytics require database backend."""
        self._content_column.controls = [
            ft.Container(height=40),
            ft.Icon(
                ft.Icons.ANALYTICS_OUTLINED,
                size=64,
                color=ft.Colors.OUTLINE,
            ),
            ft.Container(height=Theme.Spacing.MD),
            H3Text("Analytics Unavailable"),
            ft.Container(height=Theme.Spacing.SM),
            SecondaryText("Database backend required for usage analytics."),
            ft.Container(height=Theme.Spacing.XS),
            SecondaryText(
                'Use: uvx aegis-stack init my-app --services "ai[sqlite]"',
                italic=True,
            ),
        ]
        self._content_column.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        self._content_column.alignment = ft.MainAxisAlignment.START
        self.update()

    async def _on_refresh_click(self, e: ft.ControlEvent) -> None:
        """Handle refresh button click - reload stats from API."""
        # Show loading state
        self._content_column.controls = [
            ft.Container(
                content=ft.ProgressRing(width=32, height=32),
                alignment=ft.alignment.center,
                padding=Theme.Spacing.XL,
            ),
            ft.Container(
                content=SecondaryText("Refreshing..."),
                alignment=ft.alignment.center,
            ),
        ]
        self._content_column.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        self._content_column.spacing = Theme.Spacing.MD
        self.update()

        # Fetch fresh data
        await self._load_stats()
