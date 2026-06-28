"""Price, PriceRange, and SqrtPrice value objects for Liquidity OS.

[WHY] Price representations are central to DeFi operations. The domain needs
      type-safe price values that carry token pair context, prevent invalid
      comparisons, and support both human-readable (Price) and raw AMM
      (SqrtPrice) representations.

[OWNERSHIP] Domain layer — immutable value objects.

[DEPENDENTS] Allowed: entities, value_objects.snapshot, ports, apps, agents.
             Forbidden: infrastructure (database, redis, httpx).

[EXAMPLE]
    from shared.value_objects.token import Token
    from shared.value_objects.price import Price, SqrtPrice

    SOL = Token(address="So111...", symbol="SOL", decimals=9)
    USDC = Token(address="EPjF...", symbol="USDC", decimals=6)

    price = Price(value=Decimal("142.5"), base_token=USDC, quote_token=SOL)
    print(price)  # "142.5 USDC/SOL"

    sqrt = SqrtPrice(raw=2345678901234567890, tick=42, bin_id=100)
    price_from_chain = sqrt.to_price(base_token=USDC, quote_token=SOL)
"""

from __future__ import annotations

from decimal import Decimal, getcontext
from typing import Final

from pydantic import BaseModel, Field, model_validator

from shared.exceptions import InvalidConfigurationError
from shared.value_objects.token import Token

# Q64.64 fixed-point conversion constant
_Q64_FACTOR: Final[int] = 2**32


# ---------------------------------------------------------------------------
# Price
# ---------------------------------------------------------------------------


class Price(BaseModel):
    """[WHY] Represents a price value with explicit token pair context.

    [OWNERSHIP] Domain layer — immutable value object.

    [DEPENDENTS] Allowed: entities, value_objects.snapshot, ports,
                 apps.collector, apps.analytics, apps.dashboard,
                 agents.oracle, agents.navigator.

    [EXAMPLE]
        SOL = Token(address="So111...", symbol="SOL", decimals=9)
        USDC = Token(address="EPjF...", symbol="USDC", decimals=6)

        price = Price(value=Decimal("142.5"), base_token=USDC, quote_token=SOL)
        assert price.value == Decimal("142.5")
        assert str(price) == "142.5 USDC/SOL"
    """

    model_config = {"frozen": True}

    value: Decimal = Field(..., description="Price value")
    base_token: Token = Field(..., description="Token being priced (numerator)")
    quote_token: Token = Field(..., description="Token used as unit (denominator)")

    @model_validator(mode="after")
    def validate_different_tokens(self) -> Price:
        if self.base_token.address == self.quote_token.address:
            raise InvalidConfigurationError(
                field="token_pair",
                value=f"{self.base_token.symbol}/{self.quote_token.symbol}",
                reason="base and quote tokens must be different",
            )
        return self

    @property
    def pair(self) -> str:
        """Human-readable pair notation (e.g., 'USDC/SOL')."""
        return f"{self.base_token.symbol}/{self.quote_token.symbol}"

    def __str__(self) -> str:
        return f"{self.value} {self.pair}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Price):
            return NotImplemented
        if self.base_token.address != other.base_token.address:
            return False
        if self.quote_token.address != other.quote_token.address:
            return False
        return self.value == other.value

    def __lt__(self, other: Price) -> bool:
        self._assert_same_pair(other, "compare")
        return self.value < other.value

    def __le__(self, other: Price) -> bool:
        self._assert_same_pair(other, "compare")
        return self.value <= other.value

    def __gt__(self, other: Price) -> bool:
        self._assert_same_pair(other, "compare")
        return self.value > other.value

    def __ge__(self, other: Price) -> bool:
        self._assert_same_pair(other, "compare")
        return self.value >= other.value

    def __hash__(self) -> int:
        return hash((
            self.base_token.address,
            self.quote_token.address,
            self.value,
        ))

    def _assert_same_pair(self, other: Price, operation: str) -> None:
        if self.base_token.address != other.base_token.address:
            raise InvalidConfigurationError(
                field="token_pair",
                value=f"{self.pair} vs {other.pair}",
                reason=f"cannot {operation} prices with different base tokens",
            )
        if self.quote_token.address != other.quote_token.address:
            raise InvalidConfigurationError(
                field="token_pair",
                value=f"{self.pair} vs {other.pair}",
                reason=f"cannot {operation} prices with different quote tokens",
            )


# ---------------------------------------------------------------------------
# PriceRange
# ---------------------------------------------------------------------------


