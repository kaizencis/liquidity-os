"""Unit tests for shared.value_objects.liquidity module."""

from __future__ import annotations

import pytest

from shared.exceptions import InvalidConfigurationError
from shared.value_objects.liquidity import (
    BinLiquidity,
    Liquidity,
    LiquidityDistribution,
)
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
def one_sol_liq(SOL: Token) -> Liquidity:
    return Liquidity(amount=TokenAmount(token=SOL, raw=1_000_000_000))


@pytest.fixture
def two_sol_liq(SOL: Token) -> Liquidity:
    return Liquidity(amount=TokenAmount(token=SOL, raw=2_000_000_000))


@pytest.fixture
def one_usdc_liq(USDC: Token) -> Liquidity:
    return Liquidity(amount=TokenAmount(token=USDC, raw=1_000_000))


# ---------------------------------------------------------------------------
# Liquidity — Creation
# ---------------------------------------------------------------------------


class TestLiquidityCreation:
    """Tests for Liquidity creation and basic properties."""

    def test_create_liquidity(self, SOL: Token) -> None:
        amount = TokenAmount(token=SOL, raw=1_000_000_000)
        liq = Liquidity(amount=amount)
        assert liq.amount.raw == 1_000_000_000

    def test_immutable(self, one_sol_liq: Liquidity) -> None:
        with pytest.raises(Exception):
            one_sol_liq.amount = TokenAmount(  # type: ignore[misc]
                token=one_sol_liq.amount.token, raw=999
            )

    def test_is_zero_true(self, SOL: Token) -> None:
        liq = Liquidity(amount=TokenAmount(token=SOL, raw=0))
        assert liq.is_zero

    def test_is_zero_false(self, one_sol_liq: Liquidity) -> None:
        assert not one_sol_liq.is_zero

    def test_string_representation(self, one_sol_liq: Liquidity) -> None:
        assert str(one_sol_liq) == "1 SOL liquidity"


# ---------------------------------------------------------------------------
# Liquidity — Arithmetic
# ---------------------------------------------------------------------------


class TestLiquidityArithmetic:
    """Tests for Liquidity arithmetic operations."""

    def test_add_same_token(
        self, one_sol_liq: Liquidity, two_sol_liq: Liquidity
    ) -> None:
        result = one_sol_liq + two_sol_liq
        assert result.amount.raw == 3_000_000_000

    def test_add_different_tokens_raises(
        self, one_sol_liq: Liquidity, one_usdc_liq: Liquidity
    ) -> None:
        with pytest.raises(InvalidConfigurationError):
            _ = one_sol_liq + one_usdc_liq

    def test_subtract_same_token(
        self, two_sol_liq: Liquidity, one_sol_liq: Liquidity
    ) -> None:
        result = two_sol_liq - one_sol_liq
        assert result.amount.raw == 1_000_000_000

    def test_subtract_different_tokens_raises(
        self, one_sol_liq: Liquidity, one_usdc_liq: Liquidity
    ) -> None:
        with pytest.raises(InvalidConfigurationError):
            _ = one_sol_liq - one_usdc_liq

    def test_multiply_by_int(self, one_sol_liq: Liquidity) -> None:
        result = one_sol_liq * 3
        assert result.amount.raw == 3_000_000_000

    def test_rmul(self, one_sol_liq: Liquidity) -> None:
        result = 2 * one_sol_liq
        assert result.amount.raw == 2_000_000_000

    def test_add_zero(self, one_sol_liq: Liquidity, SOL: Token) -> None:
        zero = Liquidity(amount=TokenAmount(token=SOL, raw=0))
        result = one_sol_liq + zero
        assert result.amount.raw == one_sol_liq.amount.raw


# ---------------------------------------------------------------------------
# Liquidity — Equality and Comparisons
# ---------------------------------------------------------------------------


class TestLiquidityEquality:
    """Tests for Liquidity equality and ordering."""

    def test_equal(self, one_sol_liq: Liquidity) -> None:
        other = Liquidity(amount=TokenAmount(
            token=one_sol_liq.amount.token, raw=1_000_000_000
        ))
        assert one_sol_liq == other

    def test_not_equal_different_value(
        self, one_sol_liq: Liquidity, two_sol_liq: Liquidity
    ) -> None:
        assert one_sol_liq != two_sol_liq

    def test_not_equal_different_type(self, one_sol_liq: Liquidity) -> None:
        assert one_sol_liq != "1.0"

    def test_lt(self, one_sol_liq: Liquidity, two_sol_liq: Liquidity) -> None:
        assert one_sol_liq < two_sol_liq

    def test_le_equal(self, one_sol_liq: Liquidity) -> None:
        other = Liquidity(amount=TokenAmount(
            token=one_sol_liq.amount.token, raw=1_000_000_000
        ))
        assert one_sol_liq <= other

    def test_gt(self, two_sol_liq: Liquidity, one_sol_liq: Liquidity) -> None:
        assert two_sol_liq > one_sol_liq

    def test_ge_equal(self, one_sol_liq: Liquidity) -> None:
        other = Liquidity(amount=TokenAmount(
            token=one_sol_liq.amount.token, raw=1_000_000_000
        ))
        assert one_sol_liq >= other

    def test_hashable(self, one_sol_liq: Liquidity) -> None:
        liq_set = {one_sol_liq}
        assert one_sol_liq in liq_set


