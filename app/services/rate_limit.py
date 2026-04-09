from __future__ import annotations

import time

from app.config import settings


class RateLimiter:
    """In-memory sliding-window rate limiter with automatic cleanup."""

    _buckets: dict[str, list[float]] = {}
    _last_cleanup: float = 0.0
    _CLEANUP_INTERVAL: float = 300.0  # purge stale keys every 5 min

    @classmethod
    def is_limited(cls, key: str) -> bool:
        now = time.monotonic()
        cls._maybe_cleanup(now)

        window = cls._buckets.setdefault(key, [])
        cls._buckets[key] = [t for t in window if now - t < settings.rate_window]

        if len(cls._buckets[key]) >= settings.rate_max:
            return True

        cls._buckets[key].append(now)
        return False

    @classmethod
    def _maybe_cleanup(cls, now: float) -> None:
        if now - cls._last_cleanup < cls._CLEANUP_INTERVAL:
            return
        cls._last_cleanup = now
        stale = [
            k
            for k, v in cls._buckets.items()
            if not v or now - v[-1] > settings.rate_window
        ]
        for k in stale:
            del cls._buckets[k]
