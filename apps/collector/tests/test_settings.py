"""Tests for CollectorSettings — frozen dataclass."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from collector.settings import CollectorSettings


class TestCollectorSettings:
    """CollectorSettings field validation."""

    def test_defaults(self):
        """All 15 fields have correct default values."""
        s = CollectorSettings()
        assert s.interval_seconds == 60
        assert s.rate_limit_rps == 30
        assert s.api_timeout_seconds == 30.0
        assert s.pool_timeout_seconds == 8.0
        assert s.positions_timeout_seconds == 12.0
        assert s.db_timeout_seconds == 5.0
        assert s.pool_positions_timeout == 30.0
        assert s.max_retries == 2
        assert s.retry_base_delay == 1.0
        assert s.retry_max_delay == 30.0
        assert s.retry_jitter == 0.1
        assert s.db_pool_size == 5
        assert s.snapshot_retention_days == 90
        assert s.meteora_base_url == "https://dlmm.datapi.meteora.ag"
        assert s.meteora_timeout == 30.0

    def test_frozen(self):
        """Cannot modify after creation."""
        s = CollectorSettings()
        with pytest.raises(FrozenInstanceError):
            s.interval_seconds = 90  # type: ignore[misc]

    def test_custom_values(self):
        """Can override every field via constructor."""
        s = CollectorSettings(
            interval_seconds=120,
            rate_limit_rps=10,
            api_timeout_seconds=15.0,
            pool_timeout_seconds=4.0,
            positions_timeout_seconds=6.0,
            db_timeout_seconds=2.5,
            pool_positions_timeout=20.0,
            max_retries=0,
            retry_base_delay=0.5,
            retry_max_delay=10.0,
            retry_jitter=0.2,
            db_pool_size=10,
            snapshot_retention_days=0,
            meteora_base_url="https://custom.api.meteora.ag",
            meteora_timeout=15.0,
        )
        assert s.interval_seconds == 120
        assert s.rate_limit_rps == 10
        assert s.api_timeout_seconds == 15.0
        assert s.pool_timeout_seconds == 4.0
        assert s.positions_timeout_seconds == 6.0
        assert s.db_timeout_seconds == 2.5
        assert s.pool_positions_timeout == 20.0
        assert s.max_retries == 0
        assert s.retry_base_delay == 0.5
        assert s.retry_max_delay == 10.0
        assert s.retry_jitter == 0.2
        assert s.db_pool_size == 10
        assert s.snapshot_retention_days == 0
        assert s.meteora_base_url == "https://custom.api.meteora.ag"
        assert s.meteora_timeout == 15.0

    def test_type_enforcement(self):
        """Dataclass does NOT validate types at runtime — accepts any value."""
        # Python @dataclass has no runtime type enforcement. Even though
        # the type annotation says int, a string is silently accepted.
        s = CollectorSettings(interval_seconds="sixty")  # type: ignore[arg-type]
        assert s.interval_seconds == "sixty"
