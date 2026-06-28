"""PostgreSQL implementation of PoolRepository port.

[WHY] Translates between domain Pool entities and database PoolModel.
      Pure translator — no business logic, no validation strategy.
[OWNERSHIP] Infrastructure layer — implements shared.ports.pool_repo.PoolRepository.
[DEPENDENTS] Allowed: apps.collector, apps.analytics, apps.dashboard,
             agents.oracle, agents.navigator.
             Forbidden: shared (must go through ports).
[EXAMPLE]
    from sqlalchemy.ext.asyncio import AsyncSession
    from database.repositories.pool_repo_impl import PostgresPoolRepository

    repo = PostgresPoolRepository(session)
    pool = await repo.get_by_address(PoolAddress(value="7Ytt..."))
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.pool_model import PoolModel
from shared.entities.pool import Pool
from shared.enums import PoolStatus
from shared.exceptions import PoolNotFoundError
from shared.identifiers import PoolAddress
from shared.ports.pool_repo import PoolRepository
from shared.value_objects.price import Price, SqrtPrice
from shared.value_objects.token import Token


class PostgresPoolRepository(PoolRepository):
    """[WHY] PostgreSQL implementation of PoolRepository port.
    [OWNERSHIP] Infrastructure layer — translates domain ↔ ORM.
    [DEPENDENTS] Allowed: apps, agents (via PoolRepository port).
                 Forbidden: shared (must go through ports).
    [EXAMPLE]
        repo = PostgresPoolRepository(session)
        pool = await repo.get_by_address(PoolAddress(value="7Ytt..."))
        await repo.save(pool)
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with injected session."""
        self.session = session

    async def get_by_address(self, address: PoolAddress) -> Pool | None:
        """Retrieve a pool by its unique address.

        Raises:
            PoolNotFoundError: If pool with given address does not exist.
        """
        stmt = select(PoolModel).where(PoolModel.address == address.value)
        result = await self.session.execute(stmt)
        model = result.scalars().first()

        if model is None:
            raise PoolNotFoundError(address=address)

        return self._to_domain(model)

    async def save(self, pool: Pool) -> None:
        """Persist a pool (create or update)."""
        model = self._to_model(pool)
        self.session.add(model)

    async def list_all(self) -> list[Pool]:
        """Retrieve all pools."""
        stmt = select(PoolModel)
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [self._to_domain(m) for m in models]

    async def list_by_status(self, status: str) -> list[Pool]:
        """Retrieve pools filtered by status."""
        stmt = select(PoolModel).where(PoolModel.status == status)
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [self._to_domain(m) for m in models]

    def _to_model(self, pool: Pool) -> PoolModel:
        """Convert domain Pool to ORM PoolModel.

        This is a pure translator — no business logic.
        """
        return PoolModel(
            address=pool.address.value,
            token_a={
                "address": pool.token_a.address,
                "symbol": pool.token_a.symbol,
                "decimals": pool.token_a.decimals,
            },
            token_b={
                "address": pool.token_b.address,
                "symbol": pool.token_b.symbol,
                "decimals": pool.token_b.decimals,
            },
            status=pool.status.value,
            sqrt_price={
                "raw": pool.sqrt_price.raw,
                "tick": pool.sqrt_price.tick,
                "bin_id": pool.sqrt_price.bin_id,
            }
            if pool.sqrt_price is not None
            else None,
            price={
                "value": pool.price.value,
                "base_token": {
                    "address": pool.price.base_token.address,
                    "symbol": pool.price.base_token.symbol,
                    "decimals": pool.price.base_token.decimals,
                },
                "quote_token": {
                    "address": pool.price.quote_token.address,
                    "symbol": pool.price.quote_token.symbol,
                    "decimals": pool.price.quote_token.decimals,
                },
            }
            if pool.price is not None
            else None,
            fee_rate=pool.fee_rate,
            bin_step=pool.bin_step,
        )

    def _to_domain(self, model: PoolModel) -> Pool:
        """Convert ORM PoolModel to domain Pool.

        This is a pure translator — no business logic.
        """
        sqrt_price = None
        if model.sqrt_price is not None:
            sqrt_price = SqrtPrice(
                raw=model.sqrt_price["raw"],
                tick=model.sqrt_price["tick"],
                bin_id=model.sqrt_price["bin_id"],
            )

        price = None
        if model.price is not None:
            price = Price(
                value=model.price["value"],
                base_token=Token(
                    address=model.price["base_token"]["address"],
                    symbol=model.price["base_token"]["symbol"],
                    decimals=model.price["base_token"]["decimals"],
                ),
                quote_token=Token(
                    address=model.price["quote_token"]["address"],
                    symbol=model.price["quote_token"]["symbol"],
                    decimals=model.price["quote_token"]["decimals"],
                ),
            )

        return Pool(
            address=PoolAddress(value=model.address),
            token_a=Token(
                address=model.token_a["address"],
                symbol=model.token_a["symbol"],
                decimals=model.token_a["decimals"],
            ),
            token_b=Token(
                address=model.token_b["address"],
                symbol=model.token_b["symbol"],
                decimals=model.token_b["decimals"],
            ),
            status=PoolStatus(model.status),
            sqrt_price=sqrt_price,
            price=price,
            fee_rate=model.fee_rate,
            bin_step=model.bin_step,
        )
