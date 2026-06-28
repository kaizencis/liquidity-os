"""Integration tests for the full Meteora pipeline.

[WHY] Validates the complete data flow:
      MockTransport → MeteoraClient → DTO → Mapper → Adapter → Domain Entity
      Ensures all layers compose correctly end-to-end.
[OWNERSHIP] Infrastructure layer — integration contract tests.
"""

from __future__ import annotations

import httpx
import pytest

from meteora.adapters import MeteoraPoolAdapter, MeteoraPositionAdapter
from meteora.client import MeteoraClient
from meteora.settings import MeteoraSettings
from shared.enums import PoolStatus, PositionStatus
from shared.identifiers import PoolAddress, PositionAddress
from shared.value_objects.price import PriceRange

# ── Constants ──────────────────────────────────────────────────────────

POOL_ADDRESS = "7YttLhHaiUDKvigCUXjCRWUboEGhFhtNTQHspR1x9Mx"
SOL_ADDRESS = "So11111111111111111111111111111111111111112"
USDC_ADDRESS = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
POSITION_ADDRESS = "AJ6zF9a8oC4e3x2bGh1DkLmNpQrS5tUvW8yZ7X4c6R1"

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
async def test_full_pool_pipeline() -> None:
    """Full pipeline: MockTransport → Client → PoolMapper → Adapter → Pool entity.

    Mocks GET /pools/{address}, verifies the complete data flow produces
    a correct domain Pool entity with all expected fields.
    """
    client = _make_client()

    def handler(request: httpx.Request) -> httpx.Response:
        if "/pools/" in str(request.url) and request.method == "GET":
            return httpx.Response(200, json=POOL_JSON)
        return httpx.Response(404, json={"error": "not found"})

    _patch_transport(client, handler)

    try:
        adapter = MeteoraPoolAdapter(client)
        pool = await adapter.get_pool(PoolAddress(value=POOL_ADDRESS))

        # Pool entity was created
        assert pool is not None

        # Correct address
        assert str(pool.address) == POOL_ADDRESS

        # Correct tokens
        assert pool.token_a.address == SOL_ADDRESS
        assert pool.token_a.symbol == "SOL"
        assert pool.token_a.decimals == 9
        assert pool.token_b.address == USDC_ADDRESS
        assert pool.token_b.symbol == "USDC"
        assert pool.token_b.decimals == 6

        # Correct status (not blacklisted → ACTIVE)
        assert pool.status == PoolStatus.ACTIVE

        # Correct price (base=USDC, quote=SOL)
        assert pool.price is not None
        assert float(pool.price.value) == 150.0
        assert pool.price.base_token.symbol == "USDC"
        assert pool.price.quote_token.symbol == "SOL"

        # Correct fee rate (0.3% → 0.003)
        assert pool.fee_rate == pytest.approx(0.003)

        # Correct bin step
        assert pool.bin_step == 1

        # Pool properties work
        assert pool.is_active is True
        assert pool.pair == "SOL/USDC"
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_full_position_pipeline() -> None:
    """Full pipeline: MockTransport → Client → Mapper → Adapter → list[Position].

    Mocks GET /pools/{address} and GET /positions/{address}/pnl,
    verifies the complete flow produces Position entities with correct
    price_range derived from pool token context.
    """
    client = _make_client()

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "/pools/" in url and "/positions/" not in url and request.method == "GET":
            return httpx.Response(200, json=POOL_JSON)
        if "/positions/" in url and "/pnl" in url and request.method == "GET":
            return httpx.Response(200, json=[POSITION_JSON])
        return httpx.Response(404, json={"error": "not found"})

    _patch_transport(client, handler)

    try:
        adapter = MeteoraPositionAdapter(client)
        positions = await adapter.get_positions_by_pool(
            PoolAddress(value=POOL_ADDRESS)
        )

        # Got exactly one position
        assert len(positions) == 1
        pos = positions[0]

        # Correct address
        assert str(pos.address) == POSITION_ADDRESS

        # Correct pool reference
        assert str(pos.pool_address) == POOL_ADDRESS

        # Correct status (not closed → ACTIVE)
        assert pos.status == PositionStatus.ACTIVE

        # side is None (API v1.1 does not provide this)
        assert pos.side is None

        # Correct price_range using pool token context
        assert pos.price_range is not None
        assert isinstance(pos.price_range, PriceRange)

        # Low price = 140.0 USDC/SOL
        assert float(pos.price_range.low.value) == 140.0
        assert pos.price_range.low.base_token.symbol == "USDC"
        assert pos.price_range.low.quote_token.symbol == "SOL"

        # High price = 160.0 USDC/SOL
        assert float(pos.price_range.high.value) == 160.0
        assert pos.price_range.high.base_token.symbol == "USDC"
        assert pos.price_range.high.quote_token.symbol == "SOL"

        # Fee earned from allTimeFees.total.usd = 20.0
        assert pos.fee_earned == pytest.approx(20.0)

        # Price range spread and midpoint
        assert float(pos.price_range.spread) == pytest.approx(20.0)
        assert float(pos.price_range.midpoint) == pytest.approx(150.0)
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_full_pipeline_with_empty_positions() -> None:
    """Full pipeline with empty positions list.

    Mocks GET /pools/{address} returning a valid pool but
    GET /positions/{address}/pnl returning an empty list.
    Verifies the adapter returns an empty list of Position entities.
    """
    client = _make_client()

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "/pools/" in url and "/positions/" not in url and request.method == "GET":
            return httpx.Response(200, json=POOL_JSON)
        if "/positions/" in url and "/pnl" in url and request.method == "GET":
            return httpx.Response(200, json=[])
        return httpx.Response(404, json={"error": "not found"})

    _patch_transport(client, handler)

    try:
        adapter = MeteoraPositionAdapter(client)
        positions = await adapter.get_positions_by_pool(
            PoolAddress(value=POOL_ADDRESS)
        )

        # Empty list returned — no positions
        assert positions == []
        assert len(positions) == 0
    finally:
        await client.close()
