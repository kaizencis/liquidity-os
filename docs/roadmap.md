# Liquidity OS — Development Roadmap

> **Lead Architect:** Ari R. Y.
> **Last updated:** June 25, 2026
>
> **Rule:** Every milestone must be reviewed and approved before implementation begins.
> No code is written without an approved milestone plan.

---

## Legend

| Icon | Meaning |
|------|---------|
| 📐 | Design / Architecture |
| 🏗️ | Implementation |
| 🧪 | Testing |
| 📦 | Package / Library |
| 🔌 | Adapter / Integration |
| 🤖 | Agent |
| 🖥️ | App / Entrypoint |
| 🔧 | Infrastructure / DevOps |
| 📖 | Documentation |

---

## Naming Conventions

| Codename | Public Name | Folder | Role |
|----------|-------------|--------|------|
| **Hermes** | Collector Service | `apps/collector/` | Data ingestion, event emission |
| **Oracle** | Oracle Agent | `agents/oracle/` | Monitoring, alerting |
| **Navigator** | Navigator Agent | `agents/navigator/` | Execution, rebalancing |

> Hermes is an **internal codename only** — not exposed in APIs, UI, or agent roles.

---

## Dependency Graph

```
M1  (Shared Domain) ──────────► M3  (Database) ──► M5  (Collector)
       │                              │                  │
       │                              │                  ▼
       ▼                              │            M6  (Feature Store)
M2  (Decision Log)                    │                  │
       │                              │            ┌─────┴─────┐
       │                              │            ▼           ▼
       │                              │      M7 (Simulation) M8 (Rule Engine)
       │                              │            │           │
       │                              │            ▼           ▼
       │                              │            └───► M9 (Analytics)
       │                              │                      │
       │                              │               ┌──────┴──────┐
       │                              │               ▼             ▼
       │                              │          M10 (Oracle)  M11 (Navigator)
       │                              │               │             │
       │                              │               └──────┬──────┘
       │                              │                      ▼
       │                              │               M12 (Telegram)
       │                              │               M13 (Dashboard)
       │                              │                      │
       │                              │                      ▼
       │                              │               M14 (Production)
       │                              │
       ▼                              ▼
M4  (Meteora DLMM Adapter) ─────► M5  (Collector)
```

---

## Milestones

---

### M0 — Project Scaffolding ✅ *(Completed)*

| Field | Value |
|-------|-------|
| **Goal** | Initialize monorepo structure, version control, and root-level configuration files |
| **Expected output** | Git repo with directory tree, README, .gitignore, LICENSE, docker-compose.yml, .env.example |
| **Folders affected** | Root |
| **Difficulty** | ⬜ Trivial |
| **Dependencies** | None |

---

### M1 — Shared Domain Package

| Field | Value |
|-------|-------|
| **Goal** | Define every domain entity, value object, enum, and port interface that the entire system depends on. **Zero infrastructure dependencies.** |
| **Expected output** | `packages/shared/` with pure Python domain model |
| **Folders affected** | `packages/shared/` |
| **Difficulty** | 🟡 Medium |
| **Dependencies** | None |

#### Files to create

```
packages/shared/
├── __init__.py
├── entities/
│   ├── __init__.py
│   ├── pool.py          # Pool, PoolStatus, LbPair
│   ├── position.py      # Position, PositionStatus, PositionStats
│   ├── token.py         # Token, TokenAmount, USDValue
│   ├── protocol.py      # Protocol, Yield, FeeTier
│   └── decision.py      # DecisionRecord, DecisionOutcome (for Decision Log)
├── value_objects/
│   ├── __init__.py
│   ├── price.py         # Price, PriceRange, sqrtPrice
│   ├── liquidity.py     # Liquidity, LiquidityDistribution
│   ├── time_series.py   # TimestampedValue, OHLC, Volume
│   └── identifiers.py   # PoolAddress, PositionAddress, TxSignature, DecisionId
├── enums.py             # Chain, PoolState, PositionSide, RiskLevel, AgentRole
├── exceptions.py        # DomainException, PoolNotFound, InvalidConfiguration
├── ports/
│   ├── __init__.py
│   ├── pool_repo.py     # PoolRepository (interface)
│   ├── position_repo.py # PositionRepository (interface)
│   ├── collector.py     # PoolDataCollector (interface)
│   ├── notifier.py      # Notifier (interface)
│   ├── feature_store.py # FeatureStore (interface)
│   ├── decision_log.py  # DecisionLog (interface)
│   └── event_bus.py     # EventBus (interface)
├── events.py            # Domain events: PoolUpdated, PositionRebalanced, AlertTriggered
└── config.py            # BaseSettings model for shared config fields
```

