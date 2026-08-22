"""Rate limiting for the endpoints that spend money on LLM calls.

The limiter is process-local, which matches the rest of the deployment: the
session store is already in-memory and single-instance (design doc 5.7). If the
backend is ever scaled horizontally this needs to move to Redis at the same time
as the session store, otherwise each replica enforces its own quota.

Two independent limits apply to every paid request:

* **per-IP** — stops a single visitor looping the demo.
* **global** — the wallet backstop. A per-IP limit bounds nothing on its own
  because IPs are trivially rotated; only a global ceiling caps total spend.

Neither replaces a hard spend cap in the Anthropic console, which is the only
limit that cannot be bypassed by a bug in this file.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from app.core.config import settings

# Beyond this many tracked keys, drop the ones whose windows have fully expired.
# Bounds memory if the service is scanned by a bot cycling source addresses.
_MAX_TRACKED_KEYS = 10_000


class SlidingWindow:
    """Counts hits per key over a moving time window."""

    def __init__(self, limit: int, window_s: int) -> None:
        self.limit = limit
        self.window_s = window_s
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def _fresh(self, key: str, now: float) -> deque[float]:
        hits = self._hits[key]
        cutoff = now - self.window_s
        while hits and hits[0] <= cutoff:
            hits.popleft()
        return hits

    def retry_after(self, key: str, now: float | None = None) -> float | None:
        """Seconds until ``key`` has room again, or None if it's under the limit.

        Checking is deliberately separate from :meth:`record` so a caller subject
        to several limits can test them all before consuming a slot in any.
        """
        now = time.monotonic() if now is None else now
        hits = self._fresh(key, now)
        if len(hits) < self.limit:
            return None
        return max(1.0, self.window_s - (now - hits[0]))

    def record(self, key: str, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        self._hits[key].append(now)
        if len(self._hits) > _MAX_TRACKED_KEYS:
            self._evict_expired(now)

    def _evict_expired(self, now: float) -> None:
        for key in [k for k in list(self._hits) if not self._fresh(k, now)]:
            del self._hits[key]


_per_ip = SlidingWindow(settings.rate_limit_per_ip_per_hour, 60 * 60)
_global = SlidingWindow(settings.rate_limit_global_per_day, 60 * 60 * 24)

_GLOBAL_KEY = "*"


def client_ip(request: Request) -> str:
    """Best-effort caller identity.

    Render (like most PaaS hosts) terminates TLS at a proxy, so `request.client`
    is the proxy and the real caller is first in `X-Forwarded-For`. This is
    spoofable — it's a courtesy limit, not a security boundary, which is why the
    global ceiling exists.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _too_many(detail: str, retry_after: float) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=detail,
        headers={"Retry-After": str(int(retry_after))},
    )


async def llm_rate_limit(request: Request) -> None:
    """FastAPI dependency guarding any route that triggers a paid LLM call."""
    if not settings.rate_limit_enabled:
        return

    if (retry := _global.retry_after(_GLOBAL_KEY)) is not None:
        raise _too_many(
            "The demo has hit its daily budget cap. Pre-analyzed samples still "
            "work — try one of those, or check back tomorrow.",
            retry,
        )

    ip = client_ip(request)
    if (retry := _per_ip.retry_after(ip)) is not None:
        raise _too_many(
            "You've run a lot of analyses in a short window. Give it a few "
            "minutes and try again.",
            retry,
        )

    # Only consumed once every limit has passed, so a rejection by one limit
    # doesn't quietly burn quota in another.
    _global.record(_GLOBAL_KEY)
    _per_ip.record(ip)


def reset() -> None:
    """Clear all counters. For tests."""
    _per_ip._hits.clear()
    _global._hits.clear()
