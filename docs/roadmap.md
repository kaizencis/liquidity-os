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

## Dependency Graph

```
M1  (Shared Domain) ──────────► M2  (Database) ──► M4  (Collector App)
                                     │
                                     ▼
                               M5  (Feature Store) ──► M7  (Analytics)
                                     │
                                     ▼
                               M6  (Rule Engine)
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                ▼                ▼
               M8 (Luna)       M9 (Aspro)       M10 (Hermes)
                    │                │                │
                    └────────────────┼────────────────┘
                                     ▼
                              M11 (Telegram App)
                              M12 (Dashboard App)
                                     │
                                     ▼
                              M13 (Production)
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
| **Goal** | Define every domain entity, value object, enum, and port interface that the entire system depends on. This is the **heart of the architecture** — no other package imports concrete infrastructure. |
| **Expected output** | `packages/shared/` with pure Python domain model, no framework dependencies |

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
│   └── agent.py         # AgentTask, AgentLog, AgentDecision
├── value_objects/
│   ├── __init__.py
│   ├── price.py         # Price, PriceRange, sqrtPrice
│   ├── liquidity.py     # Liquidity, LiquidityDistribution
│   ├── time_series.py   # TimestampedValue, OHLC, Volume
│   └── identifiers.py   # PoolAddress, PositionAddress, TxSignature
├── enums.py             # Chain, PoolState, PositionSide, RiskLevel, AgentRole
├── exceptions.py        # DomainException, PoolNotFound, InvalidConfiguration
├── ports/
│   ├── __init__.py
│   ├── pool_repo.py     # PoolRepository (interface)
│   ├── position_repo.py # PositionRepository (interface)
│   ├── collector.py     # PoolDataCollector (interface)
│   ├── notifier.py      # Notifier (interface)
│   ├── feature_store.py # FeatureStore (interface)
│   └── agent_bus.py     # AgentMessageBus (interface)
├── events.py            # Domain events: PoolUpdated, PositionRebalanced, AlertTriggered
└── config.py            # BaseSettings model for shared config fields
```

#### Key design decisions

- **Zero dependencies** except `pydantic` for validated domain models and `enum`/`abc` from stdlib.
- All **ports** are abstract base classes (ABCs). No SQLAlchemy, no Redis, no HTTP — just interfaces.
- **Domain events** use a simple dataclass pattern — no event bus dependency at this layer.
- **Value objects** are immutable — every setter returns a new instance.
- **Entities** have identity (`.id` field), value objects are compared by value.

#### Why this file exists

| File | Why |
|------|-----|
| `entities/pool.py` | Central entity — everything references a pool. Must exist before collector, analytics, or agents. |
| `entities/position.py` | Represents a concentrated liquidity position. Used by agents, dashboard, and telegram. |
| `value_objects/price.py` | Price math is subtle (sqrtPrice, tick index, decimal scaling). Encapsulated once here. |
| `ports/*.py` | Clean architecture hinges on dependency inversion. These ABCs let infra code depend on domain, not vice versa. |
| `events.py` | Decouples components: collector emits `PoolUpdated`, rule engine subscribes, no direct coupling. |

#### Dependencies

| Depends on | Used by |
|------------|---------|
| Nothing (pure Python) | Every other package and app |

| Difficulty | 🟡 Medium — domain modeling decisions are foundational and need care |
|---|---|

---

### M2 — Database Package

| Field | Value |
|-------|-------|
| **Goal** | Implement the `PoolRepository` and `PositionRepository` ports using PostgreSQL + SQLAlchemy 2.0. Provide Alembic migrations, connection management, and a repository factory. |
| **Expected output** | `packages/database/` with models, migrations, and Postgres-backed repository implementations |

#### Files to create

