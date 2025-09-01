"""
Custom text controls with proper theme-aware styling.

These components automatically use semantic Flet colors that adapt to light/dark themes,
following the same patterns as ee-toolset for consistent visual design.
"""

import flet as ft


class PrimaryText(ft.Text):
    """
    Primary text component using theme-aware ON_SURFACE color.

    Automatically adapts to light/dark themes with proper contrast.
    Use for main content text, labels, and primary information.
    """

    def __init__(self, value: str, opacity: float = 1.0, **kwargs) -> None:
        super().__init__(
            value=value,
            opacity=opacity,
            no_wrap=False,
            color=ft.Colors.ON_SURFACE,  # Theme-aware primary text color
            font_family="Roboto",
            size=16,
            weight=ft.FontWeight.W_400,
            **kwargs,
        )


class SecondaryText(ft.Text):
    """
    Secondary text component using theme-aware ON_SURFACE_VARIANT color.

    Automatically adapts to light/dark themes with reduced contrast.
    Use for supporting text, captions, and less prominent information.
    """

    def __init__(
        self, value: str, opacity: float = 1.0, no_wrap: bool = False, **kwargs
    ) -> None:
        super().__init__(
            value=value,
            opacity=opacity,
            no_wrap=no_wrap,
            color=ft.Colors.GREY_600,  # Theme-aware secondary text color
            font_family="Roboto",
            size=14,
            weight=ft.FontWeight.W_400,
            **kwargs,
        )


class TitleText(ft.Text):
    """
    Title text component for headings and prominent labels.

    Uses theme-aware colors with larger size and bold weight.
    """

    def __init__(self, value: str, opacity: float = 1.0, **kwargs) -> None:
        # Set defaults, but allow kwargs to override
        defaults = {
            "color": ft.Colors.ON_SURFACE,  # Theme-aware primary text color
            "font_family": "Roboto",
            "size": 24,
            "weight": ft.FontWeight.W_700,
        }
        # Update defaults with any provided kwargs
        defaults.update(kwargs)

        super().__init__(
            value=value,
            opacity=opacity,
            **defaults,
        )


class ConfirmationText(ft.Text):
    """
    Confirmation/error text component with error coloring.

    Uses theme-aware error colors for warnings, confirmations, and alerts.
    """

    def __init__(self, value: str, opacity: float = 1.0, **kwargs) -> None:
        super().__init__(
            value=value,
            opacity=opacity,
            color=ft.Colors.ERROR,  # Theme-aware error color
            font_family="Roboto",
            size=14,
            weight=ft.FontWeight.W_400,
            **kwargs,
        )


class MetricText(ft.Text):
    """
    Specialized text for displaying metrics and numerical values.

    Uses bold weight and primary color for emphasis on data points.
    """

    def __init__(self, value: str, opacity: float = 1.0, **kwargs) -> None:
        super().__init__(
            value=value,
            opacity=opacity,
            color=ft.Colors.ON_SURFACE,  # Theme-aware primary text color
            font_family="Roboto",
            size=16,
            weight=ft.FontWeight.W_700,  # Bold for emphasis
            **kwargs,
        )


class LabelText(ft.Text):
    """
    Label text component for form labels and small descriptive text.

    Uses smaller size with medium weight for clear labeling.
    """

    def __init__(self, value: str, opacity: float = 1.0, **kwargs) -> None:
        # Set defaults, but allow kwargs to override
        defaults = {
            "color": ft.Colors.GREY_600,  # Theme-aware secondary color
            "font_family": "Roboto",
            "size": 12,
            "weight": ft.FontWeight.W_600,  # Medium weight for labels
        }
        # Update defaults with any provided kwargs
        defaults.update(kwargs)

        super().__init__(
            value=value,
            opacity=opacity,
            **defaults,
        )
