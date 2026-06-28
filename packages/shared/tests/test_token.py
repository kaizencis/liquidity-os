"""Unit tests for shared.value_objects.token module."""

from __future__ import annotations

from decimal import Decimal

import pytest

from shared.exceptions import InvalidConfigurationError
from shared.value_objects.token import Token, TokenAmount


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
def one_sol(SOL: Token) -> TokenAmount:
    return TokenAmount(token=SOL, raw=1_000_000_000)  # 1.0 SOL


@pytest.fixture
def half_sol(SOL: Token) -> TokenAmount:
    return TokenAmount(token=SOL, raw=500_000_000)  # 0.5 SOL


@pytest.fixture
def one_usdc(USDC: Token) -> TokenAmount:
    return TokenAmount(token=USDC, raw=1_000_000)  # 1.0 USDC


# ---------------------------------------------------------------------------
# Token
# ---------------------------------------------------------------------------


class TestToken:
    """Tests for Token value object."""

    def test_create_token(self, SOL: Token) -> None:
        assert SOL.address == "So11111111111111111111111111111111111111112"
        assert SOL.symbol == "SOL"
        assert SOL.decimals == 9

    def test_immutable(self, SOL: Token) -> None:
        with pytest.raises(Exception):
            SOL.symbol = "ETH"  # type: ignore[misc]

    def test_string_representation(self, SOL: Token) -> None:
        assert str(SOL) == "SOL"

    def test_equality(self) -> None:
        a = Token(address="addr1", symbol="A", decimals=9)
        b = Token(address="addr1", symbol="A", decimals=9)
        assert a == b

    def test_inequality(self) -> None:
        a = Token(address="addr1", symbol="A", decimals=9)
        b = Token(address="addr2", symbol="A", decimals=9)
        assert a != b

    def test_hashable(self, SOL: Token) -> None:
        token_set = {SOL}
        assert SOL in token_set

    def test_decimals_validation(self) -> None:
        with pytest.raises(Exception):
            Token(address="addr", symbol="X", decimals=-1)
        with pytest.raises(Exception):
            Token(address="addr", symbol="X", decimals=19)


# ---------------------------------------------------------------------------
# TokenAmount — Creation
# ---------------------------------------------------------------------------


class TestTokenAmountCreation:
    """Tests for TokenAmount creation and basic properties."""

    def test_create_amount(self, SOL: Token) -> None:
        amt = TokenAmount(token=SOL, raw=1_000_000_000)
        assert amt.token == SOL
        assert amt.raw == 1_000_000_000

    def test_ui_amount(self, SOL: Token) -> None:
        amt = TokenAmount(token=SOL, raw=1_500_000_000)
        assert amt.ui_amount == Decimal("1.5")

    def test_ui_amount_zero(self, SOL: Token) -> None:
        amt = TokenAmount(token=SOL, raw=0)
        assert amt.ui_amount == Decimal("0")
        assert amt.is_zero

    def test_ui_amount_small(self, USDC: Token) -> None:
        amt = TokenAmount(token=USDC, raw=1)  # 0.000001 USDC
        assert amt.ui_amount == Decimal("0.000001")

    def test_is_zero_false(self, SOL: Token) -> None:
        amt = TokenAmount(token=SOL, raw=1)
        assert not amt.is_zero

    def test_immutable(self, SOL: Token) -> None:
        amt = TokenAmount(token=SOL, raw=100)
        with pytest.raises(Exception):
            amt.raw = 200  # type: ignore[misc]

    def test_negative_raw_rejected(self, SOL: Token) -> None:
        with pytest.raises(InvalidConfigurationError):
            TokenAmount(token=SOL, raw=-1)

    def test_string_representation(self, SOL: Token) -> None:
        amt = TokenAmount(token=SOL, raw=1_500_000_000)
        assert str(amt) == "1.5 SOL"


# ---------------------------------------------------------------------------
# TokenAmount — Addition
# ---------------------------------------------------------------------------


class TestTokenAmountAddition:
    """Tests for TokenAmount addition."""

    def test_add_same_token(self, one_sol: TokenAmount, half_sol: TokenAmount) -> None:
        result = one_sol + half_sol
        assert result.raw == 1_500_000_000
        assert result.ui_amount == Decimal("1.5")

    def test_add_different_tokens_raises(
        self, one_sol: TokenAmount, one_usdc: TokenAmount
    ) -> None:
        with pytest.raises(InvalidConfigurationError) as exc_info:
            _ = one_sol + one_usdc
        assert "different tokens" in str(exc_info.value)

    def test_add_zero(self, one_sol: TokenAmount, SOL: Token) -> None:
        zero = TokenAmount(token=SOL, raw=0)
        result = one_sol + zero
        assert result.raw == one_sol.raw


# ---------------------------------------------------------------------------
# TokenAmount — Subtraction
# ---------------------------------------------------------------------------


class TestTokenAmountSubtraction:
    """Tests for TokenAmount subtraction."""

    def test_subtract_same_token(
        self, one_sol: TokenAmount, half_sol: TokenAmount
    ) -> None:
        result = one_sol - half_sol
        assert result.raw == 500_000_000
        assert result.ui_amount == Decimal("0.5")

    def test_subtract_different_tokens_raises(
        self, one_sol: TokenAmount, one_usdc: TokenAmount
    ) -> None:
        with pytest.raises(InvalidConfigurationError):
            _ = one_sol - one_usdc

    def test_subtract_self_is_zero(self, one_sol: TokenAmount) -> None:
        result = one_sol - one_sol
        assert result.is_zero