```
packages/database/
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── base.py          # DeclarativeBase, common mixins (TimestampMixin, UUIDPk)
│   ├── pool_model.py    # ORM: pools table
│   └── position_model.py # ORM: positions table
├── repositories/
│   ├── __init__.py
│   ├── pool_repo_impl.py    # PoolRepository implementation
│   └── position_repo_impl.py # PositionRepository implementation
├── migrations/          # Alembic
│   ├── env.py
│   └── versions/
├── connection.py        # AsyncEngine factory, sessionmaker, health check
├── alembic.ini
├── pyproject.toml
└── tests/
    ├── conftest.py      # Test DB in Docker, rollback after each test
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
| M1 (shared/ports, entities) | M4 (Collector), M5 (Feature Store), M7 (Analytics), Agents |

| Difficulty | 🟡 Medium — SQLAlchemy async setup, migration workflow, test infrastructure |
|---|---|

---

### M3 — Meteora DLMM Adapter

| Field | Value |
|-------|-------|
| **Goal** | Implement the `PoolDataCollector` port as a concrete HTTP + WebSocket client for the Meteora DLMM API. Handles rate limiting, reconnection, data mapping from raw JSON to domain entities. |
| **Expected output** | `apps/collector/src/adapters/` with Meteora API client |

#### Files to create

```
apps/collector/
├── src/
│   ├── __init__.py
│   └── adapters/
│       ├── __init__.py
│       ├── meteora_client.py      # HTTP client (httpx.AsyncClient)
│       ├── meteora_ws.py          # WebSocket stream handler
│       ├── mapper.py              # Raw JSON → domain entities
│       └── rate_limiter.py        # Token bucket rate limiter
├── tests/
│   ├── conftest.py
│   ├── test_meteora_client.py     # Mocked HTTP
│   └── test_mapper.py             # Fixture JSON → entities
├── pyproject.toml
└── Dockerfile                     # (created later in M13, but stub here)
```

#### Key design decisions

- **httpx** for async HTTP, **websockets** for real-time streams.
- **Mapper is pure function** — `raw_json -> Pool` — no side effects, trivially testable.
- **Rate limiter** is its own class — configurable, testable, not buried in the client.
- **WS handler** emits domain events on the bus — never touches the database directly.

#### Dependencies

| Depends on | Used by |
|------------|---------|
| M1 (entities, ports, value_objects) | M4 (Collector App) |

| Difficulty | 🟡 Medium — WebSocket reconnection logic, API quirks, rate limiting |
|---|---|

---

### M4 — Collector Application

| Field | Value |
|-------|-------|
| **Goal** | Build the runnable collector service: polls Meteora DLMM on a schedule, persists data to Postgres via repositories, handles graceful shutdown and error recovery. |
| **Expected output** | Runnable `collector` service with health endpoint and Prometheus metrics |

#### Files to create

```
apps/collector/
├── src/
│   ├── __init__.py
│   ├── main.py                  # FastAPI/ASGI entrypoint, lifespan, DI
│   ├── settings.py              # Collector-specific settings (poll interval, pools)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ingestion.py         # Orchestrates: fetch → map → store
│   │   └── scheduler.py         # Background task loop (APSchedule / asyncio)
│   ├── api/
│   │   ├── __init__.py
│   │   └── health.py            # GET /health, GET /metrics
│   └── di.py                    # Dependency injection: wire repositories to services
├── tests/
│   ├── test_ingestion.py        # Integration: fake API → fake repo → verify
│   └── test_scheduler.py
├── pyproject.toml
└── Dockerfile
```

#### Key design decisions

- **FastAPI app** even if no HTTP API is needed — health checks and metrics are essential in production. Uvicorn lifespan management is better than raw asyncio loops.
- **Ingestion service** is the core use case — it takes a collector port, a repository port, and orchestrates the flow. Pure dependency injection, no globals.
- **Scheduler** is a controlled background task — not a separate process. Must gracefully stop on SIGTERM.
- **DI is explicit** — manual wiring in `di.py` (or lightweight `lazy` container), not `fastapi.Depends` for infrastructure concerns.

#### Dependencies

| Depends on | Used by |
|------------|---------|
| M1, M2, M3 | M5 (data for features), M7 (analytics), all agents |

| Difficulty | 🟠 High — first integration of all layers, background task lifecycle, production readiness |
|---|---|

---

### M5 — Feature Store Package

| Field | Value |
|-------|-------|
| **Goal** | Compute and cache derived market features (volatility, volume change, price ranges, spread) from raw pool data. Redis-backed with TTL-based invalidation. |
| **Expected output** | `packages/feature-store/` with computation functions and a Redis-backed storage adapter |

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
| M1 (entities, value_objects, ports/feature_store), M2 (historical data from DB) | M6 (Rule Engine), M7 (Analytics), M8 (Luna) |

| Difficulty | 🟢 Low — math-heavy but isolated, well-defined scope |
|---|---|

---

### M6 — Rule Engine Package

| Field | Value |
|-------|-------|
| **Goal** | Define, register, and evaluate rebalancing rules. Rules are declarative conditions that trigger actions (alert, rebalance, escalate). |
| **Expected output** | `packages/rule-engine/` with rule DSL, registry, evaluator, and action dispatcher |

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

#### Example rule expression

```
when pool.volatility_24h > 0.15
  and pool.liquidity_concentration > 0.8