#### Key design decisions

- **Absolute zero dependencies** — only `pydantic` (validated domain models) + stdlib (`enum`, `abc`, `dataclasses`). No SQLAlchemy, no httpx, no Redis, no environment access.
- All **ports** are abstract base classes (ABCs). Infra implements, domain never knows.
- **Domain events** use a simple dataclass pattern — no event bus dependency at this layer.
- **Value objects** are immutable — every setter returns a new instance.
- **Entities** have identity (`.id` field), value objects are compared by value.
- **`config.py`** uses Pydantic `BaseSettings` but defines NO concrete settings — only the base schema. Concrete settings live in each app/package.

#### Why this file exists

| File | Why |
|------|-----|
| `entities/pool.py` | Central entity — everything references a pool. Must exist before collector, analytics, or agents. |
| `entities/position.py` | Represents a concentrated liquidity position. Used by agents, dashboard, and telegram. |
| `entities/decision.py` | Shared type for the Decision Log — every agent and service writes to it. |
| `value_objects/price.py` | Price math is subtle (sqrtPrice, tick index, decimal scaling). Encapsulated once here. |
| `ports/*.py` | Clean architecture hinges on dependency inversion. These ABCs let infra code depend on domain, not vice versa. |
| `ports/decision_log.py` | Audit trail interface — used by Oracle, Navigator, Analytics to record decisions. |
| `events.py` | Decouples components: collector emits `PoolUpdated`, rule engine subscribes, no direct coupling. |

#### Dependencies

| Depends on | Used by |
|------------|---------|
| **Nothing** (pure Python) | Every other package and app |

> **Invariant:** This package must NEVER import: `sqlalchemy`, `httpx`, `redis`, `fastapi`, `os`, `dotenv`, or any infrastructure code. Violation = build failure.

---

### M2 — Decision Log Package

| Field | Value |
|-------|-------|
| **Goal** | Implement an immutable audit trail that records every agent decision: who decided, what action, which features/rules triggered it, and the outcome. |
| **Expected output** | `packages/decision-log/` with append-only log writer and query interface |
| **Folders affected** | `packages/decision-log/` |
| **Difficulty** | 🟢 Low |
| **Dependencies** | M1 (shared — entities/decision, ports/decision_log) |

#### Files to create

```
packages/decision-log/
├── __init__.py
├── logger.py            # DecisionLogger — append-only write interface
├── query.py             # DecisionQuery — read and filter past decisions
├── models.py            # Internal DB models for decision_log table
├── settings.py          # Retention policy, storage config
├── pyproject.toml
└── tests/
    ├── test_logger.py   # Unit: verify append-only semantics
    └── test_query.py    # Unit: verify filtering and pagination
```

#### Key design decisions

- **Append-only** — no update, no delete. Decisions are immutable once written.
- **Structured context** — each record captures: agent, event_type, trigger rule, feature snapshot, outcome.
- **Queryable** — filter by agent, time range, event type, outcome. Supports pagination.
- **Retention configurable** — TTL-based cleanup (default: 90 days).
- **Implements `DecisionLog` port** from shared — DB implementation lives here, interface in shared.

#### Why this file exists

| File | Why |
|------|-----|
| `logger.py` | Core write path — every agent calls this on every decision. Must be fast and reliable. |
| `query.py` | Read path — dashboard and analytics query decisions for reports and debugging. |
| `models.py` | SQLAlchemy models for the `decision_log` table — kept internal, not exposed via ports. |
| `settings.py` | Retention, batch size, storage backend selection. |

#### Dependencies

| Depends on | Used by |
|------------|---------|
| M1 (shared) | M10 (Oracle — logs alerts), M11 (Navigator — logs executions), M9 (Analytics — reads for reports) |

---

### M3 — Database Package

| Field | Value |
|-------|-------|
| **Goal** | Implement repository ports using PostgreSQL + SQLAlchemy 2.0. Provide Alembic migrations, connection management, and a repository factory. |
| **Expected output** | `packages/database/` with models, migrations, and Postgres-backed repositories |
| **Folders affected** | `packages/database/` |
| **Difficulty** | 🟡 Medium |
| **Dependencies** | M1 (shared — ports, entities) |

