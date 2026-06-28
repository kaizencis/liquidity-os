"""HTTP client for Meteora DLMM API.

[WHY] Thin HTTP client that returns DTOs only.
      No domain knowledge, no business logic.
[OWNERSHIP] Infrastructure layer — API communication.
[DEPENDENTS] Allowed: meteora.adapters.
             Forbidden: shared, apps, agents.
[EXAMPLE]
    from meteora.client import MeteoraClient
    from meteora.settings import MeteoraSettings

    client = MeteoraClient(MeteoraSettings())
    pool = await client.get_pool("7Ytt...")
    await client.close()
"""

from __future__ import annotations

import httpx

from meteora.errors import MeteoraError
from meteora.models import (
    PaginationResponseDTO,
    PoolResponseDTO,
    PositionPnLResponseDTO,
)
from meteora.settings import MeteoraSettings


class MeteoraClient:
    """[WHY] HTTP client for Meteora API.
    [OWNERSHIP] Infrastructure layer — API communication.
    [DEPENDENTS] Allowed: meteora.adapters.
                 Forbidden: shared, apps, agents.
    [EXAMPLE]
        client = MeteoraClient(MeteoraSettings())
        pool = await client.get_pool("7Ytt...")
    """

    def __init__(self, settings: MeteoraSettings) -> None:
        """Initialize client with settings."""
        self.settings = settings
        self._client = httpx.AsyncClient(
            base_url=settings.base_url,
            timeout=settings.timeout,
        )

    async def get_pool(self, address: str) -> PoolResponseDTO | None:
        """Fetch a single pool by address.

        Returns None on 404. Raises MeteoraError on other errors.
        """
        response = await self._client.get(f"/pools/{address}")
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            raise MeteoraError(f"API error: {response.status_code}")
        return PoolResponseDTO(**response.json())

    async def get_pools(
        self,
        page: int = 1,
        page_size: int = 100,
    ) -> PaginationResponseDTO:
        """Fetch paginated list of pools.

        Args:
            page: Page number (1-based)
            page_size: Number of pools per page (max 1000)
        """
        response = await self._client.get(
            "/pools",
            params={"page": page, "page_size": page_size},
        )
        if response.status_code != 200:
            raise MeteoraError(f"API error: {response.status_code}")
        return PaginationResponseDTO(**response.json())

    async def get_positions_by_pool(
        self,
        pool_address: str,
    ) -> list[PositionPnLResponseDTO]:
        """Fetch all positions for a pool.

        Args:
            pool_address: Solana address of the pool
        """
        response = await self._client.get(f"/positions/{pool_address}/pnl")
        if response.status_code != 200:
            raise MeteoraError(f"API error: {response.status_code}")
        return [PositionPnLResponseDTO(**item) for item in response.json()]

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
