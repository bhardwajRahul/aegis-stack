"""
RAG Tab Component

Displays RAG service status and configuration, matching the output of
the `my-app rag status` CLI command.
"""

from typing import Any

import flet as ft
import httpx
from app.components.frontend.controls import (
    BodyText,
    H3Text,
    LabelText,
    SecondaryText,
    Tag,
)
from app.components.frontend.theme import AegisTheme as Theme
from app.core.config import settings

from .modal_sections import EmptyStatePlaceholder


def _format_timestamp(timestamp: str | None) -> str:
    """Format ISO timestamp for display."""
    if not timestamp:
        return "No activity"
    # Show date and time portion
    if "T" in timestamp:
        date_part, time_part = timestamp.split("T")
        time_part = time_part.split(".")[0]  # Remove microseconds
        return f"{date_part} {time_part}"
    return timestamp


class RAGCollectionsTableSection(ft.Container):
    """Collections table showing collection names and document counts."""

    def __init__(self, collections: list[dict[str, Any]]) -> None:
        """
        Initialize collections table section.

        Args:
            collections: List of collection info dicts with name and count
        """
        super().__init__()

        if not collections:
            self.content = ft.Column(
                [
                    H3Text("Collections"),
                    ft.Container(height=Theme.Spacing.SM),
                    EmptyStatePlaceholder("No collections indexed yet"),
                ],
                spacing=0,
            )
        else:
            # Table header
            header = ft.Row(
                [
                    ft.Container(LabelText("Collection"), expand=True),
                    ft.Container(LabelText("Documents"), width=100),
                ],
                spacing=Theme.Spacing.SM,
            )

            # Table rows
            rows: list[ft.Control] = [header]
            for collection in collections:
                row = ft.Row(
                    [
                        ft.Container(
                            BodyText(collection.get("name", "Unknown")),
                            expand=True,
                        ),
                        ft.Container(
                            BodyText(str(collection.get("count", 0))),
                            width=100,
                        ),
                    ],
                    spacing=Theme.Spacing.SM,
                )
                rows.append(row)

            self.content = ft.Column(
                [
                    H3Text("Collections"),
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


class RAGConfigSection(ft.Container):
    """Configuration section showing RAG service settings."""

    def __init__(self, data: dict[str, Any]) -> None:
        """
        Initialize configuration section.

        Args:
            data: RAG health data from API
        """
        super().__init__()

        enabled = data.get("enabled", False)
        status = data.get("status", "unknown")
        embedding_provider = data.get("embedding_provider", "Unknown")
        embedding_model = data.get("embedding_model", "Unknown")

        # Status color
        status_color = (
            Theme.Colors.SUCCESS if status == "healthy" else Theme.Colors.ERROR
        )

        def config_row(label: str, value: str | ft.Control) -> ft.Row:
            """Create a configuration row with label and value."""
            value_control = value if isinstance(value, ft.Control) else BodyText(value)
            return ft.Row(
                [
                    SecondaryText(
                        f"{label}:",
                        weight=Theme.Typography.WEIGHT_SEMIBOLD,
                        width=150,
                    ),
                    value_control,
                ],
                spacing=Theme.Spacing.MD,
            )

        self.content = ft.Column(
            [
                H3Text("Configuration"),
                ft.Container(height=Theme.Spacing.SM),
                config_row("Status", Tag(text=status.upper(), color=status_color)),
                config_row("Enabled", "Yes" if enabled else "No"),
                config_row("Provider", embedding_provider),
                config_row("Model", embedding_model),
            ],
            spacing=Theme.Spacing.SM,
        )
        self.padding = Theme.Spacing.MD


class RAGSettingsSection(ft.Container):
    """Settings section showing RAG chunking and search parameters."""

    def __init__(self, data: dict[str, Any]) -> None:
        """
        Initialize settings section.

        Args:
            data: RAG health data from API
        """
        super().__init__()

        chunk_size = data.get("chunk_size", "Unknown")
        chunk_overlap = data.get("chunk_overlap", "Unknown")
        default_top_k = data.get("default_top_k", "Unknown")
        persist_directory = data.get("persist_directory", "Unknown")
        last_activity = data.get("last_activity")

        def setting_row(label: str, value: str) -> ft.Row:
            """Create a setting row with label and value."""
            return ft.Row(
                [
                    SecondaryText(
                        f"{label}:",
                        weight=Theme.Typography.WEIGHT_SEMIBOLD,
                        width=150,
                    ),
                    BodyText(str(value)),
                ],
                spacing=Theme.Spacing.MD,
            )

        rows = [
            H3Text("Settings"),
            ft.Container(height=Theme.Spacing.SM),
            setting_row("Chunk Size", str(chunk_size)),
            setting_row("Chunk Overlap", str(chunk_overlap)),
            setting_row("Default Top K", str(default_top_k)),
            setting_row("Persist Directory", str(persist_directory)),
        ]

        # Only show last activity if there is activity
        if last_activity:
            rows.append(setting_row("Last Activity", _format_timestamp(last_activity)))

        self.content = ft.Column(rows, spacing=Theme.Spacing.SM)
        self.padding = Theme.Spacing.MD


class RAGTab(ft.Container):
    """
    RAG tab content for the AI Service modal.

    Fetches and displays RAG service status matching the CLI `rag status` command.
    """

    def __init__(self) -> None:
        """Initialize RAG tab."""
        super().__init__()

        # Content container that will be updated after data loads
        self._content_column = ft.Column(
            [
                ft.Container(
                    content=ft.ProgressRing(width=32, height=32),
                    alignment=ft.alignment.center,
                    padding=Theme.Spacing.XL,
                ),
                ft.Container(
                    content=SecondaryText("Loading RAG status..."),
                    alignment=ft.alignment.center,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=Theme.Spacing.MD,
        )

        self.content = self._content_column

    def did_mount(self) -> None:
        """Called when the control is added to the page. Fetches data."""
        self.page.run_task(self._load_status)

    async def _load_status(self) -> None:
        """Fetch RAG status from API and update the UI."""
        try:
            async with httpx.AsyncClient() as client:
                # Fetch health status
                health_response = await client.get(
                    f"http://localhost:{settings.PORT}/api/v1/rag/health",
                    timeout=10.0,
                )

                if health_response.status_code != 200:
                    self._render_error(
                        f"API returned status {health_response.status_code}"
                    )
                    return

                health_data = health_response.json()

                # Fetch collection names
                collections_response = await client.get(
                    f"http://localhost:{settings.PORT}/api/v1/rag/collections",
                    timeout=10.0,
                )

                collections: list[dict[str, Any]] = []
                if collections_response.status_code == 200:
                    collection_names = collections_response.json()

                    # Fetch details for each collection
                    for name in collection_names:
                        try:
                            detail_response = await client.get(
                                f"http://localhost:{settings.PORT}/api/v1/rag/collections/{name}",
                                timeout=5.0,
                            )
                            if detail_response.status_code == 200:
                                detail = detail_response.json()
                                collections.append(
                                    {
                                        "name": detail.get("name", name),
                                        "count": detail.get("count", 0),
                                    }
                                )
                            else:
                                collections.append({"name": name, "count": "?"})
                        except Exception:
                            collections.append({"name": name, "count": "?"})

                self._render_status(health_data, collections)

        except httpx.TimeoutException:
            self._render_error("Request timed out")
        except httpx.ConnectError:
            self._render_error("Could not connect to backend API")
        except Exception as e:
            self._render_error(str(e))

    def _render_status(
        self, data: dict[str, Any], collections: list[dict[str, Any]]
    ) -> None:
        """Render the status sections with loaded data."""
        # Refresh button row
        refresh_row = ft.Row(
            [
                ft.Container(expand=True),  # Spacer
                ft.IconButton(
                    icon=ft.Icons.REFRESH,
                    icon_color=Theme.Colors.PRIMARY,
                    tooltip="Refresh RAG status",
                    on_click=self._on_refresh_click,
                ),
            ],
            alignment=ft.MainAxisAlignment.END,
        )

        self._content_column.controls = [
            refresh_row,
            RAGCollectionsTableSection(collections),
            ft.Divider(height=20, color=ft.Colors.OUTLINE_VARIANT),
            RAGConfigSection(data),
            ft.Divider(height=20, color=ft.Colors.OUTLINE_VARIANT),
            RAGSettingsSection(data),
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
                content=H3Text("Failed to load RAG status"),
                alignment=ft.alignment.center,
            ),
            ft.Container(
                content=SecondaryText(message),
                alignment=ft.alignment.center,
            ),
        ]
        self._content_column.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        self.update()

    async def _on_refresh_click(self, e: ft.ControlEvent) -> None:
        """Handle refresh button click - reload status from API."""
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
        await self._load_status()
