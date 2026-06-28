"""PostgreSQL implementation of PositionRepository port.

[WHY] Translates between domain Position entities and database PositionModel.
      Pure translator — no business logic, no validation strategy.
[OWNERSHIP] Infrastructure layer — implements shared.ports.position_repo.PositionRepository.
[DEPENDENTS] Allowed: apps.collector, apps.dashboard, agents.navigator.
             Forbidden: shared (must go through ports).
[EXAMPLE]
    from sqlalchemy.ext.asyncio import AsyncSession
    from database.repositories.position_repo_impl import PostgresPositionRepository

    repo = PostgresPositionRepository(session)
    position = await repo.get_by_address(PositionAddress(value="AJ6z..."))
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.position_model import PositionModel
from shared.entities.position import Position
from shared.enums import PositionSide, PositionStatus
from shared.exceptions import PositionNotFoundError
from shared.identifiers import PoolAddress, PositionAddress
from shared.ports.position_repo import PositionRepository
from shared.value_objects.liquidity import BinLiquidity, Liquidity, LiquidityDistribution
from shared.value_objects.price import Price, PriceRange
from shared.value_objects.token import Token, TokenAmount


class PostgresPositionRepository(PositionRepository):
    """[WHY] PostgreSQL implementation of PositionRepository port.
    [OWNERSHIP] Infrastructure layer — translates domain ↔ ORM.
    [DEPENDENTS] Allowed: apps, agents (via PositionRepository port).
                 Forbidden: shared (must go through ports).
    [EXAMPLE]
        repo = PostgresPositionRepository(session)
        position = await repo.get_by_address(PositionAddress(value="AJ6z..."))
        await repo.save(position)
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with injected session."""
        self.session = session

    async def get_by_address(self, address: PositionAddress) -> Position:
        """Retrieve a position by its unique address.

        Raises:
            PositionNotFoundError: If position with given address does not exist.
        """
        stmt = select(PositionModel).where(PositionModel.address == address.value)
        result = await self.session.execute(stmt)
        model = result.scalars().first()

        if model is None:
            raise PositionNotFoundError(address=address)

        return self._to_domain(model)

    async def get_by_pool(self, pool_address: PoolAddress) -> list[Position]:
        """Retrieve all positions for a specific pool."""
        stmt = select(PositionModel).where(
            PositionModel.pool_address == pool_address.value
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [self._to_domain(m) for m in models]

    async def save(self, position: Position) -> None:
        """Persist a position (create or update)."""
        model = self._to_model(position)
        self.session.add(model)

    async def list_active(self) -> list[Position]:
        """Retrieve all active positions."""
        stmt = select(PositionModel).where(
            PositionModel.status == PositionStatus.ACTIVE.value
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [self._to_domain(m) for m in models]

    def _to_model(self, position: Position) -> PositionModel:
        """Convert domain Position to ORM PositionModel.

        This is a pure translator — no business logic.
        """
        # Build price_range JSONB with full Price objects
        price_range_json = None
        if position.price_range is not None:
            price_range_json = {
                "low": {
                    "value": float(position.price_range.low.value),
                    "base_token": {
                        "address": position.price_range.low.base_token.address,
                        "symbol": position.price_range.low.base_token.symbol,
                        "decimals": position.price_range.low.base_token.decimals,
                    },
                    "quote_token": {
                        "address": position.price_range.low.quote_token.address,
                        "symbol": position.price_range.low.quote_token.symbol,
                        "decimals": position.price_range.low.quote_token.decimals,
                    },
                },
                "high": {
                    "value": float(position.price_range.high.value),
                    "base_token": {
                        "address": position.price_range.high.base_token.address,
                        "symbol": position.price_range.high.base_token.symbol,
                        "decimals": position.price_range.high.base_token.decimals,
                    },
                    "quote_token": {
                        "address": position.price_range.high.quote_token.address,
                        "symbol": position.price_range.high.quote_token.symbol,
                        "decimals": position.price_range.high.quote_token.decimals,
                    },
                },
            }

        # Build liquidity JSONB
        liquidity_json = None
        if position.liquidity is not None:
            liquidity_json = {
                "amount": {
                    "raw": position.liquidity.amount.raw,
                    "token": {
                        "address": position.liquidity.amount.token.address,
                        "symbol": position.liquidity.amount.token.symbol,
                        "decimals": position.liquidity.amount.token.decimals,
                    },
                }
            }

        # Build distribution JSONB
        distribution_json = None
        if position.liquidity_distribution is not None:
            distribution_json = {
                "bins": [
                    {
                        "bin_id": bin_liq.bin_id,
                        "liquidity": {
                            "amount": {
                                "raw": bin_liq.liquidity.amount.raw,
                                "token": {
                                    "address": bin_liq.liquidity.amount.token.address,
                                    "symbol": bin_liq.liquidity.amount.token.symbol,
                                    "decimals": bin_liq.liquidity.amount.token.decimals,
                                },
                            }
                        },
                    }
                    for bin_liq in position.liquidity_distribution.bins
                ]
            }

        return PositionModel(
            address=position.address.value,
            pool_address=position.pool_address.value,
            status=position.status.value,
            side=position.side.value,
            price_range=price_range_json,
            liquidity=liquidity_json,
            distribution=distribution_json,
            fee_earned=position.fee_earned,
        )

    def _to_domain(self, model: PositionModel) -> Position:
        """Convert ORM PositionModel to domain Position.

        This is a pure translator — no business logic.
        """
        price_range = None
        if model.price_range is not None:
            low_data = model.price_range["low"]
            high_data = model.price_range["high"]
            price_range = PriceRange(
                low=Price(
                    value=low_data["value"],
                    base_token=Token(
                        address=low_data["base_token"]["address"],
                        symbol=low_data["base_token"]["symbol"],
                        decimals=low_data["base_token"]["decimals"],
                    ),
                    quote_token=Token(
                        address=low_data["quote_token"]["address"],
                        symbol=low_data["quote_token"]["symbol"],
                        decimals=low_data["quote_token"]["decimals"],
                    ),
                ),
                high=Price(
                    value=high_data["value"],
                    base_token=Token(
                        address=high_data["base_token"]["address"],
                        symbol=high_data["base_token"]["symbol"],
                        decimals=high_data["base_token"]["decimals"],
                    ),
                    quote_token=Token(
                        address=high_data["quote_token"]["address"],
                        symbol=high_data["quote_token"]["symbol"],
                        decimals=high_data["quote_token"]["decimals"],
                    ),
                ),
            )

        liquidity = None
        if model.liquidity is not None:
            liquidity = Liquidity(
                amount=TokenAmount(
                    token=Token(
                        address=model.liquidity["amount"]["token"]["address"],
                        symbol=model.liquidity["amount"]["token"]["symbol"],
                        decimals=model.liquidity["amount"]["token"]["decimals"],
                    ),
                    raw=model.liquidity["amount"]["raw"],
                )
            )

        liquidity_distribution = None
        if model.distribution is not None:
            liquidity_distribution = LiquidityDistribution(
                bins=[
                    BinLiquidity(
                        bin_id=bin_data["bin_id"],
                        liquidity=Liquidity(
                            amount=TokenAmount(
                                token=Token(
                                    address=bin_data["liquidity"]["amount"]["token"]["address"],
                                    symbol=bin_data["liquidity"]["amount"]["token"]["symbol"],
                                    decimals=bin_data["liquidity"]["amount"]["token"]["decimals"],
                                ),
                                raw=bin_data["liquidity"]["amount"]["raw"],
                            )
                        ),
                    )
                    for bin_data in model.distribution["bins"]
                ]
            )

        return Position(
            address=PositionAddress(value=model.address),
            pool_address=PoolAddress(value=model.pool_address),
            status=PositionStatus(model.status),
            side=PositionSide(model.side),
            price_range=price_range,
            liquidity=liquidity,
            liquidity_distribution=liquidity_distribution,
            fee_earned=model.fee_earned,
        )
