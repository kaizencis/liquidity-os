"""SQLAlchemy ORM models for Decision Log.

[WHY] Defines the database schema for the decision_log table.
      This is an internal implementation detail — not exposed via ports.

[OWNERSHIP] Infrastructure layer — database models.

[DEPENDENTS] Allowed: logger, query.
             Forbidden: shared, apps, agents.

[EXAMPLE]
    from decision_log.models import DecisionLogModel

    model = DecisionLogModel(
        id=uuid4(),
        agent="oracle",
        event_type="alert_triggered",
    )
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


class DecisionLogModel(Base):
    """[WHY] SQLAlchemy model for the decision_log table.

    [OWNERSHIP] Infrastructure layer — internal ORM model.

    [DEPENDENTS] Allowed: logger, query.
                 Forbidden: shared, apps, agents.

    [EXAMPLE]
        model = DecisionLogModel(
            id=uuid4(),
            agent="oracle",
            event_type="alert_triggered",
            outcome="pending",
            timestamp=datetime.now(timezone.utc),
        )
    """

    __tablename__ = "decision_log"

    # Identity
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
        comment="UUID v4 unique identifier",
    )

    # Decision context
    agent = Column(
        String(50),
        nullable=False,
        comment="Agent role: oracle, navigator, collector, system",
    )
    event_type = Column(
        String(100),
        nullable=False,
        comment="Decision type: alert_triggered, rebalance_proposed, etc.",
    )
    trigger_rule = Column(
        Text,
        nullable=True,
        default="",
        comment="Rule/condition that triggered this decision",
    )

    # Optional pool reference
    pool_address = Column(
        String(44),
        nullable=True,
        comment="Related pool address (optional)",
    )

    # Outcome
    outcome = Column(
        String(50),
        nullable=False,
        default="pending",
        comment="Current outcome: pending, approved, rejected, executed, cancelled, expired",
    )

    # Temporal
    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        comment="When the decision was made (UTC)",
    )

    # Context data (JSONB for flexibility)
    features = Column(
        JSONB,
        nullable=True,
        default="{}",
        comment="Feature values at decision time (JSON)",
    )
    metadata_ = Column(
        "metadata",
        JSONB,
        nullable=True,
        default="{}",
        comment="Freeform context data (JSON)",
    )

    # Audit
    created_at = Column(
        DateTime(timezone=True),
        nullable=True,
        default=lambda: datetime.now(timezone.utc),
        comment="Record creation time (audit)",
    )

    def __repr__(self) -> str:
        return f"<DecisionLogModel(id={self.id}, agent={self.agent}, outcome={self.outcome})>"
