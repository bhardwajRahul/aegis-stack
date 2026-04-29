"""
Tests for insights service bracket syntax parser.

Tests parsing of insights[sources...] syntax for data source selection.
"""

import pytest

from aegis.core.insights_service_parser import (
    DEFAULT_SOURCES,
    InsightsServiceConfig,
    is_insights_service_with_options,
    parse_insights_service_config,
)


class TestParseInsightsServiceConfig:
    """Test insights service bracket parsing."""

    def test_plain_insights_returns_defaults(self) -> None:
        """Plain 'insights' returns default sources (github, pypi)."""
        config = parse_insights_service_config("insights")
        assert config.sources == ["github", "pypi"]

    def test_empty_brackets_returns_defaults(self) -> None:
        """Empty brackets return default sources."""
        config = parse_insights_service_config("insights[]")
        assert config.sources == DEFAULT_SOURCES

    def test_single_source(self) -> None:
        """Single source in brackets."""
        config = parse_insights_service_config("insights[github]")
        assert config.sources == ["github"]

    def test_two_sources(self) -> None:
        """Two sources in brackets."""
        config = parse_insights_service_config("insights[github,pypi]")
        assert config.sources == ["github", "pypi"]

    def test_all_sources(self) -> None:
        """All four sources in brackets."""
        config = parse_insights_service_config("insights[github,pypi,plausible,reddit]")
        assert config.sources == ["github", "pypi", "plausible", "reddit"]

    def test_sources_with_spaces(self) -> None:
        """Spaces around values are stripped."""
        config = parse_insights_service_config("insights[ github , plausible ]")
        assert config.sources == ["github", "plausible"]

    def test_case_insensitive(self) -> None:
        """Source names are lowercased."""
        config = parse_insights_service_config("insights[GitHub,PyPI]")
        assert config.sources == ["github", "pypi"]

    def test_single_plausible(self) -> None:
        """Just plausible source."""
        config = parse_insights_service_config("insights[plausible]")
        assert config.sources == ["plausible"]

    def test_single_reddit(self) -> None:
        """Just reddit source."""
        config = parse_insights_service_config("insights[reddit]")
        assert config.sources == ["reddit"]

    def test_unknown_source_raises(self) -> None:
        """Unknown source name raises ValueError.

        Wording shifted from "Unknown source" to the generic
        "Unknown value" / "Valid sources" form when the parsing layer
        was unified under aegis/core/option_spec.py (R3); the source
        name still appears in the message for grep-ability.
        """
        with pytest.raises(ValueError, match="Unknown value 'stripe'.*Valid sources"):
            parse_insights_service_config("insights[github,stripe]")

    def test_duplicate_source_raises(self) -> None:
        """Duplicate source raises ValueError.

        Wording shifted to the generic "Duplicate value(s) for 'sources'"
        form under R3.
        """
        with pytest.raises(
            ValueError, match=r"Duplicate value\(s\) for 'sources'.*github"
        ):
            parse_insights_service_config("insights[github,github]")

    def test_wrong_service_name_raises(self) -> None:
        """Non-insights service string raises ValueError.

        Generic parser wording is "Expected 'insights' or 'insights[options]'
        format" rather than "Expected 'insights' service" — same intent.
        """
        with pytest.raises(ValueError, match="Expected 'insights'"):
            parse_insights_service_config("auth[basic]")

    def test_malformed_brackets_raises(self) -> None:
        """Missing closing bracket raises ValueError."""
        with pytest.raises(ValueError, match="Malformed brackets"):
            parse_insights_service_config("insights[github")

    def test_no_brackets_with_suffix_raises(self) -> None:
        """Invalid format without brackets raises ValueError."""
        with pytest.raises(ValueError, match="Expected 'insights'"):
            parse_insights_service_config("insights_extra")

    def test_whitespace_stripped(self) -> None:
        """Leading/trailing whitespace is stripped."""
        config = parse_insights_service_config("  insights[github]  ")
        assert config.sources == ["github"]

    def test_defaults_are_independent(self) -> None:
        """Default sources are a fresh copy each time."""
        config1 = parse_insights_service_config("insights")
        config2 = parse_insights_service_config("insights")
        config1.sources.append("plausible")
        assert config2.sources == ["github", "pypi"]


class TestIsInsightsServiceWithOptions:
    """Test bracket detection."""

    def test_plain_insights_returns_false(self) -> None:
        """Plain 'insights' has no options."""
        assert is_insights_service_with_options("insights") is False

    def test_bracket_syntax_returns_true(self) -> None:
        """Bracket syntax is detected."""
        assert is_insights_service_with_options("insights[github]") is True

    def test_all_sources_returns_true(self) -> None:
        """Full bracket syntax is detected."""
        assert (
            is_insights_service_with_options("insights[github,pypi,plausible,reddit]")
            is True
        )

    def test_empty_brackets_returns_true(self) -> None:
        """Empty brackets are still bracket syntax."""
        assert is_insights_service_with_options("insights[]") is True

    def test_whitespace_stripped(self) -> None:
        """Whitespace is handled."""
        assert is_insights_service_with_options("  insights[github]  ") is True

    def test_non_insights_returns_false(self) -> None:
        """Other services return False."""
        assert is_insights_service_with_options("auth[basic]") is False


class TestInsightsServiceConfig:
    """Test InsightsServiceConfig dataclass."""

    def test_default_factory(self) -> None:
        """Default config has default sources."""
        config = InsightsServiceConfig()
        assert config.sources == DEFAULT_SOURCES

    def test_custom_sources(self) -> None:
        """Custom sources are preserved."""
        config = InsightsServiceConfig(sources=["plausible", "reddit"])
        assert config.sources == ["plausible", "reddit"]
