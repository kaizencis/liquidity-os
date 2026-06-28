"""Tests for retry_with_backoff — exponential backoff retry logic."""

from __future__ import annotations

import asyncio
from unittest.mock import patch, call

import pytest

from collector.retry import retry_with_backoff, _default_is_retryable


def _make_failing_fn(fail_until: int):
    """Return an async function that raises TimeoutError for `fail_until` attempts,
    then returns 'ok'."""
    counter = 0

    async def fn():
        nonlocal counter
        counter += 1
        if counter <= fail_until:
            raise asyncio.TimeoutError()
        return "ok"

    return fn


class TestRetry:
    """retry_with_backoff correctness."""

    @pytest.mark.asyncio
    async def test_success_first_try(self):
        """fn succeeds immediately — returned directly, no retry."""

        async def ok():
            return "done"

        result = await retry_with_backoff(ok)
        assert result == "done"

    @pytest.mark.asyncio
    async def test_retry_on_timeout(self):
        """asyncio.TimeoutError triggers retry."""
        fn = _make_failing_fn(1)  # fail once, succeed once
        result = await retry_with_backoff(fn)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_retry_on_builtin_timeout(self):
        """Builtin TimeoutError also triggers retry (not just asyncio version)."""
        call_count = 0

        async def fn():
            nonlocal call_count
            call_count += 1
            raise TimeoutError()

        with pytest.raises(TimeoutError):
            await retry_with_backoff(fn, max_retries=1)
        assert call_count == 2, "Should have been retried once"

    @pytest.mark.asyncio
    async def test_retry_then_succeed(self):
        """Fail once, succeed on retry."""
        fn = _make_failing_fn(1)
        result = await retry_with_backoff(fn)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_exhausted_retries(self):
        """All retries exhausted — last error raised."""
        fn = _make_failing_fn(99)  # always fails
        with pytest.raises(asyncio.TimeoutError):
            await retry_with_backoff(fn, max_retries=2)

    @pytest.mark.asyncio
    async def test_non_retryable_immediate(self):
        """ValueError is not retried — re-raised immediately.
        Also verifies default classifier behavior.
        """

        async def fn():
            raise ValueError("bad")

        with pytest.raises(ValueError, match="bad"):
            await retry_with_backoff(fn)

    @pytest.mark.asyncio
    async def test_custom_classifier(self):
        """Custom is_retryable overrides default classifier."""

        async def fn():
            raise ValueError("custom")

        classifier = lambda e: isinstance(e, ValueError)
        with pytest.raises(ValueError):
            await retry_with_backoff(fn, max_retries=1, is_retryable=classifier)

    @pytest.mark.asyncio
    async def test_backoff_doubles(self):
        """Each retry delay doubles (with jitter=0 for deterministic test)."""
        recorded = []

        async def sleeper(delay):
            recorded.append(delay)

        fn = _make_failing_fn(2)  # fail twice, succeed on 3rd
        with patch("asyncio.sleep", side_effect=sleeper):
            await retry_with_backoff(fn, max_retries=2, base_delay=1.0, jitter=0.0)

        assert len(recorded) == 2, f"Expected 2 backoff sleeps, got {len(recorded)}"
        assert recorded[0] == pytest.approx(1.0, rel=0.01)
        assert recorded[1] == pytest.approx(2.0, rel=0.01)

    @pytest.mark.asyncio
    async def test_max_delay_cap(self):
        """Backoff delay is capped at max_delay."""
        recorded = []

        async def sleeper(delay):
            recorded.append(delay)

        fn = _make_failing_fn(99)
        with patch("asyncio.sleep", side_effect=sleeper):
            with pytest.raises(asyncio.TimeoutError):
                await retry_with_backoff(
                    fn, max_retries=3, base_delay=10.0, max_delay=25.0, jitter=0.0
                )

        for d in recorded:
            assert d <= 25.0, f"Delay {d} > max_delay 25.0"

    @pytest.mark.asyncio
    async def test_max_retries_zero(self):
        """max_retries=0 means exactly 1 attempt, no retry."""
        call_count = 0

        async def fn():
            nonlocal call_count
            call_count += 1
            raise asyncio.TimeoutError()

        with pytest.raises(asyncio.TimeoutError):
            await retry_with_backoff(fn, max_retries=0)
        assert call_count == 1, "fn should be called exactly once"

    @pytest.mark.asyncio
    async def test_jitter_range(self):
        """Jitter randomizes delay within expected range."""
        import random
        from unittest.mock import patch as mock_patch

        fn = _make_failing_fn(1)  # fails once → 1 backoff

        # First call: uniform(-0.1, 0.1) = -0.1 → delay = 1.0 * (1 - 0.1) = 0.9
        with mock_patch.object(random, "uniform", return_value=-0.1):
            with mock_patch("asyncio.sleep") as mock_sleep:
                await retry_with_backoff(fn, max_retries=1, base_delay=1.0, jitter=0.1)
                assert mock_sleep.call_args == call(0.9), f"Expected 0.9, got {mock_sleep.call_args}"

    @pytest.mark.asyncio
    async def test_args_kwargs_passed(self):
        """fn receives positional and keyword arguments."""

        async def summer(a, b, **kw):
            return a + b + kw.get("c", 0)

        result = await retry_with_backoff(summer, 1, 2, c=3)
        assert result == 6

    # ---- standalone classifier tests ---- #

    def test_default_classifier(self):
        """_default_is_retryable catches timeout errors only."""
        assert _default_is_retryable(asyncio.TimeoutError()) is True
        assert _default_is_retryable(TimeoutError()) is True
        assert _default_is_retryable(ValueError()) is False
        assert _default_is_retryable(TypeError()) is False
        assert _default_is_retryable(RuntimeError()) is False
