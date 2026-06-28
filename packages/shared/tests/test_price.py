"""Unit tests for shared.value_objects.price module."""

from __future__ import annotations

from decimal import Decimal

import pytest

from shared.exceptions import InvalidConfigurationError
from shared.value_objects.price import Price, PriceRange, SqrtPrice
from shared.value_objects.token import Token

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
def BTC() -> Token:
    return Token(
        address="9n4nbM75f5Ui33ZbPYXn59EwSgE8CGsHtAeTH5YFeJ9E",
        symbol="BTC",
        decimals=8,
    )


@pytest.fixture
def sol_usdc_price(SOL: Token, USDC: Token) -> Price:
    return Price(value=Decimal("142.5"), base_token=USDC, quote_token=SOL)


@pytest.fixture
def sol_usdc_price_2(SOL: Token, USDC: Token) -> Price:
    return Price(value=Decimal("150.0"), base_token=USDC, quote_token=SOL)


# ---------------------------------------------------------------------------
# Price — Creation
# ---------------------------------------------------------------------------


class TestPriceCreation:
    """Tests for Price creation and basic properties."""

    def test_create_price(self, SOL: Token, USDC: Token) -> None:
        price = Price(value=Decimal("142.5"), base_token=USDC, quote_token=SOL)
        assert price.value == Decimal("142.5")
        assert price.base_token == USDC
        assert price.quote_token == SOL

    def test_immutable(self, sol_usdc_price: Price) -> None:
        with pytest.raises(Exception):
            sol_usdc_price.value = Decimal("200")  # type: ignore[misc]

    def test_different_tokens_rejected(self, SOL: Token) -> None:
        with pytest.raises(InvalidConfigurationError) as exc_info:
            Price(value=Decimal("1"), base_token=SOL, quote_token=SOL)
        assert "different" in str(exc_info.value).lower()

    def test_pair_property(self, sol_usdc_price: Price) -> None:
        assert sol_usdc_price.pair == "USDC/SOL"

    def test_string_representation(self, sol_usdc_price: Price) -> None:
        assert str(sol_usdc_price) == "142.5 USDC/SOL"


# ---------------------------------------------------------------------------
# Price — Equality
# ---------------------------------------------------------------------------


class TestPriceEquality:
    """Tests for Price equality semantics."""

    def test_equal_same_value(self, SOL: Token, USDC: Token) -> None:
        a = Price(value=Decimal("142.5"), base_token=USDC, quote_token=SOL)
        b = Price(value=Decimal("142.5"), base_token=USDC, quote_token=SOL)
        assert a == b

    def test_not_equal_different_value(self, sol_usdc_price: Price, sol_usdc_price_2: Price) -> None:
        assert sol_usdc_price != sol_usdc_price_2

    def test_not_equal_different_base(self, SOL: Token, USDC: Token, BTC: Token) -> None:
        a = Price(value=Decimal("142.5"), base_token=USDC, quote_token=SOL)
        b = Price(value=Decimal("142.5"), base_token=BTC, quote_token=SOL)
        assert a != b

    def test_not_equal_different_quote(self, SOL: Token, USDC: Token, BTC: Token) -> None:
        a = Price(value=Decimal("142.5"), base_token=USDC, quote_token=SOL)
        b = Price(value=Decimal("142.5"), base_token=USDC, quote_token=BTC)
        assert a != b

    def test_not_equal_different_type(self, sol_usdc_price: Price) -> None:
        assert sol_usdc_price != "142.5"


# ---------------------------------------------------------------------------
# Price — Comparisons
# ---------------------------------------------------------------------------


class TestPriceComparisons:
    """Tests for Price ordering operators."""

    def test_lt(self, sol_usdc_price: Price, sol_usdc_price_2: Price) -> None:
        assert sol_usdc_price < sol_usdc_price_2

    def test_le_equal(self, sol_usdc_price: Price) -> None:
        other = Price(value=Decimal("142.5"), base_token=sol_usdc_price.base_token,
                      quote_token=sol_usdc_price.quote_token)
        assert sol_usdc_price <= other

    def test_le_less(self, sol_usdc_price: Price, sol_usdc_price_2: Price) -> None:
        assert sol_usdc_price <= sol_usdc_price_2

    def test_gt(self, sol_usdc_price_2: Price, sol_usdc_price: Price) -> None:
        assert sol_usdc_price_2 > sol_usdc_price

    def test_ge_equal(self, sol_usdc_price: Price) -> None:
        other = Price(value=Decimal("142.5"), base_token=sol_usdc_price.base_token,
                      quote_token=sol_usdc_price.quote_token)
        assert sol_usdc_price >= other

    def test_compare_different_base_raises(self, SOL: Token, USDC: Token, BTC: Token) -> None:
        a = Price(value=Decimal("142.5"), base_token=USDC, quote_token=SOL)
        b = Price(value=Decimal("142.5"), base_token=BTC, quote_token=SOL)
        with pytest.raises(InvalidConfigurationError):
            _ = a < b

    def test_compare_different_quote_raises(self, SOL: Token, USDC: Token, BTC: Token) -> None:
        a = Price(value=Decimal("142.5"), base_token=USDC, quote_token=SOL)
        b = Price(value=Decimal("142.5"), base_token=USDC, quote_token=BTC)
        with pytest.raises(InvalidConfigurationError):
            _ = a > b


