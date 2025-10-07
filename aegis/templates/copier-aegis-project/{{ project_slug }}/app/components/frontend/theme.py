"""Simple theme management for the dashboard."""

import flet as ft


class ThemeManager:
    """Manages light/dark theme switching for the Flet page."""

    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.is_dark_mode = True  # Default to dark

    async def initialize_themes(self) -> None:
        """Initialize theme system with dark mode as default."""
        self.page.theme_mode = ft.ThemeMode.DARK
        self.is_dark_mode = True
        self.page.update()

    async def toggle_theme(self) -> None:
        """Toggle between light and dark themes."""
        if self.is_dark_mode:
            self.page.theme_mode = ft.ThemeMode.LIGHT
            self.is_dark_mode = False
        else:
            self.page.theme_mode = ft.ThemeMode.DARK
            self.is_dark_mode = True

        self.page.update()

    def get_status_colors(self, is_healthy: bool) -> tuple[str, str, str]:
        """Get (background, text, border) colors for status indicators."""
        if is_healthy:
            if self.is_dark_mode:
                return (ft.Colors.GREEN_900, ft.Colors.GREEN_100, ft.Colors.GREEN)
            else:
                return (ft.Colors.GREEN_100, ft.Colors.GREEN_800, ft.Colors.GREEN)
        else:
            if self.is_dark_mode:
                return (ft.Colors.RED_900, ft.Colors.RED_100, ft.Colors.ERROR)
            else:
                return (ft.Colors.RED_100, ft.Colors.RED_800, ft.Colors.ERROR)

    def get_info_colors(self) -> tuple[str, str, str]:
        """Get (background, text, border) colors for info cards."""
        if self.is_dark_mode:
            return (ft.Colors.BLUE_900, ft.Colors.BLUE_100, ft.Colors.PRIMARY)
        else:
            return (ft.Colors.BLUE_100, ft.Colors.BLUE_800, ft.Colors.PRIMARY)
