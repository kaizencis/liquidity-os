"""Tests for Meteora mappers — PoolMapper and PositionMapper.

[WHY] Validates DTO → domain entity translation is correct and complete.
[OWNERSHIP] Infrastructure layer — mapper tests.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from meteora.mappers import PoolMapper, PositionMapper
from meteora.models import (
    PoolConfigDTO,
    PoolResponseDTO,
    PositionPnLResponseDTO,
    TokenAmountDTO,
    TokenMetricsDTO,
    TokenPairWithTotalDTO,
    TotalUsdDTO,
)
from shared.enums import PoolStatus, PositionStatus
from shared.identifiers import PoolAddress, PositionAddress
from shared.value_objects.price import Price, PriceRange
from shared.value_objects.token import Token


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# Valid Solana base58 addresses (32-44 chars, matching [1-9A-HJ-NP-Za-km-z])
POOL_ADDR = "7YttLkHDoNj9wyDur5pM1ejNaAvT9X4eSTY"
SOL_ADDR = "So11111111111111111111111111111111111111112"
USDC_ADDR = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
POSITION_ADDR = "AJ6z3Zm9uGaNbJf8xLq3Tn7Wp9Yr2KbV4CdE"


def _make_pool_dto(
    *,
    address: str = POOL_ADDR,
    is_blacklisted: bool = False,
    base_fee_pct: float = 0.3,
    bin_step: int = 1,
    current_price: float = 150.0,
) -> PoolResponseDTO:
    """Build a PoolResponseDTO for testing."""
    return PoolResponseDTO(
        address=address,
        name="SOL/USDC",
        token_x=TokenMetricsDTO(address=SOL_ADDR, symbol="SOL", decimals=9),
        token_y=TokenMetricsDTO(address=USDC_ADDR, symbol="USDC", decimals=6),
        pool_config=PoolConfigDTO(bin_step=bin_step, base_fee_pct=base_fee_pct),
        current_price=current_price,
        dynamic_fee_pct=0.3,
        tvl=1_000_000.0,
        is_blacklisted=is_blacklisted,
        created_at=1_700_000_000,
    )


def _make_position_dto(
    *,
    position_address: str = POSITION_ADDR,
    min_price: str = "140.0",
    max_price: str = "160.0",
    is_closed: bool = False,
    fee_usd: str = "125.50",
) -> PositionPnLResponseDTO:
    """Build a PositionPnLResponseDTO for testing."""
    return PositionPnLResponseDTO(
        positionAddress=position_address,
        minPrice=min_price,
        maxPrice=max_price,
        lowerBinId=100,
        upperBinId=200,
        isClosed=is_closed,
        allTimeDeposits=TokenPairWithTotalDTO(
            tokenX=TokenAmountDTO(amount="1000000", usd="150.0"),
            tokenY=TokenAmountDTO(amount="500000", usd="50.0"),
            total=TotalUsdDTO(usd="200.0"),
        ),
        allTimeFees=TokenPairWithTotalDTO(
            tokenX=TokenAmountDTO(amount="50000", usd="75.0"),
            tokenY=TokenAmountDTO(amount="25000", usd=fee_usd),
            total=TotalUsdDTO(usd=fee_usd),
        ),
    )


def _make_pool() -> "Pool":
    """Build a Pool entity for position mapper tests."""
    from shared.entities.pool import Pool as PoolEntity

    return PoolMapper.to_domain(_make_pool_dto())


# ---------------------------------------------------------------------------
# PoolMapper tests
# ---------------------------------------------------------------------------


class TestPoolMapper:
    """Tests for PoolMapper.to_domain."""

    def test_pool_mapper_to_domain(self) -> None:
        """PoolResponseDTO → Pool, all fields mapped correctly."""
        dto = _make_pool_dto()
        pool = PoolMapper.to_domain(dto)

        # Address
        assert pool.address == PoolAddress(value=POOL_ADDR)

        # Tokens
        assert pool.token_a == Token(address=SOL_ADDR, symbol="SOL", decimals=9)
        assert pool.token_b == Token(address=USDC_ADDR, symbol="USDC", decimals=6)

        # Status
        assert pool.status == PoolStatus.ACTIVE

        # Price
        assert pool.price is not None
        assert pool.price.value == Decimal("150.0")
        assert pool.price.base_token.symbol == "USDC"
        assert pool.price.quote_token.symbol == "SOL"

        # Fee rate: 0.3 / 100 = 0.003
        assert pool.fee_rate == pytest.approx(0.003)
        assert pool.bin_step == 1

    def test_pool_mapper_sqrt_price_is_none(self) -> None:
        """sqrt_price is always None — API does not provide it."""
        dto = _make_pool_dto()
        pool = PoolMapper.to_domain(dto)

        assert pool.sqrt_price is None

    def test_pool_mapper_fee_rate_conversion(self) -> None:
        """DTO has 0.3 (percent) → Domain has 0.003."""
        dto = _make_pool_dto(base_fee_pct=0.3)
        pool = PoolMapper.to_domain(dto)

        assert pool.fee_rate == pytest.approx(0.003)

    def test_pool_mapper_is_blacklisted_true(self) -> None:
        """is_blacklisted=True → PoolStatus.PAUSED."""
        dto = _make_pool_dto(is_blacklisted=True)
        pool = PoolMapper.to_domain(dto)

        assert pool.status == PoolStatus.PAUSED

    def test_pool_mapper_is_blacklisted_false(self) -> None:
        """is_blacklisted=False → PoolStatus.ACTIVE."""
        dto = _make_pool_dto(is_blacklisted=False)
        pool = PoolMapper.to_domain(dto)

        assert pool.status == PoolStatus.ACTIVE


# ---------------------------------------------------------------------------
# PositionMapper tests
# ---------------------------------------------------------------------------


class TestPositionMapper:
    """Tests for PositionMapper.to_domain."""

    def test_position_mapper_to_domain(self) -> None:
        """PositionPnLResponseDTO + Pool → Position, all fields mapped."""
        pool = _make_pool()
        dto = _make_position_dto()
        position = PositionMapper.to_domain(dto, pool)

        # Address
        assert position.address == PositionAddress(value=POSITION_ADDR)

        # Pool address
        assert position.pool_address == pool.address

        # Status — isClosed=False → ACTIVE
        assert position.status == PositionStatus.ACTIVE

        # Side — always None (API v1.1)
        assert position.side is None

        # Liquidity — always None
        assert position.liquidity is None
        assert position.liquidity_distribution is None

        # Fee earned — 125.50
        assert position.fee_earned == pytest.approx(125.50)

        # Price range present
        assert position.price_range is not None

    def test_position_mapper_side_is_none(self) -> None:
        """side is always None — API does not provide side information."""
        pool = _make_pool()
        dto = _make_position_dto()
        position = PositionMapper.to_domain(dto, pool)

        assert position.side is None

    def test_position_mapper_price_range_from_pool_tokens(self) -> None:
        """PriceRange.low/high use pool.token_b (base) and pool.token_a (quote)."""
        pool = _make_pool()
        dto = _make_position_dto(min_price="140.0", max_price="160.0")
        position = PositionMapper.to_domain(dto, pool)

        assert position.price_range is not None
        pr = position.price_range

        # low price
        assert pr.low.value == Decimal("140.0")
        assert pr.low.base_token == pool.token_b  # USDC is base
        assert pr.low.quote_token == pool.token_a  # SOL is quote

        # high price
        assert pr.high.value == Decimal("160.0")
        assert pr.high.base_token == pool.token_b
        assert pr.high.quote_token == pool.token_a

    def test_position_mapper_price_range_none_when_no_prices(self) -> None:
        """When minPrice/maxPrice are None/empty, price_range=None."""
        pool = _make_pool()
        dto = _make_position_dto(min_price="", max_price="")
        position = PositionMapper.to_domain(dto, pool)

        assert position.price_range is None

    def test_position_mapper_fee_earned(self) -> None:
        """allTimeFees.total.usd mapped to float."""
        pool = _make_pool()
        dto = _make_position_dto(fee_usd="999.99")
        position = PositionMapper.to_domain(dto, pool)

        assert position.fee_earned == pytest.approx(999.99)