#### Files to create

```
packages/database/
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── base.py            # DeclarativeBase, common mixins (TimestampMixin, UUIDPk)
│   ├── pool_model.py      # ORM: pools table
│   ├── position_model.py  # ORM: positions table
│   └── decision_model.py  # ORM: decision_log table (internal to decision-log package)
├── repositories/
│   ├── __init__.py
│   ├── pool_repo_impl.py      # PoolRepository implementation
│   └── position_repo_impl.py  # PositionRepository implementation
├── migrations/
│   ├── env.py
│   └── versions/
├── connection.py          # AsyncEngine factory, sessionmaker, health check
├── alembic.ini
├── pyproject.toml
└── tests/
    ├── conftest.py        # Test DB in Docker, rollback after each test
    ├── test_pool_repo.py
    └── test_position_repo.py
```

#### Key design decisions

- **SQLAlchemy 2.0 style** — `select()` statements, `asyncpg` driver, no `Session.query()` legacy.
- **Repositories accept a session** — no global session state, no `request.session` magic.
- **Migrations are explicit** — every schema change is a new Alembic migration file.
- **Test containers** — integration tests spin a real Postgres via `testcontainers` or Docker.

#### Dependencies

| Depends on | Used by |
|------------|---------|
| M1 (shared/ports, entities) | M5 (Collector), M6 (Feature Store), M9 (Analytics), Agents |

---

### M4 — Meteora DLMM Adapter

| Field | Value |
|-------|-------|
| **Goal** | Implement the `PoolDataCollector` port as a concrete HTTP + WebSocket client for the Meteora DLMM API. Handles rate limiting, reconnection, data mapping from raw JSON to domain entities. |
| **Expected output** | `apps/collector/src/adapters/` with Meteora API client |
| **Folders affected** | `apps/collector/src/adapters/` |
| **Difficulty** | 🟡 Medium |
| **Dependencies** | M1 (shared — entities, ports, value_objects) |

#### Files to create

```
apps/collector/src/adapters/
├── __init__.py
├── meteora_client.py      # HTTP client (httpx.AsyncClient)
├── meteora_ws.py          # WebSocket stream handler
├── mapper.py              # Raw JSON → domain entities
└── rate_limiter.py        # Token bucket rate limiter

apps/collector/tests/
├── conftest.py
├── test_meteora_client.py     # Mocked HTTP
└── test_mapper.py             # Fixture JSON → entities

apps/collector/pyproject.toml
```

#### Key design decisions

- **httpx** for async HTTP, **websockets** for real-time streams.
- **Mapper is pure function** — `raw_json -> Pool` — no side effects, trivially testable.
- **Rate limiter** is its own class — configurable, testable, not buried in the client.
- **WS handler** emits domain events on the bus — never touches the database directly.

#### Dependencies

| Depends on | Used by |
|------------|---------|
| M1 (entities, ports, value_objects) | M5 (Collector Service) |

---

### M5 — Collector Service (codename: Hermes)

| Field | Value |
|-------|-------|
| **Goal** | Build the runnable collector service: polls Meteora DLMM on a schedule, persists data to Postgres via repositories, emits domain events, handles graceful shutdown and error recovery. |
| **Expected output** | Runnable `collector` service with health endpoint and Prometheus metrics |
| **Folders affected** | `apps/collector/` |
| **Difficulty** | 🟠 High |
| **Dependencies** | M1, M3 (Database), M4 (Meteora Adapter) |

#### Files to create

```
apps/collector/src/
├── __init__.py
├── main.py                  # FastAPI/ASGI entrypoint, lifespan, DI
├── settings.py              # Collector-specific settings (poll interval, pools)
├── services/
│   ├── __init__.py
│   ├── ingestion.py         # Orchestrates: fetch → map → store → emit events
│   └── scheduler.py         # Background task loop (APSchedule / asyncio)
├── api/
│   ├── __init__.py
│   └── health.py            # GET /health, GET /metrics
└── di.py                    # Dependency injection: wire repositories to services

apps/collector/tests/
├── test_ingestion.py        # Integration: fake API → fake repo → verify
└── test_scheduler.py

apps/collector/pyproject.toml
apps/collector/Dockerfile
```

#### Key design decisions

