"""Snapshot immutable domain record for Liquidity OS.

[WHY] Snapshots are the primary data units in the time-series architecture.
      They capture pool state at a specific point in time, enabling auditability,
      replay, and deterministic simulation.

[OWNERSHIP] Domain layer — immutable domain record (value object with natural key).

[DEPENDENTS] Allowed: ports.snapshot_repo, apps.collector, apps.analytics,
             agents.oracle, agents.navigator.
             Forbidden: infrastructure (database, redis, httpx).

[EXAMPLE]
    from shared.value_objects.snapshot import Snapshot
    from shared.identifiers import PoolAddress
    from shared.value_objects.price import Price, SqrtPrice
    from shared.value_objects.token import Token, TokenAmount
    from decimal import Decimal
    from datetime import datetime, timezone

    SOL = Token(address="So111...", symbol="SOL", decimals=9)
    USDC = Token(address="EPjF...", symbol="USDC", decimals=6)

    snapshot = Snapshot(
        pool=PoolAddress("7Ytt..."),
        timestamp=datetime.now(timezone.utc),
        sqrt_price=SqrtPrice(raw=79228162514264337593543950336, tick=0, bin_id=0),
        price=Price(value=Decimal("142.5"), base_token=USDC, quote_token=SOL),
        liquidity=TokenAmount(token=SOL, raw=1_000_000_000),
    )
    assert snapshot.pool == PoolAddress("7Ytt...")
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from shared.identifiers import PoolAddress
from shared.value_objects.price import Price, SqrtPrice
from shared.value_objects.token import TokenAmount


class Snapshot(BaseModel):
    """[WHY] Immutable time-series record capturing pool state at a point in time.

    [OWNERSHIP] Domain layer — immutable domain record with natural key.

    [DEPENDENTS] Allowed: ports.snapshot_repo, apps.collector, apps.analytics,
                 agents.oracle, agents.navigator.
                 Forbidden: infrastructure packages.

    [NATURAL KEY]
        (pool, timestamp) — two snapshots with same pool and timestamp are equal.

    [EXAMPLE]
        snapshot = Snapshot(
            pool=PoolAddress("7Ytt..."),
            timestamp=datetime.now(timezone.utc),
            sqrt_price=SqrtPrice(raw=79228162514264337593543950336, tick=0, bin_id=0),
            price=Price(value=Decimal("142.5"), base_token=USDC, quote_token=SOL),
            liquidity=TokenAmount(token=SOL, raw=1_000_000_000),
        )
        assert snapshot.price.value == Decimal("142.5")
    """

    model_config = {"frozen": True}

    pool: PoolAddress = Field(..., description="Pool identifier")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Observation timestamp (UTC)",
    )
    sqrt_price: SqrtPrice | None = Field(default=None, description="Raw DLMM price state")
    price: Price | None = Field(default=None, description="Derived human-readable price")
    liquidity: TokenAmount | None = Field(default=None, description="Total pool liquidity")
    volume_24h: TokenAmount | None = Field(default=None, description="24-hour trading volume")
    fees_24h: TokenAmount | None = Field(default=None, description="24-hour fees collected")
    metadata: dict = Field(default_factory=dict, description="Freeform context data")

    def __eq__(self, other: object) -> bool:
        """Equality based on natural key (pool, timestamp)."""
        if not isinstance(other, Snapshot):
            return NotImplemented
        return self.pool == other.pool and self.timestamp == other.timestamp

    def __hash__(self) -> int:
        """Hash based on natural key (pool, timestamp)."""
        return hash((self.pool, self.timestamp))

    def __str__(self) -> str:
        return f"Snapshot({self.pool}, {self.timestamp.isoformat()})"
