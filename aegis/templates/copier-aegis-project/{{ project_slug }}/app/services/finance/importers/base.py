"""Shared import primitives used by the OFX/QFX, QIF, and CSV importers.

Parsers produce ``ParsedTransaction`` records; ``import_service`` ingests them
(batch bookkeeping + two-lane dedup). House rule: amounts are integer minor
units and **negative means an outflow**. ``amount`` is sign-normalized while
``raw_amount`` / ``raw_sign_convention`` preserve the source's original form.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

_PUNCTUATION = re.compile(r"[^0-9A-Za-z\s]")
_WHITESPACE = re.compile(r"\s+")


def normalize_payee(raw: str | None) -> str:
    """Uppercase, ASCII-fold, strip punctuation, collapse whitespace.

    ``"  Café   Münchén!! "`` -> ``"CAFE MUNCHEN"``. Folding via NFKD keeps the
    base letters (é -> e) so an accented and un-accented spelling of the same
    merchant collapse to one stable dedup key — the goal is a key, not a pretty
    display name.
    """
    if not raw:
        return ""
    folded = (
        unicodedata.normalize("NFKD", raw).encode("ascii", "ignore").decode("ascii")
    )
    stripped = _PUNCTUATION.sub(" ", folded)
    return _WHITESPACE.sub(" ", stripped).strip().upper()


def to_cents(amount: Decimal | float | int | str) -> int:
    """Convert a decimal money amount to signed integer minor units (cents)."""
    return int((Decimal(str(amount)) * 100).to_integral_value())


@dataclass
class ParsedTransaction:
    """A source-agnostic transaction produced by a parser."""

    date: date
    amount: int  # sign-normalized cents (negative = outflow)
    source: str  # 'ofx' | 'qfx' | 'qif' | 'csv'
    external_id: str | None = None
    external_id_source: str | None = None
    import_hash: str | None = None
    raw_amount: int | None = None
    raw_sign_convention: str | None = None
    name: str | None = None
    original_description: str | None = None
    memo: str | None = None
    check_number: str | None = None
    # Account routing hint (e.g. OFX ACCTID) — resolved against
    # finance_account.provider_account_id, else the explicit account_id param.
    account_key: str | None = None


@dataclass
class ImportResult:
    """Outcome of an import run (returned to the caller / API)."""

    batch_id: int | None = None
    rows_total: int = 0
    rows_inserted: int = 0
    rows_updated: int = 0
    rows_duplicate: int = 0
    rows_error: int = 0