then alert("High volatility in concentrated pool")
```

#### Dependencies

| Depends on | Used by |
|------------|---------|
| M1 (entities, enums, events), M5 (features for conditions) | M7 (Analytics), M8 (Luna), M9 (Aspro) |

| Difficulty | 🟠 High — AST design is subtle, parser needs care, evaluation must be safe (no infinite loops) |
|---|---|

---

### M7 — Analytics Service

| Field | Value |
|-------|-------|
| **Goal** | Continuous computation of pool-level health metrics, signal generation, and periodic reporting. Internal gRPC/REST API for agents to query metrics. |
| **Expected output** | Runnable `analytics` service computing metrics on schedule, exposing an internal HTTP API |

#### Files to create

```
apps/analytics/
├── src/
│   ├── __init__.py
│   ├── main.py                  # FastAPI entrypoint
│   ├── settings.py              # Metrics config, compute intervals
│   ├── services/
│   │   ├── __init__.py
│   │   ├── metric_computer.py   # Coordinates DB read → feature compute → store
│   │   ├── signal_generator.py  # Buy/sell/hold signals from features + rules
│   │   └── reporter.py          # Periodic summary reports (daily, hourly)
│   ├── api/
│   │   ├── __init__.py
│   │   ├── health.py
│   │   ├── metrics.py           # GET /metrics/:pool — queryable by agents
│   │   └── signals.py           # GET /signals/:pool — latest signal
│   └── di.py                    # Wire dependencies
├── tests/
│   ├── test_metric_computer.py
│   └── test_signal_generator.py
├── pyproject.toml
└── Dockerfile
```

#### Key design decisions

- **Reads from DB, writes to feature store** — doesn't own data, only derives it.
- **Signal generator** uses rule engine to produce actionable signals.
- **API is internal only** — not exposed to the internet, consumed by agents and dashboard.
- **Reporter produces structured reports** — consumed by Telegram app for daily digests.

#### Dependencies

| Depends on | Used by |
|------------|---------|
| M1, M2, M5, M6 | M8 (Luna — reads signals), M11 (Telegram — reports) |

| Difficulty | 🟡 Medium — composition of existing packages, API design, report generation |
|---|---|

---

### M8 — Luna Agent (Monitor)

| Field | Value |
|-------|-------|
| **Goal** | Autonomous monitoring agent that continuously evaluates pool health, detects anomalies, and generates alerts. Luna is the "eyes" of the system. |
| **Expected output** | Runnable agent process with configurable monitoring loops and alert dispatch |

#### Files to create

```
agents/luna/
├── src/
│   ├── __init__.py
│   ├── main.py                  # Agent entrypoint, lifecycle
│   ├── settings.py              # Pool watchlist, alert thresholds, check interval
│   ├── monitors/
│   │   ├── __init__.py
│   │   ├── pool_health.py       # Health checks: TVL, volume, fees, utilization
│   │   ├── anomaly.py           # Anomaly detection: price spike, drop, divergence
│   │   └── risk.py              # Risk assessment: impermanent loss, concentration risk
│   ├── alerts/
│   │   ├── __init__.py
│   │   ├── dispatcher.py        # Route alerts to notifier (Telegram, webhook, log)
│   │   └── severity.py          # Alert severity levels, escalation rules
│   └── reporter.py              # Generate periodic status reports
├── tests/
│   ├── test_pool_health.py
│   ├── test_anomaly.py
│   └── test_dispatcher.py
├── pyproject.toml
└── Dockerfile
```

#### Key design decisions

- **Luna is stateless** — reads metrics from Analytics API, writes alerts to message bus / DB. No local state beyond configuration.
- **Monitors are plugins** — add a new monitor by creating a file in `monitors/` and registering it. No changes to core logic.
- **Alerts go through the Notifier port** — Telegram, Slack, webhook — all pluggable.
- **Luna does NOT rebalance** — she only watches and alerts. Execution is Aspro's job.

#### Dependencies

| Depends on | Used by |
|------------|---------|
| M1 (ports/notifier), M5 (feature queries), M7 (metrics API) | M10 (Hermes — receives alerts) |

| Difficulty | 🟡 Medium — monitoring logic is straightforward; plugin architecture needs careful design |
|---|---|

---

### M9 — Aspro Agent (Executor)

| Field | Value |
|-------|-------|
| **Goal** | Execution agent that handles rebalancing actions: calculates target allocations, simulates impact, prepares transactions, and manages approval workflows. |
| **Expected output** | Runnable agent process with action queue, transaction builder, and approval state machine |

#### Files to create

```
agents/aspro/
├── src/
│   ├── __init__.py
│   ├── main.py                  # Agent entrypoint, lifecycle
│   ├── settings.py              # Slippage tolerance, max tx size, approval config
│   ├── executor/
│   │   ├── __init__.py
│   │   ├── strategy.py          # Rebalancing strategy: compute target distribution
│   │   ├── simulator.py         # Simulate impact of a rebalance before executing
│   │   └── tx_builder.py        # Build Solana transaction instructions
│   ├── approval/
│   │   ├── __init__.py
│   │   ├── workflow.py          # Approval state machine (pending → approved → executed / rejected)
│   │   ├── thresholds.py        # Auto-approve if under threshold, escalate if over
│   │   └── timeout.py           # Auto-reject if not approved within TTL
│   └── actions/
│       ├── __init__.py
│       └── action_queue.py      # Persistent queue of pending actions
├── tests/
│   ├── test_strategy.py
│   ├── test_simulator.py
│   ├── test_workflow.py
│   └── test_action_queue.py
├── pyproject.toml
└── Dockerfile
```

#### Key design decisions

- **Aspro never holds keys** — transaction signing is delegated to a wallet service / hardware module. Aspro only builds and proposes transactions.
- **Approval workflow is a state machine** — clear states: `draft → pending → approved → executed | rejected → cancelled`.
- **Auto-approve thresholds** — small rebalances (configurable) skip human approval. Large moves require manual confirm (via Telegram).
- **Action queue is persisted in Postgres** — survives agent restart.

#### Dependencies

| Depends on | Used by |
|------------|---------|
| M1 (ports, entities), M2 (persist actions), M6 (rules for triggers), M7 (signals for yes/no) | M10 (Hermes — orchestrates), M11 (Telegram — approval UI) |

| Difficulty | 🔴 Very High — approval workflow correctness, transaction safety, state machine must be bug-free |
|---|---|

---

### M10 — Hermes Agent (Orchestrator)

| Field | Value |
|-------|-------|
| **Goal** | The "brain" of Liquidity OS. Hermes coordinates the other agents: delegates monitoring tasks to Luna, execution tasks to Aspro, manages schedules, and handles escalation when things go wrong. |
| **Expected output** | Runnable orchestrator agent with task queue, delegation manager, and escalation policies |

#### Files to create

```
agents/hermes/
├── src/
│   ├── __init__.py
│   ├── main.py                  # Agent entrypoint, lifecycle
│   ├── settings.py              # Agent coordination config, schedule, escalation contacts
│   ├── orchestrator/
│   │   ├── __init__.py
│   │   ├── task_manager.py      # Create, assign, track, retry tasks
│   │   ├── delegation.py        # Decide which agent handles what
│   │   └── scheduler.py         # Cron-style task scheduling
│   ├── escalation/
│   │   ├── __init__.py
│   │   ├── policy.py            # Escalation policies: if Luna silent → alert, if Aspro stuck → intervene
│   │   └── override.py          # Manual override: human can cancel/reassign tasks
│   └── bus/
│       ├── __init__.py
│       └── message_bus.py       # In-process message bus (or Redis pub/sub) for agent communication
├── tests/
│   ├── test_task_manager.py
│   ├── test_delegation.py
│   └── test_policy.py
├── pyproject.toml
└── Dockerfile
```

#### Key design decisions

- **Hermes does NOT do direct work** — it delegates. No data fetching, no transaction building. Pure orchestration.
- **Task-based abstraction** — everything is a `Task` with `id`, `type`, `status`, `assignee`, `deadline`. Tracked in Postgres.
- **Escalation policies are declarative rules** — similar to the rule engine but for operational concerns (agent health, task deadlines).
- **Message bus** decouples agents — Luna emits `alert.generated`, Aspro subscribes and may trigger a rebalance. Hermes subscribes to everything for oversight.

#### Dependencies

| Depends on | Used by |
|------------|---------|
| M1 (ports/agent_bus, entities/agent), M2 (task persistence), M6 (escalation rules) | M11 (Telegram — status queries), M12 (Dashboard — orchestrator view) |

| Difficulty | 🔴 Very High — coordination logic is subtle, task lifecycle must be robust, agent health monitoring |
|---|---|

---

### M11 — Telegram Bot App

| Field | Value |
|-------|-------|
| **Goal** | Full-featured Telegram bot for interacting with Liquidity OS: real-time alerts, rebalance approvals, pool queries, daily reports, and manual commands. |
| **Expected output** | Runnable Telegram bot with command handlers, inline keyboards, and notification dispatch |

#### Files to create

```
apps/telegram/
├── src/
│   ├── __init__.py
│   ├── main.py                  # python-telegram-bot / pyrogram entrypoint
│   ├── settings.py              # Bot token, allowed users, chat IDs
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── commands.py          # /start, /status, /pools, /positions, /alerts
│   │   ├── approvals.py         # Inline keyboard approval for rebalance actions
│   │   ├── reports.py           # /report daily, /report pool:<address>
│   │   └── admin.py             # /config, /agents, /override
│   ├── keyboards/
│   │   ├── __init__.py
│   │   └── builder.py           # Reusable inline keyboard layouts
│   ├── dispatcher.py            # Route notifications to Telegram (implements Notifier port)
│   └── formatter.py             # Domain entities → Telegram markdown messages
├── tests/
│   ├── test_formatter.py
│   ├── test_commands.py
│   └── test_approvals.py
├── pyproject.toml
└── Dockerfile
```

#### Key design decisions

- **Telegram is a view layer** — it renders data from APIs, never owns business logic. Approval "yes/no" writes to Aspro's action queue, nothing more.
- **python-telegram-bot v21+** — async-native, webhook support.
- **Formatter is pure** — `Pool -> str`, no IO. Easy to unit test and ensures consistent message formatting.
- **Notifications go through the Notifier port** — if the bot is down, notifications queue in DB for retry.

#### Dependencies

| Depends on | Used by |
|------------|---------|
| M1 (ports/notifier, entities), M7 (reports via API), M8 (alerts), M9 (approvals), M10 (status queries) | End users |

| Difficulty | 🟡 Medium — Telegram API surface is well-documented; the complexity is in approval UX and error handling |
|---|---|

---

### M12 — Dashboard App

| Field | Value |
|-------|-------|
| **Goal** | Web dashboard for real-time visualization of pool metrics, position health, agent activity, and system status. FastAPI backend + lightweight frontend (Next.js or HTMX). |
| **Expected output** | Runnable web app with real-time charts, pool overview, and agent activity log |

#### Files to create

```
apps/dashboard/
├── backend/
│   ├── src/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI entrypoint (or reuse analytics service)
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
| M1, M2 (read models), M5 (feature queries), M7 (metrics), M8/M9/M10 (agent status) | End users (ops team) |

