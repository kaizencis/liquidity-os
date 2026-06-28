"""Tests for MeteoraClient HTTP client.

[WHY] Validates client behaviour against mocked HTTP responses.
      Ensures DTO construction, error handling, and edge cases.
[OWNERSHIP] Infrastructure layer — client contract tests.
"""

from __future__ import annotations

import json

import httpx
import pytest

from meteora.client import MeteoraClient
from meteora.errors import MeteoraError
from meteora.settings import MeteoraSettings

# ── Constants ──────────────────────────────────────────────────────────

POOL_ADDRESS = "7YttLhHaiUDKvigCUXjCRWUboEGhFhtNTQHspR1x9Mx"
SOL_ADDRESS = "So11111111111111111111111111111111111111112"
USDC_ADDRESS = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
POSITION_ADDRESS = "AJ6zF9a8oC4e3x2bGh1DkLmNpQrS5tUvW8yZ7X4c6R1"

# ── Shared test data ───────────────────────────────────────────────────

POOL_JSON: dict = {
    "address": POOL_ADDRESS,
    "name": "SOL/USDC",
    "token_x": {"address": SOL_ADDRESS, "symbol": "SOL", "decimals": 9},
    "token_y": {"address": USDC_ADDRESS, "symbol": "USDC", "decimals": 6},
    "pool_config": {"bin_step": 1, "base_fee_pct": 0.3},
    "current_price": 150.0,
    "dynamic_fee_pct": 0.3,
    "tvl": 1_000_000.0,
    "is_blacklisted": False,
    "created_at": 1234567890,
}

POSITION_JSON: dict = {
    "positionAddress": POSITION_ADDRESS,
    "minPrice": "140.0",
    "maxPrice": "160.0",
    "lowerBinId": 100,
    "upperBinId": 200,
    "isClosed": False,
    "allTimeDeposits": {
        "tokenX": {"amount": "1000000", "usd": "150.0"},
        "tokenY": {"amount": "500000", "usd": "50.0"},
        "total": {"usd": "200.0", "sol": "1.5"},
    },
    "allTimeFees": {
        "tokenX": {"amount": "100000", "usd": "15.0"},
        "tokenY": {"amount": "50000", "usd": "5.0"},
        "total": {"usd": "20.0", "sol": "0.15"},
    },
}

PAGINATION_JSON: dict = {
    "total": 1000,
    "pages": 10,
    "current_page": 1,
    "page_size": 100,
    "data": [POOL_JSON],
}


# ── Helpers ────────────────────────────────────────────────────────────

def _make_client() -> MeteoraClient:
    """Create a MeteoraClient with test settings."""
    return MeteoraClient(MeteoraSettings())


def _patch_transport(client: MeteoraClient, handler) -> None:
    """Replace the internal httpx client with one using MockTransport."""
    client._client = httpx.AsyncClient(
        base_url=client.settings.base_url,
        timeout=client.settings.timeout,
        transport=httpx.MockTransport(handler),
    )


# ── Tests ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_pool_success() -> None:
    """Mock 200 response → PoolResponseDTO returned."""
    client = _make_client()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=POOL_JSON)

    _patch_transport(client, handler)

    try:
        result = await client.get_pool(POOL_ADDRESS)

        assert result is not None
        assert result.address == POOL_ADDRESS
        assert result.name == "SOL/USDC"
        assert result.token_x.symbol == "SOL"
        assert result.token_y.symbol == "USDC"
        assert result.pool_config.bin_step == 1
        assert result.current_price == 150.0
        assert result.tvl == 1_000_000.0
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_get_pool_not_found() -> None:
    """Mock 404 response → returns None."""
    client = _make_client()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "not found"})

    _patch_transport(client, handler)

    try:
        result = await client.get_pool(POOL_ADDRESS)
        assert result is None
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_get_pools_success() -> None:
    """Mock paginated response → PaginationResponseDTO returned."""
    client = _make_client()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=PAGINATION_JSON)

    _patch_transport(client, handler)

    try:
        result = await client.get_pools(page=1, page_size=100)

        assert result.total == 1000
        assert result.pages == 10
        assert result.current_page == 1
        assert result.page_size == 100
        assert len(result.data) == 1
        assert result.data[0].address == POOL_ADDRESS
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_get_positions_success() -> None:
    """Mock position list response → list[PositionPnLResponseDTO]."""
    client = _make_client()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[POSITION_JSON])

    _patch_transport(client, handler)

    try:
        result = await client.get_positions_by_pool(POOL_ADDRESS)

        assert len(result) == 1
        pos = result[0]
        assert pos.positionAddress == POSITION_ADDRESS
        assert pos.minPrice == "140.0"
        assert pos.maxPrice == "160.0"
        assert pos.lowerBinId == 100
        assert pos.upperBinId == 200
        assert pos.isClosed is False
        assert pos.allTimeDeposits.total.usd == "200.0"
        assert pos.allTimeFees.tokenX.amount == "100000"
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_timeout_raises() -> None:
    """Mock httpx timeout → exception propagates."""
    client = _make_client()

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("Request timed out")

    _patch_transport(client, handler)

    try:
        with pytest.raises(httpx.TimeoutException, match="timed out"):
            await client.get_pool(POOL_ADDRESS)
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_retry_success_on_second_attempt() -> None:
    """Second independent call succeeds after first fails.

    The client has no built-in retry; this verifies that a transient
    failure on one call does not affect a subsequent call.
    """
    client = _make_client()
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(500, json={"error": "server error"})
        return httpx.Response(200, json=POOL_JSON)

    _patch_transport(client, handler)

    try:
        # First call fails → MeteoraError
        with pytest.raises(MeteoraError, match="API error: 500"):
            await client.get_pool(POOL_ADDRESS)

        # Second call succeeds → PoolResponseDTO
        result = await client.get_pool(POOL_ADDRESS)
        assert result is not None
        assert result.address == POOL_ADDRESS
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_retry_exhausted() -> None:
    """All requests fail → MeteoraError raised."""
    client = _make_client()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "service unavailable"})

    _patch_transport(client, handler)

    try:
        with pytest.raises(MeteoraError, match="API error: 503"):
            await client.get_pool(POOL_ADDRESS)
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_invalid_json() -> None:
    """Mock response with non-JSON body → decoding error raised."""
    client = _make_client()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"this is not json")

    _patch_transport(client, handler)

    try:
        with pytest.raises(Exception):
            await client.get_pool(POOL_ADDRESS)
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_malformed_response() -> None:
    """Mock response with missing required fields → ValidationError raised."""
    from pydantic import ValidationError

    client = _make_client()

    def handler(request: httpx.Request) -> httpx.Response:
        # Valid JSON but missing required fields for PoolResponseDTO
        return httpx.Response(200, json={"name": "SOL/USDC"})

    _patch_transport(client, handler)

    try:
        with pytest.raises(ValidationError):
            await client.get_pool(POOL_ADDRESS)
    finally:
        await client.close()
