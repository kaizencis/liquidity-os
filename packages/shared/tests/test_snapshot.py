"""Unit tests for shared.value_objects.snapshot module."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from shared.identifiers import PoolAddress
from shared.value_objects.price import Price, SqrtPrice
from shared.value_objects.snapshot import Snapshot
from shared.value_objects.token import Token, TokenAmount
from decimal import Decimal

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def SOL() -> Token:
    return Token(
        address="So11111111111111111111111111111111111111112",
        symbol="SOL",
        decimals=9,
    )


@pytest.fixture
def USDC() -> Token:
    return Token(
        address="EPjFwd4pz9iJGSVQiGieoXyBdKXX4usSJr7jTyCn9e",
        symbol="USDC",
        decimals=6,
    )


@pytest.fixture
def pool_address() -> PoolAddress:
    return PoolAddress(value="7YttLkHDoNj9wyDur5pM1ejNaAvT9X4eSTY")


@pytest.fixture
def timestamp() -> datetime:
    return datetime(2026, 6, 28, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def snapshot(
    pool_address: PoolAddress,
    timestamp: datetime,
    SOL: Token,
    USDC: Token,
) -> Snapshot:
    return Snapshot(
        pool=pool_address,
        timestamp=timestamp,
        sqrt_price=SqrtPrice(raw=79228162514264337593543950336, tick=0, bin_id=0),
        price=Price(value=Decimal("142.5"), base_token=USDC, quote_token=SOL),
        liquidity=TokenAmount(token=SOL, raw=1_000_000_000),
    )


# ---------------------------------------------------------------------------
# Snapshot — Creation
# ---------------------------------------------------------------------------


class TestSnapshotCreation:
    """Tests for Snapshot creation and basic properties."""

    def test_create_snapshot(
        self,
        pool_address: PoolAddress,
        timestamp: datetime,
        SOL: Token,
        USDC: Token,
    ) -> None:
        snapshot = Snapshot(
            pool=pool_address,
            timestamp=timestamp,
            sqrt_price=SqrtPrice(raw=79228162514264337593543950336, tick=0, bin_id=0),
            price=Price(value=Decimal("142.5"), base_token=USDC, quote_token=SOL),
            liquidity=TokenAmount(token=SOL, raw=1_000_000_000),
        )
        assert snapshot.pool == pool_address
        assert snapshot.timestamp == timestamp
        assert snapshot.price.value == Decimal("142.5")
        assert snapshot.liquidity.raw == 1_000_000_000

    def test_immutable(self, snapshot: Snapshot) -> None:
        with pytest.raises(Exception):
            snapshot.price = None  # type: ignore[misc]

    def test_default_timestamp(self, pool_address: PoolAddress) -> None:
        snapshot = Snapshot(pool=pool_address)
        assert isinstance(snapshot.timestamp, datetime)
        assert snapshot.timestamp.tzinfo is not None

    def test_optional_fields_none(self, pool_address: PoolAddress, timestamp: datetime) -> None:
        snapshot = Snapshot(pool=pool_address, timestamp=timestamp)
        assert snapshot.sqrt_price is None
        assert snapshot.price is None
        assert snapshot.liquidity is None
        assert snapshot.volume_24h is None
        assert snapshot.fees_24h is None

    def test_string_representation(self, snapshot: Snapshot) -> None:
        result = str(snapshot)
        assert "Snapshot(" in result
        assert "7YttLkHDoNj9wyDur5pM1ejNaAvT9X4eSTY" in result


# ---------------------------------------------------------------------------
# Snapshot — Natural Key Equality
# ---------------------------------------------------------------------------


class TestSnapshotEquality:
    """Tests for Snapshot equality based on natural key (pool, timestamp)."""

    def test_equal_same_key(
        self,
        pool_address: PoolAddress,
        timestamp: datetime,
        SOL: Token,
        USDC: Token,
    ) -> None:
        a = Snapshot(
            pool=pool_address,
            timestamp=timestamp,
            price=Price(value=Decimal("142.5"), base_token=USDC, quote_token=SOL),
        )
        b = Snapshot(
            pool=pool_address,
            timestamp=timestamp,
            price=Price(value=Decimal("150.0"), base_token=USDC, quote_token=SOL),
        )
        # Same natural key, different content — should be EQUAL
        assert a == b

    def test_not_equal_different_pool(
        self,
        timestamp: datetime,
        SOL: Token,
        USDC: Token,
    ) -> None:
        a = Snapshot(
            pool=PoolAddress(value="7YttLkHDoNj9wyDur5pM1ejNaAvT9X4eSTY"),
            timestamp=timestamp,
        )
        b = Snapshot(
            pool=PoolAddress(value="AJ6z3Zm9uGaNbJf8xLq3kR5pWtY7vH2n"),
            timestamp=timestamp,
        )
        assert a != b

    def test_not_equal_different_timestamp(
        self,
        pool_address: PoolAddress,
        SOL: Token,
        USDC: Token,
    ) -> None:
        a = Snapshot(pool=pool_address, timestamp=datetime(2026, 6, 28, 12, 0, 0, tzinfo=timezone.utc))
        b = Snapshot(pool=pool_address, timestamp=datetime(2026, 6, 28, 13, 0, 0, tzinfo=timezone.utc))
        assert a != b

    def test_not_equal_different_type(self, snapshot: Snapshot) -> None:
        assert snapshot != "not a snapshot"


# ---------------------------------------------------------------------------
# Snapshot — Hashing
# ---------------------------------------------------------------------------


class TestSnapshotHashing:
    """Tests for Snapshot hashing based on natural key."""

    def test_hashable(self, snapshot: Snapshot) -> None:
        snapshot_set = {snapshot}
        assert snapshot in snapshot_set

    def test_same_key_same_hash(
        self,
        pool_address: PoolAddress,
        timestamp: datetime,
        SOL: Token,
        USDC: Token,
    ) -> None:
        a = Snapshot(pool=pool_address, timestamp=timestamp)
        b = Snapshot(pool=pool_address, timestamp=timestamp)
        assert hash(a) == hash(b)

    def test_different_key_different_hash(
        self,
        pool_address: PoolAddress,
        SOL: Token,
        USDC: Token,
    ) -> None:
        a = Snapshot(
            pool=pool_address,
            timestamp=datetime(2026, 6, 28, 12, 0, 0, tzinfo=timezone.utc),
        )
        b = Snapshot(
            pool=pool_address,
            timestamp=datetime(2026, 6, 28, 13, 0, 0, tzinfo=timezone.utc),
        )
        assert hash(a) != hash(b)

    def test_dict_key(self, snapshot: Snapshot) -> None:
        snapshot_dict = {snapshot: "value"}
        assert snapshot in snapshot_dict


# ---------------------------------------------------------------------------
# Snapshot — Serialization
# ---------------------------------------------------------------------------


class TestSnapshotSerialization:
    """Tests for Snapshot serialization safety."""

    def test_model_dump(self, snapshot: Snapshot) -> None:
        data = snapshot.model_dump()
        assert isinstance(data, dict)
        assert "pool" in data
        assert "timestamp" in data
        assert "price" in data

    def test_model_dump_json(self, snapshot: Snapshot) -> None:
        json_str = snapshot.model_dump_json()
        assert isinstance(json_str, str)
        assert "7YttLkHDoNj9wyDur5pM1ejNaAvT9X4eSTY" in json_str

    def test_roundtrip(self, snapshot: Snapshot) -> None:
        data = snapshot.model_dump()
        restored = Snapshot(**data)
        assert restored == snapshot
        assert restored.pool == snapshot.pool
        assert restored.timestamp == snapshot.timestamp
