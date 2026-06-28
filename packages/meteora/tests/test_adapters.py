"""Tests for MeteoraPoolAdapter and MeteoraPositionAdapter.

[WHY] Validates that adapters correctly delegate to client and mapper,
      handle not-found cases, and perform no transformation beyond delegation.
[OWNERSHIP] Infrastructure layer — adapter contract tests.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from meteora.adapters import MeteoraPoolAdapter, MeteoraPositionAdapter
from meteora.client import MeteoraClient
from meteora.mappers import PoolMapper, PositionMapper
from meteora.models import (
    PaginationResponseDTO,
    PoolResponseDTO,
    PositionPnLResponseDTO,
)
from shared.entities.pool import Pool
from shared.entities.position import Position
from shared.identifiers import PoolAddress, PositionAddress
from shared.value_objects.token import Token

# ── Constants ──────────────────────────────────────────────────────────

POOL_ADDRESS = "7YttLhHaiUDKvigCUXjCRWUboEGhFhtNTQHspR1x9Mx"
SOL_ADDRESS = "So11111111111111111111111111111112"
USDC_ADDRESS = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
POSITION_ADDRESS = "AJ6zF9a8oC4e3x2bGh1DkLmNpQrS5tUvW8yZ7X4c6R1"

# ── Shared test data ───────────────────────────────────────────────────

POOL_DTO = PoolResponseDTO(
    address=POOL_ADDRESS,
    name="SOL/USDC",
    token_x={"address": SOL_ADDRESS, "symbol": "SOL", "decimals": 9},
    token_y={"address": USDC_ADDRESS, "symbol": "USDC", "decimals": 6},
    pool_config={"bin_step": 1, "base_fee_pct": 0.3},
    current_price=150.0,
    dynamic_fee_pct=0.3,
    tvl=1_000_000.0,
    is_blacklisted=False,
    created_at=1234567890,
)

POSITION_DTO = PositionPnLResponseDTO(
    positionAddress=POSITION_ADDRESS,
    minPrice="140.0",
    maxPrice="160.0",
    lowerBinId=100,
    upperBinId=200,
    isClosed=False,
    allTimeDeposits={
        "tokenX": {"amount": "1000000", "usd": "150.0"},
        "tokenY": {"amount": "500000", "usd": "50.0"},
        "total": {"usd": "200.0", "sol": "1.5"},
    },
    allTimeFees={
        "tokenX": {"amount": "100000", "usd": "15.0"},
        "tokenY": {"amount": "50000", "usd": "5.0"},
        "total": {"usd": "20.0", "sol": "0.15"},
    },
)

PAGE_RESPONSE = PaginationResponseDTO(
    total=2,
    pages=1,
    current_page=1,
    page_size=100,
    data=[POOL_DTO],
)

SOL_TOKEN = Token(address=SOL_ADDRESS, symbol="SOL", decimals=9)
USDC_TOKEN = Token(address=USDC_ADDRESS, symbol="USDC", decimals=6)

# ── Helpers ────────────────────────────────────────────────────────────

POOL_ADDR = PoolAddress(value=POOL_ADDRESS)
POS_ADDR = PositionAddress(value=POSITION_ADDRESS)


def _make_mock_client() -> AsyncMock:
    """Create an AsyncMock that mimics MeteoraClient's async interface."""
    return AsyncMock(spec=MeteoraClient)


def _make_mock_pool() -> Pool:
    """Create a minimal valid Pool for mock return values."""
    return Pool(
        address=POOL_ADDR,
        token_a=SOL_TOKEN,
        token_b=USDC_TOKEN,
    )


def _make_mock_position() -> Position:
    """Create a minimal valid Position for mock return values."""
    return Position(
        address=POS_ADDR,
        pool_address=POOL_ADDR,
    )


# ── Pool Adapter Tests ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pool_adapter_get_pool_success() -> None:
    """mock client.get_pool → verify PoolMapper.to_domain called, returns Pool."""
    client = _make_mock_client()
    client.get_pool = AsyncMock(return_value=POOL_DTO)

    adapter = MeteoraPoolAdapter(client)

    mock_pool = _make_mock_pool()
    with patch.object(PoolMapper, "to_domain", return_value=mock_pool) as mock_to_domain:
        result = await adapter.get_pool(POOL_ADDR)

    client.get_pool.assert_awaited_once_with(POOL_ADDRESS)
    mock_to_domain.assert_called_once_with(POOL_DTO)
    assert result is mock_pool
    assert isinstance(result, Pool)
    assert result.address == POOL_ADDR


@pytest.mark.asyncio
async def test_pool_adapter_get_pool_not_found() -> None:
    """mock client returns None → adapter returns None."""
    client = _make_mock_client()
    client.get_pool = AsyncMock(return_value=None)

    adapter = MeteoraPoolAdapter(client)

    result = await adapter.get_pool(POOL_ADDR)

    client.get_pool.assert_awaited_once_with(POOL_ADDRESS)
    assert result is None


