"""Domain enumerations for Liquidity OS.

[WHY] Enums define the finite set of states and categories that domain
      entities can occupy. They prevent invalid states at the type level
      and make business rules explicit (e.g., only ACTIVE pools can be
      rebalanced).

[OWNERSHIP] Domain layer — used by all entities, ports, apps, and agents.

[DEPENDENTS] Allowed: entities, value_objects, ports, apps, agents.
             Forbidden: infrastructure (database, redis, httpx).

[EXAMPLE]
    from shared.enums import PoolStatus, AgentRole

    if pool.status == PoolStatus.ACTIVE:
        await navigator.rebalance(pool)

    decision = DecisionRecord(agent=AgentRole.ORACLE, ...)
"""

from enum import StrEnum, unique


@unique
class PoolStatus(StrEnum):
    """[WHY] Represents the operational state of a Meteora DLMM pool.

    [OWNERSHIP] Domain layer — immutable enumeration.

    [DEPENDENTS] Allowed: entities.pool, ports.pool_repo,
                 apps.collector, apps.analytics, apps.dashboard,
                 agents.oracle, agents.navigator.

    [EXAMPLE]
        assert pool.status == PoolStatus.ACTIVE
        if pool.status == PoolStatus.CLOSED:
            raise InvalidConfiguration("Cannot rebalance closed pool")
    """

    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"
    MIGRATING = "migrating"


@unique
class PositionStatus(StrEnum):
    """[WHY] Represents the lifecycle state of a liquidity position.

    [OWNERSHIP] Domain layer — immutable enumeration.

    [DEPENDENTS] Allowed: entities.position, ports.position_repo,
                 apps.collector, apps.dashboard, agents.navigator.

    [EXAMPLE]
        if position.status == PositionStatus.ACTIVE:
            await navigator.update_range(position, new_range)
    """

    ACTIVE = "active"
    CLOSED = "closed"
    PENDING_CLOSE = "pending_close"
    LIQUIDATED = "liquidated"


@unique
class PositionSide(StrEnum):
    """[WHY] Indicates which side of the liquidity curve a position covers.

    [OWNERSHIP] Domain layer — immutable enumeration.

    [DEPENDENTS] Allowed: entities.position, apps.collector,
                 agents.navigator.

    [EXAMPLE]
        if position.side == PositionSide.BOTH:
            fee_earned = position.left_fee + position.right_fee
    """

    BOTH = "both"
    BID_ONLY = "bid_only"
    ASK_ONLY = "ask_only"


@unique
class AgentRole(StrEnum):
    """[WHY] Identifies which agent or component made a decision.

    [OWNERSHIP] Domain layer — immutable enumeration.

    [DEPENDENTS] Allowed: entities.decision, ports.decision_log,
                 agents.oracle, agents.navigator, apps.collector.

    [EXAMPLE]
        record = DecisionRecord(
            agent=AgentRole.COLLECTOR,
            event_type="snapshot_created",
            ...
        )
    """

    ORACLE = "oracle"
    NAVIGATOR = "navigator"
    COLLECTOR = "collector"
    SYSTEM = "system"


@unique
class DecisionOutcome(StrEnum):
    """[WHY] Represents the result of a decision or approval workflow.

    [OWNERSHIP] Domain layer — immutable enumeration.

    [DEPENDENTS] Allowed: entities.decision, ports.decision_log,
                 agents.navigator, apps.telegram.

    [EXAMPLE]
        if decision.outcome == DecisionOutcome.APPROVED:
            await navigator.execute(decision)
        elif decision.outcome == DecisionOutcome.EXPIRED:
            await decision_log.archive(decision)
    """

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


@unique
class AlertSeverity(StrEnum):
    """[WHY] Classifies the urgency of an alert for routing and display.

    [OWNERSHIP] Domain layer — immutable enumeration.

    [DEPENDENTS] Allowed: ports.notifier, agents.oracle, apps.telegram.

    [EXAMPLE]
        if severity == AlertSeverity.CRITICAL:
            await notifier.send_alert(alert, priority="high")
    """

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@unique
class RiskLevel(StrEnum):
    """[WHY] Classifies pool or position risk for rule evaluation.

    [OWNERSHIP] Domain layer — immutable enumeration.

    [DEPENDENTS] Allowed: value_objects.feature, ports.feature_provider,
                 rule_engine, agents.oracle.

    [EXAMPLE]
        if risk == RiskLevel.HIGH:
            rule_engine.evaluate("high_risk_pool", context)
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
