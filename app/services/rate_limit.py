from __future__ import annotations

import time

from app.config import settings


class RateLimiter:
    """In-memory sliding-window rate limiter with automatic cleanup."""

    _buckets: dict[str, list[float]] = {}  # noqa: RUF012
    _last_cleanup: float = 0.0
    _CLEANUP_INTERVAL: float = 300.0

    @classmethod
    def is_limited(cls, key: str) -> bool:
        now = time.monotonic()
        cls._maybe_cleanup(now)

        window = settings.rate_window
        bucket = cls._buckets.setdefault(key, [])
        cls._buckets[key] = [t for t in bucket if now - t < window]

        if len(cls._buckets[key]) >= settings.rate_max:
            return True

        cls._buckets[key].append(now)
        return False

    @classmethod
    def _maybe_cleanup(cls, now: float) -> None:
        if now - cls._last_cleanup < cls._CLEANUP_INTERVAL:
            return
        cls._last_cleanup = now
        window = settings.rate_window
        stale = [k for k, v in cls._buckets.items() if not v or now - v[-1] > window]
        for k in stale:
            del cls._buckets[k]

    @classmethod
    def reset(cls) -> None:
        """For testing."""
        cls._buckets.clear()
        cls._last_cleanup = 0.0