- **FastAPI app** — health checks and metrics are essential in production. Uvicorn lifespan management is better than raw asyncio loops.
- **Ingestion service** is the core use case — it takes a collector port, a repository port, and orchestrates the flow. Pure dependency injection, no globals.
- **Event emission** — after storing data, emit `PoolUpdated` / `PositionUpdated` via the EventBus port.
- **Scheduler** is a controlled background task — not a separate process. Must gracefully stop on SIGTERM.
- **DI is explicit** — manual wiring in `di.py`, not `fastapi.Depends` for infrastructure concerns.

#### Why codename Hermes

The Collector Service is the system's central nervous system — it ingests all external data and emits the events that drive everything downstream. "Hermes" (messenger of the gods) is the internal codename. Not exposed in APIs, logs, or user-facing text.

#### Dependencies

| Depends on | Used by |
|------------|---------|
| M1, M3, M4 | M6 (Feature Store), M9 (Analytics), M10 (Oracle), M11 (Navigator) |

---

### M6 — Feature Store Package

| Field | Value |
|-------|-------|
| **Goal** | Compute and cache derived market features (volatility, volume change, price ranges, spread) from raw pool data. Redis-backed with TTL-based invalidation. |
| **Expected output** | `packages/feature-store/` with computation functions and a Redis-backed storage adapter |
| **Folders affected** | `packages/feature-store/` |
| **Difficulty** | 🟢 Low |
| **Dependencies** | M1 (shared — entities, value_objects, ports/feature_store), M3 (historical data from DB) |

#### Files to create

```
packages/feature-store/
├── __init__.py
├── features/
│   ├── __init__.py
│   ├── volatility.py        # Rolling volatility, ATR
│   ├── volume.py            # Volume delta, volume profile
│   ├── price.py             # Price range, bin activity, spread
│   └── liquidity.py         # Liquidity depth, concentration ratio
├── store.py                 # FeatureStore implementation (Redis)
├── computer.py              # FeatureComputer — orchestrates computation pipeline
├── settings.py              # Redis config, TTLs, window sizes
├── pyproject.toml
└── tests/
    ├── test_volatility.py   # Unit tests with fixed inputs
    └── test_store.py        # Integration with Redis (testcontainers)
```

#### Key design decisions

- **Features are pure functions** — `compute_volatility(prices: Sequence[Price]) -> float`. No IO, trivial to unit test.
- **FeatureComputer** composes multiple feature functions and caches results.
- **Redis store** implements the `FeatureStore` port — swap to any other store without changing features.
- **TTLs are per-feature** — volatile features recompute every tick, stable ones last longer.

#### Dependencies

| Depends on | Used by |
|------------|---------|
| M1, M3 | M7 (Simulation), M8 (Rule Engine), M9 (Analytics), M10 (Oracle) |

---

### M7 — Simulation Engine

| Field | Value |
|-------|-------|
| **Goal** | Replay historical data snapshots through the Rule Engine to validate rule changes before production. Dry-run mode for testing rebalancing strategies without real transactions. |
| **Expected output** | `packages/simulation/` with replay engine, comparison reporter, and dry-run executor |
| **Folders affected** | `packages/simulation/` |
| **Difficulty** | 🟡 Medium |
| **Dependencies** | M1 (shared), M6 (Feature Store), M8 (Rule Engine) |

#### Files to create

```
packages/simulation/
├── __init__.py
├── replay.py               # ReplayEngine — steps through historical snapshots
├── scenario.py             # Scenario — defines what to test (time range, rule config)
├── reporter.py             # Compare outcomes: current rules vs. modified rules
├── executor.py             # DryRunExecutor — runs Navigator logic without transactions
├── snapshot.py             # SnapshotLoader — loads historical data from DB
├── settings.py             # Simulation config (max steps, timeout, output format)
├── pyproject.toml
└── tests/
    ├── test_replay.py      # Unit: step through fixed snapshot sequence
    ├── test_reporter.py    # Unit: compare two outcome sets
    └── test_scenario.py    # Unit: scenario construction and validation
```

#### Key design decisions

- **ReplayEngine is deterministic** — given the same snapshots and rule config, it produces the same decisions every time.
- **Scenario is a data class** — time range, rule overrides, feature overrides. Serializable to JSON for reproducibility.
- **Reporter produces structured output** — JSON diff between current and proposed rule outcomes. Consumed by dashboard and Telegram.
- **DryRunExecutor wraps Navigator logic** — same strategy code, different output (log instead of transaction).
- **Does NOT touch production** — reads historical snapshots, writes to simulation output (separate table or file).

#### Why this milestone exists