| Difficulty | 🟡 Medium — UI complexity is moderate; real-time WebSocket adds some complexity |
|---|---|

---

### M13 — Production Readiness

| Field | Value |
|-------|-------|
| **Goal** | Harden every service for production: refined Dockerfiles, CI/CD pipelines, monitoring, alerting, documentation, and runbooks. |
| **Expected output** | Production-grade deployment artifacts, CI/CD passing, monitoring dashboards, operational runbooks |

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
├── architecture.md         # Detailed architecture decision records (ADRs)
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

#### Dependencies

| Depends on | Used by |
|------------|---------|
| All previous milestones | Operations team, future contributors |

| Difficulty | 🟡 Medium — configuration work, CI/CD tools, documentation |
|---|---|

---

## Summary

| # | Milestone | Folder | Difficulty | Depends on |
|---|-----------|--------|------------|------------|
| M0 | Project Scaffolding ✅ | Root | ⬜ Trivial | — |
| **M1** | **Shared Domain Package** | `packages/shared/` | 🟡 Medium | — |
| **M2** | **Database Package** | `packages/database/` | 🟡 Medium | M1 |
| **M3** | **Meteora DLMM Adapter** | `apps/collector/src/adapters/` | 🟡 Medium | M1 |
| **M4** | **Collector Application** | `apps/collector/` | 🟠 High | M1, M2, M3 |
| **M5** | **Feature Store Package** | `packages/feature-store/` | 🟢 Low | M1, M2 |
| **M6** | **Rule Engine Package** | `packages/rule-engine/` | 🟠 High | M1, M5 |
| **M7** | **Analytics Service** | `apps/analytics/` | 🟡 Medium | M1, M2, M5, M6 |
| **M8** | **Luna Agent (Monitor)** | `agents/luna/` | 🟡 Medium | M1, M5, M7 |
| **M9** | **Aspro Agent (Executor)** | `agents/aspro/` | 🔴 Very High | M1, M2, M6, M7 |
| **M10** | **Hermes Agent (Orchestrator)** | `agents/hermes/` | 🔴 Very High | M1, M2, M6 |
| **M11** | **Telegram Bot App** | `apps/telegram/` | 🟡 Medium | M1, M7, M8, M9, M10 |
| **M12** | **Dashboard App** | `apps/dashboard/` | 🟡 Medium | M1, M2, M5, M7, M8, M9, M10 |
| **M13** | **Production Readiness** | `.github/`, `docker/`, `docs/`, `scripts/` | 🟡 Medium | All |

---

## Architectural Invariants

These rules apply to every milestone. Violations must be rejected during review.

1. **Domain layer imports NOTHING** outside its own package. No FastAPI, no SQLAlchemy, no httpx, no Redis.
2. **Ports are interfaces, not implementations.** Infra packages implement ports, domain never knows about them.
3. **Apps are thin entrypoints.** They wire dependencies and start loops. Business logic lives in packages or use-case services.
4. **Agents communicate through the bus, not by importing each other.** Hermes → bus → Luna, never `from agents.luna import ...`.
5. **Every public function is unit-testable.** Pure logic in domain and use cases. IO is mocked at the port boundary.
6. **Configuration is explicit.** No magic constants in code. Everything configurable via settings / env.
7. **Errors are typed.** Every domain exception has a distinct class. No bare `Exception` or `assert False`.
