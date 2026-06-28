"""SQLAlchemy ORM model for Pool entity.

[WHY] Defines the database schema for the pools table.
      This is an internal implementation detail — not exposed via ports.

[OWNERSHIP] Infrastructure layer — database models.

[DEPENDENTS] Allowed: repositories.pool_repo_impl.
             Forbidden: shared, apps, agents.

[EXAMPLE]
    from database.models.pool_model import PoolModel

    model = PoolModel(
        id=uuid4(),
        address="7YttLkHDoNj9wyDur5pM1ejNaAvT9X4eSTY",
        token_a={"address": "So111...", "symbol": "SOL", "decimals": 9},
        token_b={"address": "EPjF...", "symbol": "USDC", "decimals": 6},
        status="active",
        fee_rate=0.003,
        bin_step=1,
    )
"""

from __future__ import annotations

from sqlalchemy import Column, Float, Integer, String
from sqlalchemy.dialects.postgresql import JSONB

from database.models.base import Base, TimestampMixin, UUIDMixin


class PoolModel(UUIDMixin, TimestampMixin, Base):
    """[WHY] SQLAlchemy model for the pools table.

    [OWNERSHIP] Infrastructure layer — internal ORM model.

    [DEPENDENTS] Allowed: repositories.pool_repo_impl.
                 Forbidden: shared, apps, agents.

    [EXAMPLE]
        model = PoolModel(
            id=uuid4(),
            address="7YttLkHDoNj9wyDur5pM1ejNaAvT9X4eSTY",
            token_a={"address": "So111...", "symbol": "SOL", "decimals": 9},
            token_b={"address": "EPjF...", "symbol": "USDC", "decimals": 6},
            status="active",
            fee_rate=0.003,
            bin_step=1,
        )
    """

    __tablename__ = "pools"

    # Identity
    address = Column(
        String(44),
        nullable=False,
        unique=True,
        comment="Base-58 encoded Solana address (32-44 chars)",
    )

    # Token pair (stored as JSONB for simplicity)
    token_a = Column(
        JSONB,
        nullable=False,
        comment="First token in the pair (JSON: {address, symbol, decimals})",
    )
    token_b = Column(
        JSONB,
        nullable=False,
        comment="Second token in the pair (JSON: {address, symbol, decimals})",
    )

    # Status
    status = Column(
        String(50),
        nullable=False,
        default="active",
        comment="Pool operational status: active, paused, closed, migrating",
    )

    # Price (stored as JSONB for simplicity)
    sqrt_price = Column(
        JSONB,
        nullable=True,
        comment="Current sqrt price (JSON: {raw, tick, bin_id})",
    )
    price = Column(
        JSONB,
        nullable=True,
        comment="Current price (JSON: {value, base_token, quote_token})",
    )

    # Configuration
    fee_rate = Column(
        Float,
        nullable=False,
        default=0.003,
        comment="Pool fee rate (e.g., 0.003 = 0.3%)",
    )
    bin_step = Column(
        Integer,
        nullable=False,
        default=1,
        comment="Price step between bins",
    )

    def __repr__(self) -> str:
        return f"<PoolModel(id={self.id}, address={self.address}, status={self.status})>"
