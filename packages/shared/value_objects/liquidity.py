"""Liquidity and LiquidityDistribution value objects for Liquidity OS.

[WHY] Liquidity is the core resource in DeFi. The domain needs type-safe
      representations for individual liquidity amounts and their distribution
      across bins in Meteora DLMM.

[OWNERSHIP] Domain layer — immutable value objects.

[DEPENDENTS] Allowed: entities, value_objects.snapshot, ports, apps, agents.
             Forbidden: infrastructure (database, redis, httpx).

[EXAMPLE]
    from shared.value_objects.token import Token, TokenAmount
    from shared.value_objects.liquidity import Liquidity, LiquidityDistribution

    SOL = Token(address="So111...", symbol="SOL", decimals=9)
    amount = TokenAmount(token=SOL, raw=1_000_000_000)
    liq = Liquidity(amount=amount)

    dist = LiquidityDistribution(
        bin_liquidity={0: liq, 1: liq * 2, 2: liq * 3}
    )
    assert dist.total.amount.raw == 6_000_000_000
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from shared.exceptions import InvalidConfigurationError
from shared.value_objects.token import TokenAmount


# ---------------------------------------------------------------------------
# Liquidity
# ---------------------------------------------------------------------------


class Liquidity(BaseModel):
    """[WHY] Represents a liquidity amount in a specific token.

    [OWNERSHIP] Domain layer — immutable value object.

    [DEPENDENTS] Allowed: entities.pool, entities.position,
                 value_objects.snapshot, ports, apps.collector,
                 apps.analytics, apps.dashboard, agents.oracle,
                 agents.navigator.

    [EXAMPLE]
        SOL = Token(address="So111...", symbol="SOL", decimals=9)
        amount = TokenAmount(token=SOL, raw=1_000_000_000)
        liq = Liquidity(amount=amount)
        assert liq.amount.raw == 1_000_000_000
    """

    model_config = {"frozen": True}

    amount: TokenAmount = Field(..., description="Liquidity amount in token units")

    @property
    def is_zero(self) -> bool:
        """Check if this liquidity amount is zero."""
        return self.amount.is_zero

    def __add__(self, other: Liquidity) -> Liquidity:
        """Add two liquidity amounts (same token required)."""
        return Liquidity(amount=self.amount + other.amount)

    def __sub__(self, other: Liquidity) -> Liquidity:
        """Subtract two liquidity amounts (same token required)."""
        return Liquidity(amount=self.amount - other.amount)

    def __mul__(self, factor: int | float) -> Liquidity:
        """Multiply liquidity by a scalar factor."""
        return Liquidity(amount=self.amount * factor)

    def __rmul__(self, factor: int | float) -> Liquidity:
        """Support factor * liquidity syntax."""
        return self.__mul__(factor)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Liquidity):
            return NotImplemented
        return self.amount == other.amount

    def __lt__(self, other: Liquidity) -> bool:
        return self.amount < other.amount

    def __le__(self, other: Liquidity) -> bool:
        return self.amount <= other.amount

    def __gt__(self, other: Liquidity) -> bool:
        return self.amount > other.amount

    def __ge__(self, other: Liquidity) -> bool:
        return self.amount >= other.amount

    def __hash__(self) -> int:
        return hash((self.amount.token.address, self.amount.raw))

    def __str__(self) -> str:
        return f"{self.amount.ui_amount} {self.amount.token.symbol} liquidity"


# ---------------------------------------------------------------------------
# LiquidityDistribution
# ---------------------------------------------------------------------------


class BinLiquidity(BaseModel):
    """[WHY] Represents liquidity in a single DLMM bin.

    [OWNERSHIP] Domain layer — immutable value object.

    [DEPENDENTS] Allowed: value_objects.liquidity_distribution,
                 entities.pool, apps.collector, apps.analytics.

    [EXAMPLE]
        liq = Liquidity(amount=TokenAmount(token=SOL, raw=1_000_000_000))
        bin_liq = BinLiquidity(bin_id=42, liquidity=liq)
        assert bin_liq.bin_id == 42
    """

    model_config = {"frozen": True}

    bin_id: int = Field(..., description="Meteora DLMM bin identifier")
    liquidity: Liquidity = Field(..., description="Liquidity in this bin")

    def __hash__(self) -> int:
        return hash((self.bin_id, self.liquidity))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BinLiquidity):
            return NotImplemented
        return self.bin_id == other.bin_id and self.liquidity == other.liquidity


class LiquidityDistribution(BaseModel):
    """[WHY] Represents how liquidity is distributed across DLMM bins.

    [OWNERSHIP] Domain layer — immutable value object.

    [DEPENDENTS] Allowed: entities.pool, entities.position,
                 value_objects.snapshot, ports, apps.collector,
                 apps.analytics, agents.oracle, agents.navigator.

    [EXAMPLE]
        SOL = Token(address="So111...", symbol="SOL", decimals=9)
        liq1 = Liquidity(amount=TokenAmount(token=SOL, raw=1_000_000_000))
        liq2 = Liquidity(amount=TokenAmount(token=SOL, raw=2_000_000_000))

        dist = LiquidityDistribution(
            bins=[
                BinLiquidity(bin_id=0, liquidity=liq1),
                BinLiquidity(bin_id=1, liquidity=liq2),
            ]
        )
        assert len(dist) == 2
        assert dist.total.amount.raw == 3_000_000_000
    """

    model_config = {"frozen": True}

    bins: list[BinLiquidity] = Field(
        default_factory=list,
        description="List of bin liquidity entries",
    )

    @model_validator(mode="after")
    def validate_unique_bin_ids(self) -> LiquidityDistribution:
        bin_ids = [b.bin_id for b in self.bins]
        if len(bin_ids) != len(set(bin_ids)):
            raise InvalidConfigurationError(
                field="bins",
                value=f"{len(bin_ids)} bins",
                reason="duplicate bin_ids not allowed",
            )
        return self

    @property
    def total(self) -> Liquidity:
        """Sum of liquidity across all bins."""
        if not self.bins:
            raise InvalidConfigurationError(
                field="bins",
                value="empty",
                reason="cannot compute total of empty distribution",
            )
        result = self.bins[0].liquidity
        for bin_liq in self.bins[1:]:
            result = result + bin_liq.liquidity
        return result

    @property
    def bin_count(self) -> int:
        """Number of bins with liquidity."""
        return len(self.bins)

    @property
    def active_bin_ids(self) -> list[int]:
        """List of bin IDs that have liquidity, sorted."""
        return sorted(b.bin_id for b in self.bins if not b.liquidity.is_zero)

    def get_bin(self, bin_id: int) -> Liquidity | None:
        """Get liquidity for a specific bin, or None if not present."""
        for bin_liq in self.bins:
            if bin_liq.bin_id == bin_id:
                return bin_liq.liquidity
        return None

    def __len__(self) -> int:
        return len(self.bins)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, LiquidityDistribution):
            return NotImplemented
        if len(self.bins) != len(other.bins):
            return False
        self_map = {b.bin_id: b.liquidity for b in self.bins}
        other_map = {b.bin_id: b.liquidity for b in other.bins}
        return self_map == other_map

    def __hash__(self) -> int:
        return hash(tuple(sorted((b.bin_id, b.liquidity) for b in self.bins)))

    def __str__(self) -> str:
        if self.bin_count == 0:
            return f"LiquidityDistribution({self.bin_count} bins)"
        return f"LiquidityDistribution({self.bin_count} bins, total={self.total})"