# ---------------------------------------------------------------------------
# TokenAmount — Multiplication
# ---------------------------------------------------------------------------


class TestTokenAmountMultiplication:
    """Tests for TokenAmount multiplication."""

    def test_multiply_by_int(self, one_sol: TokenAmount) -> None:
        result = one_sol * 3
        assert result.raw == 3_000_000_000
        assert result.ui_amount == Decimal("3.0")

    def test_multiply_by_float(self, one_sol: TokenAmount) -> None:
        result = one_sol * 1.5
        assert result.raw == 1_500_000_000

    def test_multiply_by_decimal(self, one_sol: TokenAmount) -> None:
        result = one_sol * Decimal("2.5")
        assert result.raw == 2_500_000_000

    def test_rmul(self, one_sol: TokenAmount) -> None:
        result = 2 * one_sol
        assert result.raw == 2_000_000_000

    def test_multiply_by_token_amount_raises(self, one_sol: TokenAmount) -> None:
        with pytest.raises(InvalidConfigurationError):
            _ = one_sol * one_sol


# ---------------------------------------------------------------------------
# TokenAmount — Division
# ---------------------------------------------------------------------------


class TestTokenAmountDivision:
    """Tests for TokenAmount division."""

    def test_divide_by_int(self, one_sol: TokenAmount) -> None:
        result = one_sol / 2
        assert result.raw == 500_000_000
        assert result.ui_amount == Decimal("0.5")

    def test_divide_by_decimal(self, one_sol: TokenAmount) -> None:
        result = one_sol / Decimal("4")
        assert result.raw == 250_000_000

    def test_divide_by_zero_raises(self, one_sol: TokenAmount) -> None:
        with pytest.raises(InvalidConfigurationError) as exc_info:
            _ = one_sol / 0
        assert "divide by zero" in str(exc_info.value)

    def test_divide_by_token_amount_raises(self, one_sol: TokenAmount) -> None:
        with pytest.raises(InvalidConfigurationError):
            _ = one_sol / one_sol


# ---------------------------------------------------------------------------
# TokenAmount — Comparisons
# ---------------------------------------------------------------------------


class TestTokenAmountComparisons:
    """Tests for TokenAmount comparisons."""

    def test_eq_same(self, one_sol: TokenAmount) -> None:
        other = TokenAmount(token=one_sol.token, raw=1_000_000_000)
        assert one_sol == other

    def test_eq_different_value(self, one_sol: TokenAmount, half_sol: TokenAmount) -> None:
        assert one_sol != half_sol

    def test_eq_different_token(self, one_sol: TokenAmount, one_usdc: TokenAmount) -> None:
        # Different tokens are never equal, even if raw values match
        usdc_with_matching_raw = TokenAmount(
            token=one_usdc.token, raw=one_sol.raw
        )
        assert one_sol != usdc_with_matching_raw

    def test_lt(self, half_sol: TokenAmount, one_sol: TokenAmount) -> None:
        assert half_sol < one_sol

    def test_le(self, one_sol: TokenAmount) -> None:
        other = TokenAmount(token=one_sol.token, raw=1_000_000_000)
        assert one_sol <= other
        assert one_sol <= one_sol

    def test_gt(self, one_sol: TokenAmount, half_sol: TokenAmount) -> None:
        assert one_sol > half_sol

    def test_ge(self, one_sol: TokenAmount) -> None:
        other = TokenAmount(token=one_sol.token, raw=1_000_000_000)
        assert one_sol >= other

    def test_compare_different_tokens_raises(
        self, one_sol: TokenAmount, one_usdc: TokenAmount
    ) -> None:
        with pytest.raises(InvalidConfigurationError):
            _ = one_sol < one_usdc
        with pytest.raises(InvalidConfigurationError):
            _ = one_sol > one_usdc


# ---------------------------------------------------------------------------
# TokenAmount — Hashing
# ---------------------------------------------------------------------------


class TestTokenAmountHashing:
    """Tests for TokenAmount hashing."""

    def test_hashable(self, one_sol: TokenAmount) -> None:
        amount_set = {one_sol}
        assert one_sol in amount_set

    def test_same_value_same_hash(self, one_sol: TokenAmount) -> None:
        other = TokenAmount(token=one_sol.token, raw=1_000_000_000)
        assert hash(one_sol) == hash(other)

    def test_different_value_different_hash(self, one_sol: TokenAmount, half_sol: TokenAmount) -> None:
        assert hash(one_sol) != hash(half_sol)


# ---------------------------------------------------------------------------
# TokenAmount — Edge Cases
# ---------------------------------------------------------------------------


class TestTokenAmountEdgeCases:
    """Tests for TokenAmount edge cases."""

    def test_large_amount(self, SOL: Token) -> None:
        large = TokenAmount(token=SOL, raw=10**18)
        assert large.ui_amount == Decimal("1000000000.0")

    def test_one_lamport(self, SOL: Token) -> None:
        tiny = TokenAmount(token=SOL, raw=1)
        assert tiny.ui_amount == Decimal("0.000000001")

    def test_chained_operations(self, SOL: Token) -> None:
        amt = TokenAmount(token=SOL, raw=1_000_000_000)
        result = (amt * 2) - amt
        assert result.ui_amount == Decimal("1.0")
