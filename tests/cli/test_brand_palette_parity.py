"""Brand-palette parity across the tool and the generated app (issue #865).

The brand accents (teal, secondary teal, warning amber, error red) were declared
independently in three places, which let ``styles.py``'s ``PulseColors.AMBER``
drift to ``#F59E0B`` while everything else stayed on brand ``#F5A623``.

The generated app now has ONE source — ``BrandPalette`` in ``styles.py`` (the
import root; ``theme.py`` imports it) — that ``PulseColors`` and ``theme.py``'s
``DarkColorPalette`` both derive from. The tool's ``aegis/cli/brand.py`` can't
import the generated app (standalone projects don't depend on the aegis tool),
so it keeps its own literals; this test is the guard that they never drift from
the canonical source again.

The template palettes are read by parsing (``ast``) rather than importing, so the
test needs neither ``flet`` nor a rendered project.
"""

from __future__ import annotations

import ast
from pathlib import Path

from aegis.cli import brand
from aegis.core.component_files import get_template_path

_FRONTEND = (
    get_template_path() / "{{ project_slug }}" / "app" / "components" / "frontend"
)
STYLES_PY = _FRONTEND / "styles.py"
THEME_PY = _FRONTEND / "theme.py"

CANONICAL_CLASS = "BrandPalette"


def _class_fields(source: Path, class_name: str) -> dict[str, ast.expr]:
    """Map each annotated field of ``class_name`` to its default-value AST node."""
    tree = ast.parse(source.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return {
                stmt.target.id: stmt.value
                for stmt in node.body
                if isinstance(stmt, ast.AnnAssign)
                and isinstance(stmt.target, ast.Name)
                and stmt.value is not None
            }
    raise AssertionError(f"class {class_name} not found in {source.name}")


def _literals(fields: dict[str, ast.expr]) -> dict[str, str]:
    """Fields whose default is a plain string literal → their value."""
    return {
        name: node.value
        for name, node in fields.items()
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }


def _brand_ref_attr(node: ast.expr) -> str | None:
    """If ``node`` is ``BrandPalette.<ATTR>``, return ``<ATTR>``; else None."""
    if (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == CANONICAL_CLASS
    ):
        return node.attr
    return None


def _canonical() -> dict[str, str]:
    return _literals(_class_fields(STYLES_PY, CANONICAL_CLASS))


def test_tool_palette_matches_canonical_brand_source() -> None:
    """``aegis/cli/brand.py`` mirrors the generated app's ``BrandPalette``."""
    src = _canonical()
    assert src["TEAL"] == brand.AEGIS_TEAL
    assert src["TEAL_DARK"] == brand.AEGIS_TEAL_DARK
    assert src["AMBER"] == brand.AEGIS_WARNING
    assert src["RED"] == brand.AEGIS_ERROR


def test_pulse_colors_derive_from_canonical_source() -> None:
    """``PulseColors`` brand accents reference ``BrandPalette`` (no re-drift).

    Asserting the AST node is a ``BrandPalette.<X>`` reference — not merely that
    the resolved value matches — is what structurally forecloses the amber drift
    that motivated this issue: a future literal edit would fail here.
    """
    fields = _class_fields(STYLES_PY, "PulseColors")
    for pulse_field, brand_field in (
        ("TEAL", "TEAL"),
        ("AMBER", "AMBER"),
        ("STOP", "RED"),
    ):
        assert _brand_ref_attr(fields[pulse_field]) == brand_field, (
            f"PulseColors.{pulse_field} must derive from {CANONICAL_CLASS}.{brand_field}"
        )


def test_dark_theme_brand_colors_derive_from_canonical_source() -> None:
    """``theme.py``'s ``DarkColorPalette`` brand accents reference ``BrandPalette``."""
    fields = _class_fields(THEME_PY, "DarkColorPalette")
    for theme_field, brand_field in (
        ("ACCENT", "TEAL"),
        ("ACCENT_SECONDARY", "TEAL_DARK"),
        ("ACCENT_WARNING", "AMBER"),
        ("ACCENT_STOP", "RED"),
    ):
        assert _brand_ref_attr(fields[theme_field]) == brand_field, (
            f"DarkColorPalette.{theme_field} must derive from "
            f"{CANONICAL_CLASS}.{brand_field}"
        )
