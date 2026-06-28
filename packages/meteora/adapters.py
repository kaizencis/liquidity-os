"""Adapters implementing PoolReader and PositionReader ports.

[WHY] Connects Meteora API client to domain ports.
      Uses mappers for translation.
[OWNERSHIP] Infrastructure layer — port implementations.
[DEPENDENTS] Allowed: apps.collector, apps.analytics.
             Forbidden: shared, agents (must go through ports).
[EXAMPLE]
    from meteora.adapters import MeteoraPoolAdapter
    from meteora.client import MeteoraClient
    from meteora.settings import MeteoraSettings

    client = MeteoraClient(MeteoraSettings())
    adapter = MeteoraPoolAdapter(client)
    pool = await adapter.get_pool(PoolAddress(value="7Ytt..."))
"""

from __future__ import annotations

from meteora.client import MeteoraClient
from meteora.mappers import PoolMapper, PositionMapper
from shared.entities.pool import Pool
from shared.entities.position import Position
from shared.identifiers import PoolAddress
from shared.ports.meteora_reader import PoolReader, PositionReader


class MeteoraPoolAdapter(PoolReader):
    """[WHY] Implements PoolReader using Meteora API.
    [OWNERSHIP] Infrastructure layer — port implementation.
    [DEPENDENTS] Allowed: apps.collector, apps.analytics.
                 Forbidden: shared, agents (must go through ports).
    [EXAMPLE]
        adapter = MeteoraPoolAdapter(client)
        pool = await adapter.get_pool(PoolAddress(value="7Ytt..."))
    """

    def __init__(self, client: MeteoraClient) -> None:
        """Initialize adapter with client."""
        self.client = client

    async def get_pool(self, address: PoolAddress) -> Pool | None:
        """Fetch a single pool by address."""
        dto = await self.client.get_pool(address.value)
        if dto is None:
            return None
        return PoolMapper.to_domain(dto)

    async def list_pools(self, limit: int = 100, page: int = 1) -> list[Pool]:
        """Fetch multiple pools."""
        response = await self.client.get_pools(page=page, page_size=limit)
        return [PoolMapper.to_domain(dto) for dto in response.data]


class MeteoraPositionAdapter(PositionReader):
    """[WHY] Implements PositionReader using Meteora API.
    [OWNERSHIP] Infrastructure layer — port implementation.
    [DEPENDENTS] Allowed: apps.collector, apps.dashboard.
                 Forbidden: shared, agents (must go through ports).
    [EXAMPLE]
        adapter = MeteoraPositionAdapter(client)
        positions = await adapter.get_positions_by_pool(PoolAddress(value="7Ytt..."))
    """

    def __init__(self, client: MeteoraClient) -> None:
        """Initialize adapter with client."""
        self.client = client

    async def get_positions_by_pool(self, pool_address: PoolAddress) -> list[Position]:
        """Fetch all positions for a pool."""
        # Fetch pool for token context (required by PositionMapper)
        pool_dto = await self.client.get_pool(pool_address.value)
        if pool_dto is None:
            return []

        # Convert pool to domain entity
        from meteora.mappers import PoolMapper
        pool = PoolMapper.to_domain(pool_dto)

        # Fetch positions and map with pool context
        dtos = await self.client.get_positions_by_pool(pool_address.value)
        return [PositionMapper.to_domain(dto, pool) for dto in dtos]
