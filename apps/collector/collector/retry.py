"""Retry with exponential backoff for the Collector Service.

[WHY] Provides configurable retry logic for transient failures.
      Default classifier catches timeout errors.
      Providers extend for 5xx/429 via custom is_retryable.
[OWNERSHIP] Collector Service — infrastructure.
[DEPENDENTS] Allowed: collector.collector.
             Forbidden: shared, agents, other apps.
[EXAMPLE]
    from collector.retry import retry_with_backoff

    result = await retry_with_backoff(
        api_call, arg1, arg2,
        max_retries=2,
        is_retryable=my_classifier,
    )
"""

from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

T = TypeVar("T")


def _default_is_retryable(exc: Exception) -> bool:
    """Default retry classifier: timeout errors only.

    Catches asyncio.TimeoutError (from asyncio.wait_for) and
    TimeoutError (from httpx or other network clients).
    """
    return isinstance(exc, (asyncio.TimeoutError, TimeoutError))


async def retry_with_backoff(
    fn: Callable[..., Awaitable[T]],
    *args: Any,
    max_retries: int = 2,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    jitter: float = 0.1,
    is_retryable: Callable[[Exception], bool] | None = None,
    **kwargs: Any,
) -> T:
    """Execute fn with retry and exponential backoff.

    Each retry attempt gets its own timeout window — the timeout
    wrapper must be inside fn, not outside retry_with_backoff.

    Args:
        fn: Async callable to execute.
        *args: Positional arguments passed to fn.
        max_retries: Maximum number of retries (0 = no retry).
        base_delay: Initial delay in seconds.
        max_delay: Maximum delay cap.
        jitter: Random jitter fraction (±).
        is_retryable: Optional classifier. Default catches timeout errors.
        **kwargs: Keyword arguments passed to fn.

    Returns:
        Result of fn if successful.

    Raises:
        Last exception raised by fn if all attempts fail.
        Non-retryable exceptions are re-raised immediately.
    """
    classifier = _default_is_retryable if is_retryable is None else is_retryable
    last_error: Exception | None = None

    # total attempts = max_retries + 1 (initial try)
    for attempt in range(1, max_retries + 2):
        try:
            return await fn(*args, **kwargs)
        except Exception as exc:
            last_error = exc
            if not classifier(exc) or attempt > max_retries:
                raise

        # Exponential backoff with jitter
        delay = base_delay * (2 ** (attempt - 1))
        delay = min(delay, max_delay)
        delay *= 1 + random.uniform(-jitter, jitter)
        await asyncio.sleep(delay)

    # Should not reach here — last attempt raises or returns
    raise last_error  # type: ignore[misc]
