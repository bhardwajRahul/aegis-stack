"""Shared formatting utilities for display across CLI and frontend."""


def format_number(num: int) -> str:
    """Format large numbers with commas (e.g., 1234567 -> '1,234,567')."""
    return f"{num:,}"


def format_cost(cost: float) -> str:
    """Format cost with dollar sign and appropriate decimal places.

    Uses 6 decimal places for tiny amounts (< $0.01) to show token-level
    pricing accurately, 4 decimal places otherwise for readability.
    """
    if cost < 0.01:
        return f"${cost:.6f}"
    return f"${cost:.4f}"


def format_percentage(pct: float) -> str:
    """Format percentage with one decimal place (e.g., 90.5%)."""
    return f"{pct:.1f}%"