class PriceRange(BaseModel):
    """[WHY] Represents a bounded price interval for a token pair.

    [OWNERSHIP] Domain layer — immutable value object.

    [DEPENDENTS] Allowed: entities, value_objects.snapshot, ports,
                 agents.oracle, agents.navigator.

    [EXAMPLE]
        low = Price(value=Decimal("140"), base_token=USDC, quote_token=SOL)
        high = Price(value=Decimal("150"), base_token=USDC, quote_token=SOL)
        rng = PriceRange(low=low, high=high)

        assert rng.contains(Price(value=Decimal("145"), base_token=USDC, quote_token=SOL))
        assert not rng.contains(Price(value=Decimal("155"), base_token=USDC, quote_token=SOL))
    """

    model_config = {"frozen": True}

    low: Price = Field(..., description="Lower bound of the price range")
    high: Price = Field(..., description="Upper bound of the price range")

    @model_validator(mode="after")
    def validate_range(self) -> PriceRange:
        if self.low.base_token.address != self.high.base_token.address:
            raise InvalidConfigurationError(
                field="token_pair",
                value=f"{self.low.pair} vs {self.high.pair}",
                reason="low and high must share the same base token",
            )
        if self.low.quote_token.address != self.high.quote_token.address:
            raise InvalidConfigurationError(
                field="token_pair",
                value=f"{self.low.pair} vs {self.high.pair}",
                reason="low and high must share the same quote token",
            )
        if self.low.value > self.high.value:
            raise InvalidConfigurationError(
                field="range",
                value=f"low={self.low.value}, high={self.high.value}",
                reason="low must be less than or equal to high",
            )
        return self

    def contains(self, price: Price) -> bool:
        """Check if a price falls within this range (inclusive)."""
        self._assert_same_pair(price, "check containment")
        return self.low.value <= price.value <= self.high.value

    @property
    def spread(self) -> Decimal:
        """Difference between high and low prices."""
        return self.high.value - self.low.value

    @property
    def midpoint(self) -> Decimal:
        """Arithmetic mean of low and high prices."""
        return (self.low.value + self.high.value) / 2

    def __str__(self) -> str:
        return f"[{self.low.value} — {self.high.value}] {self.low.pair}"

    def __hash__(self) -> int:
        return hash((self.low, self.high))

    def _assert_same_pair(self, price: Price, operation: str) -> None:
        if self.low.base_token.address != price.base_token.address:
            raise InvalidConfigurationError(
                field="token_pair",
                value=f"{self.low.pair} vs {price.pair}",
                reason=f"cannot {operation} with different base token",
            )
        if self.low.quote_token.address != price.quote_token.address:
            raise InvalidConfigurationError(
                field="token_pair",
                value=f"{self.low.pair} vs {price.pair}",
                reason=f"cannot {operation} with different quote token",
            )


# ---------------------------------------------------------------------------
# SqrtPrice
# ---------------------------------------------------------------------------


class SqrtPrice(BaseModel):
    """[WHY] Raw price representation in Meteora DLMM's Q64.64 fixed-point format.

    [OWNERSHIP] Domain layer — immutable value object.

    [DEPENDENTS] Allowed: entities.snapshot, ports.snapshot_repo,
                 apps.collector, apps.analytics.

    [PRECISION]
    - raw: stored as integer, no precision loss from on-chain source
    - to_price(): converts via (raw / 2^32)^2 → Decimal
    - Precision: ~18 decimal digits, sufficient for all DeFi calculations
    - Reconstructing SqrtPrice from Price is lossy (requires tick/bin_id)

    [EXAMPLE]
        sqrt = SqrtPrice(raw=2345678901234567890, tick=42, bin_id=100)
        price = sqrt.to_price(base_token=USDC, quote_token=SOL)
        assert price.base_token.symbol == "USDC"
    """

    model_config = {"frozen": True}

    raw: int = Field(
        ...,
        description="sqrtPriceX64 — Q64.64 fixed-point square root of price",
    )
    tick: int = Field(
        ...,
        description="Discrete price level index",
    )
    bin_id: int = Field(
        ...,
        description="Meteora DLMM bin identifier",
    )

    @model_validator(mode="after")
    def validate_raw_non_negative(self) -> SqrtPrice:
        if self.raw < 0:
            raise InvalidConfigurationError(
                field="raw",
                value=self.raw,
                reason="sqrtPriceX64 must be non-negative",
            )
        return self

    def to_price(self, base_token: Token, quote_token: Token) -> Price:
        """Convert raw sqrtPriceX64 to a human-readable Price.

        Formula: price = (raw / 2^32)^2
        This is the standard Meteora DLMM conversion.
        """
        decimal_raw = Decimal(self.raw)
        divisor = Decimal(_Q64_FACTOR)
        price_value = (decimal_raw / divisor) ** 2
        return Price(
            value=price_value,
            base_token=base_token,
            quote_token=quote_token,
        )

    def __str__(self) -> str:
        return f"SqrtPrice(raw={self.raw}, tick={self.tick}, bin={self.bin_id})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SqrtPrice):
            return NotImplemented
        return (
            self.raw == other.raw
            and self.tick == other.tick
            and self.bin_id == other.bin_id
        )

    def __hash__(self) -> int:
        return hash((self.raw, self.tick, self.bin_id))
