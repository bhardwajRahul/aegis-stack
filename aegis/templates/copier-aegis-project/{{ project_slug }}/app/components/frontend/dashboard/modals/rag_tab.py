"""
RAG Tab Component

Displays RAG service status and configuration, matching the output of
the `my-app rag status` CLI command.
"""

from collections.abc import Callable
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


class IndexedFileRow(ft.Container):
    """Single row showing an indexed file with chunk count."""

    def __init__(self, source: str, chunks: int) -> None:
        super().__init__()

        # Extract just the filename for display, full path on hover
        filename = source.split("/")[-1] if "/" in source else source

        self.content = ft.Row(
            [
                ft.Container(
                    ft.Icon(ft.Icons.DESCRIPTION_OUTLINED, size=14),
                    width=24,
                ),
                ft.Container(
                    BodyText(filename, tooltip=source),
                    expand=True,
                ),
                ft.Container(
                    SecondaryText(f"{chunks} chunks"),
                    width=80,
                ),
            ],
            spacing=Theme.Spacing.SM,
        )
        self.padding = ft.padding.symmetric(
            vertical=Theme.Spacing.XS,
            horizontal=Theme.Spacing.SM,
        )


class CollectionRowCard(ft.Container):
    """Expandable card for a collection showing files on click."""

    def __init__(
        self,
        collection: dict[str, Any],
        on_load_files: Callable[[str], None],
    ) -> None:
        super().__init__()

        self.collection_name = collection.get("name", "Unknown")
        self.doc_count = collection.get("count", 0)
        self.on_load_files = on_load_files

        self.is_expanded = False
        self.files_loaded = False
        self.files: list[dict[str, Any]] = []

        # Expand/collapse icon
        self._icon = ft.Icon(ft.Icons.ARROW_RIGHT, size=16)

        # Loading indicator for files
        self._loading_indicator = ft.Container(
            content=ft.Row(
                [
                    ft.ProgressRing(width=16, height=16, stroke_width=2),
                    SecondaryText("Loading files..."),
                ],
                spacing=Theme.Spacing.SM,
            ),
            visible=False,
            padding=ft.padding.only(left=Theme.Spacing.LG),
        )

        # Files container (populated when expanded)
        self._files_container = ft.Container(
            visible=False,
            padding=ft.padding.only(left=Theme.Spacing.LG, top=Theme.Spacing.SM),
        )

        # Header row (clickable)
        self.header = ft.GestureDetector(
            content=ft.Container(
                content=ft.Row(
                    [
                        self._icon,
                        ft.Container(
                            BodyText(self.collection_name),
                            expand=True,
                        ),
                        ft.Container(
                            SecondaryText(str(self.doc_count)),
                            width=100,
                        ),
                    ],
                    spacing=Theme.Spacing.SM,
                ),
                padding=ft.padding.symmetric(
                    vertical=Theme.Spacing.SM,
                    horizontal=Theme.Spacing.SM,
                ),
            ),
            on_tap=self._toggle_expand,
            mouse_cursor=ft.MouseCursor.CLICK,
        )

        self.content = ft.Column(
            [
                self.header,
                self._loading_indicator,
                self._files_container,
            ],
            spacing=0,
        )

    def _toggle_expand(self, e: ft.ControlEvent) -> None:
        """Toggle file list expansion."""
        self.is_expanded = not self.is_expanded

        # Update icon
        self._icon.name = (
            ft.Icons.ARROW_DROP_DOWN if self.is_expanded else ft.Icons.ARROW_RIGHT
        )

        if self.is_expanded and not self.files_loaded:
            # Show loading, trigger file load
            self._loading_indicator.visible = True
            self.on_load_files(self.collection_name)
        else:
            # Just toggle visibility
            self._files_container.visible = self.is_expanded

        self.update()

    def set_files(self, files: list[dict[str, Any]]) -> None:
        """Update the files list after loading."""
        self.files = files
        self.files_loaded = True
        self._loading_indicator.visible = False

        if not files:
            self._files_container.content = ft.Container(
                content=SecondaryText("No files indexed"),
                padding=Theme.Spacing.SM,
            )
        else:
            file_rows = [IndexedFileRow(f["source"], f["chunks"]) for f in files]
            self._files_container.content = ft.Column(
                file_rows,
                spacing=0,
            )

        self._files_container.visible = self.is_expanded
        self.update()

    def set_error(self, message: str) -> None:
        """Show error state for file loading."""
        self.files_loaded = True
        self._loading_indicator.visible = False
        self._files_container.content = ft.Container(
            content=SecondaryText(f"Error: {message}"),
            padding=Theme.Spacing.SM,
        )
        self._files_container.visible = self.is_expanded
        self.update()


