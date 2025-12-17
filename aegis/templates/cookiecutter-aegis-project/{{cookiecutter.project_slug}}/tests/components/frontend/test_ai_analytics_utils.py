"""Tests for AI analytics tab utility functions."""

import flet as ft
from app.components.frontend.dashboard.modals.ai_analytics_tab import (
    _format_cost,
    _format_number,
    _get_success_rate_color,
)
from app.components.frontend.theme import AegisTheme as Theme


class TestFormatCost:
    """Tests for the _format_cost function."""

    def test_format_cost_with_small_value(self) -> None:
        """Should format small costs with 6 decimal places."""
        assert _format_cost(0.000015) == "$0.000015"

    def test_format_cost_with_zero(self) -> None:
        """Should format zero correctly."""
        assert _format_cost(0) == "$0.000000"

    def test_format_cost_with_large_value(self) -> None:
        """Should format larger costs correctly."""
        assert _format_cost(123.456789) == "$123.456789"

    def test_format_cost_with_very_small_value(self) -> None:
        """Should handle very small token costs."""
        assert _format_cost(0.000001) == "$0.000001"

    def test_format_cost_with_whole_number(self) -> None:
        """Should pad whole numbers with zeros."""
        assert _format_cost(5.0) == "$5.000000"


class TestFormatNumber:
    """Tests for the _format_number function."""

    def test_format_number_zero(self) -> None:
        """Should format zero correctly."""
        assert _format_number(0) == "0"

    def test_format_number_small(self) -> None:
        """Should not add commas to small numbers."""
        assert _format_number(999) == "999"

    def test_format_number_thousands(self) -> None:
        """Should add comma for thousands."""
        assert _format_number(1000) == "1,000"

    def test_format_number_millions(self) -> None:
        """Should add commas for millions."""
        assert _format_number(1000000) == "1,000,000"

    def test_format_number_large(self) -> None:
        """Should handle large token counts."""
        assert _format_number(1234567890) == "1,234,567,890"


class TestGetSuccessRateColor:
    """Tests for the _get_success_rate_color function."""

    def test_high_success_rate(self) -> None:
        """Should return SUCCESS color for 95%+."""
        assert _get_success_rate_color(95.0) == Theme.Colors.SUCCESS
        assert _get_success_rate_color(100.0) == Theme.Colors.SUCCESS

    def test_medium_success_rate(self) -> None:
        """Should return ORANGE for 80-94%."""
        assert _get_success_rate_color(80.0) == ft.Colors.ORANGE
        assert _get_success_rate_color(94.9) == ft.Colors.ORANGE

    def test_low_success_rate(self) -> None:
        """Should return ERROR color for <80%."""
        assert _get_success_rate_color(79.9) == Theme.Colors.ERROR
        assert _get_success_rate_color(0.0) == Theme.Colors.ERROR
