"""Pool entity for Liquidity OS.

[WHY] Pool is the central aggregate root — everything references a pool.
      Must exist before collector, analytics, or agents.

[OWNERSHIP] Domain layer — aggregate root.

[DEPENDENTS] Allowed: ports.pool_repo, apps.collector, apps.analytics,
             apps.dashboard, agents.oracle, agents.navigator.
             Forbidden: infrastructure (database, redis, httpx).

[EXAMPLE]
    from shared.entities.pool import Pool
    from shared.enums import PoolStatus

    pool = Pool(
        address=PoolAddress("7Ytt..."),
        token_a=SOL,
        token_b=USDC,
        status=PoolStatus.ACTIVE,
    )
    assert pool.status == PoolStatus.ACTIVE
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from shared.enums import PoolStatus
from shared.identifiers import PoolAddress
from shared.value_objects.price import Price, SqrtPrice
from shared.value_objects.token import Token


class Pool(BaseModel):
    """[WHY] Represents a Meteora DLMM pool — the central entity in the system.

    [OWNERSHIP] Domain layer — aggregate root.

    [DEPENDENTS] Allowed: ports.pool_repo, ports.snapshot_repo,
                 apps.collector, apps.analytics, apps.dashboard,
                 agents.oracle, agents.navigator.
                 Forbidden: infrastructure packages.

    [EXAMPLE]
        pool = Pool(
            address=PoolAddress("7Ytt..."),
            token_a=SOL,
            token_b=USDC,
            status=PoolStatus.ACTIVE,
        )
        assert pool.is_active
    """

    model_config = {"frozen": True}

    address: PoolAddress = Field(..., description="Unique pool identifier")
    token_a: Token = Field(..., description="First token in the pair")
    token_b: Token = Field(..., description="Second token in the pair")
    status: PoolStatus = Field(default=PoolStatus.ACTIVE, description="Pool operational status")
    sqrt_price: SqrtPrice | None = Field(default=None, description="Current sqrt price (from latest snapshot)")
    price: Price | None = Field(default=None, description="Current price (from latest snapshot)")
    fee_rate: float = Field(default=0.003, description="Pool fee rate (e.g., 0.003 = 0.3%)")
    bin_step: int = Field(default=1, description="Price step between bins")

    @property
    def is_active(self) -> bool:
        """Check if pool is in active state."""
        return self.status == PoolStatus.ACTIVE

    @property
    def pair(self) -> str:
        """Human-readable pair notation (e.g., 'SOL/USDC')."""
        return f"{self.token_a.symbol}/{self.token_b.symbol}"

    def __str__(self) -> str:
        return f"Pool({self.pair}, {self.status.value})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Pool):
            return NotImplemented
        return self.address == other.address

    def __hash__(self) -> int:
        return hash(self.address)