Before deploying a new rule or changing a rebalancing threshold, operators need confidence the change won't cause harm. Simulation Engine provides that confidence by replaying history with the proposed changes and comparing outcomes.

#### Use cases

1. **Pre-deployment validation:** "Will this new volatility threshold have triggered fewer false positives last month?"
2. **Strategy backtesting:** "How would a more aggressive rebalance strategy have performed during the May crash?"
3. **Regression testing:** "Did my refactored rule engine produce the same decisions as the old one?"

#### Dependencies

| Depends on | Used by |
|------------|---------|
| M1, M6 (Feature Store), M8 (Rule Engine) | M9 (Analytics — runs simulations), M13 (Dashboard — shows results) |

---

### M8 — Rule Engine Package

| Field | Value |
|-------|-------|
| **Goal** | Define, register, and evaluate rebalancing rules. Rules are declarative conditions that trigger actions (alert, rebalance, escalate). |
| **Expected output** | `packages/rule-engine/` with rule DSL, registry, evaluator, and action dispatcher |
| **Folders affected** | `packages/rule-engine/` |
| **Difficulty** | 🟠 High |
| **Dependencies** | M1 (shared — enums, events), M6 (Feature Store — for feature values) |

#### Files to create

```
packages/rule-engine/
├── __init__.py
├── ast.py                  # Rule AST nodes: Condition, Action, Rule
├── parser.py               # Parse rule expression strings → AST
├── registry.py             # RuleRegistry — load, list, enable/disable rules
├── evaluator.py            # Evaluate a rule's conditions against current state + features
├── actions.py              # Action definitions: Alert, Rebalance, Escalate, Log
├── engine.py               # RuleEngine — orchestrates evaluation of all active rules
├── settings.py             # Rule limits, eval timeout, cooldown
├── pyproject.toml
└── tests/
    ├── test_ast.py
    ├── test_parser.py
    ├── test_evaluator.py
    └── test_engine.py
```

#### Key design decisions

- **Rules are data, not code** — stored as structured expressions (AST), not Python lambdas. Makes them persistable, auditable, and UI-editable.
- **Evaluator is pure** — `evaluate(rule, state, features) -> ActionResult`. No side effects.
- **Engine handles cooldowns** — prevents repeated triggers on the same condition.
- **Actions are extensible** — add a new action type by implementing a single function signature.
- **Tested via Simulation Engine** — before deploying rule changes, replay history to validate.

#### Example rule expression

```
when pool.volatility_24h > 0.15
  and pool.liquidity_concentration > 0.8
then alert("High volatility in concentrated pool")
```

#### Dependencies

| Depends on | Used by |
|------------|---------|
| M1 (shared), M6 (Feature Store) | M7 (Simulation), M9 (Analytics), M10 (Oracle), M11 (Navigator) |

---

### M9 — Analytics Service

| Field | Value |
|-------|-------|
| **Goal** | Continuous computation of pool-level health metrics, signal generation, and periodic reporting. Internal HTTP API for agents and dashboard. |
| **Expected output** | Runnable `analytics` service computing metrics on schedule, exposing an internal HTTP API |
| **Folders affected** | `apps/analytics/` |
| **Difficulty** | 🟡 Medium |
| **Dependencies** | M1, M3 (Database), M6 (Feature Store), M8 (Rule Engine) |

#### Files to create

```
apps/analytics/src/
├── __init__.py
├── main.py                  # FastAPI entrypoint
├── settings.py              # Metrics config, compute intervals
├── services/
│   ├── __init__.py
│   ├── metric_computer.py   # Coordinates DB read → feature compute → store
│   ├── signal_generator.py  # Buy/sell/hold signals from features + rules
│   └── reporter.py          # Periodic summary reports (daily, hourly)
├── api/
│   ├── __init__.py
│   ├── health.py
│   ├── metrics.py           # GET /metrics/:pool — queryable by agents
│   └── signals.py           # GET /signals/:pool — latest signal
└── di.py                    # Wire dependencies

apps/analytics/tests/
├── test_metric_computer.py
└── test_signal_generator.py

apps/analytics/pyproject.toml
apps/analytics/Dockerfile
```

#### Key design decisions

- **Reads from DB, writes to feature store** — doesn't own data, only derives it.
- **Signal generator** uses rule engine to produce actionable signals.
- **API is internal only** — not exposed to the internet, consumed by agents and dashboard.
- **Reporter produces structured reports** — consumed by Telegram app for daily digests.