# ---------------------------------------------------------------------------
# Price — Hashing
# ---------------------------------------------------------------------------


class TestPriceHashing:
    """Tests for Price hashing."""

    def test_hashable(self, sol_usdc_price: Price) -> None:
        price_set = {sol_usdc_price}
        assert sol_usdc_price in price_set

    def test_same_value_same_hash(self, SOL: Token, USDC: Token) -> None:
        a = Price(value=Decimal("142.5"), base_token=USDC, quote_token=SOL)
        b = Price(value=Decimal("142.5"), base_token=USDC, quote_token=SOL)
        assert hash(a) == hash(b)

    def test_different_value_different_hash(self, sol_usdc_price: Price, sol_usdc_price_2: Price) -> None:
        assert hash(sol_usdc_price) != hash(sol_usdc_price_2)


# ---------------------------------------------------------------------------
# PriceRange — Creation
# ---------------------------------------------------------------------------


class TestPriceRangeCreation:
    """Tests for PriceRange creation and validation."""

    def test_create_range(self, SOL: Token, USDC: Token) -> None:
        low = Price(value=Decimal("140"), base_token=USDC, quote_token=SOL)
        high = Price(value=Decimal("150"), base_token=USDC, quote_token=SOL)
        rng = PriceRange(low=low, high=high)
        assert rng.low.value == Decimal("140")
        assert rng.high.value == Decimal("150")

    def test_equal_low_high_allowed(self, SOL: Token, USDC: Token) -> None:
        price = Price(value=Decimal("142.5"), base_token=USDC, quote_token=SOL)
        rng = PriceRange(low=price, high=price)
        assert rng.low.value == rng.high.value

    def test_low_greater_than_high_rejected(self, SOL: Token, USDC: Token) -> None:
        low = Price(value=Decimal("150"), base_token=USDC, quote_token=SOL)
        high = Price(value=Decimal("140"), base_token=USDC, quote_token=SOL)
        with pytest.raises(InvalidConfigurationError) as exc_info:
            PriceRange(low=low, high=high)
        assert "low must be less than or equal to high" in str(exc_info.value)

    def test_different_base_tokens_rejected(self, SOL: Token, USDC: Token, BTC: Token) -> None:
        low = Price(value=Decimal("140"), base_token=USDC, quote_token=SOL)
        high = Price(value=Decimal("150"), base_token=BTC, quote_token=SOL)
        with pytest.raises(InvalidConfigurationError) as exc_info:
            PriceRange(low=low, high=high)
        assert "base token" in str(exc_info.value).lower()

    def test_different_quote_tokens_rejected(self, SOL: Token, USDC: Token, BTC: Token) -> None:
        low = Price(value=Decimal("140"), base_token=USDC, quote_token=SOL)
        high = Price(value=Decimal("150"), base_token=USDC, quote_token=BTC)
        with pytest.raises(InvalidConfigurationError) as exc_info:
            PriceRange(low=low, high=high)
        assert "quote token" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# PriceRange — Behavior
# ---------------------------------------------------------------------------


class TestPriceRangeBehavior:
    """Tests for PriceRange methods."""

    @pytest.fixture
    def range_140_150(self, SOL: Token, USDC: Token) -> PriceRange:
        low = Price(value=Decimal("140"), base_token=USDC, quote_token=SOL)
        high = Price(value=Decimal("150"), base_token=USDC, quote_token=SOL)
        return PriceRange(low=low, high=high)

    def test_contains_inside(self, range_140_150: PriceRange, SOL: Token, USDC: Token) -> None:
        price = Price(value=Decimal("145"), base_token=USDC, quote_token=SOL)
        assert range_140_150.contains(price)

    def test_contains_at_boundary_low(self, range_140_150: PriceRange, SOL: Token, USDC: Token) -> None:
        price = Price(value=Decimal("140"), base_token=USDC, quote_token=SOL)
        assert range_140_150.contains(price)

    def test_contains_at_boundary_high(self, range_140_150: PriceRange, SOL: Token, USDC: Token) -> None:
        price = Price(value=Decimal("150"), base_token=USDC, quote_token=SOL)
        assert range_140_150.contains(price)

    def test_not_contains_outside(self, range_140_150: PriceRange, SOL: Token, USDC: Token) -> None:
        price = Price(value=Decimal("155"), base_token=USDC, quote_token=SOL)
        assert not range_140_150.contains(price)

    def test_not_contains_different_pair(self, range_140_150: PriceRange, SOL: Token, BTC: Token) -> None:
        price = Price(value=Decimal("145"), base_token=BTC, quote_token=SOL)
        with pytest.raises(InvalidConfigurationError):
            range_140_150.contains(price)

    def test_spread(self, range_140_150: PriceRange) -> None:
        assert range_140_150.spread == Decimal("10")

    def test_midpoint(self, range_140_150: PriceRange) -> None:
        assert range_140_150.midpoint == Decimal("145")

    def test_string_representation(self, range_140_150: PriceRange) -> None:
        assert str(range_140_150) == "[140 — 150] USDC/SOL"


