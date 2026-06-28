"""Tests for RateLimiter — lock-based async rate limiter."""

from __future__ import annotations

import asyncio
import time

import pytest

from collector.rate_limiter import RateLimiter


class TestRateLimiter:
    """RateLimiter correctness and timing."""

    @pytest.mark.asyncio
    async def test_first_acquire_no_delay(self):
        """First caller passes immediately without blocking."""
        rl = RateLimiter(rps=30)
        t0 = time.monotonic()
        await rl.acquire()
        dt = time.monotonic() - t0
        assert dt < 0.01, f"First acquire blocked for {dt:.4f}s"

    @pytest.mark.asyncio
    async def test_second_acquire_delayed(self):
        """Second caller waits approximately min_interval."""
        rl = RateLimiter(rps=10)  # min_interval = 0.1s
        await rl.acquire()
        t0 = time.monotonic()
        await rl.acquire()
        dt = time.monotonic() - t0
        assert dt == pytest.approx(0.1, rel=0.4), f"Second acquire took {dt:.4f}s"

    @pytest.mark.asyncio
    async def test_rps_30(self):
        """30 calls at 30 RPS take approximately 1 second."""
        rl = RateLimiter(rps=30)
        t0 = time.monotonic()
        for _ in range(30):
            await rl.acquire()
        dt = time.monotonic() - t0
        assert dt == pytest.approx(1.0, rel=0.4), f"30 acquires took {dt:.4f}s"

    @pytest.mark.asyncio
    async def test_rps_1(self):
        """2 calls at 1 RPS take approximately 1 second."""
        rl = RateLimiter(rps=1)
        await rl.acquire()
        t0 = time.monotonic()
        await rl.acquire()
        dt = time.monotonic() - t0
        assert dt == pytest.approx(1.0, rel=0.4), f"2nd acquire took {dt:.4f}s"

    @pytest.mark.asyncio
    async def test_concurrent_serialized(self):
        """Concurrent callers are serialized and rate is not exceeded."""
        rl = RateLimiter(rps=100)
        n_calls = 10

        async def acquire_and_record():
            t = time.monotonic()
            await rl.acquire()
            return time.monotonic() - t

        results = await asyncio.gather(*[acquire_and_record() for _ in range(n_calls)])
        gaps = [results[i] - results[i - 1] for i in range(1, len(results))]
        mean_gap = sum(gaps) / len(gaps) if gaps else 0
        assert mean_gap >= 0.008, f"Mean gap {mean_gap:.4f}s < 0.008s"

    def test_invalid_rps(self):
        """rps <= 0 raises ValueError."""
        with pytest.raises(ValueError, match="rps must be positive"):
            RateLimiter(rps=0)
        with pytest.raises(ValueError, match="rps must be positive"):
            RateLimiter(rps=-1)

    @pytest.mark.asyncio
    async def test_after_idle_no_accumulation(self):
        """After idle period, next call returns immediately (no token accumulation)."""
        rl = RateLimiter(rps=10)
        await rl.acquire()
        await asyncio.sleep(0.5)
        t0 = time.monotonic()
        await rl.acquire()
        dt = time.monotonic() - t0
        assert dt < 0.05, f"Acquire after idle blocked for {dt:.4f}s (tokens accumulated)"

    def test_uses_monotonic_clock(self):
        """Implementation uses time.monotonic, not time.time."""
        import inspect
        import collector.rate_limiter as rl_mod

        source = inspect.getsource(rl_mod)
        assert "time.monotonic()" in source, "Must use monotonic clock"
        assert "time.time()" not in source, "Must NOT use wall clock"
        assert "import time" in source

    @pytest.mark.asyncio
    async def test_approximately_fair(self):
        """Start order roughly preserved under normal load."""
        rl = RateLimiter(rps=5)
        n = 5
        order = []

        async def task(idx):
            await rl.acquire()
            order.append(idx)

        tasks = [asyncio.create_task(task(i)) for i in range(n)]
        await asyncio.sleep(0.1)
        await asyncio.gather(*tasks)

        swaps = sum(1 for i in range(n) if order[i] != i)
        assert swaps <= 2, f"Fairness violation: start order {list(range(n))}, completion {order}"
