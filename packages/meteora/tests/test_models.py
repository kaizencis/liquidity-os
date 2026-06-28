"""DTO validation tests for Meteora models.

[WHY] Validates Pydantic DTO construction and error handling.
[OWNERSHIP] Infrastructure layer — model contract tests.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from meteora.models import (
    PoolConfigDTO,
    PoolResponseDTO,
    PositionPnLResponseDTO,
    TokenAmountDTO,
    TokenMetricsDTO,
    TokenPairWithTotalDTO,
    TotalUsdDTO,
)


def _valid_token_metrics() -> TokenMetricsDTO:
    """Create a valid TokenMetricsDTO for reuse."""
    return TokenMetricsDTO(address="So11111111111111111111111111111112", symbol="SOL", decimals=9)


def _valid_pool_config() -> PoolConfigDTO:
    """Create a valid PoolConfigDTO for reuse."""
    return PoolConfigDTO(bin_step=1, base_fee_pct=0.3)


def _valid_token_pair_with_total() -> TokenPairWithTotalDTO:
    """Create a valid TokenPairWithTotalDTO for reuse."""
    return TokenPairWithTotalDTO(
        tokenX=TokenAmountDTO(amount="1000000", usd="150.0"),
        tokenY=TokenAmountDTO(amount="500000", usd="50.0"),
        total=TotalUsdDTO(usd="200.0", sol="1.5"),
    )


# ── Test 1 ──────────────────────────────────────────────────────────
def test_pool_response_dto_valid() -> None:
    """Valid payload accepted with all fields."""
    dto = PoolResponseDTO(
        address="7YttLhHaiUDKvigCUXjCRWUboEGhFhtNTQHspR1x9Mx",
        name="SOL/USDC",
        token_x=_valid_token_metrics(),
        token_y=TokenMetricsDTO(
            address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            symbol="USDC",
            decimals=6,
        ),
        pool_config=_valid_pool_config(),
        current_price=150.0,
        dynamic_fee_pct=0.3,
        tvl=1_000_000.0,
        is_blacklisted=False,
        created_at=1234567890,
    )

    assert dto.address == "7YttLhHaiUDKvigCUXjCRWUboEGhFhtNTQHspR1x9Mx"
    assert dto.name == "SOL/USDC"
    assert dto.token_x.symbol == "SOL"
    assert dto.token_y.symbol == "USDC"
    assert dto.pool_config.bin_step == 1
    assert dto.current_price == 150.0
    assert dto.tvl == 1_000_000.0
    assert dto.is_blacklisted is False
    assert dto.created_at == 1234567890


# ── Test 2 ──────────────────────────────────────────────────────────
def test_pool_response_dto_missing_required() -> None:
    """Missing required field raises ValidationError."""
    with pytest.raises(ValidationError):
        PoolResponseDTO(
            # Missing 'address' and other required fields
            name="SOL/USDC",
        )


# ── Test 3 ──────────────────────────────────────────────────────────
def test_position_pnl_response_dto_valid() -> None:
    """Valid payload accepted."""
    dto = PositionPnLResponseDTO(
        positionAddress="AJ6zF9a8oC4e3x2bGh1DkLmNpQrS5tUvW8yZ7X4c6R1",
        minPrice="140.0",
        maxPrice="160.0",
        lowerBinId=100,
        upperBinId=200,
        isClosed=False,
        allTimeDeposits=_valid_token_pair_with_total(),
        allTimeFees=_valid_token_pair_with_total(),
    )

    assert dto.positionAddress == "AJ6zF9a8oC4e3x2bGh1DkLmNpQrS5tUvW8yZ7X4c6R1"
    assert dto.minPrice == "140.0"
    assert dto.maxPrice == "160.0"
    assert dto.lowerBinId == 100
    assert dto.upperBinId == 200
    assert dto.isClosed is False
    assert dto.allTimeDeposits.total.usd == "200.0"
    assert dto.allTimeFees.tokenX.amount == "1000000"


# ── Test 4 ──────────────────────────────────────────────────────────
def test_position_pnl_response_dto_missing_required() -> None:
    """Missing required field raises ValidationError."""
    with pytest.raises(ValidationError):
        PositionPnLResponseDTO(
            # Missing 'positionAddress' and other required fields
            isClosed=False,
        )


# ── Test 5 ──────────────────────────────────────────────────────────
def test_total_usd_dto_optional_sol() -> None:
    """TotalUsdDTO works with and without sol field."""
    # With sol
    with_sol = TotalUsdDTO(usd="500.0", sol="2.5")
    assert with_sol.usd == "500.0"
    assert with_sol.sol == "2.5"

    # Without sol (defaults to None)
    without_sol = TotalUsdDTO(usd="300.0")
    assert without_sol.usd == "300.0"
    assert without_sol.sol is None