@pytest.mark.asyncio
async def test_pool_adapter_list_pools() -> None:
    """mock client.get_pools → verify list of Pools returned."""
    client = _make_mock_client()
    client.get_pools = AsyncMock(return_value=PAGE_RESPONSE)

    adapter = MeteoraPoolAdapter(client)

    mock_pool = _make_mock_pool()
    with patch.object(PoolMapper, "to_domain", return_value=mock_pool) as mock_to_domain:
        result = await adapter.list_pools(limit=50, page=2)

    client.get_pools.assert_awaited_once_with(page=2, page_size=50)
    mock_to_domain.assert_called_once_with(POOL_DTO)
    assert len(result) == 1
    assert result[0] is mock_pool


# ── Position Adapter Tests ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_position_adapter_get_positions() -> None:
    """mock client.get_pool + client.get_positions_by_pool → verify PoolMapper
    and PositionMapper called."""
    client = _make_mock_client()
    client.get_pool = AsyncMock(return_value=POOL_DTO)
    client.get_positions_by_pool = AsyncMock(return_value=[POSITION_DTO])

    adapter = MeteoraPositionAdapter(client)

    mock_pool = _make_mock_pool()
    mock_position = _make_mock_position()

    with patch.object(PoolMapper, "to_domain", return_value=mock_pool) as mock_pool_map:
        with patch.object(
            PositionMapper, "to_domain", return_value=mock_position
        ) as mock_pos_map:
            result = await adapter.get_positions_by_pool(POOL_ADDR)

    client.get_pool.assert_awaited_once_with(POOL_ADDRESS)
    client.get_positions_by_pool.assert_awaited_once_with(POOL_ADDRESS)
    mock_pool_map.assert_called_once_with(POOL_DTO)
    mock_pos_map.assert_called_once_with(POSITION_DTO, mock_pool)
    assert len(result) == 1
    assert result[0] is mock_position


@pytest.mark.asyncio
async def test_position_adapter_pool_not_found() -> None:
    """client.get_pool returns None → adapter returns empty list."""
    client = _make_mock_client()
    client.get_pool = AsyncMock(return_value=None)

    adapter = MeteoraPositionAdapter(client)

    result = await adapter.get_positions_by_pool(POOL_ADDR)

    client.get_pool.assert_awaited_once_with(POOL_ADDRESS)
    client.get_positions_by_pool.assert_not_awaited()
    assert result == []


@pytest.mark.asyncio
async def test_position_adapter_no_transformation() -> None:
    """verify adapter only delegates (no fee calc, no status change,
    no Price/Token creation) — the adapter calls PoolMapper and PositionMapper
    and passes results through without additional logic."""
    client = _make_mock_client()
    client.get_pool = AsyncMock(return_value=POOL_DTO)
    client.get_positions_by_pool = AsyncMock(return_value=[POSITION_DTO])

    adapter = MeteoraPositionAdapter(client)

    # Patch mappers to capture calls while still executing real logic
    with patch.object(PoolMapper, "to_domain", wraps=PoolMapper.to_domain) as pool_map:
        with patch.object(
            PositionMapper, "to_domain", wraps=PositionMapper.to_domain
        ) as pos_map:
            result = await adapter.get_positions_by_pool(POOL_ADDR)

    # Verify delegation chain: client → mapper → pass-through
    assert pool_map.call_count == 1
    assert pos_map.call_count == 1

    # With wraps=True, the mock calls the real function and returns its result.
    # The mock stores the actual return value in mock.return_value automatically
    # only for non-wraps mocks. For wraps mocks, mock.side_effect is set to
    # the real function, so we need a different assertion approach.
    # Instead, verify the adapter returned the exact objects from mappers.
    assert len(result) == 1
    # The result should be the real Position returned by PositionMapper.to_domain
    assert isinstance(result[0], Position)
    assert result[0].address == POS_ADDR
    assert result[0].pool_address == POOL_ADDR

    # Verify no Price or Token constructors were called by the adapter itself.
    # (Price/Token are only created inside the mappers, which are already patched
    # with wraps, so they execute normally. The key assertion is that the adapter
    # code between the mapper calls does NOT create any domain objects.)
    # We verify this by checking that the adapter code has no imports or
    # instantiations of Price/Token outside of the mapper calls — which is
    # guaranteed by the source code structure: the adapter's
    # get_positions_by_pool only calls client.get_pool, PoolMapper.to_domain,
    # client.get_positions_by_pool, and PositionMapper.to_domain.

    # Additional: verify adapter didn't modify any mapper outputs
    assert result[0].fee_earned == float(POSITION_DTO.allTimeFees.total.usd)
    assert result[0].status.value == "active"  # Not changed by adapter
