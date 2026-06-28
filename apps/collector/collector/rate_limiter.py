"""Rate limiter for Meteora API calls.

[WHY] Lock-based rate limiter using monotonic clock.
      Serializes concurrent acquire() calls to enforce requests-per-second.
      No background tasks, no queues, approximately fair.
[OWNERSHIP] Collector Service — infrastructure.
[DEPENDENTS] Allowed: collector.collector.
             Forbidden: shared, agents, other apps.
[EXAMPLE]
    from collector.rate_limiter import RateLimiter

    limiter = RateLimiter(rps=30)
    await limiter.acquire()   # blocks until allowed
    # make HTTP call
"""

from __future__ import annotations

import asyncio
import time


class RateLimiter:
    """Lock-based rate limiter with monotonic clock.

    First caller passes immediately without delay.
    Subsequent callers wait for the remaining interval.
    Approximately fair — waiting order is roughly preserved under normal load.
    """

    def __init__(self, rps: int) -> None:
        """Initialize rate limiter.

        Args:
            rps: Maximum requests per second. Must be > 0.

        Raises:
            ValueError: If rps is not positive.
        """
        if rps <= 0:
            raise ValueError(f"rps must be positive, got {rps}")
        self._min_interval: float = 1.0 / rps
        self._last: float = 0.0
        self._lock: asyncio.Lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait for rate-limit capacity.

        Blocks until the minimum interval has elapsed since the last
        acquire() returned. The first call returns immediately.
        """
        async with self._lock:
            now = time.monotonic()
            if self._last == 0.0:
                # First call: no delay, record timestamp.
                self._last = now
                return

            elapsed = now - self._last
            sleep_for = self._min_interval - elapsed
            if sleep_for > 0:
                await asyncio.sleep(sleep_for)

            self._last = time.monotonic()
