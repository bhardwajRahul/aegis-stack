"""Theme management for Flet frontend."""

import flet as ft


class ThemeManager:
    """Manages theme configuration for the Flet application."""
    
    def __init__(self, page: ft.Page) -> None:
        """Initialize theme manager with page reference."""
        self.page = page
        self.is_dark_mode = False
    
    async def initialize_themes(self) -> None:
        """Initialize the theme system."""
        # Set initial light theme
        self.page.theme = self.get_theme()
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.is_dark_mode = False
    
    async def toggle_theme(self) -> None:
        """Toggle between light and dark themes."""
        if self.is_dark_mode:
            self.page.theme = self.get_theme()
            self.page.theme_mode = ft.ThemeMode.LIGHT
            self.is_dark_mode = False
        else:
            self.page.theme = self.get_dark_theme()
            self.page.theme_mode = ft.ThemeMode.DARK
            self.is_dark_mode = True
        
        self.page.update()
    
    @staticmethod
    def get_theme() -> ft.Theme:
        """Get the default light theme configuration."""
        return ft.Theme(
            color_scheme_seed=ft.Colors.BLUE,
        )
    
    @staticmethod 
    def get_dark_theme() -> ft.Theme:
        """Get the dark theme configuration."""
        return ft.Theme(
            color_scheme_seed=ft.Colors.BLUE,
        )