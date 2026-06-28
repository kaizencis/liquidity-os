"""Decision entity for Liquidity OS.

[WHY] Shared type for the Decision Log — every agent and service writes
      to it. Represents an auditable decision record.

[OWNERSHIP] Domain layer — entity.

[DEPENDENTS] Allowed: ports.decision_log, agents.oracle, agents.navigator,
             apps.analytics, apps.dashboard.
             Forbidden: infrastructure (database, redis, httpx).

[EXAMPLE]
    from shared.entities.decision import Decision
    from shared.enums import AgentRole, DecisionOutcome

    decision = Decision(
        id=DecisionId.generate(),
        agent=AgentRole.ORACLE,
        event_type="alert_triggered",
        trigger="volatility > 0.15",
        outcome=DecisionOutcome.PENDING,
    )
    assert decision.is_pending
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from shared.enums import AgentRole, DecisionOutcome
from shared.identifiers import DecisionId, PoolAddress


class Decision(BaseModel):
    """[WHY] Represents an auditable decision record in the system.

    [OWNERSHIP] Domain layer — entity.

    [DEPENDENTS] Allowed: ports.decision_log, agents.oracle, agents.navigator,
                 apps.analytics, apps.dashboard, apps.telegram.
                 Forbidden: infrastructure packages.

    [EXAMPLE]
        decision = Decision(
            id=DecisionId.generate(),
            agent=AgentRole.NAVIGATOR,
            event_type="rebalance_proposed",
            trigger="liquidity_out_of_range",
            pool_address=PoolAddress("7Ytt..."),
            outcome=DecisionOutcome.PENDING,
        )
        assert decision.is_pending
        assert decision.agent == AgentRole.NAVIGATOR
    """

    model_config = {"frozen": True}

    id: DecisionId = Field(..., description="Unique decision identifier")
    agent: AgentRole = Field(..., description="Which agent made this decision")
    event_type: str = Field(..., description="Type of decision (e.g., 'alert_triggered')")
    trigger: str = Field(default="", description="What rule/condition triggered this decision")
    pool_address: PoolAddress | None = Field(default=None, description="Related pool (if applicable)")
    outcome: DecisionOutcome = Field(default=DecisionOutcome.PENDING, description="Current outcome status")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the decision was made",
    )
    features: dict = Field(default_factory=dict, description="Feature values at decision time")
    metadata: dict = Field(default_factory=dict, description="Freeform context data")

    @property
    def is_pending(self) -> bool:
        """Check if decision is still pending."""
        return self.outcome == DecisionOutcome.PENDING

    @property
    def is_terminal(self) -> bool:
        """Check if decision has reached a terminal state."""
        return self.outcome in {
            DecisionOutcome.EXECUTED,
            DecisionOutcome.REJECTED,
            DecisionOutcome.CANCELLED,
            DecisionOutcome.EXPIRED,
        }

    def __str__(self) -> str:
        return f"Decision({self.id}, {self.agent.value}, {self.outcome.value})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Decision):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
