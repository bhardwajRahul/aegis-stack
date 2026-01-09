"""
LLM Catalog Tab Component

Displays LLM catalog information including model stats, vendor breakdown,
and searchable model list.
"""

import asyncio
from typing import Any

import flet as ft
import httpx
from app.components.frontend.controls import (
    BodyText,
    H3Text,
    LabelText,
    SecondaryText,
)
from app.components.frontend.theme import AegisTheme as Theme
from app.core.config import settings
from app.core.formatting import format_number

from .modal_sections import EmptyStatePlaceholder, MetricCard


class CatalogStatsSection(ft.Container):
    """Hero stats section showing catalog overview metrics."""

    def __init__(self, stats: dict[str, Any]) -> None:
        super().__init__()

        vendor_count = stats.get("vendor_count", 0)
        model_count = stats.get("model_count", 0)
        deployment_count = stats.get("deployment_count", 0)
        price_count = stats.get("price_count", 0)

        self.content = ft.Column(
            [
                H3Text("Catalog Overview"),
                ft.Container(height=Theme.Spacing.SM),
                ft.Row(
                    [
                        MetricCard("Vendors", str(vendor_count), Theme.Colors.PRIMARY),
                        MetricCard(
                            "Models", format_number(model_count), ft.Colors.PURPLE
                        ),
                        MetricCard(
                            "Deployments",
                            format_number(deployment_count),
                            ft.Colors.CYAN,
                        ),
                        MetricCard(
                            "Prices", format_number(price_count), Theme.Colors.SUCCESS
                        ),
                    ],
                    spacing=Theme.Spacing.MD,
                ),
            ],
            spacing=0,
        )
        self.padding = Theme.Spacing.MD


class VendorsSection(ft.Container):
    """Vendors table with model counts."""

    def __init__(self, vendors: list[dict[str, Any]]) -> None:
        super().__init__()

        if not vendors:
            self.content = ft.Column(
                [
                    H3Text("Vendors"),
                    ft.Container(height=Theme.Spacing.SM),
                    EmptyStatePlaceholder(
                        "No vendors found. Run 'llm sync' to populate."
                    ),
                ],
                spacing=0,
            )
        else:
            header = ft.Row(
                [
                    ft.Container(LabelText("Vendor"), expand=True),
                    ft.Container(LabelText("Models"), width=80),
                ],
                spacing=Theme.Spacing.SM,
            )

            rows: list[ft.Control] = [header]
            for vendor in vendors[:15]:  # Show top 15
                rows.append(
                    ft.Row(
                        [
                            ft.Container(
                                BodyText(vendor.get("name", "Unknown")), expand=True
                            ),
                            ft.Container(
                                SecondaryText(str(vendor.get("model_count", 0))),
                                width=80,
                            ),
                        ],
                        spacing=Theme.Spacing.SM,
                    )
                )

            self.content = ft.Column(
                [
                    H3Text("Top Vendors"),
                    ft.Container(height=Theme.Spacing.SM),
                    ft.Container(
                        content=ft.Column(
                            rows, spacing=Theme.Spacing.XS, scroll=ft.ScrollMode.AUTO
                        ),
                        bgcolor=ft.Colors.SURFACE,
                        border_radius=Theme.Components.CARD_RADIUS,
                        border=ft.border.all(1, ft.Colors.OUTLINE),
                        padding=Theme.Spacing.MD,
                        height=250,
                    ),
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
            on_submit=self._on_search,
        )

        # Vendor dropdown
        vendor_options = [ft.dropdown.Option("", "All Vendors")]
        for v in vendors:
            vendor_options.append(ft.dropdown.Option(v))
        self._vendor_dropdown = ft.Dropdown(
            options=vendor_options,
            value="",
            width=150,
            border_radius=Theme.Components.INPUT_RADIUS,
        )

        # Modality dropdown
        modality_options = [ft.dropdown.Option("", "All Modalities")]
        for m in modalities:
            modality_options.append(ft.dropdown.Option(m))
        self._modality_dropdown = ft.Dropdown(
            options=modality_options,
            value="",
            width=150,
            border_radius=Theme.Components.INPUT_RADIUS,
        )

        # Search button
        self._search_button = ft.ElevatedButton(
            text="Search",
            icon=ft.Icons.SEARCH,
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
                H3Text("Model Search"),
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
        # Table header
        header = ft.Row(
            [
                ft.Container(LabelText("Model"), width=250),
                ft.Container(LabelText("Vendor"), width=100),
                ft.Container(LabelText("Context"), width=80),
                ft.Container(LabelText("Input $/1M"), width=80),
                ft.Container(LabelText("Output $/1M"), width=80),
            ],
            spacing=Theme.Spacing.SM,
        )

        rows: list[ft.Control] = [header]
        for model in models:
            input_price = model.get("input_price")
            output_price = model.get("output_price")
            model_id = model.get("model_id", "")
            rows.append(
                ft.Row(
                    [
                        ft.Container(
                            BodyText(model_id, tooltip=model_id),
                            width=250,
                        ),
                        ft.Container(SecondaryText(model.get("vendor", "")), width=100),
                        ft.Container(
                            SecondaryText(f"{model.get('context_window', 0):,}"),
                            width=80,
                        ),
                        ft.Container(
                            SecondaryText(
                                f"${input_price:.2f}" if input_price else "-"
                            ),
                            width=80,
                        ),
                        ft.Container(
                            SecondaryText(
                                f"${output_price:.2f}" if output_price else "-"
                            ),
                            width=80,
                        ),
                    ],
                    spacing=Theme.Spacing.SM,
                )
            )

        self._status_text.visible = False
        self._results_container.controls = [
            ft.Container(
                content=ft.Column(
                    rows, spacing=Theme.Spacing.XS, scroll=ft.ScrollMode.AUTO
                ),
                bgcolor=ft.Colors.SURFACE,
                border_radius=Theme.Components.CARD_RADIUS,
                border=ft.border.all(1, ft.Colors.OUTLINE),
                padding=Theme.Spacing.MD,
                height=300,
            )
        ]
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
                # Fetch all data in parallel
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

                results = await asyncio.gather(
                    stats_task,
                    vendors_task,
                    modalities_task,
                    return_exceptions=True,
                )

                stats_resp, vendors_resp, modalities_resp = results

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

                self._render_content(stats, vendors, modalities)

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
                    icon_color=Theme.Colors.PRIMARY,
                    tooltip="Refresh catalog",
                    on_click=self._on_refresh_click,
                ),
            ],
            alignment=ft.MainAxisAlignment.END,
        )

        self._content_column.controls = [
            refresh_row,
            CatalogStatsSection(stats),
            ft.Divider(height=20, color=ft.Colors.OUTLINE_VARIANT),
            VendorsSection(vendors),
            ft.Divider(height=20, color=ft.Colors.OUTLINE_VARIANT),
            ModelSearchSection(vendor_names, modality_names, self.page),
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
