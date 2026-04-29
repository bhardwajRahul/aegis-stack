"""
Tests for the generic option-spec parser (R3 of plugin refactor).

These tests lock in the contract of ``aegis/core/option_spec.py``
independent of any specific service. The per-service parser tests
(``test_ai_service_parser.py`` etc.) cover the service-shaped behaviour;
this file covers the generic mechanics.
"""

from dataclasses import dataclass, field

import pytest

from aegis.core.option_spec import (
    OptionMode,
    OptionSpec,
    compute_auto_requires,
    is_spec_with_options,
    parse_options,
)


@dataclass
class _FakeSpec:
    """Minimal stand-in for ``PluginSpec`` — just ``name`` + ``options``."""

    name: str
    options: list[OptionSpec] = field(default_factory=list)


# ---------------------------------------------------------------------
# is_spec_with_options
# ---------------------------------------------------------------------


class TestIsSpecWithOptions:
    def test_no_brackets(self) -> None:
        assert not is_spec_with_options("ai")

    def test_with_brackets(self) -> None:
        assert is_spec_with_options("ai[sqlite]")

    def test_empty_brackets(self) -> None:
        assert is_spec_with_options("ai[]")

    def test_strips_whitespace(self) -> None:
        assert is_spec_with_options("  ai[sqlite]  ")
        assert not is_spec_with_options("  ai  ")


# ---------------------------------------------------------------------
# parse_options — defaults
# ---------------------------------------------------------------------


class TestParseDefaults:
    def test_bare_name_returns_defaults(self) -> None:
        spec = _FakeSpec(
            name="x",
            options=[
                OptionSpec(
                    name="mode", mode=OptionMode.SINGLE, choices=["a", "b"], default="a"
                ),
                OptionSpec(
                    name="tags",
                    mode=OptionMode.MULTI,
                    choices=["t1", "t2"],
                    default=["t1"],
                ),
                OptionSpec(
                    name="loud", mode=OptionMode.FLAG, choices=["loud"], default=False
                ),
            ],
        )
        assert parse_options("x", spec) == {"mode": "a", "tags": ["t1"], "loud": False}

    def test_empty_brackets_returns_defaults(self) -> None:
        spec = _FakeSpec(
            name="x",
            options=[
                OptionSpec(
                    name="mode", mode=OptionMode.SINGLE, choices=["a"], default="a"
                ),
            ],
        )
        assert parse_options("x[]", spec) == {"mode": "a"}

    def test_no_options_declared_returns_empty_dict(self) -> None:
        assert parse_options("x", _FakeSpec(name="x")) == {}

    def test_multi_default_is_copied(self) -> None:
        """Defaults must not be aliased — mutating one parse result must not
        affect another or the spec.
        """
        default = ["a"]
        spec = _FakeSpec(
            name="x",
            options=[
                OptionSpec(
                    name="tags", mode=OptionMode.MULTI, choices=["a"], default=default
                )
            ],
        )
        r1 = parse_options("x", spec)
        r1["tags"].append("mutated")
        r2 = parse_options("x", spec)
        assert r2["tags"] == ["a"]
        assert default == ["a"]

    def test_flag_default_none_becomes_false(self) -> None:
        spec = _FakeSpec(
            name="x",
            options=[OptionSpec(name="loud", mode=OptionMode.FLAG, choices=["loud"])],
        )
        assert parse_options("x", spec) == {"loud": False}

    def test_single_default_none(self) -> None:
        spec = _FakeSpec(
            name="x",
            options=[OptionSpec(name="mode", mode=OptionMode.SINGLE, choices=["a"])],
        )
        assert parse_options("x", spec) == {"mode": None}


# ---------------------------------------------------------------------
# parse_options — values
# ---------------------------------------------------------------------


