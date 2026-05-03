"""
Symmetric encryption helper for sensitive column values.

Used to protect at-rest secrets like per-project GitHub PATs and
Plausible API keys, which are stored in the database alongside their
metadata. A DB dump should never reveal a usable token.

How it works
------------
The helper derives a Fernet-compatible key deterministically from
``settings.SECRET_KEY`` (SHA-256 + url-safe base64). Anything Aegis
already trusts ``SECRET_KEY`` for (JWT signing, OAuth session cookies)
gets the same protection here. The derivation is one-way: rotating
``SECRET_KEY`` invalidates every previously-encrypted value, by design
— the same contract Flet's ``flet.security.encrypt`` exposes on the
frontend.

Why Fernet
----------
Fernet is the cryptography library's batteries-included AEAD primitive
(AES-128 in CBC mode + HMAC-SHA-256), with a fresh random IV per call,
so two encryptions of the same plaintext produce different ciphertexts.
That means ciphertext-equality leaks nothing about plaintext-equality
across rows.

The helper is process-cached so we don't re-derive the key on every
encrypt/decrypt call.
"""

from __future__ import annotations

import base64
import hashlib

from app.core.config import settings
from cryptography.fernet import Fernet

_cached_fernet: Fernet | None = None


def _fernet() -> Fernet:
    """Return the per-process Fernet instance, building it on first use."""
    global _cached_fernet
    if _cached_fernet is None:
        digest = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
        key = base64.urlsafe_b64encode(digest)
        _cached_fernet = Fernet(key)
    return _cached_fernet


def _reset_cache() -> None:
    """Drop the cached Fernet so the next call re-derives from settings.

    Used by tests that mutate ``settings.SECRET_KEY`` mid-run; do not
    call from production code.
    """
    global _cached_fernet
    _cached_fernet = None


def encrypt_secret(plaintext: str) -> str:
    """Encrypt a plaintext string. Returns the urlsafe-base64 ciphertext."""
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_secret(ciphertext: str) -> str:
    """Decrypt a ciphertext produced by ``encrypt_secret``.

    Raises ``cryptography.fernet.InvalidToken`` if the ciphertext was
    produced with a different key (typically: the secret was rotated).
    """
    return _fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
