"""Position ORM model for database persistence.

WHY: Persists Position domain entities to PostgreSQL.
OWNERSHIP: M3 (Database Package) — persistence layer.
DEPENDENTS: Repositories, migrations.
PATTERN: Matches PoolModel structure, pure persistence model with no business logic.
"""

from sqlalchemy import Column, Float, Integer, String
from sqlalchemy.dialects.postgresql import JSONB

from database.models.base import Base, TimestampMixin, UUIDMixin


class PositionModel(UUIDMixin, TimestampMixin, Base):
    """Position table schema.

    Maps to the Position entity from packages/shared.
    Uses JSONB for complex domain objects (PriceRange, Liquidity, LiquidityDistribution).
    Stores enums as VARCHAR strings for flexibility.
    """

    __tablename__ = "position"

    address = Column(String(44), nullable=False)
    pool_address = Column(String(44), nullable=False)
    status = Column(String(50), nullable=False, default="active")
    side = Column(String(50), nullable=False, default="both")
    price_range = Column(JSONB, nullable=True)
    liquidity = Column(JSONB, nullable=True)
    distribution = Column(JSONB, nullable=True)
    fee_earned = Column(Float, nullable=False, default=0.0)
