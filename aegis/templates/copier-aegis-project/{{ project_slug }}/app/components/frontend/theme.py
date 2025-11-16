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


class AegisTheme:
    """
    Centralized design system for Aegis Stack dashboard.

    High-tech dark theme inspired by modern dev tools (Supabase, Vercel).
    Single source of truth for colors, typography, spacing, and component styles.
    """

    class Colors:
        """Color palette - optimized for dark mode with vibrant accents."""

        # Primary Brand (Teal/Cyan - high-tech cyberpunk feel)
        PRIMARY = ft.Colors.TEAL_400
        PRIMARY_DARK = ft.Colors.TEAL_600
        PRIMARY_LIGHT = ft.Colors.TEAL_200

        # Accent (Vibrant highlights for CTAs and emphasis)
        ACCENT = ft.Colors.CYAN_400
        ACCENT_GLOW = ft.Colors.CYAN_300

        # Status Colors (Semantic feedback)
        SUCCESS = ft.Colors.GREEN_400
        WARNING = ft.Colors.AMBER_400
        ERROR = ft.Colors.RED_400
        INFO = ft.Colors.BLUE_400

        # Surface Levels (Semantic - auto-adapt to light/dark mode)
        SURFACE_0 = ft.Colors.SURFACE  # Deepest background
        SURFACE_1 = (
            ft.Colors.SURFACE_CONTAINER_LOW
        )  # Standard card/container backgrounds
        SURFACE_2 = (
            ft.Colors.SURFACE_CONTAINER_HIGH
        )  # Elevated elements (modals, dropdowns)
        SURFACE_3 = ft.Colors.SURFACE_CONTAINER_HIGHEST  # Hover/active states

        # Text Colors (Semantic - auto-adapt to light/dark mode)
        TEXT_PRIMARY = ft.Colors.ON_SURFACE  # Main content text
        TEXT_SECONDARY = ft.Colors.ON_SURFACE_VARIANT  # Supporting text
        TEXT_TERTIARY = ft.Colors.ON_SURFACE_VARIANT  # De-emphasized text
        TEXT_DISABLED = ft.Colors.with_opacity(
            0.5, ft.Colors.ON_SURFACE_VARIANT
        )  # Disabled state (50% opacity)

        # Borders & Dividers (Semantic - auto-adapt to light/dark mode)
        BORDER_SUBTLE = ft.Colors.with_opacity(
            0.3, ft.Colors.OUTLINE_VARIANT
        )  # Minimal separation (30% opacity)
        BORDER_DEFAULT = ft.Colors.OUTLINE_VARIANT  # Standard borders
        BORDER_STRONG = ft.Colors.OUTLINE  # Emphasized borders

        # Badge & Chip Text (High contrast for colored backgrounds)
        BADGE_TEXT = (
            ft.Colors.WHITE
        )  # White text for status badges with colored backgrounds

    class Typography:
        """Typography scale and weights."""

        # Size Scale (px)
        DISPLAY = 32  # Hero/display text
        H1 = 28  # Page titles
        H2 = 24  # Major section headers
        H3 = 18  # Subsection headers
        BODY_LARGE = 16  # Emphasized body text
        BODY = 14  # Default body text
        BODY_SMALL = 12  # Supporting/secondary text
        CAPTION = 10  # Labels, captions, compact UI

        # Font Weights
        WEIGHT_REGULAR = ft.FontWeight.W_400
        WEIGHT_MEDIUM = ft.FontWeight.W_500
        WEIGHT_SEMIBOLD = ft.FontWeight.W_600
        WEIGHT_BOLD = ft.FontWeight.W_700

    class Spacing:
        """Spacing system based on 8px grid."""

        XS = 4  # Minimal spacing
        SM = 8  # Small spacing
        MD = 16  # Default spacing
        LG = 24  # Large spacing
        XL = 32  # Extra large spacing
        XXL = 48  # Maximum spacing

    class Components:
        """Component-specific styling constants."""

        # Border Radius
        CARD_RADIUS = 12  # Cards, containers
        BADGE_RADIUS = 8  # Badges, pills
        BUTTON_RADIUS = 6  # Buttons, inputs
        INPUT_RADIUS = 6  # Form inputs

        # Elevation (shadow depth)
        CARD_ELEVATION = 2  # Default card shadow
        CARD_ELEVATION_HOVER = 4  # Hover state shadow

        # Animation Durations (ms)
        TRANSITION_FAST = 150  # Quick interactions
        TRANSITION_NORMAL = 200  # Standard transitions
        TRANSITION_SLOW = 300  # Deliberate animations
