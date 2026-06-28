"""Mappers for converting Meteora API DTOs to domain entities.

[WHY] Single translation point between API DTOs and domain entities.
      No synthetic values, no placeholders, no assumptions.
[OWNERSHIP] Infrastructure layer — translation logic.
[DEPENDENTS] Allowed: meteora.adapters.
             Forbidden: shared, apps, agents.
[EXAMPLE]
    from meteora.mappers import PoolMapper, PositionMapper
    from meteora.models import PoolResponseDTO

    dto = PoolResponseDTO(...)
    pool = PoolMapper.to_domain(dto)
"""

from __future__ import annotations

from decimal import Decimal

from meteora.models import PoolResponseDTO, PositionPnLResponseDTO
from shared.entities.pool import Pool
from shared.entities.position import Position
from shared.enums import PoolStatus, PositionStatus
from shared.identifiers import PoolAddress, PositionAddress
from shared.value_objects.price import Price, PriceRange
from shared.value_objects.token import Token


class PoolMapper:
    """[WHY] Translates PoolResponseDTO to domain Pool entity.
    [OWNERSHIP] Infrastructure layer — translation logic.
    [DEPENDENTS] Allowed: meteora.adapters.
                 Forbidden: shared, apps, agents.
    [EXAMPLE]
        pool = PoolMapper.to_domain(pool_dto)
    """

    @staticmethod
    def to_domain(dto: PoolResponseDTO) -> Pool:
        """Convert API DTO to domain Pool entity.

        Only maps fields available in API response.
        No synthetic or approximated values.
        """
        return Pool(
            address=PoolAddress(value=dto.address),
            token_a=Token(
                address=dto.token_x.address,
                symbol=dto.token_x.symbol,
                decimals=dto.token_x.decimals,
            ),
            token_b=Token(
                address=dto.token_y.address,
                symbol=dto.token_y.symbol,
                decimals=dto.token_y.decimals,
            ),
            status=PoolStatus.PAUSED if dto.is_blacklisted else PoolStatus.ACTIVE,
            sqrt_price=None,  # NOT in API - no synthetic value
            price=Price(
                value=Decimal(str(dto.current_price)),
                base_token=Token(
                    address=dto.token_y.address,
                    symbol=dto.token_y.symbol,
                    decimals=dto.token_y.decimals,
                ),
                quote_token=Token(
                    address=dto.token_x.address,
                    symbol=dto.token_x.symbol,
                    decimals=dto.token_x.decimals,
                ),
            ),
            fee_rate=dto.pool_config.base_fee_pct / 100,
            bin_step=dto.pool_config.bin_step,
        )


class PositionMapper:
    """[WHY] Translates PositionPnLResponseDTO to domain Position entity.
    [OWNERSHIP] Infrastructure layer — translation logic.
    [DEPENDENTS] Allowed: meteora.adapters.
                 Forbidden: shared, apps, agents.
    [EXAMPLE]
        from shared.entities.pool import Pool
        position = PositionMapper.to_domain(position_dto, pool)
    """

    @staticmethod
    def to_domain(dto: PositionPnLResponseDTO, pool: Pool) -> Position:
        """Convert API DTO to domain Position entity.

        Args:
            dto: API response DTO.
            pool: Domain Pool entity for token context.

        Only maps fields available in API response.
        No synthetic or approximated values.
        """
        # Derive status from isClosed
        status = PositionStatus.CLOSED if dto.isClosed else PositionStatus.ACTIVE

        # Extract min/max prices from DTO
        min_price = float(dto.minPrice) if dto.minPrice else 0.0
        max_price = float(dto.maxPrice) if dto.maxPrice else 0.0

        # Build PriceRange from pool token context
        price_range = None
        if min_price > 0 and max_price > 0:
            from shared.value_objects.price import Price
            from decimal import Decimal
            price_range = PriceRange(
                low=Price(
                    value=Decimal(str(min_price)),
                    base_token=pool.token_b,  # API: token_y = base
                    quote_token=pool.token_a,  # API: token_x = quote
                ),
                high=Price(
                    value=Decimal(str(max_price)),
                    base_token=pool.token_b,
                    quote_token=pool.token_a,
                ),
            )

        return Position(
            address=PositionAddress(value=dto.positionAddress),
            pool_address=pool.address,
            status=status,
            side=None,  # Contract v1.1: API does not provide side information
            price_range=price_range,  # Now uses real pool token context
            liquidity=None,  # NOT in API - allTimeDeposits is cumulative
            liquidity_distribution=None,  # NOT in API
            fee_earned=float(dto.allTimeFees.total.usd),
        )