class TestParseValues:
    def _spec(self) -> _FakeSpec:
        return _FakeSpec(
            name="svc",
            options=[
                OptionSpec(
                    name="mode", mode=OptionMode.SINGLE, choices=["a", "b"], default="a"
                ),
                OptionSpec(
                    name="tags",
                    mode=OptionMode.MULTI,
                    choices=["t1", "t2", "t3"],
                    default=[],
                ),
                OptionSpec(
                    name="loud", mode=OptionMode.FLAG, choices=["loud"], default=False
                ),
            ],
        )

    def test_single_value(self) -> None:
        assert parse_options("svc[b]", self._spec())["mode"] == "b"

    def test_multi_values_preserve_order(self) -> None:
        result = parse_options("svc[t2,t1]", self._spec())
        assert result["tags"] == ["t2", "t1"]

    def test_flag_present_is_true(self) -> None:
        assert parse_options("svc[loud]", self._spec())["loud"] is True

    def test_mixed_modes_in_one_call(self) -> None:
        result = parse_options("svc[b,t1,t3,loud]", self._spec())
        assert result == {"mode": "b", "tags": ["t1", "t3"], "loud": True}

    def test_whitespace_stripped(self) -> None:
        result = parse_options("svc[ b , t1 ]", self._spec())
        assert result == {"mode": "b", "tags": ["t1"], "loud": False}

    def test_case_insensitive(self) -> None:
        # Bracket values are normalised to lowercase before matching.
        result = parse_options("svc[B,T1,LOUD]", self._spec())
        assert result == {"mode": "b", "tags": ["t1"], "loud": True}


# ---------------------------------------------------------------------
# parse_options — errors
# ---------------------------------------------------------------------


class TestParseErrors:
    def _spec(self) -> _FakeSpec:
        return _FakeSpec(
            name="svc",
            options=[
                OptionSpec(name="mode", mode=OptionMode.SINGLE, choices=["a", "b"]),
                OptionSpec(name="tags", mode=OptionMode.MULTI, choices=["t1", "t2"]),
                OptionSpec(name="loud", mode=OptionMode.FLAG, choices=["loud"]),
            ],
        )

    def test_unknown_value(self) -> None:
        with pytest.raises(ValueError, match="Unknown value 'nope'"):
            parse_options("svc[nope]", self._spec())

    def test_unknown_value_lists_each_options_choices(self) -> None:
        with pytest.raises(ValueError, match=r"Valid mode.*Valid tags.*Valid loud"):
            parse_options("svc[nope]", self._spec())

    def test_duplicate_single_select(self) -> None:
        with pytest.raises(
            ValueError, match="Cannot specify multiple values for 'mode'"
        ):
            parse_options("svc[a,b]", self._spec())

    def test_duplicate_multi_value(self) -> None:
        with pytest.raises(ValueError, match=r"Duplicate value\(s\) for 'tags'"):
            parse_options("svc[t1,t1]", self._spec())

    def test_duplicate_flag(self) -> None:
        with pytest.raises(ValueError, match="Duplicate flag 'loud'"):
            parse_options("svc[loud,loud]", self._spec())

    def test_wrong_base_name(self) -> None:
        with pytest.raises(ValueError, match="Expected 'svc'"):
            parse_options("other[a]", self._spec())

    def test_malformed_brackets(self) -> None:
        with pytest.raises(ValueError, match="Malformed brackets"):
            parse_options("svc[a", self._spec())


# ---------------------------------------------------------------------
# compute_auto_requires
# ---------------------------------------------------------------------


class TestComputeAutoRequires:
    def test_no_options_returns_empty(self) -> None:
        spec = _FakeSpec(name="x")
        assert compute_auto_requires(spec, {}) == []

    def test_option_without_auto_requires_skipped(self) -> None:
        spec = _FakeSpec(
            name="x",
            options=[OptionSpec(name="mode", mode=OptionMode.SINGLE, choices=["a"])],
        )
        assert compute_auto_requires(spec, {"mode": "a"}) == []

    def test_auto_requires_evaluated(self) -> None:
        spec = _FakeSpec(
            name="x",
            options=[
                OptionSpec(
                    name="storage",
                    mode=OptionMode.SINGLE,
                    choices=["memory", "sqlite", "postgres"],
                    default="memory",
                    auto_requires=lambda v: [f"database[{v}]"] if v != "memory" else [],
                ),
            ],
        )
        assert compute_auto_requires(spec, {"storage": "memory"}) == []
        assert compute_auto_requires(spec, {"storage": "sqlite"}) == [
            "database[sqlite]"
        ]
        assert compute_auto_requires(spec, {"storage": "postgres"}) == [
            "database[postgres]"
        ]

    def test_multiple_options_concatenate(self) -> None:
        spec = _FakeSpec(
            name="x",
            options=[
                OptionSpec(
                    name="a",
                    mode=OptionMode.SINGLE,
                    choices=["x"],
                    auto_requires=lambda v: ["one"],
                ),
                OptionSpec(
                    name="b",
                    mode=OptionMode.SINGLE,
                    choices=["y"],
                    auto_requires=lambda v: ["two", "three"],
                ),
            ],
        )
        assert compute_auto_requires(spec, {"a": "x", "b": "y"}) == [
            "one",
            "two",
            "three",
        ]