class RAGCollectionsTableSection(ft.Container):
    """Collections table with expandable rows showing file details."""

    def __init__(
        self,
        collections: list[dict[str, Any]],
        page: ft.Page,
    ) -> None:
        """
        Initialize collections table section.

        Args:
            collections: List of collection info dicts with name and count
            page: Flet page for async operations
        """
        super().__init__()

        self.page = page
        self._collection_cards: dict[str, CollectionRowCard] = {}

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
                    ft.Container(width=24),  # Icon space
                    ft.Container(LabelText("Collection"), expand=True),
                    ft.Container(LabelText("Documents"), width=100),
                ],
                spacing=Theme.Spacing.SM,
            )

            # Create expandable row cards
            rows: list[ft.Control] = []
            for collection in collections:
                card = CollectionRowCard(
                    collection=collection,
                    on_load_files=self._load_files_for_collection,
                )
                self._collection_cards[collection.get("name", "")] = card
                rows.append(card)

            self.content = ft.Column(
                [
                    H3Text("Collections"),
                    ft.Container(height=Theme.Spacing.SM),
                    ft.Container(
                        content=ft.Column(
                            [header] + rows,
                            spacing=Theme.Spacing.XS,
                        ),
                        bgcolor=ft.Colors.SURFACE,
                        border_radius=Theme.Components.CARD_RADIUS,
                        border=ft.border.all(1, ft.Colors.OUTLINE),
                        padding=Theme.Spacing.MD,
                    ),
                ],
                spacing=0,
            )
        self.padding = Theme.Spacing.MD

    def _load_files_for_collection(self, collection_name: str) -> None:
        """Trigger async file loading for a collection."""
        self.page.run_task(self._fetch_files, collection_name)

    async def _fetch_files(self, collection_name: str) -> None:
        """Fetch files for a collection from the API."""
        card = self._collection_cards.get(collection_name)
        if not card:
            return

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://localhost:{settings.PORT}/api/v1/rag/collections/{collection_name}/files",
                    timeout=10.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    card.set_files(data.get("files", []))
                else:
                    card.set_error(f"API returned {response.status_code}")

        except httpx.TimeoutException:
            card.set_error("Request timed out")
        except httpx.ConnectError:
            card.set_error("Could not connect to API")
        except Exception as e:
            card.set_error(str(e))


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


class SearchResultCard(ft.Container):
    """Display a single search result."""

    def __init__(self, result: dict[str, Any], rank: int) -> None:
        super().__init__()

        content = result.get("content", "")
        metadata = result.get("metadata", {})
        score = result.get("score", 0.0)
        source = metadata.get("source", "Unknown")

        # Truncate content for display
        max_content_len = 200
        display_content = (
            content[:max_content_len] + "..."
            if len(content) > max_content_len
            else content
        )

        # Extract filename from source
        filename = source.split("/")[-1] if "/" in source else source

        # Score color based on relevance
        score_pct = int(score * 100)
        score_color = (
            Theme.Colors.SUCCESS
            if score_pct >= 70
            else Theme.Colors.WARNING
            if score_pct >= 40
            else Theme.Colors.ERROR
        )

        self.content = ft.Container(
            content=ft.Column(
                [
                    # Header: rank, source, score
                    ft.Row(
                        [
                            LabelText(f"#{rank}"),
                            ft.Container(
                                SecondaryText(filename, tooltip=source),
                                expand=True,
                            ),
                            Tag(text=f"{score_pct}%", color=score_color),
                        ],
                        spacing=Theme.Spacing.SM,
                    ),
                    # Content preview
                    ft.Container(
                        content=BodyText(display_content),
                        padding=ft.padding.only(top=Theme.Spacing.XS),
                    ),
                ],
                spacing=Theme.Spacing.XS,
            ),
            padding=Theme.Spacing.SM,
            bgcolor=ft.Colors.SURFACE,
            border_radius=Theme.Components.CARD_RADIUS,
            border=ft.border.all(1, ft.Colors.OUTLINE),
        )


