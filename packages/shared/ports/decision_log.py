"""Decision log interface for Liquidity OS.

[WHY] Defines the contract for immutable audit trail. Every agent decision
      is recorded here — append-only, queryable, never modified.

[OWNERSHIP] Domain layer — port interface.

[DEPENDENTS] Allowed: decision-log (implements), agents.oracle, agents.navigator,
             apps.analytics, apps.dashboard, apps.telegram.
             Forbidden: infrastructure implementations in this file.

[EXAMPLE]
    from shared.ports.decision_log import DecisionLog

    class PostgresDecisionLog(DecisionLog):
        async def append(self, decision: Decision) -> None:
            # SQL insert here
            ...
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from shared.entities.decision import Decision
from shared.enums import AgentRole, DecisionOutcome
from shared.identifiers import DecisionId


class DecisionLog(ABC):
    """[WHY] Provides append-only audit trail for all agent decisions.

    [OWNERSHIP] Domain layer — defines the contract for decision logging.

    [DEPENDENTS] Allowed: decision-log (implements), oracle, navigator,
                 analytics, dashboard, telegram.
                 Forbidden: shared, database (must go through ports).

    [EXAMPLE]
        log = PostgresDecisionLog(session)
        await log.append(decision)
        record = await log.get_by_id(DecisionId.generate())
    """

    @abstractmethod
    async def append(self, decision: Decision) -> None:
        """Record a new decision (immutable — no update)."""

    @abstractmethod
    async def get_by_id(self, decision_id: DecisionId) -> Decision | None:
        """Retrieve a decision by its unique ID."""

    @abstractmethod
    async def query(
        self,
        agent: AgentRole | None = None,
        outcome: DecisionOutcome | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 100,
    ) -> list[Decision]:
        """Query decisions with optional filters."""

    @abstractmethod
    async def count(
        self,
        agent: AgentRole | None = None,
        outcome: DecisionOutcome | None = None,
    ) -> int:
        """Count decisions matching optional filters."""
