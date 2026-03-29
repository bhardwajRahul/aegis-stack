"""Simple in-memory rate limiter for auth endpoints."""

import time
from collections import defaultdict

from app.core.config import settings
from fastapi import HTTPException, Request, status


class RateLimiter:
    """In-memory rate limiter using sliding window."""

    def __init__(
        self,
        max_requests: int = 5,
        window_seconds: int = 60,
        trust_proxy_headers: bool = False,
    ) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.trust_proxy_headers = trust_proxy_headers
        self._requests: dict[str, list[float]] = defaultdict(list)

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP from request."""
        if self.trust_proxy_headers:
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _cleanup(self, key: str) -> None:
        """Remove expired timestamps."""
        cutoff = time.time() - self.window_seconds
        self._requests[key] = [t for t in self._requests[key] if t > cutoff]

    def check(self, request: Request) -> None:
        """Check rate limit. Raises 429 if exceeded."""
        ip = self._get_client_ip(request)
        self._cleanup(ip)

        if len(self._requests[ip]) >= self.max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
                headers={"Retry-After": str(self.window_seconds)},
            )

        self._requests[ip].append(time.time())

    def reset(self) -> None:
        """Clear all rate limit state. Useful for testing."""
        self._requests.clear()


# Shared instances for auth endpoints
login_limiter = RateLimiter(
    max_requests=5, window_seconds=60, trust_proxy_headers=settings.TRUST_PROXY_HEADERS
)
register_limiter = RateLimiter(
    max_requests=3, window_seconds=60, trust_proxy_headers=settings.TRUST_PROXY_HEADERS
)
password_reset_limiter = RateLimiter(
    max_requests=3, window_seconds=60, trust_proxy_headers=settings.TRUST_PROXY_HEADERS
)
