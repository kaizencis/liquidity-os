"""Decision Log append-only writer implementation.

[WHY] Implements the DecisionLog port for PostgreSQL persistence.
      Provides append-only semantics — no update, no delete.

[OWNERSHIP] Infrastructure layer — implements shared.ports.decision_log.DecisionLog.

[DEPENDENTS] Allowed: apps, agents (via DecisionLog port).
             Forbidden: shared (must go through ports).

[EXAMPLE]
    from decision_log.logger import PostgresDecisionLog

    logger = PostgresDecisionLog(session)
    await logger.append(decision)
"""

from __future__ import annotations

import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from decision_log.errors import DuplicateDecisionError
from decision_log.models import DecisionLogModel
from shared.entities.decision import Decision
from shared.enums import AgentRole, DecisionOutcome
from shared.identifiers import DecisionId
from shared.ports.decision_log import DecisionLog


class PostgresDecisionLog(DecisionLog):
    """[WHY] PostgreSQL implementation of the DecisionLog port.

    [OWNERSHIP] Infrastructure layer — append-only audit trail.

    [DEPENDENTS] Allowed: apps, agents (via DecisionLog port).
                 Forbidden: shared (must go through ports).

    [EXAMPLE]
        log = PostgresDecisionLog(session)
        await log.append(decision)
        record = await log.get_by_id(decision.id)
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def append(self, decision: Decision) -> None:
        """Record a new decision (immutable — no update)."""
        # Check for duplicate
        existing = await self.get_by_id(decision.id)
        if existing is not None:
            raise DuplicateDecisionError(decision_id=decision.id)

        # Insert (never UPDATE)
        row = self._to_row(decision)
        await self.session.execute(
            DecisionLogModel.__table__.insert().values(**row)
        )

    async def get_by_id(self, decision_id: DecisionId) -> Decision | None:
        """Retrieve a decision by its unique ID."""
        stmt = select(DecisionLogModel).where(
            DecisionLogModel.id == decision_id.value
        )
        result = await self.session.execute(stmt)
        model = result.scalars().first()
        if model is None:
            return None
        return self._to_domain(model)

    async def query(
        self,
        agent: AgentRole | None = None,
        outcome: DecisionOutcome | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 100,
    ) -> list[Decision]:
        """Query decisions with optional filters."""
        stmt = select(DecisionLogModel)

        if agent:
            stmt = stmt.where(DecisionLogModel.agent == agent.value)
        if outcome:
            stmt = stmt.where(DecisionLogModel.outcome == outcome.value)
        if start:
            stmt = stmt.where(DecisionLogModel.timestamp >= start)
        if end:
            stmt = stmt.where(DecisionLogModel.timestamp <= end)

        stmt = stmt.order_by(DecisionLogModel.timestamp.desc()).limit(limit)

        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [self._to_domain(m) for m in models]

    async def count(
        self,
        agent: AgentRole | None = None,
        outcome: DecisionOutcome | None = None,
    ) -> int:
        """Count decisions matching optional filters."""
        from sqlalchemy import func

        stmt = select(func.count(DecisionLogModel.id))

        if agent:
            stmt = stmt.where(DecisionLogModel.agent == agent.value)
        if outcome:
            stmt = stmt.where(DecisionLogModel.outcome == outcome.value)

        result = await self.session.execute(stmt)
        return result.scalar() or 0

    def _to_row(self, decision: Decision) -> dict:
        """Convert domain Decision to database row dict."""
        return {
            "id": decision.id.value,
            "agent": decision.agent.value,
            "event_type": decision.event_type,
            "trigger_rule": decision.trigger,
            "pool_address": decision.pool_address.value if decision.pool_address else None,
            "outcome": decision.outcome.value,
            "timestamp": decision.timestamp,
            "features": json.dumps(decision.features),
            "metadata": json.dumps(decision.metadata),
        }

    def _to_domain(self, model: DecisionLogModel) -> Decision:
        """Convert database model to domain Decision."""
        return Decision(
            id=DecisionId(value=model.id),
            agent=AgentRole(model.agent),
            event_type=model.event_type,
            trigger=model.trigger_rule or "",
            pool_address=None,  # TODO: Add PoolAddress if model.pool_address else PoolAddress(value=model.pool_address)
            outcome=DecisionOutcome(model.outcome),
            timestamp=model.timestamp,
            features=json.loads(model.features) if model.features else {},
            metadata=json.loads(model.metadata_) if model.metadata_ else {},
        )