#### Dependencies

| Depends on | Used by |
|------------|---------|
| M1, M3, M6, M8 | M10 (Oracle — reads signals), M12 (Telegram — reports) |

---

### M10 — Oracle Agent (Monitor)

| Field | Value |
|-------|-------|
| **Goal** | Autonomous monitoring agent that continuously evaluates pool health, detects anomalies, and generates alerts. Oracle is the "eyes" of the system. |
| **Expected output** | Runnable agent process with configurable monitoring loops and alert dispatch |
| **Folders affected** | `agents/oracle/` |
| **Difficulty** | 🟡 Medium |
| **Dependencies** | M1 (shared — ports/notifier), M6 (Feature Store), M9 (Analytics — metrics API) |

#### Files to create

```
agents/oracle/src/
├── __init__.py
├── main.py                  # Agent entrypoint, lifecycle
├── settings.py              # Pool watchlist, alert thresholds, check interval
├── monitors/
│   ├── __init__.py
│   ├── pool_health.py       # Health checks: TVL, volume, fees, utilization
│   ├── anomaly.py           # Anomaly detection: price spike, drop, divergence
│   └── risk.py              # Risk assessment: impermanent loss, concentration risk
├── alerts/
│   ├── __init__.py
│   ├── dispatcher.py        # Route alerts to notifier (Telegram, webhook, log)
│   └── severity.py          # Alert severity levels, escalation rules
└── reporter.py              # Generate periodic status reports

agents/oracle/tests/
├── test_pool_health.py
├── test_anomaly.py
└── test_dispatcher.py

agents/oracle/pyproject.toml
agents/oracle/Dockerfile
```

#### Key design decisions

- **Oracle is stateless** — reads metrics from Analytics API, writes alerts to message bus / DB. No local state beyond configuration.
- **Monitors are plugins** — add a new monitor by creating a file in `monitors/` and registering it. No changes to core logic.
- **Alerts go through the Notifier port** — Telegram, Slack, webhook — all pluggable.
- **Oracle does NOT rebalance** — it only watches and alerts. Execution is Navigator's job.
- **Every decision is logged** — Oracle calls Decision Log on every alert generated.

#### Dependencies

| Depends on | Used by |
|------------|---------|
| M1, M6, M9 | M12 (Telegram — receives alerts), M13 (Dashboard — shows alerts) |

---

### M11 — Navigator Agent (Executor)

| Field | Value |
|-------|-------|
| **Goal** | Execution agent that handles rebalancing actions: calculates target allocations, simulates impact, prepares transactions, and manages approval workflows. |
| **Expected output** | Runnable agent process with action queue, transaction builder, and approval state machine |
| **Folders affected** | `agents/navigator/` |
| **Difficulty** | 🔴 Very High |
| **Dependencies** | M1 (shared — ports, entities), M3 (Database — persist actions), M8 (Rule Engine — triggers), M9 (Analytics — signals) |

#### Files to create

```
agents/navigator/src/
├── __init__.py
├── main.py                  # Agent entrypoint, lifecycle
├── settings.py              # Slippage tolerance, max tx size, approval config
├── executor/
│   ├── __init__.py
│   ├── strategy.py          # Rebalancing strategy: compute target distribution
│   ├── simulator.py         # Simulate impact of a rebalance before executing
│   └── tx_builder.py        # Build Solana transaction instructions
├── approval/
│   ├── __init__.py
│   ├── workflow.py          # Approval state machine (pending → approved → executed / rejected)
│   ├── thresholds.py        # Auto-approve if under threshold, escalate if over
│   └── timeout.py           # Auto-reject if not approved within TTL
└── actions/
    ├── __init__.py
    └── action_queue.py      # Persistent queue of pending actions

agents/navigator/tests/
├── test_strategy.py
├── test_simulator.py
├── test_workflow.py
└── test_action_queue.py

agents/navigator/pyproject.toml
agents/navigator/Dockerfile
```

#### Key design decisions

- **Navigator never holds keys** — transaction signing is delegated to a wallet service / hardware module. Navigator only builds and proposes transactions.
- **Approval workflow is a state machine** — clear states: `draft → pending → approved → executed | rejected → cancelled`.
- **Auto-approve thresholds** — small rebalances (configurable) skip human approval. Large moves require manual confirm (via Telegram).
- **Action queue is persisted in Postgres** — survives agent restart.
- **Every decision is logged** — Navigator calls Decision Log on every execution attempt.

