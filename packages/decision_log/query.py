"""Decision Log read-only query interface.

[WHY] Provides read-only access to decision log records.
      Separate from write logic (logger.py) for clear CQS separation.

[OWNERSHIP] Infrastructure layer — read path for DecisionLog.

[DEPENDENTS] Allowed: apps, agents (via DecisionLog port).
             Forbidden: shared (must go through ports).

[EXAMPLE]
    from decision_log.query import DecisionQuery

    query = DecisionQuery(session)
    decisions = await query.query_by_agent(AgentRole.ORACLE)
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from decision_log.models import DecisionLogModel
from shared.entities.decision import Decision
from shared.enums import AgentRole, DecisionOutcome
from shared.identifiers import DecisionId


class DecisionQuery:
    """[WHY] Provides read-only queries for the Decision Log.

    [OWNERSHIP] Infrastructure layer — read path.

    [DEPENDENTS] Allowed: apps, agents (via DecisionLog port).
                 Forbidden: shared (must go through ports).

    [EXAMPLE]
        query = DecisionQuery(session)
        oracle_decisions = await query.query_by_agent(AgentRole.ORACLE)
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def query_all(self, limit: int = 100) -> list[Decision]:
        """Retrieve all decisions with limit."""
        stmt = select(DecisionLogModel).order_by(
            DecisionLogModel.timestamp.desc()
        ).limit(limit)

        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [self._to_domain(m) for m in models]

    async def query_by_agent(
        self, agent: AgentRole, limit: int = 100
    ) -> list[Decision]:
        """Retrieve decisions filtered by agent."""
        stmt = (
            select(DecisionLogModel)
            .where(DecisionLogModel.agent == agent.value)
            .order_by(DecisionLogModel.timestamp.desc())
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [self._to_domain(m) for m in models]

    async def query_by_outcome(
        self, outcome: DecisionOutcome, limit: int = 100
    ) -> list[Decision]:
        """Retrieve decisions filtered by outcome."""
        stmt = (
            select(DecisionLogModel)
            .where(DecisionLogModel.outcome == outcome.value)
            .order_by(DecisionLogModel.timestamp.desc())
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [self._to_domain(m) for m in models]

    async def query_by_time_range(
        self,
        start: datetime,
        end: datetime,
        limit: int = 100,
    ) -> list[Decision]:
        """Retrieve decisions within a time range."""
        stmt = (
            select(DecisionLogModel)
            .where(DecisionLogModel.timestamp >= start)
            .where(DecisionLogModel.timestamp <= end)
            .order_by(DecisionLogModel.timestamp.desc())
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [self._to_domain(m) for m in models]

    async def count(
        self,
        agent: AgentRole | None = None,
        outcome: DecisionOutcome | None = None,
    ) -> int:
        """Count decisions matching optional filters."""
        stmt = select(func.count(DecisionLogModel.id))

        if agent:
            stmt = stmt.where(DecisionLogModel.agent == agent.value)
        if outcome:
            stmt = stmt.where(DecisionLogModel.outcome == outcome.value)

        result = await self.session.execute(stmt)
        return result.scalar() or 0

    def _to_domain(self, model: DecisionLogModel) -> Decision:
        """Convert database model to domain Decision."""
        return Decision(
            id=DecisionId(value=model.id),
            agent=AgentRole(model.agent),
            event_type=model.event_type,
            trigger=model.trigger_rule or "",
            pool_address=None,
            outcome=DecisionOutcome(model.outcome),
            timestamp=model.timestamp,
            features=json.loads(model.features) if model.features else {},
            metadata=json.loads(model.metadata_) if model.metadata_ else {},
        )
