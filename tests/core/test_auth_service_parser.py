"""
Tests for auth service bracket syntax parser.

Tests the parsing of auth[level] syntax where:
- Levels: basic, rbac

Default (plain "auth" without brackets): basic
"""

import pytest

from aegis.core.auth_service_parser import (
    AuthServiceConfig,
    is_auth_service_with_options,
    parse_auth_service_config,
)


class TestAuthServiceParserDefaults:
    """Test default values when no options specified."""

    def test_bare_auth_returns_basic_default(self) -> None:
        """auth → basic"""
        result = parse_auth_service_config("auth")
        assert result.level == "basic"

    def test_empty_brackets_returns_basic_default(self) -> None:
        """auth[] → basic"""
        result = parse_auth_service_config("auth[]")
        assert result.level == "basic"


class TestAuthServiceParserLevels:
    """Test with different auth levels specified."""

    def test_basic_level_explicit(self) -> None:
        """auth[basic] → basic"""
        result = parse_auth_service_config("auth[basic]")
        assert result.level == "basic"

    def test_rbac_level_explicit(self) -> None:
        """auth[rbac] → rbac"""
        result = parse_auth_service_config("auth[rbac]")
        assert result.level == "rbac"

    def test_level_case_insensitive_rbac_uppercase(self) -> None:
        """auth[RBAC] → rbac (case insensitive)"""
        result = parse_auth_service_config("auth[RBAC]")
        assert result.level == "rbac"

    def test_level_case_insensitive_rbac_mixed(self) -> None:
        """auth[RbAc] → rbac (case insensitive)"""
        result = parse_auth_service_config("auth[RbAc]")
        assert result.level == "rbac"

    def test_level_case_insensitive_basic_uppercase(self) -> None:
        """auth[BASIC] → basic (case insensitive)"""
        result = parse_auth_service_config("auth[BASIC]")
        assert result.level == "basic"

    def test_org_level(self) -> None:
        """auth[org] → org"""
        result = parse_auth_service_config("auth[org]")
        assert result.level == "org"

    def test_org_level_case_insensitive(self) -> None:
        """auth[ORG] → org (case insensitive)"""
        result = parse_auth_service_config("auth[ORG]")
        assert result.level == "org"


class TestAuthServiceParserWhitespace:
    """Test whitespace handling."""

    def test_leading_trailing_whitespace_bare(self) -> None:
        """Whitespace around whole string handled (bare auth)"""
        result = parse_auth_service_config("  auth  ")
        assert result.level == "basic"

    def test_leading_trailing_whitespace_with_brackets(self) -> None:
        """Whitespace around whole string handled (with brackets)"""
        result = parse_auth_service_config("  auth[rbac]  ")
        assert result.level == "rbac"

    def test_spaces_inside_brackets(self) -> None:
        """auth[  rbac  ] parses correctly with internal spaces"""
        result = parse_auth_service_config("auth[  rbac  ]")
        assert result.level == "rbac"

    def test_tabs_inside_brackets(self) -> None:
        """auth[\trbac\t] parses correctly with tabs"""
        result = parse_auth_service_config("auth[\trbac\t]")
        assert result.level == "rbac"


class TestAuthServiceParserErrors:
    """Test error cases."""

    def test_unknown_level_raises_error(self) -> None:
        """Unknown level should raise ValueError with helpful message."""
        with pytest.raises(ValueError) as exc_info:
            parse_auth_service_config("auth[invalid]")
        error_msg = str(exc_info.value)
        assert "Unknown auth level" in error_msg or "invalid" in error_msg

    def test_unknown_level_suggests_valid_options(self) -> None:
        """Error message should suggest valid auth levels."""
        with pytest.raises(ValueError) as exc_info:
            parse_auth_service_config("auth[unknown]")
        error_msg = str(exc_info.value).lower()
        assert "basic" in error_msg or "rbac" in error_msg

    def test_invalid_service_name_raises_error(self) -> None:
        """Non-auth service should raise error."""
        with pytest.raises(ValueError) as exc_info:
            parse_auth_service_config("comms[rbac]")
        error_msg = str(exc_info.value).lower()
        assert "auth" in error_msg

    def test_malformed_brackets_missing_closing(self) -> None:
        """Malformed brackets should raise error."""
        with pytest.raises(ValueError):
            parse_auth_service_config("auth[rbac")

    def test_malformed_brackets_missing_opening(self) -> None:
        """Malformed brackets should raise error."""
        with pytest.raises(ValueError):
            parse_auth_service_config("authrbac]")

    def test_multiple_values_raises_error(self) -> None:
        """Multiple values in brackets should raise error."""
        with pytest.raises(ValueError):
            parse_auth_service_config("auth[basic, rbac]")


class TestAuthServiceConfigDataclass:
    """Test the AuthServiceConfig dataclass."""

    def test_config_attributes(self) -> None:
        """AuthServiceConfig has expected attributes."""
        config = AuthServiceConfig(level="rbac")
        assert config.level == "rbac"

    def test_config_equality_same_values(self) -> None:
        """AuthServiceConfig instances with same values are equal."""
        config1 = AuthServiceConfig(level="basic")
        config2 = AuthServiceConfig(level="basic")
        assert config1 == config2

    def test_config_equality_different_values(self) -> None:
        """AuthServiceConfig instances with different values are not equal."""
        config1 = AuthServiceConfig(level="basic")
        config2 = AuthServiceConfig(level="rbac")
        assert config1 != config2