#### Dependencies

| Depends on | Used by |
|------------|---------|
| M1, M3, M8, M9 | M12 (Telegram — approval UI), M13 (Dashboard — status) |

---

### M12 — Telegram Bot App

| Field | Value |
|-------|-------|
| **Goal** | Full-featured Telegram bot for interacting with Liquidity OS: real-time alerts, rebalance approvals, pool queries, daily reports, and manual commands. |
| **Expected output** | Runnable Telegram bot with command handlers, inline keyboards, and notification dispatch |
| **Folders affected** | `apps/telegram/` |
| **Difficulty** | 🟡 Medium |
| **Dependencies** | M1, M9 (Analytics — reports), M10 (Oracle — alerts), M11 (Navigator — approvals) |

#### Files to create

```
apps/telegram/src/
├── __init__.py
├── main.py                  # python-telegram-bot entrypoint
├── settings.py              # Bot token, allowed users, chat IDs
├── handlers/
│   ├── __init__.py
│   ├── commands.py          # /start, /status, /pools, /positions, /alerts
│   ├── approvals.py         # Inline keyboard approval for rebalance actions
│   ├── reports.py           # /report daily, /report pool:<address>
│   └── admin.py             # /config, /agents, /override
├── keyboards/
│   ├── __init__.py
│   └── builder.py           # Reusable inline keyboard layouts
├── dispatcher.py            # Route notifications to Telegram (implements Notifier port)
└── formatter.py             # Domain entities → Telegram markdown messages

apps/telegram/tests/
├── test_formatter.py
├── test_commands.py
└── test_approvals.py

apps/telegram/pyproject.toml
apps/telegram/Dockerfile
```

#### Key design decisions

- **Telegram is a view layer** — it renders data from APIs, never owns business logic. Approval "yes/no" writes to Navigator's action queue, nothing more.
- **python-telegram-bot v21+** — async-native, webhook support.
- **Formatter is pure** — `Pool -> str`, no IO. Easy to unit test and ensures consistent message formatting.
- **Notifications go through the Notifier port** — if the bot is down, notifications queue in DB for retry.

#### Dependencies

| Depends on | Used by |
|------------|---------|
| M1, M9, M10, M11 | End users |

---

### M13 — Dashboard App

| Field | Value |
|-------|-------|
| **Goal** | Web dashboard for real-time visualization of pool metrics, position health, agent activity, and system status. |
| **Expected output** | Runnable web app with real-time charts, pool overview, and agent activity log |
| **Folders affected** | `apps/dashboard/` |
| **Difficulty** | 🟡 Medium |
| **Dependencies** | M1, M3 (read models), M6 (Feature Store), M9 (Analytics), M10 (Oracle), M11 (Navigator) |

#### Files to create

```
apps/dashboard/
├── backend/
│   ├── src/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI entrypoint
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── pools.py         # GET /api/pools, GET /api/pools/:address
│   │   │   ├── positions.py     # GET /api/positions
│   │   │   ├── agents.py        # GET /api/agents/:name/status
│   │   │   └── system.py        # GET /api/system/health
│   │   └── ws.py                # WebSocket for real-time updates
│   └── pyproject.toml
├── frontend/                    # (optional — can be HTMX instead)
│   ├── package.json
│   ├── pages/
│   ├── components/
│   └── public/
├── Dockerfile
└── tests/
    └── test_routes.py
```

#### Key design decisions

- **Backend is a thin proxy** — reads from DB and feature store, no computation. The analytics service does the work.
- **Real-time via WebSocket** — pushes pool updates from collector to browser.
- **Frontend choice deferred** — architecture supports both Next.js (rich UI) and HTMX (simple, fast). Decide when implementing.

#### Dependencies

| Depends on | Used by |
|------------|---------|
| M1, M3, M6, M9, M10, M11 | End users (ops team) |

---

### M14 — Production Readiness

| Field | Value |
|-------|-------|
| **Goal** | Harden every service for production: refined Dockerfiles, CI/CD pipelines, monitoring, alerting, documentation, and runbooks. |
| **Expected output** | Production-grade deployment artifacts, CI/CD passing, monitoring dashboards, operational runbooks |
| **Folders affected** | `.github/`, `docker/`, `docs/`, `scripts/` |
| **Difficulty** | 🟡 Medium |
| **Dependencies** | All previous milestones |

#### Files to create / update

