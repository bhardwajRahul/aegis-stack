"""Guards that shared literals are referenced through constants, not retyped.

Magic strings that have a constant but get retyped anyway drift silently (a
typo in a ``.get()`` key returns ``None`` instead of raising). These tests
scan the source and fail if a known literal is hardcoded outside its single
definition in ``aegis/constants.py``.
"""

from __future__ import annotations

from pathlib import Path

from aegis.constants import AnswerKeys

AEGIS_ROOT = Path(__file__).resolve().parents[2] / "aegis"


def _source_files() -> list[Path]:
    """All first-party Python sources, excluding generated templates."""
    return [
        p
        for p in AEGIS_ROOT.rglob("*.py")
        if "templates" not in p.parts and "__pycache__" not in p.parts
    ]


def test_copier_answers_filename_not_hardcoded() -> None:
    """``.copier-answers.yml`` must go through ``AnswerKeys.ANSWERS_FILENAME``.

    constants.py is the single allowed site (the definition).
    """
    literal = f'"{AnswerKeys.ANSWERS_FILENAME}"'  # the quoted string form
    offenders: list[str] = []
    for path in _source_files():
        if path.name == "constants.py":
            continue
        for lineno, line in enumerate(path.read_text().splitlines(), start=1):
            if literal in line:
                rel = path.relative_to(AEGIS_ROOT.parent)
                offenders.append(f"{rel}:{lineno}: {line.strip()}")

    assert not offenders, (
        "Hardcoded '.copier-answers.yml' literal found; use "
        "AnswerKeys.ANSWERS_FILENAME instead:\n  " + "\n  ".join(offenders)
    )


def test_infrastructure_order_matches_registry() -> None:
    """``INFRASTRUCTURE_ORDER`` must stay in sync with the component registry.

    The interactive prompts iterate ``ComponentNames.INFRASTRUCTURE_ORDER``; an
    optional component (any non-CORE type: infrastructure or frontend) added
    to ``COMPONENTS`` but forgotten here would silently never be offered. The
    registry dict order is the intended display order, so require an exact
    match.
    """
    from aegis.constants import ComponentNames
    from aegis.core.components import COMPONENTS, ComponentType

    derived = [
        name for name, spec in COMPONENTS.items() if spec.type != ComponentType.CORE
    ]
    assert derived == ComponentNames.INFRASTRUCTURE_ORDER, (
        "ComponentNames.INFRASTRUCTURE_ORDER drifted from the COMPONENTS "
        f"registry.\n  registry: {derived}\n  constant: "
        f"{ComponentNames.INFRASTRUCTURE_ORDER}"
    )
