"""A small fixed-window rate limiter for sensitive routes.

In-process and intentionally simple: it protects a single-instance deployment
and documents the intent. Behind more than one worker, point ``_HITS`` at Redis
(the dependency signature does not change).
"""

from __future__ import annotations

import time
from collections import defaultdict

from fastapi import HTTPException, Request, status

from app.core.security import SESSION_COOKIE_NAME

_HITS: dict[str, list[float]] = defaultdict(list)


def _client_key(request: Request) -> str:
    """Prefer the session cookie so one user cannot burn a whole NAT's quota."""
    session = request.cookies.get(SESSION_COOKIE_NAME)
    if session:
        return f"session:{session[-32:]}"
    client = request.client.host if request.client else "unknown"
    return f"ip:{client}"


class RateLimiter:
    """FastAPI dependency: ``Depends(RateLimiter(times=5, seconds=60))``."""

    def __init__(self, times: int, seconds: int, scope: str = "default") -> None:
        self.times = times
        self.seconds = seconds
        self.scope = scope

    async def __call__(self, request: Request) -> None:
        now = time.monotonic()
        key = f"{self.scope}:{_client_key(request)}"
        window_start = now - self.seconds

        hits = [stamp for stamp in _HITS[key] if stamp > window_start]
        if len(hits) >= self.times:
            retry_after = max(1, int(self.seconds - (now - hits[0])))
            _HITS[key] = hits
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Try again in {retry_after}s.",
                headers={"Retry-After": str(retry_after)},
            )

        hits.append(now)
        _HITS[key] = hits


def reset_rate_limits() -> None:
    """Used by the test suite; never called at runtime."""
    _HITS.clear()