class TestAuthServiceParserOAuth:
    """Test the ``oauth`` modifier — bracket toggle for social login.

    OAuth is a modifier (a flag, not a slot), so it composes freely
    with the level + engine slots. Order doesn't matter and it can
    appear with or without the other tokens.
    """

    def test_bare_auth_defaults_oauth_false(self) -> None:
        """auth -> oauth=False (default)"""
        result = parse_auth_service_config("auth")
        assert result.oauth is False

    def test_basic_level_alone_defaults_oauth_false(self) -> None:
        """auth[basic] -> oauth=False (default, no modifier)"""
        result = parse_auth_service_config("auth[basic]")
        assert result.oauth is False

    def test_oauth_only(self) -> None:
        """auth[oauth] -> level=basic (default), oauth=True"""
        result = parse_auth_service_config("auth[oauth]")
        assert result.level == "basic"
        assert result.oauth is True

    def test_oauth_with_rbac(self) -> None:
        """auth[rbac,oauth] -> level=rbac, oauth=True"""
        result = parse_auth_service_config("auth[rbac,oauth]")
        assert result.level == "rbac"
        assert result.oauth is True

    def test_oauth_with_org(self) -> None:
        """auth[org,oauth] -> level=org, oauth=True"""
        result = parse_auth_service_config("auth[org,oauth]")
        assert result.level == "org"
        assert result.oauth is True

    def test_oauth_with_basic_explicit(self) -> None:
        """auth[basic,oauth] -> level=basic, oauth=True"""
        result = parse_auth_service_config("auth[basic,oauth]")
        assert result.level == "basic"
        assert result.oauth is True

    def test_oauth_with_engine(self) -> None:
        """auth[oauth,sqlite] -> level=basic, engine=sqlite, oauth=True"""
        result = parse_auth_service_config("auth[oauth,sqlite]")
        assert result.level == "basic"
        assert result.engine == "sqlite"
        assert result.oauth is True

    def test_oauth_with_level_and_engine(self) -> None:
        """auth[rbac,oauth,postgres] -> level=rbac, engine=postgres, oauth=True"""
        result = parse_auth_service_config("auth[rbac,oauth,postgres]")
        assert result.level == "rbac"
        assert result.engine == "postgres"
        assert result.oauth is True

    def test_oauth_order_independent_first(self) -> None:
        """auth[oauth,rbac] equivalent to auth[rbac,oauth]"""
        result = parse_auth_service_config("auth[oauth,rbac]")
        assert result.level == "rbac"
        assert result.oauth is True

    def test_oauth_order_independent_middle(self) -> None:
        """auth[rbac,oauth,sqlite] equivalent to auth[rbac,sqlite,oauth]"""
        a = parse_auth_service_config("auth[rbac,oauth,sqlite]")
        b = parse_auth_service_config("auth[rbac,sqlite,oauth]")
        c = parse_auth_service_config("auth[oauth,rbac,sqlite]")
        assert a == b == c

    def test_oauth_case_insensitive_uppercase(self) -> None:
        """auth[OAUTH] -> oauth=True (case insensitive)"""
        result = parse_auth_service_config("auth[OAUTH]")
        assert result.oauth is True

    def test_oauth_case_insensitive_mixed(self) -> None:
        """auth[OAuth] -> oauth=True (case insensitive)"""
        result = parse_auth_service_config("auth[OAuth]")
        assert result.oauth is True

    def test_oauth_with_whitespace(self) -> None:
        """auth[ rbac , oauth ] parses correctly with spaces around tokens."""
        result = parse_auth_service_config("auth[ rbac , oauth ]")
        assert result.level == "rbac"
        assert result.oauth is True

    def test_duplicate_oauth_raises(self) -> None:
        """auth[oauth,oauth] should raise — repeating a modifier is a typo."""
        with pytest.raises(ValueError) as exc_info:
            parse_auth_service_config("auth[oauth,oauth]")
        assert "oauth" in str(exc_info.value).lower()
        assert "duplicate" in str(exc_info.value).lower()

    def test_unknown_modifier_error_lists_oauth(self) -> None:
        """Unknown token error should mention oauth as a valid modifier."""
        with pytest.raises(ValueError) as exc_info:
            parse_auth_service_config("auth[bogus]")
        assert "oauth" in str(exc_info.value).lower()


class TestIsAuthServiceWithOptions:
    """Test the is_auth_service_with_options helper function.

    This function determines if bracket syntax is used, which affects
    whether interactive selection or CLI parsing should be used.
    """

    def test_plain_auth_returns_false(self) -> None:
        """Plain 'auth' without brackets should return False.

        When user specifies just 'auth', the system may prompt interactively
        for level selection (or use default).
        """
        assert is_auth_service_with_options("auth") is False

    def test_auth_with_empty_brackets_returns_true(self) -> None:
        """auth[] should return True (explicit but empty options)."""
        assert is_auth_service_with_options("auth[]") is True

    def test_auth_with_basic_returns_true(self) -> None:
        """auth[basic] should return True."""
        assert is_auth_service_with_options("auth[basic]") is True

    def test_auth_with_rbac_returns_true(self) -> None:
        """auth[rbac] should return True."""
        assert is_auth_service_with_options("auth[rbac]") is True

    def test_auth_with_spaces_returns_false(self) -> None:
        """'auth' with surrounding spaces should return False."""
        assert is_auth_service_with_options("  auth  ") is False

    def test_auth_bracket_with_spaces_returns_true(self) -> None:
        """'auth[rbac]' with surrounding spaces should return True."""
        assert is_auth_service_with_options("  auth[rbac]  ") is True

    def test_non_auth_service_returns_false(self) -> None:
        """Non-auth services should return False."""
        assert is_auth_service_with_options("ai") is False
        assert is_auth_service_with_options("comms") is False

    def test_partial_auth_name_returns_false(self) -> None:
        """Partial matches like 'auth_test' should return False."""
        assert is_auth_service_with_options("auth_test") is False
        assert is_auth_service_with_options("my_auth") is False