# ---------------------------------------------------------------------------
# SqrtPrice — Creation
# ---------------------------------------------------------------------------


class TestSqrtPriceCreation:
    """Tests for SqrtPrice creation and validation."""

    def test_create_sqrt_price(self) -> None:
        sqrt = SqrtPrice(raw=2345678901234567890, tick=42, bin_id=100)
        assert sqrt.raw == 2345678901234567890
        assert sqrt.tick == 42
        assert sqrt.bin_id == 100

    def test_immutable(self) -> None:
        sqrt = SqrtPrice(raw=1000, tick=1, bin_id=1)
        with pytest.raises(Exception):
            sqrt.raw = 2000  # type: ignore[misc]

    def test_negative_raw_rejected(self) -> None:
        with pytest.raises(InvalidConfigurationError) as exc_info:
            SqrtPrice(raw=-1, tick=0, bin_id=0)
        assert "non-negative" in str(exc_info.value)

    def test_zero_raw_allowed(self) -> None:
        sqrt = SqrtPrice(raw=0, tick=0, bin_id=0)
        assert sqrt.raw == 0

    def test_string_representation(self) -> None:
        sqrt = SqrtPrice(raw=123456789, tick=42, bin_id=100)
        assert str(sqrt) == "SqrtPrice(raw=123456789, tick=42, bin=100)"


# ---------------------------------------------------------------------------
# SqrtPrice — to_price Conversion
# ---------------------------------------------------------------------------


class TestSqrtPriceToPrice:
    """Tests for SqrtPrice.to_price conversion."""

    def test_conversion_basic(self, SOL: Token, USDC: Token) -> None:
        sqrt = SqrtPrice(raw=79228162514264337593543950336, tick=0, bin_id=0)
        price = sqrt.to_price(base_token=USDC, quote_token=SOL)
        # raw / 2^32 = ~18446744073.709551616
        # (raw / 2^32)^2 = ~340282366920938463463374607431768211456
        # This is a very large number — represents raw price without decimal scaling
        assert price.base_token == USDC
        assert price.quote_token == SOL
        assert isinstance(price.value, Decimal)

    def test_conversion_preserves_precision(self, SOL: Token, USDC: Token) -> None:
        # Use a known sqrt_price that maps to a clean price
        # sqrt(142.5) ≈ 11.9373..., so raw = 11.9373... * 2^32 ≈ 51234567890
        raw = 51234567890
        sqrt = SqrtPrice(raw=raw, tick=42, bin_id=100)
        price = sqrt.to_price(base_token=USDC, quote_token=SOL)
        # Verify no precision loss in conversion
        expected = (Decimal(raw) / Decimal(2**32)) ** 2
        assert price.value == expected

    def test_zero_sqrt_price(self, SOL: Token, USDC: Token) -> None:
        sqrt = SqrtPrice(raw=0, tick=-999999, bin_id=0)
        price = sqrt.to_price(base_token=USDC, quote_token=SOL)
        assert price.value == Decimal("0")

    def test_large_sqrt_price(self, SOL: Token, USDC: Token) -> None:
        # Max realistic sqrtPriceX64 for high-price tokens
        sqrt = SqrtPrice(raw=2**64 - 1, tick=1000, bin_id=9999)
        price = sqrt.to_price(base_token=USDC, quote_token=SOL)
        assert price.value > 0
        assert isinstance(price.value, Decimal)


# ---------------------------------------------------------------------------
# SqrtPrice — Equality and Hashing
# ---------------------------------------------------------------------------


class TestSqrtPriceEquality:
    """Tests for SqrtPrice equality and hashing."""

    def test_equal(self) -> None:
        a = SqrtPrice(raw=1000, tick=1, bin_id=1)
        b = SqrtPrice(raw=1000, tick=1, bin_id=1)
        assert a == b

    def test_not_equal_different_raw(self) -> None:
        a = SqrtPrice(raw=1000, tick=1, bin_id=1)
        b = SqrtPrice(raw=2000, tick=1, bin_id=1)
        assert a != b

    def test_not_equal_different_tick(self) -> None:
        a = SqrtPrice(raw=1000, tick=1, bin_id=1)
        b = SqrtPrice(raw=1000, tick=2, bin_id=1)
        assert a != b

    def test_not_equal_different_bin(self) -> None:
        a = SqrtPrice(raw=1000, tick=1, bin_id=1)
        b = SqrtPrice(raw=1000, tick=1, bin_id=2)
        assert a != b

    def test_hashable(self) -> None:
        sqrt = SqrtPrice(raw=1000, tick=1, bin_id=1)
        sqrt_set = {sqrt}
        assert sqrt in sqrt_set

    def test_same_values_same_hash(self) -> None:
        a = SqrtPrice(raw=1000, tick=1, bin_id=1)
        b = SqrtPrice(raw=1000, tick=1, bin_id=1)
        assert hash(a) == hash(b)
