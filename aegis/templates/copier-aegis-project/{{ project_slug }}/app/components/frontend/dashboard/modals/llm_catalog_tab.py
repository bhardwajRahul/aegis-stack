"""
LLM Catalog Tab Component

Displays LLM catalog information including model stats, featured models
from Big 3 vendors, and searchable model list.
"""

import asyncio
import re
from typing import Any

import flet as ft
import httpx
from app.components.frontend.controls import (
    DataTable,
    DataTableColumn,
    H3Text,
    SecondaryText,
)
from app.components.frontend.theme import AegisTheme as Theme
from app.core.config import settings
from app.core.formatting import format_number

from .modal_sections import EmptyStatePlaceholder, MetricCard, SectionHeader

# Featured vendors (2 per row)
# Note: These must match vendor names from OpenRouter exactly
FEATURED_VENDORS = ["openai", "anthropic", "google", "xai", "deepseek", "groq"]
MODELS_PER_VENDOR = 5

# Pattern to extract YYYYMMDD dates from model IDs
_DATE_PATTERN = re.compile(r"(\d{8})(?:\D|$)")

# Vendor display names and colors
VENDOR_DISPLAY = {
    "openai": {"name": "OpenAI", "color": "#10A37F"},
    "anthropic": {"name": "Anthropic", "color": "#D4A574"},
    "google": {"name": "Google", "color": "#4285F4"},
    "xai": {"name": "Grok", "color": "#1DA1F2"},
    "deepseek": {"name": "DeepSeek", "color": "#5B6EE1"},
    "groq": {"name": "Groq", "color": "#F55036"},
}


class CatalogStatsSection(ft.Container):
    """Stats section showing catalog overview metrics."""

    def __init__(self, stats: dict[str, Any]) -> None:
        super().__init__()

        vendor_count = stats.get("vendor_count", 0)
        model_count = stats.get("model_count", 0)
        deployment_count = stats.get("deployment_count", 0)
        price_count = stats.get("price_count", 0)

        self.content = ft.Row(
            [
                MetricCard("Vendors", str(vendor_count), Theme.Colors.PRIMARY),
                MetricCard("Models", format_number(model_count), ft.Colors.PURPLE),
                MetricCard(
                    "Deployments", format_number(deployment_count), ft.Colors.CYAN
                ),
                MetricCard("Prices", format_number(price_count), Theme.Colors.SUCCESS),
            ],
            spacing=Theme.Spacing.MD,
        )
        self.padding = Theme.Spacing.MD


def _extract_model_date(model: dict[str, Any]) -> int:
    """Extract date for sorting (newer = higher).

    Uses released_on field from API if available, otherwise
    falls back to extracting YYYYMMDD from model_id.
    """
    # First try released_on field (e.g., "2024-08-06")
    released_on = model.get("released_on")
    if released_on:
        try:
            # Convert "2024-08-06" to 20240806
            return int(released_on.replace("-", ""))
        except (ValueError, AttributeError):
            pass

    # Fallback: extract YYYYMMDD from model_id
    model_id = model.get("model_id", "")
    match = _DATE_PATTERN.search(model_id)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            pass
    return 0


def _is_alias_model(model_id: str) -> bool:
    """Check if model is an alias (ends with -latest or :latest)."""
    return model_id.endswith("-latest") or model_id.endswith(":latest")


def _format_price(price: float | None) -> str:
    """Format price per million tokens."""
    if price is None:
        return "-"
    return f"${price:.2f}"


def _format_context(ctx: int) -> str:
    """Format context window size."""
    if ctx >= 1_000_000:
        return f"{ctx // 1_000_000}M"
    elif ctx >= 1_000:
        return f"{ctx // 1_000}K"
    return str(ctx)


