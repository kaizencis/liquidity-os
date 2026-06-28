"""Token and TokenAmount value objects for Liquidity OS.

[WHY] Tokens are the atomic units of value in DeFi. The domain needs a
      type-safe way to represent token identity (which token) and token
      amounts (how much) without mixing different tokens accidentally.

[OWNERSHIP] Domain layer — immutable value objects.

[DEPENDENTS] Allowed: entities, value_objects, ports, apps, agents.
             Forbidden: infrastructure (database, redis, httpx).

[EXAMPLE]
    from shared.value_objects.token import Token, TokenAmount

    SOL = Token(
        address="So11111111111111111111111111111111111111112",
        symbol="SOL",
        decimals=9,
    )

    amount = TokenAmount(token=SOL, raw=1_500_000_000)  # 1.5 SOL
    print(amount.ui_amount)  # 1.5

    double = amount * 2
    print(double.ui_amount)  # 3.0
"""

from __future__ import annotations

from decimal import Decimal, getcontext
from typing import Final

from pydantic import BaseModel, Field, model_validator

from shared.exceptions import InvalidConfigurationError

# Set high precision for financial calculations
getcontext().prec = 38

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAX_UI_AMOUNT: Final[Decimal] = Decimal("18446744073709551615")  # 2^64 - 1


# ---------------------------------------------------------------------------
# Token
# ---------------------------------------------------------------------------


class Token(BaseModel):
    """[WHY] Uniquely identifies a token on Solana — address, symbol, decimals.

    [OWNERSHIP] Domain layer — immutable value object.

    [DEPENDENTS] Allowed: entities.pool, entities.position, entities.snapshot,
                 value_objects.token_amount, apps.collector, apps.analytics,
                 apps.dashboard, agents.oracle, agents.navigator.

    [EXAMPLE]
        SOL = Token(
            address="So11111111111111111111111111111111111111112",
            symbol="SOL",
            decimals=9,
        )
        assert SOL.symbol == "SOL"
        assert SOL.decimals == 9
    """

    model_config = {"frozen": True}

    address: str = Field(..., description="On-chain token mint address")
    symbol: str = Field(..., description="Human-readable token symbol (e.g., 'SOL')")
    decimals: int = Field(..., ge=0, le=18, description="Number of decimal places")

    def __str__(self) -> str:
        return self.symbol


# ---------------------------------------------------------------------------
# TokenAmount
# ---------------------------------------------------------------------------


class TokenAmount(BaseModel):
    """[WHY] Represents a quantity of a specific Token with safe arithmetic.

    [OWNERSHIP] Domain layer — immutable value object.

    [DEPENDENTS] Allowed: entities.pool, entities.position, entities.snapshot,
                 value_objects.price, apps.collector, apps.analytics,
                 apps.dashboard, agents.oracle, agents.navigator.

    [EXAMPLE]
        SOL = Token(address="So11...", symbol="SOL", decimals=9)
        one_sol = TokenAmount(token=SOL, raw=1_000_000_000)
        two_sol = one_sol * 2

        assert one_sol.ui_amount == Decimal("1.0")
        assert two_sol.ui_amount == Decimal("2.0")

        # Mixing tokens raises an error
        USDC = Token(address="EPjF...", symbol="USDC", decimals=6)
        usdc_amount = TokenAmount(token=USDC, raw=1_000_000)
        try:
            one_sol + usdc_amount  # raises InvalidConfigurationError
        except InvalidConfigurationError as e:
            print(e)  # "Cannot add amounts of different tokens: SOL + USDC"
    """

    model_config = {"frozen": True}

    token: Token = Field(..., description="The token this amount refers to")
    raw: int = Field(..., description="Amount in smallest unit (lamports, base units)")

    @model_validator(mode="after")
    def validate_raw_range(self) -> TokenAmount:
        if self.raw < 0:
            raise InvalidConfigurationError(
                field="raw",
                value=self.raw,
                reason="token amount cannot be negative",
            )
        return self

    # -- Derived properties --------------------------------------------------

    @property
    def ui_amount(self) -> Decimal:
        """Human-readable amount (e.g., 1.5 for 1_500_000_000 lamports of SOL)."""
        divisor = Decimal(10) ** self.token.decimals
        return Decimal(self.raw) / divisor

    @property
    def is_zero(self) -> bool:
        """Check if this amount is zero."""
        return self.raw == 0

    # -- Same-token validation -----------------------------------------------

    def _assert_same_token(self, other: TokenAmount, operation: str) -> None:
        if self.token.address != other.token.address:
            raise InvalidConfigurationError(
                field="token",
                value=f"{self.token.symbol} + {other.token.symbol}",
                reason=f"cannot {operation} amounts of different tokens",
            )

    # -- Arithmetic ----------------------------------------------------------

    def __add__(self, other: TokenAmount) -> TokenAmount:
        """Add two amounts of the same token."""
        self._assert_same_token(other, "add")
        return TokenAmount(token=self.token, raw=self.raw + other.raw)

    def __sub__(self, other: TokenAmount) -> TokenAmount:
        """Subtract two amounts of the same token."""
        self._assert_same_token(other, "subtract")
        return TokenAmount(token=self.token, raw=self.raw - other.raw)

    def __mul__(self, factor: int | float | Decimal) -> TokenAmount:
        """Multiply amount by a scalar factor."""
        if isinstance(factor, TokenAmount):
            raise InvalidConfigurationError(
                field="factor",
                value=type(factor).__name__,
                reason="cannot multiply TokenAmount by TokenAmount",
            )
        result = int(Decimal(str(factor)) * self.raw)
        return TokenAmount(token=self.token, raw=result)

    def __rmul__(self, factor: int | float | Decimal) -> TokenAmount:
        """Support factor * amount syntax."""
        return self.__mul__(factor)

    def __truediv__(self, divisor: int | float | Decimal) -> TokenAmount:
        """Divide amount by a scalar divisor."""
        if isinstance(divisor, TokenAmount):
            raise InvalidConfigurationError(
                field="divisor",
                value=type(divisor).__name__,
                reason="cannot divide TokenAmount by TokenAmount",
            )
        if Decimal(str(divisor)) == 0:
            raise InvalidConfigurationError(
                field="divisor",
                value=0,
                reason="cannot divide by zero",
            )
        result = int(Decimal(self.raw) / Decimal(str(divisor)))
        return TokenAmount(token=self.token, raw=result)

    # -- Comparisons ---------------------------------------------------------

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TokenAmount):
            return NotImplemented
        if self.token.address != other.token.address:
            return False
        return self.raw == other.raw

    def __lt__(self, other: TokenAmount) -> bool:
        self._assert_same_token(other, "compare")
        return self.raw < other.raw

    def __le__(self, other: TokenAmount) -> bool:
        self._assert_same_token(other, "compare")
        return self.raw <= other.raw

    def __gt__(self, other: TokenAmount) -> bool:
        self._assert_same_token(other, "compare")
        return self.raw > other.raw

    def __ge__(self, other: TokenAmount) -> bool:
        self._assert_same_token(other, "compare")
        return self.raw >= other.raw

    def __hash__(self) -> int:
        return hash((self.token.address, self.raw))

    def __str__(self) -> str:
        return f"{self.ui_amount} {self.token.symbol}"
