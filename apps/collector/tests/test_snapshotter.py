"""Tests for Snapshotter — Pool → Snapshot factory."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from collector.snapshotter import Snapshotter
from shared.entities.pool import Pool
from shared.enums import PoolStatus
from shared.identifiers import PoolAddress
from shared.value_objects.price import Price, SqrtPrice
from shared.value_objects.snapshot import Snapshot
from shared.value_objects.token import Token


@pytest.fixture
def token_a():
    return Token(
        address="So11111111111111111111111111111111111111112",
        symbol="SOL",
        decimals=9,
    )


@pytest.fixture
def token_b():
    return Token(
        address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        symbol="USDC",
        decimals=6,
    )


@pytest.fixture
def sample_pool(token_a, token_b):
    return Pool(
        address=PoolAddress(value="7YttVPABs9FKVhiMq2eih6nGByCPqjRUoACKsHFK1hYs"),
        token_a=token_a,
        token_b=token_b,
        status=PoolStatus.ACTIVE,
        sqrt_price=SqrtPrice(raw=79228162514264337593543950336, tick=0, bin_id=0),
        price=Price(
            value=Decimal("142.5"),
            base_token=token_b,
            quote_token=token_a,
        ),
    )


@pytest.fixture
def reference_ts():
    return datetime(2026, 6, 25, 12, 0, 0, tzinfo=timezone.utc)


class TestSnapshotter:
    """Snapshotter.from_pool transformation tests."""

    def test_pool_address(self, sample_pool):
        """Snapshot pool == Pool address."""
        snap = Snapshotter.from_pool(sample_pool)
        assert snap.pool == sample_pool.address

    def test_price_copied(self, sample_pool):
        """Price copied from Pool."""
        snap = Snapshotter.from_pool(sample_pool)
        assert snap.price == sample_pool.price

    def test_sqrt_price_copied(self, sample_pool):
        """SqrtPrice copied from Pool."""
        snap = Snapshotter.from_pool(sample_pool)
        assert snap.sqrt_price == sample_pool.sqrt_price

    def test_default_timestamp(self, sample_pool):
        """Default timestamp is close to now."""
        before = datetime.now(timezone.utc)
        snap = Snapshotter.from_pool(sample_pool)
        after = datetime.now(timezone.utc)
        assert (
            before - timedelta(seconds=1) <= snap.timestamp <= after + timedelta(seconds=1)
        ), f"Timestamp {snap.timestamp} outside expected range"

    def test_provided_timestamp(self, sample_pool, reference_ts):
        """Provided timestamp is honoured."""
        snap = Snapshotter.from_pool(sample_pool, timestamp=reference_ts)
        assert snap.timestamp == reference_ts

    def test_none_price(self, token_a, token_b):
        """Pool with None price → snapshot.price is None."""
        pool = Pool(
            address=PoolAddress(value="7YttVPABs9FKVhiMq2eih6nGByCPqjRUoACKsHFK1hYs"),
            token_a=token_a,
            token_b=token_b,
            status=PoolStatus.ACTIVE,
        )
        assert pool.price is None
        snap = Snapshotter.from_pool(pool)
        assert snap.price is None

    def test_none_sqrt_price(self, token_a, token_b):
        """Pool with None sqrt_price → snapshot.sqrt_price is None."""
        pool = Pool(
            address=PoolAddress(value="7YttVPABs9FKVhiMq2eih6nGByCPqjRUoACKsHFK1hYs"),
            token_a=token_a,
            token_b=token_b,
            status=PoolStatus.ACTIVE,
        )
        assert pool.sqrt_price is None
        snap = Snapshotter.from_pool(pool)
        assert snap.sqrt_price is None

    def test_metadata_provided(self, sample_pool):
        """Provided metadata stored in snapshot."""
        snap = Snapshotter.from_pool(sample_pool, metadata={"source": "test"})
        assert snap.metadata == {"source": "test"}

    def test_metadata_default(self, sample_pool):
        """Default metadata is empty dict."""
        snap = Snapshotter.from_pool(sample_pool)
        assert snap.metadata == {}

    def test_snapshot_frozen(self, sample_pool):
        """Snapshot is immutable."""
        snap = Snapshotter.from_pool(sample_pool)
        with pytest.raises(ValidationError):
            snap.pool = PoolAddress(value="other")  # type: ignore[misc]