class FeaturedModelsSection(ft.Container):
    """Featured models from Big 3 vendors (OpenAI, Anthropic, Google)."""

    def __init__(self, featured_models: dict[str, list[dict[str, Any]]]) -> None:
        """
        Initialize featured models section.

        Args:
            featured_models: Dict mapping vendor name to list of model dicts
        """
        super().__init__()

        if not any(featured_models.values()):
            self.content = ft.Column(
                [
                    SectionHeader("Featured Models"),
                    ft.Container(height=Theme.Spacing.SM),
                    EmptyStatePlaceholder(
                        "No models found. Run 'llm sync' to populate."
                    ),
                ],
                spacing=0,
            )
        else:
            vendor_sections = []

            for vendor_key in FEATURED_VENDORS:
                models = featured_models.get(vendor_key, [])
                if not models:
                    continue

                # Filter out aliases and sort by date (newest first)
                filtered = [
                    m for m in models if not _is_alias_model(m.get("model_id", ""))
                ]
                sorted_models = sorted(
                    filtered,
                    key=_extract_model_date,
                    reverse=True,
                )[:MODELS_PER_VENDOR]

                if not sorted_models:
                    continue

                vendor_info = VENDOR_DISPLAY.get(
                    vendor_key,
                    {"name": vendor_key.title(), "color": Theme.Colors.PRIMARY},
                )

                # Vendor header with column labels
                vendor_header = ft.Container(
                    content=ft.Row(
                        [
                            ft.Container(
                                width=4,
                                height=20,
                                bgcolor=vendor_info["color"],
                                border_radius=2,
                            ),
                            ft.Text(
                                vendor_info["name"],
                                size=14,
                                weight=ft.FontWeight.W_600,
                                expand=True,
                            ),
                            ft.Container(
                                SecondaryText("Context", size=11),
                                width=50,
                                alignment=ft.alignment.center_right,
                            ),
                            ft.Container(
                                SecondaryText("In $/M", size=11),
                                width=60,
                                alignment=ft.alignment.center_right,
                            ),
                            ft.Container(
                                SecondaryText("Out $/M", size=11),
                                width=60,
                                alignment=ft.alignment.center_right,
                            ),
                        ],
                        spacing=Theme.Spacing.SM,
                    ),
                    padding=ft.padding.symmetric(
                        horizontal=Theme.Spacing.MD, vertical=8
                    ),
                    bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                    border=ft.border.only(bottom=ft.BorderSide(1, ft.Colors.OUTLINE)),
                )

                # Model rows
                model_rows = []
                for model in sorted_models:
                    model_id = model.get("model_id", "")
                    context = model.get("context_window", 0)
                    input_price = model.get("input_price")
                    output_price = model.get("output_price")

                    row = ft.Container(
                        content=ft.Row(
                            [
                                ft.Container(
                                    ft.Text(
                                        model_id,
                                        size=12,
                                        weight=ft.FontWeight.W_500,
                                        overflow=ft.TextOverflow.ELLIPSIS,
                                    ),
                                    expand=True,
                                    tooltip=model_id,
                                ),
                                ft.Container(
                                    SecondaryText(_format_context(context), size=12),
                                    width=50,
                                    alignment=ft.alignment.center_right,
                                ),
                                ft.Container(
                                    SecondaryText(_format_price(input_price), size=12),
                                    width=60,
                                    alignment=ft.alignment.center_right,
                                ),
                                ft.Container(
                                    SecondaryText(_format_price(output_price), size=12),
                                    width=60,
                                    alignment=ft.alignment.center_right,
                                ),
                            ],
                            spacing=Theme.Spacing.SM,
                        ),
                        bgcolor=ft.Colors.SURFACE,
                        padding=ft.padding.symmetric(
                            horizontal=Theme.Spacing.MD, vertical=6
                        ),
                    )
                    model_rows.append(row)

                # Combine vendor header and models
                vendor_section = ft.Container(
                    content=ft.Column([vendor_header, *model_rows], spacing=0),
                    border_radius=Theme.Components.CARD_RADIUS,
                    border=ft.border.all(1, ft.Colors.OUTLINE),
                    clip_behavior=ft.ClipBehavior.HARD_EDGE,
                    expand=True,
                )
                vendor_sections.append(vendor_section)

            # Arrange in rows of 2
            rows = []
            for i in range(0, len(vendor_sections), 2):
                row_items = vendor_sections[i : i + 2]
                rows.append(ft.Row(row_items, spacing=Theme.Spacing.MD))

            self.content = ft.Column(
                [
                    SectionHeader("Featured Models"),
                    ft.Container(height=Theme.Spacing.SM),
                    ft.Column(rows, spacing=Theme.Spacing.MD),
                ],
                spacing=0,
            )
        self.padding = Theme.Spacing.MD