# ---------------------------------------------------------------------------
# BinLiquidity
# ---------------------------------------------------------------------------


class TestBinLiquidity:
    """Tests for BinLiquidity value object."""

    def test_create(self, one_sol_liq: Liquidity) -> None:
        bin_liq = BinLiquidity(bin_id=42, liquidity=one_sol_liq)
        assert bin_liq.bin_id == 42
        assert bin_liq.liquidity == one_sol_liq

    def test_immutable(self, one_sol_liq: Liquidity) -> None:
        bin_liq = BinLiquidity(bin_id=42, liquidity=one_sol_liq)
        with pytest.raises(Exception):
            bin_liq.bin_id = 99  # type: ignore[misc]

    def test_equal(self, one_sol_liq: Liquidity) -> None:
        a = BinLiquidity(bin_id=42, liquidity=one_sol_liq)
        b = BinLiquidity(bin_id=42, liquidity=one_sol_liq)
        assert a == b

    def test_not_equal_different_bin(self, one_sol_liq: Liquidity) -> None:
        a = BinLiquidity(bin_id=42, liquidity=one_sol_liq)
        b = BinLiquidity(bin_id=99, liquidity=one_sol_liq)
        assert a != b

    def test_not_equal_different_liquidity(
        self, one_sol_liq: Liquidity, two_sol_liq: Liquidity
    ) -> None:
        a = BinLiquidity(bin_id=42, liquidity=one_sol_liq)
        b = BinLiquidity(bin_id=42, liquidity=two_sol_liq)
        assert a != b

    def test_hashable(self, one_sol_liq: Liquidity) -> None:
        bin_liq = BinLiquidity(bin_id=42, liquidity=one_sol_liq)
        bin_set = {bin_liq}
        assert bin_liq in bin_set


# ---------------------------------------------------------------------------
# LiquidityDistribution — Creation
# ---------------------------------------------------------------------------


class TestLiquidityDistributionCreation:
    """Tests for LiquidityDistribution creation and validation."""

    def test_create_empty(self) -> None:
        dist = LiquidityDistribution(bins=[])
        assert len(dist) == 0
        assert dist.bin_count == 0

    def test_create_with_bins(
        self, one_sol_liq: Liquidity, two_sol_liq: Liquidity
    ) -> None:
        dist = LiquidityDistribution(
            bins=[
                BinLiquidity(bin_id=0, liquidity=one_sol_liq),
                BinLiquidity(bin_id=1, liquidity=two_sol_liq),
            ]
        )
        assert len(dist) == 2
        assert dist.bin_count == 2

    def test_duplicate_bin_ids_rejected(self, one_sol_liq: Liquidity) -> None:
        with pytest.raises(InvalidConfigurationError) as exc_info:
            LiquidityDistribution(
                bins=[
                    BinLiquidity(bin_id=0, liquidity=one_sol_liq),
                    BinLiquidity(bin_id=0, liquidity=one_sol_liq),
                ]
            )
        assert "duplicate" in str(exc_info.value).lower()

    def test_immutable(self, one_sol_liq: Liquidity) -> None:
        dist = LiquidityDistribution(
            bins=[BinLiquidity(bin_id=0, liquidity=one_sol_liq)]
        )
        with pytest.raises(Exception):
            dist.bins = []  # type: ignore[misc]


# ---------------------------------------------------------------------------
# LiquidityDistribution — Total
# ---------------------------------------------------------------------------


class TestLiquidityDistributionTotal:
    """Tests for LiquidityDistribution.total property."""

    def test_total_single_bin(self, one_sol_liq: Liquidity) -> None:
        dist = LiquidityDistribution(
            bins=[BinLiquidity(bin_id=0, liquidity=one_sol_liq)]
        )
        assert dist.total.amount.raw == 1_000_000_000

    def test_total_multiple_bins(
        self, one_sol_liq: Liquidity, two_sol_liq: Liquidity
    ) -> None:
        dist = LiquidityDistribution(
            bins=[
                BinLiquidity(bin_id=0, liquidity=one_sol_liq),
                BinLiquidity(bin_id=1, liquidity=two_sol_liq),
            ]
        )
        assert dist.total.amount.raw == 3_000_000_000

    def test_total_empty_raises(self) -> None:
        dist = LiquidityDistribution(bins=[])
        with pytest.raises(InvalidConfigurationError) as exc_info:
            _ = dist.total
        assert "empty" in str(exc_info.value).lower()

    def test_total_mixed_tokens_raises(
        self, one_sol_liq: Liquidity, one_usdc_liq: Liquidity
    ) -> None:
        dist = LiquidityDistribution(
            bins=[
                BinLiquidity(bin_id=0, liquidity=one_sol_liq),
                BinLiquidity(bin_id=1, liquidity=one_usdc_liq),
            ]
        )
        with pytest.raises(InvalidConfigurationError):
            _ = dist.total


