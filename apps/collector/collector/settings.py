"""Frozen settings for the Collector Service.

[WHY] Central configuration for all collector behavior.
      All timeouts, limits, and connection parameters in one place.
[OWNERSHIP] Collector Service — configuration.
[DEPENDENTS] Allowed: collector modules.
             Forbidden: shared, agents, other apps.
[EXAMPLE]
    from collector.settings import CollectorSettings
    settings = CollectorSettings()
    assert settings.interval_seconds == 60
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CollectorSettings:
    """Frozen settings for the Collector Service.

    All timeouts are in seconds.
    Rate limits are in requests per second.
    """

    # --- Scheduling ---
    interval_seconds: int = 60
    """Seconds between collector cycles."""

    # --- Rate Limiting ---
    rate_limit_rps: int = 30
    """Maximum HTTP requests per second to Meteora API."""

    # --- Timeout Hierarchy ---
    api_timeout_seconds: float = 30.0
    """Total HTTP connection timeout (httpx client-level)."""

    pool_timeout_seconds: float = 8.0
    """Single pool request timeout. Unused after R4 — kept for contract completeness."""

    positions_timeout_seconds: float = 12.0
    """Single position request timeout per attempt."""

    db_timeout_seconds: float = 5.0
    """Single database persistence timeout."""

    pool_positions_timeout: float = 30.0
    """Aggregate timeout for batch position persistence. Partial writes accepted."""

    # --- Retry ---
    max_retries: int = 2
    """Maximum retry attempts (initial + 2 retries = 3 total attempts)."""

    retry_base_delay: float = 1.0
    """Base delay in seconds for exponential backoff."""

    retry_max_delay: float = 30.0
    """Maximum delay cap for backoff."""

    retry_jitter: float = 0.1
    """Jitter fraction applied to backoff delay (±10%)."""

    # --- Database ---
    db_pool_size: int = 5
    """Number of database connections in the pool."""

    snapshot_retention_days: int = 90
    """Days to retain snapshots before cleanup. 0 = keep forever."""

    # --- Meteora API ---
    meteora_base_url: str = "https://dlmm.datapi.meteora.ag"
    """Base URL for the Meteora DLMM API."""

    meteora_timeout: float = 30.0
    """HTTP client timeout for Meteora API calls (httpx)."""