class ModelSearchSection(ft.Container):
    """Model search with filters and results table."""

    def __init__(
        self, vendors: list[str], modalities: list[str], page: ft.Page
    ) -> None:
        super().__init__()

        self.page = page
        self._vendors = vendors
        self._modalities = modalities

        # Search input
        self._search_input = ft.TextField(
            hint_text="Search models by name...",
            expand=True,
            border_radius=Theme.Components.INPUT_RADIUS,
            border_color=ft.Colors.OUTLINE,
            text_size=13,
            on_submit=self._on_search,
        )

        # Vendor dropdown
        vendor_options = [ft.dropdown.Option("", "All Vendors")]
        for v in vendors:
            vendor_options.append(ft.dropdown.Option(v))
        self._vendor_dropdown = ft.Dropdown(
            label="Vendor",
            options=vendor_options,
            value="",
            width=150,
            border_radius=Theme.Components.INPUT_RADIUS,
            border_color=ft.Colors.OUTLINE,
            text_size=13,
        )

        # Modality dropdown
        modality_options = [ft.dropdown.Option("", "All Modalities")]
        for m in modalities:
            modality_options.append(ft.dropdown.Option(m))
        self._modality_dropdown = ft.Dropdown(
            label="Modality",
            options=modality_options,
            value="",
            width=150,
            border_radius=Theme.Components.INPUT_RADIUS,
            border_color=ft.Colors.OUTLINE,
            text_size=13,
        )

        # Search button
        self._search_button = ft.OutlinedButton(
            text="Search",
            icon=ft.Icons.SEARCH,
            icon_color=ft.Colors.ON_SURFACE_VARIANT,
            style=ft.ButtonStyle(
                color=ft.Colors.ON_SURFACE_VARIANT,
                side=ft.BorderSide(1, ft.Colors.ON_SURFACE_VARIANT),
                shape=ft.RoundedRectangleBorder(radius=Theme.Components.INPUT_RADIUS),
            ),
            on_click=self._on_search_click,
        )

        # Results container
        self._results_container = ft.Column([], spacing=Theme.Spacing.XS)

        # Status text
        self._status_text = ft.Container(
            content=SecondaryText("Enter a search term or select filters"),
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
                self._vendor_dropdown,
                self._modality_dropdown,
                self._search_button,
            ],
            spacing=Theme.Spacing.SM,
        )

        self.content = ft.Column(
            [
                SectionHeader("Model Search"),
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

    def _on_search(self, e: ft.ControlEvent) -> None:
        self._do_search()

    def _on_search_click(self, e: ft.ControlEvent) -> None:
        self._do_search()

    def _do_search(self) -> None:
        pattern = self._search_input.value
        vendor = self._vendor_dropdown.value
        modality = self._modality_dropdown.value

        # Require at least one filter
        if not pattern and not vendor and not modality:
            self._show_status("Please enter a search term or select a filter")
            return

        self.page.run_task(self._execute_search, pattern, vendor, modality)

    def _show_status(self, message: str) -> None:
        self._status_text.content = SecondaryText(message)
        self._status_text.visible = True
        self._results_container.controls = []
        self.update()

    async def _execute_search(
        self, pattern: str | None, vendor: str | None, modality: str | None
    ) -> None:
        self._loading.visible = True
        self._status_text.visible = False
        self._results_container.controls = []
        self.update()

        try:
            params: dict[str, Any] = {"limit": 25}
            if pattern:
                params["pattern"] = pattern
            if vendor:
                params["vendor"] = vendor
            if modality:
                params["modality"] = modality

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://localhost:{settings.PORT}/api/v1/llm/models",
                    params=params,
                    timeout=10.0,
                )

                self._loading.visible = False

                if response.status_code == 200:
                    models = response.json()
                    if not models:
                        self._show_status("No models found")
                    else:
                        self._display_results(models)
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
            self._show_status(f"Error: {e!s}")

    def _display_results(self, models: list[dict[str, Any]]) -> None:
        # Define columns
        columns = [
            DataTableColumn("Model"),  # expands
            DataTableColumn("Vendor", width=100),
            DataTableColumn("Context", width=70, alignment="right"),
            DataTableColumn("In $/M", width=70, alignment="right"),
            DataTableColumn("Out $/M", width=70, alignment="right"),
        ]

        # Build row data
        rows: list[list[ft.Control]] = []
        for model in models:
            model_id = model.get("model_id", "")
            vendor = model.get("vendor", "")
            context = model.get("context_window", 0)
            input_price = model.get("input_price")
            output_price = model.get("output_price")

            rows.append(
                [
                    ft.Text(
                        model_id,
                        size=12,
                        weight=ft.FontWeight.W_500,
                        overflow=ft.TextOverflow.ELLIPSIS,
                        tooltip=model_id,
                    ),
                    SecondaryText(vendor, size=12),
                    SecondaryText(_format_context(context), size=12),
                    SecondaryText(_format_price(input_price), size=12),
                    SecondaryText(_format_price(output_price), size=12),
                ]
            )

        # Build table with scrolling
        table = DataTable(
            columns=columns,
            rows=rows,
            row_padding=8,
            scroll_height=250,
            empty_message="No models found",
        )

        self._status_text.visible = False
        self._results_container.controls = [table]
        self.update()


class LLMCatalogTab(ft.Container):
    """
    LLM Catalog tab content for the AI Service modal.

    Fetches and displays LLM catalog information including stats,
    vendors, and searchable model list.
    """

    def __init__(self) -> None:
        super().__init__()

        self._content_column = ft.Column(
            [
                ft.Container(
                    content=ft.ProgressRing(width=32, height=32),
                    alignment=ft.alignment.center,
                    padding=Theme.Spacing.XL,
                ),
                ft.Container(
                    content=SecondaryText("Loading LLM catalog..."),
                    alignment=ft.alignment.center,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=Theme.Spacing.MD,
        )

        self.content = self._content_column

    def did_mount(self) -> None:
        """Called when the control is added to the page."""
        self.page.run_task(self._load_data)

    async def _load_data(self) -> None:
        """Fetch all data from API and update UI."""
        try:
            async with httpx.AsyncClient() as client:
                # Fetch stats, vendors, modalities, featured vendor models in parallel
                stats_task = client.get(
                    f"http://localhost:{settings.PORT}/api/v1/llm/status",
                    timeout=10.0,
                )
                vendors_task = client.get(
                    f"http://localhost:{settings.PORT}/api/v1/llm/vendors",
                    timeout=10.0,
                )
                modalities_task = client.get(
                    f"http://localhost:{settings.PORT}/api/v1/llm/modalities",
                    timeout=10.0,
                )

                # Fetch models for featured vendors
                featured_tasks = [
                    client.get(
                        f"http://localhost:{settings.PORT}/api/v1/llm/models",
                        params={"vendor": vendor, "limit": 15},
                        timeout=10.0,
                    )
                    for vendor in FEATURED_VENDORS
                ]

                results = await asyncio.gather(
                    stats_task,
                    vendors_task,
                    modalities_task,
                    *featured_tasks,
                    return_exceptions=True,
                )

                stats_resp = results[0]
                vendors_resp = results[1]
                modalities_resp = results[2]
                featured_responses = results[3:]

                # Process responses
                stats = (
                    stats_resp.json()
                    if not isinstance(stats_resp, Exception)
                    and stats_resp.status_code == 200
                    else {}
                )
                vendors = (
                    vendors_resp.json()
                    if not isinstance(vendors_resp, Exception)
                    and vendors_resp.status_code == 200
                    else []
                )
                modalities = (
                    modalities_resp.json()
                    if not isinstance(modalities_resp, Exception)
                    and modalities_resp.status_code == 200
                    else []
                )

                # Build featured models dict
                featured_models: dict[str, list[dict[str, Any]]] = {}
                for i, vendor in enumerate(FEATURED_VENDORS):
                    resp = featured_responses[i]
                    if not isinstance(resp, Exception) and resp.status_code == 200:
                        featured_models[vendor] = resp.json()
                    else:
                        featured_models[vendor] = []

                self._render_content(stats, vendors, modalities, featured_models)

        except httpx.TimeoutException:
            self._render_error("Request timed out")
        except httpx.ConnectError:
            self._render_error("Could not connect to backend API")
        except Exception as e:
            self._render_error(str(e))

    def _render_content(
        self,
        stats: dict[str, Any],
        vendors: list[dict[str, Any]],
        modalities: list[dict[str, Any]],
        featured_models: dict[str, list[dict[str, Any]]],
    ) -> None:
        """Render the content sections with loaded data."""
        # Extract vendor/modality names for dropdowns
        vendor_names = [v.get("name", "") for v in vendors]
        modality_names = [m.get("modality", "") for m in modalities]

        # Refresh button
        refresh_row = ft.Row(
            [
                ft.Container(expand=True),
                ft.IconButton(
                    icon=ft.Icons.REFRESH,
                    icon_color=ft.Colors.ON_SURFACE_VARIANT,
                    tooltip="Refresh catalog",
                    on_click=self._on_refresh_click,
                ),
            ],
            alignment=ft.MainAxisAlignment.END,
        )

        self._content_column.controls = [
            refresh_row,
            CatalogStatsSection(stats),
            ModelSearchSection(vendor_names, modality_names, self.page),
            ft.Divider(height=20, color=ft.Colors.OUTLINE),
            FeaturedModelsSection(featured_models),
        ]
        self._content_column.scroll = ft.ScrollMode.AUTO
        self._content_column.spacing = 0
        self.update()

    def _render_error(self, message: str) -> None:
        """Render an error state."""
        self._content_column.controls = [
            ft.Container(
                content=ft.Icon(
                    ft.Icons.ERROR_OUTLINE, size=48, color=Theme.Colors.ERROR
                ),
                alignment=ft.alignment.center,
                padding=Theme.Spacing.MD,
            ),
            ft.Container(
                content=H3Text("Failed to load LLM catalog"),
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
        """Handle refresh button click - reload data from API."""
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

        await self._load_data()