# ---------------------------------------------------------------------------
# LiquidityDistribution — Other Properties
# ---------------------------------------------------------------------------


class TestLiquidityDistributionProperties:
    """Tests for LiquidityDistribution properties and methods."""

    @pytest.fixture
    def mixed_dist(
        self, SOL: Token, one_sol_liq: Liquidity, two_sol_liq: Liquidity
    ) -> LiquidityDistribution:
        zero_liq = Liquidity(amount=TokenAmount(token=SOL, raw=0))
        return LiquidityDistribution(
            bins=[
                BinLiquidity(bin_id=10, liquidity=one_sol_liq),
                BinLiquidity(bin_id=20, liquidity=two_sol_liq),
                BinLiquidity(bin_id=30, liquidity=zero_liq),
            ]
        )

    def test_bin_count(self, mixed_dist: LiquidityDistribution) -> None:
        assert mixed_dist.bin_count == 3

    def test_active_bin_ids(self, mixed_dist: LiquidityDistribution) -> None:
        # bin_id=30 has zero liquidity, should be excluded
        assert mixed_dist.active_bin_ids == [10, 20]

    def test_active_bin_ids_sorted(self, mixed_dist: LiquidityDistribution) -> None:
        assert mixed_dist.active_bin_ids == sorted(mixed_dist.active_bin_ids)

    def test_get_bin_found(self, mixed_dist: LiquidityDistribution) -> None:
        liq = mixed_dist.get_bin(10)
        assert liq is not None
        assert liq.amount.raw == 1_000_000_000

    def test_get_bin_not_found(self, mixed_dist: LiquidityDistribution) -> None:
        liq = mixed_dist.get_bin(999)
        assert liq is None


# ---------------------------------------------------------------------------
# LiquidityDistribution — Equality and Hashing
# ---------------------------------------------------------------------------


class TestLiquidityDistributionEquality:
    """Tests for LiquidityDistribution equality and hashing."""

    def test_equal_same_bins(self, one_sol_liq: Liquidity) -> None:
        a = LiquidityDistribution(
            bins=[BinLiquidity(bin_id=0, liquidity=one_sol_liq)]
        )
        b = LiquidityDistribution(
            bins=[BinLiquidity(bin_id=0, liquidity=one_sol_liq)]
        )
        assert a == b

    def test_not_equal_different_count(
        self, one_sol_liq: Liquidity, two_sol_liq: Liquidity
    ) -> None:
        a = LiquidityDistribution(
            bins=[BinLiquidity(bin_id=0, liquidity=one_sol_liq)]
        )
        b = LiquidityDistribution(
            bins=[
                BinLiquidity(bin_id=0, liquidity=one_sol_liq),
                BinLiquidity(bin_id=1, liquidity=two_sol_liq),
            ]
        )
        assert a != b

    def test_not_equal_different_bin_ids(self, one_sol_liq: Liquidity) -> None:
        a = LiquidityDistribution(
            bins=[BinLiquidity(bin_id=0, liquidity=one_sol_liq)]
        )
        b = LiquidityDistribution(
            bins=[BinLiquidity(bin_id=1, liquidity=one_sol_liq)]
        )
        assert a != b

    def test_equal_order_independent(self, one_sol_liq: Liquidity, two_sol_liq: Liquidity) -> None:
        a = LiquidityDistribution(
            bins=[
                BinLiquidity(bin_id=0, liquidity=one_sol_liq),
                BinLiquidity(bin_id=1, liquidity=two_sol_liq),
            ]
        )
        b = LiquidityDistribution(
            bins=[
                BinLiquidity(bin_id=1, liquidity=two_sol_liq),
                BinLiquidity(bin_id=0, liquidity=one_sol_liq),
            ]
        )
        assert a == b

    def test_hashable(self, one_sol_liq: Liquidity) -> None:
        dist = LiquidityDistribution(
            bins=[BinLiquidity(bin_id=0, liquidity=one_sol_liq)]
        )
        dist_set = {dist}
        assert dist in dist_set


# ---------------------------------------------------------------------------
# LiquidityDistribution — String Representation
# ---------------------------------------------------------------------------


class TestLiquidityDistributionString:
    """Tests for LiquidityDistribution string representation."""

    def test_str_empty(self) -> None:
        dist = LiquidityDistribution(bins=[])
        assert str(dist) == "LiquidityDistribution(0 bins)"

    def test_str_with_bins(self, one_sol_liq: Liquidity) -> None:
        dist = LiquidityDistribution(
            bins=[BinLiquidity(bin_id=0, liquidity=one_sol_liq)]
        )
        result = str(dist)
        assert "1 bins" in result
        assert "total=" in result