```
.github/
├── workflows/
│   ├── ci.yml              # Lint → type-check → test on every PR
│   └── cd.yml              # Build → tag → push Docker images
docker/
├── collector.Dockerfile    # Multi-stage, slim images
├── analytics.Dockerfile
├── telegram.Dockerfile
├── dashboard.Dockerfile
├── docker-bake.hcl         # Build all services in parallel
scripts/
├── migrate.sh
├── seed.sh
├── backup.sh
└── restore.sh
docs/
├── architecture.md         # Already created
├── roadmap.md              # This file
├── operations.md           # Runbooks: restart, backup, incident response
├── api.md                  # API reference (auto-generated)
├── deployment.md           # Deployment guide
└── contributing.md         # How to add a new pool, rule, or agent
```

#### Key deliverables

| Deliverable | Description |
|-------------|-------------|
| **CI pipeline** | Ruff lint, mypy type-check, pytest with coverage, Docker build check |
| **CD pipeline** | Docker image build & push on tags, deployment to staging |
| **Dockerfiles** | Multi-stage, distroless runtime images, non-root user, healthcheck |
| **Monitoring** | Prometheus metrics on every service, Grafana dashboard template |
| **Logging** | Structured JSON logs, log aggregation config (Loki / ELK) |
| **Runbooks** | Step-by-step incident response, backup/restore, upgrade procedure |

---

## Summary

| # | Milestone | Folder | Difficulty | Depends on |
|---|-----------|--------|------------|------------|
| M0 | ✅ Project Scaffolding | Root | ⬜ Trivial | — |
| **M1** | **Shared Domain Package** | `packages/shared/` | 🟡 Medium | — |
| **M2** | **Decision Log Package** | `packages/decision-log/` | 🟢 Low | M1 |
| **M3** | **Database Package** | `packages/database/` | 🟡 Medium | M1 |
| **M4** | **Meteora DLMM Adapter** | `apps/collector/src/adapters/` | 🟡 Medium | M1 |
| **M5** | **Collector Service (Hermes)** | `apps/collector/` | 🟠 High | M1, M3, M4 |
| **M6** | **Feature Store Package** | `packages/feature-store/` | 🟢 Low | M1, M3 |
| **M7** | **Simulation Engine** | `packages/simulation/` | 🟡 Medium | M1, M6, M8 |
| **M8** | **Rule Engine Package** | `packages/rule-engine/` | 🟠 High | M1, M6 |
| **M9** | **Analytics Service** | `apps/analytics/` | 🟡 Medium | M1, M3, M6, M8 |
| **M10** | **Oracle Agent (Monitor)** | `agents/oracle/` | 🟡 Medium | M1, M6, M9 |
| **M11** | **Navigator Agent (Executor)** | `agents/navigator/` | 🔴 Very High | M1, M3, M8, M9 |
| **M12** | **Telegram Bot App** | `apps/telegram/` | 🟡 Medium | M1, M9, M10, M11 |
| **M13** | **Dashboard App** | `apps/dashboard/` | 🟡 Medium | M1, M3, M6, M9-M11 |
| **M14** | **Production Readiness** | `.github/`, `docker/`, `docs/`, `scripts/` | 🟡 Medium | All |

---

## Architectural Invariants

These rules apply to every milestone. Violations must be rejected during review.

1. **Domain layer imports NOTHING** outside `packages/shared/`. No FastAPI, no SQLAlchemy, no httpx, no Redis, no `os`, no `dotenv`. This is absolute.
2. **Ports are interfaces, not implementations.** Infra packages implement ports, domain never knows about them.
3. **Apps are thin entrypoints.** They wire dependencies and start loops. Business logic lives in packages or use-case services.
4. **Agents communicate through the bus, not by importing each other.** Oracle → bus → Navigator, never `from agents.navigator import ...`.
5. **Every public function is unit-testable.** Pure logic in domain and use cases. IO is mocked at the port boundary.
6. **Configuration is explicit.** No magic constants in code. Everything configurable via settings / env.
7. **Errors are typed.** Every domain exception has a distinct class. No bare `Exception` or `assert False`.
8. **Every agent decision is logged.** Oracle and Navigator must write to Decision Log before executing any action.
9. **Architectural comments are mandatory.** Every public class/model/interface/service includes: why it exists, which layer owns it, which layers may depend on it, one usage example. See `docs/architecture.md` for the format.
10. **Readability over brevity.** Clear names, explicit logic, short functions, type hints everywhere. No clever one-liners, no magic numbers.