class SearchPreviewSection(ft.Container):
    """Search preview panel for testing semantic search."""

    def __init__(self, collections: list[str], page: ft.Page) -> None:
        super().__init__()

        self.page = page
        self.collections = collections

        # Search input
        self._search_input = ft.TextField(
            hint_text="Enter search query...",
            expand=True,
            border_radius=Theme.Components.INPUT_RADIUS,
            on_submit=self._on_search_submit,
        )

        # Collection dropdown
        self._collection_dropdown = ft.Dropdown(
            options=[ft.dropdown.Option(c) for c in collections],
            value=collections[0] if collections else None,
            width=200,
            border_radius=Theme.Components.INPUT_RADIUS,
        )

        # Search button
        self._search_button = ft.ElevatedButton(
            text="Search",
            icon=ft.Icons.SEARCH,
            on_click=self._on_search_click,
        )

        # Results container
        self._results_container = ft.Column(
            [],
            spacing=Theme.Spacing.SM,
        )

        # Status text
        self._status_text = ft.Container(
            content=SecondaryText("Enter a query to search"),
            visible=True,
        )

        # Loading indicator
        self._loading = ft.Container(
            content=ft.Row(
                [
                    ft.ProgressRing(width=20, height=20, stroke_width=2),
                    SecondaryText("Searching..."),
                ],
                spacing=Theme.Spacing.SM,
            ),
            visible=False,
        )

        # Build layout
        search_row = ft.Row(
            [
                self._search_input,
                self._collection_dropdown,
                self._search_button,
            ],
            spacing=Theme.Spacing.SM,
        )

        self.content = ft.Column(
            [
                H3Text("Search Preview"),
                ft.Container(height=Theme.Spacing.SM),
                search_row,
                ft.Container(height=Theme.Spacing.SM),
                self._loading,
                self._status_text,
                self._results_container,
            ],
            spacing=0,
        )
        self.padding = Theme.Spacing.MD

    def _on_search_submit(self, e: ft.ControlEvent) -> None:
        """Handle Enter key in search field."""
        self._do_search()

    def _on_search_click(self, e: ft.ControlEvent) -> None:
        """Handle search button click."""
        self._do_search()

    def _do_search(self) -> None:
        """Trigger the search."""
        query = self._search_input.value
        collection = self._collection_dropdown.value

        if not query or not query.strip():
            self._show_status("Please enter a search query")
            return

        if not collection:
            self._show_status("Please select a collection")
            return

        self.page.run_task(self._execute_search, query.strip(), collection)

    def _show_status(self, message: str) -> None:
        """Show a status message."""
        self._status_text.content = SecondaryText(message)
        self._status_text.visible = True
        self._results_container.controls = []
        self.update()

    def _show_loading(self) -> None:
        """Show loading state."""
        self._loading.visible = True
        self._status_text.visible = False
        self._results_container.controls = []
        self.update()

    async def _execute_search(self, query: str, collection: str) -> None:
        """Execute semantic search via API."""
        self._show_loading()

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"http://localhost:{settings.PORT}/api/v1/rag/search",
                    json={
                        "query": query,
                        "collection_name": collection,
                        "top_k": 5,
                    },
                    timeout=30.0,
                )

                self._loading.visible = False

                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])

                    if not results:
                        self._show_status("No results found")
                    else:
                        self._display_results(results)
                else:
                    self._show_status(f"Search failed: {response.status_code}")

        except httpx.TimeoutException:
            self._loading.visible = False
            self._show_status("Search timed out")
        except httpx.ConnectError:
            self._loading.visible = False
            self._show_status("Could not connect to API")
        except Exception as e:
            self._loading.visible = False
            self._show_status(f"Error: {str(e)}")

    def _display_results(self, results: list[dict[str, Any]]) -> None:
        """Display search results."""
        self._status_text.visible = False
        result_cards = [
            SearchResultCard(result, result.get("rank", i + 1))
            for i, result in enumerate(results)
        ]
        self._results_container.controls = result_cards
        self.update()


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

        # Extract collection names for search dropdown
        collection_names = [c.get("name", "") for c in collections if c.get("name")]

        sections: list[ft.Control] = [
            refresh_row,
            RAGCollectionsTableSection(collections, self.page),
        ]

        # Add search preview if there are collections
        if collection_names:
            sections.extend(
                [
                    ft.Divider(height=20, color=ft.Colors.OUTLINE_VARIANT),
                    SearchPreviewSection(collection_names, self.page),
                ]
            )

        sections.extend(
            [
                ft.Divider(height=20, color=ft.Colors.OUTLINE_VARIANT),
                RAGConfigSection(data),
                ft.Divider(height=20, color=ft.Colors.OUTLINE_VARIANT),
                RAGSettingsSection(data),
            ]
        )

        self._content_column.controls = sections
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
