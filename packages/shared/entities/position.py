"""Position entity for Liquidity OS.

[WHY] Represents a concentrated liquidity position on Meteora DLMM.
      Used by agents, dashboard, and telegram.

[OWNERSHIP] Domain layer — entity.

[DEPENDENTS] Allowed: ports.position_repo, apps.collector, apps.dashboard,
             agents.navigator.
             Forbidden: infrastructure (database, redis, httpx).

[EXAMPLE]
    from shared.entities.position import Position
    from shared.enums import PositionStatus, PositionSide

    position = Position(
        address=PositionAddress("AJ6z..."),
        pool_address=PoolAddress("7Ytt..."),
        status=PositionStatus.ACTIVE,
        side=PositionSide.BOTH,
    )
    assert position.is_active
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from shared.enums import PositionSide, PositionStatus
from shared.identifiers import PoolAddress, PositionAddress
from shared.value_objects.liquidity import Liquidity, LiquidityDistribution
from shared.value_objects.price import Price, PriceRange


class Position(BaseModel):
    """[WHY] Represents a liquidity position within a Meteora DLMM pool.

    [OWNERSHIP] Domain layer — entity.

    [DEPENDENTS] Allowed: ports.position_repo, ports.snapshot_repo,
                 apps.collector, apps.dashboard, agents.navigator.
                 Forbidden: infrastructure packages.

    [EXAMPLE]
        position = Position(
            address=PositionAddress("AJ6z..."),
            pool_address=PoolAddress("7Ytt..."),
            status=PositionStatus.ACTIVE,
            side=PositionSide.BOTH,
            price_range=PriceRange(low=low_price, high=high_price),
            liquidity=Liquidity(amount=TokenAmount(token=SOL, raw=1_000_000_000)),
        )
        assert position.is_active
        assert position.liquidity > Liquidity(amount=TokenAmount(token=SOL, raw=0))
    """

    model_config = {"frozen": True}

    address: PositionAddress = Field(..., description="Unique position identifier")
    pool_address: PoolAddress = Field(..., description="Parent pool identifier")
    status: PositionStatus = Field(default=PositionStatus.ACTIVE, description="Position lifecycle state")
    side: PositionSide | None = Field(default=None, description="Which side of liquidity curve (None = API unavailable)")
    price_range: PriceRange | None = Field(default=None, description="Concentrated price range")
    liquidity: Liquidity | None = Field(default=None, description="Total liquidity in position")
    liquidity_distribution: LiquidityDistribution | None = Field(
        default=None,
        description="Liquidity distribution across bins",
    )
    fee_earned: float = Field(default=0.0, description="Total fees earned by this position")

    @property
    def is_active(self) -> bool:
        """Check if position is in active state."""
        return self.status == PositionStatus.ACTIVE

    @property
    def has_liquidity(self) -> bool:
        """Check if position has any liquidity."""
        return self.liquidity is not None and not self.liquidity.is_zero

    def __str__(self) -> str:
        return f"Position({self.address}, {self.status.value})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Position):
            return NotImplemented
        return self.address == other.address

    def __hash__(self) -> int:
        return hash(self.address)
