"""In-memory token blacklist for JWT revocation."""

import time


class TokenBlacklist:
    """In-memory set of revoked tokens with auto-expiry cleanup."""

    def __init__(self) -> None:
        # Maps token_jti -> expiry_timestamp
        self._revoked: dict[str, float] = {}

    def revoke(self, token_jti: str, expires_at: float) -> None:
        """Add a token to the blacklist."""
        self._revoked[token_jti] = expires_at
        self._cleanup()

    def is_revoked(self, token_jti: str) -> bool:
        """Check if a token is revoked."""
        self._cleanup()
        return token_jti in self._revoked

    def _cleanup(self) -> None:
        """Remove expired entries."""
        now = time.time()
        self._revoked = {jti: exp for jti, exp in self._revoked.items() if exp > now}

    def reset(self) -> None:
        """Clear all state. For testing."""
        self._revoked.clear()


token_blacklist = TokenBlacklist()
