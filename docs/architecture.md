# Liquidity OS — Architecture

> **Last updated:** June 25, 2026
>
> This document defines the system architecture, component responsibilities, and design invariants.
> For implementation milestones, see [roadmap.md](./roadmap.md).

---

## System Overview

Liquidity OS is a modular, multi-agent platform for automated liquidity management on Meteora DLMM. The system follows Clean Architecture: **domain logic is pure and infrastructure is pluggable**.

```
┌─────────────────────────────────────────────────────────────────┐
│                        LIQUIDITY OS                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐    │
│  │Collector │  │Analytics │  │Dashboard │  │  Telegram    │    │
│  │Service   │  │Service   │  │App       │  │  Bot App     │    │
│  │(Hermes)  │  │          │  │          │  │              │    │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘    │
│       │              │             │               │            │
│  ┌────┴──────────────┴─────────────┴───────────────┴─────────┐  │
│  │                    PACKAGES LAYER                         │  │
│  │  ┌──────────┐ ┌────────┐ ┌──────────┐ ┌───────────────┐  │  │
│  │  │ Database │ │ Shared │ │  Rule    │ │ Feature Store │  │  │
│  │  │          │ │        │ │  Engine  │ │               │  │  │
│  │  └──────────┘ └────────┘ └──────────┘ └───────────────┘  │  │
│  │  ┌──────────────┐ ┌──────────────┐                        │  │
│  │  │ Decision Log │ │  Simulation  │                        │  │
│  │  │              │ │  Engine      │                        │  │
│  │  └──────────────┘ └──────────────┘                        │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────┐  ┌──────────┐                                    │
│  │   Luna   │  │  Aspro   │  ← Agents (consumer layer)         │
│  │  Agent   │  │  Agent   │                                    │
│  └──────────┘  └──────────┘                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Layers

| Layer | Responsibility | Import Rule |
|-------|---------------|-------------|
| **Domain (shared)** | Entities, value objects, ports, events | **Zero imports** from outside this layer |
| **Packages** | Business logic, data access, feature computation | Import only from Domain |
| **Apps** | Entrypoints, HTTP servers, bot handlers | Import from Packages + Domain |
| **Agents** | Autonomous processes (Luna, Aspro) | Import from Packages + Domain, communicate via bus |
| **Infrastructure** | Docker, CI/CD, deployment | Composes apps and agents |

---

## Components

### Collector Service (codename: Hermes)

| | |
|---|---|
| **Folder** | `apps/collector/` |
| **Role** | The central nervous system. Ingests pool data from Meteora DLMM via HTTP + WebSocket, persists to the database, and emits domain events. |
| **Codenamed** | Hermes (internal only — not exposed in API or UI) |
| **Does NOT** | Orchestrate other agents. Pure data ingestion and event emission. |
| **Key ports used** | `PoolDataCollector`, `PoolRepository`, `PositionRepository` |
| **Emits** | `PoolUpdated`, `PositionUpdated`, `LiquidityChanged` |

### Analytics Service

| | |
|---|---|
| **Folder** | `apps/analytics/` |
| **Role** | Continuously computes pool health metrics, generates buy/sell/hold signals, and produces periodic reports. Internal HTTP API for agents and dashboard. |
| **Key ports used** | `PoolRepository`, `FeatureStore` |
| **Depends on** | Rule Engine (for signal generation) |
| **Exposes** | `GET /metrics/:pool`, `GET /signals/:pool` |

### Dashboard App

| | |
|---|---|
| **Folder** | `apps/dashboard/` |
| **Role** | Web UI for real-time pool visualization, agent status, and operational controls. |
| **Key ports used** | `PoolRepository`, `FeatureStore` (read-only) |
| **Tech** | FastAPI backend + Next.js or HTMX frontend (TBD) |

### Telegram Bot App

| | |
|---|---|
| **Folder** | `apps/telegram/` |
| **Role** | User-facing interface for alerts, approvals, reports, and manual commands. |
| **Key ports used** | `Notifier` (implements it), `PoolRepository` (read-only) |
| **Does NOT** | Own business logic — renders data from APIs, writes approvals to Aspro's queue. |

### Luna Agent (Monitor)

| | |
|---|---|
| **Folder** | `agents/luna/` |
| **Role** | "Eyes of the system." Continuously monitors pool health, detects anomalies, and generates alerts. Stateless — reads metrics from Analytics API. |
| **Key ports used** | `Notifier`, `FeatureStore` |
| **Does NOT** | Rebalance. Only watches and alerts. |
| **Plugin model** | Monitors are pluggable — add a file in `monitors/`, register it, done. |

### Aspro Agent (Executor)

| | |
|---|---|
| **Folder** | `agents/aspro/` |
| **Role** | "Hands of the system." Handles rebalancing execution: strategy calculation, simulation, transaction building, and approval workflows. |
| **Key ports used** | `FeatureStore`, `PoolRepository` |
| **Does NOT** | Hold wallet keys. Builds and proposes transactions; signing is external. |
| **Critical** | Approval state machine must be deterministic and auditable. |

---

## Packages

### Shared (`packages/shared/`)

| | |
|---|---|
| **Role** | Domain layer — entities, value objects, enums, port interfaces, domain events, base exceptions. |
| **Dependencies** | **ZERO**. Only `pydantic` (for validated models) + stdlib (`enum`, `abc`, `dataclasses`). |
| **Used by** | Every other package, app, and agent. |

**This is the architectural invariant.** Shared must never import: SQLAlchemy, httpx, redis, fastapi, or any infrastructure code. If a new concept needs a port interface, it lives here. If it needs an implementation, it lives in the package that owns the infrastructure.

### Database (`packages/database/`)

| | |
|---|---|
| **Role** | Implements `PoolRepository` and `PositionRepository` ports using PostgreSQL + SQLAlchemy 2.0. Manages migrations via Alembic. |
| **Dependencies** | M1 (shared — ports and entities) |

### Feature Store (`packages/feature-store/`)

| | |
|---|---|
| **Role** | Computes derived market features (volatility, volume change, price ranges, liquidity concentration). Redis-backed cache with per-feature TTLs. |
| **Dependencies** | M1 (shared — value objects, ports/feature_store) |

### Rule Engine (`packages/rule-engine/`)

| | |
|---|---|
| **Role** | Declarative rule evaluation. Rules are AST-based expressions that evaluate conditions against market state and trigger actions (alert, rebalance, escalate). |
| **Dependencies** | M1 (shared — enums, events), M5 (Feature Store — for feature values) |

### Decision Log (`packages/decision-log/`)

| | |
|---|---|
| **Role** | Audit trail for every agent decision. Records: who decided, what action, which features/rules triggered it, what the outcome was. Immutable append-only log. |
| **Dependencies** | M1 (shared — entities/agent, events) |
| **Used by** | Luna, Aspro (write), Analytics, Dashboard, Telegram (read) |

### Simulation Engine (`packages/simulation/`)

| | |
|---|---|
| **Role** | Replays historical data snapshots through the Rule Engine to validate rule changes before production. Dry-run mode for testing rebalancing strategies without real transactions. |
| **Dependencies** | M1 (shared), M5 (Feature Store), M6 (Rule Engine) |
| **Used by** | Rule Engine developers, Analytics (backtesting) |

---

## Domain Events

Components communicate through domain events, not direct imports.

```
Collector Service ──► PoolUpdated ──► Feature Store
                                       │
                                       ▼
                                  Analytics
                                       │
                                       ▼
                              Rule Engine evaluates
                                       │
                          ┌────────────┴────────────┐
                          ▼                         ▼
                    AlertTriggered            RebalanceProposed
                          │                         │
                          ▼                         ▼
                    Luna (confirms)           Aspro (executes)
                          │                         │
                          ▼                         ▼
                    Notifier                  ActionQueue
                    (Telegram)               (Database)
```

### Event Flow

1. **Collector** ingests pool data → emits `PoolUpdated`
2. **Feature Store** recomputes features → triggers downstream evaluation
3. **Analytics** reads features, runs Rule Engine → emits signals
4. **Luna** monitors for anomalies → emits `AlertTriggered`
5. **Aspro** receives rebalance proposals → builds transactions → approval workflow
6. **Decision Log** records every decision from steps 3-5

---

## Dependency Rules

### Architectural Invariants

These are non-negotiable. Every code review must verify them.

| # | Rule | Rationale |
|---|------|-----------|
| 1 | **Domain imports nothing** outside `packages/shared/` | Ensures domain logic is testable without any infrastructure |
| 2 | **Ports are interfaces** — infra implements them | Dependency inversion: domain defines contracts, infra fulfills them |
| 3 | **Apps are thin entrypoints** — no business logic in `main.py` | Logic belongs in packages; apps wire dependencies and start loops |
| 4 | **Agents communicate via bus** — never import each other | Decoupling: Luna and Aspro can be developed, tested, deployed independently |
| 5 | **Every public function is unit-testable** | Pure logic in domain and use cases; IO mocked at port boundaries |
| 6 | **Configuration is explicit** — no magic constants | Every tunable value lives in settings / env vars |
| 7 | **Errors are typed** — no bare `Exception` | Enables precise error handling at every boundary |

### Import Graph (Allowed)

```
shared  ←── database
shared  ←── feature-store
shared  ←── rule-engine
shared  ←── decision-log
shared  ←── simulation
shared  ←── apps/*
shared  ←── agents/*

database      ←── apps/collector
database      ←── apps/analytics
database      ←── apps/dashboard
feature-store ←── apps/analytics
rule-engine   ←── apps/analytics
feature-store ←── rule-engine
rule-engine   ←── simulation
feature-store ←── simulation
```

### Import Graph (Forbidden)

```
shared        ╳── anything
apps/*        ╳── agents/*
agents/*      ╳── agents/* (other agents)
database      ╳── apps/* (circular)
rule-engine   ╳── database (goes through ports)
```

---

## Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Domain models | Pydantic v2 | Validated, immutable, serialization built-in |
| Database | PostgreSQL 16 + SQLAlchemy 2.0 | Async, mature, excellent Python support |
| Migrations | Alembic | Standard for SQLAlchemy, auto-generates from models |
| Caching | Redis 7 | TTL-based feature cache, pub/sub for events |
| HTTP client | httpx | Async, modern, connection pooling |
| WebSockets | websockets lib | Native async, Meteora DLMM support |
| Web framework | FastAPI | Async, type-safe, auto-docs, health checks |
| Telegram | python-telegram-bot v21+ | Async, well-maintained, webhook support |
| Containers | Docker + Compose | Multi-service orchestration |
| CI/CD | GitHub Actions | Native integration, matrix builds |
| Linting | Ruff | Fast, comprehensive, replaces flake8+isort |
| Type checking | mypy | Strict mode for catch-before-ship |

---

## Decision Log (package)

The Decision Log is an **immutable audit trail**. Every action the system takes — alert triggered, rebalance proposed, rule evaluated — is recorded with:

- `timestamp` — when the decision was made
- `agent` — which agent made it (Luna, Aspro, or system)
- `event_type` — what kind of decision (alert, rebalance, escalation)
- `trigger` — which rule or condition caused it
- `features` — snapshot of feature values at decision time
- `outcome` — what actually happened (executed, rejected, pending)
- `metadata` — freeform JSON for context

**Why it exists:**
- Debugging: "Why did Aspro rebalance at 3am?"
- Auditing: compliance, post-mortem analysis
- Simulation: replay decisions with modified rules to compare outcomes
- Trust: operators can see exactly why the system acted

---

## Simulation Engine (package)

The Simulation Engine replays historical data through the current Rule Engine configuration to answer: *"What would have happened?"*

**Use cases:**
- **Pre-deployment validation:** Before pushing a new rule, simulate it against last 30 days of data. Compare outcomes with current production rules.
- **Strategy backtesting:** Test rebalancing strategies against historical volatility events.
- **Dry-run mode:** Run Aspro's logic without actually building transactions.

**Architecture:**
- Reads historical snapshots from the database
- Feeds them through Feature Store (recomputes features for each snapshot)
- Runs Rule Engine evaluation on each time step
- Records all decisions in Decision Log (simulation tag)
- Produces a comparison report: current rules vs. modified rules

**Does NOT:**
- Touch production data
- Send notifications
- Build real transactions

---

## Service Communication Matrix

| From → To | Collector | Analytics | Luna | Aspro | Telegram | Dashboard |
|-----------|:---------:|:---------:|:----:|:-----:|:--------:|:---------:|
| **Collector** | — | events | — | — | — | — |
| **Analytics** | — | — | metrics | signals | reports | metrics |
| **Luna** | — | — | — | — | alerts | — |
| **Aspro** | — | — | — | — | approvals | status |
| **Telegram** | — | query | query | query | — | — |
| **Dashboard** | — | query | query | query | — | — |

All communication goes through the **database** (persistent state) or **domain events** (ephemeral signals). No direct HTTP calls between agents.

---

## Architectural Comments (Mandatory)

Every **public** class, model, interface, and service must include a concise docstring that answers exactly four questions. No exceptions. This is not optional — it is part of the architecture.

### Format

```python
class PoolRepository(ABC):
    """[WHY] Persists and retrieves Pool entities from the data store.

    [OWNERSHIP] Domain layer — defines the contract for pool persistence.

    [DEPENDENTS] Allowed: database (implements), collector, analytics, dashboard.
                Forbidden: shared, agents (must go through ports).

    [EXAMPLE]
        repo = PostgresPoolRepository(session)
        pool = await repo.get_by_address("7YttLkHDoNj9wyDur5pM1ejNaAvT9X4eSTY...")
    """
```

### The Four Questions

| # | Question | What to write |
|---|----------|---------------|
| 1 | **Why does this exist?** | The problem it solves. One sentence. |
| 2 | **Which layer owns it?** | Domain, Package, App, or Agent. |
| 3 | **Which layers depend on it?** | Allowed importers. Explicit "Forbidden" list if non-obvious. |
| 4 | **One practical example** | Realistic usage snippet. Not abstract — concrete code. |

### Rules

- **Public** = any class, function, or constant that is importable from outside its module (`__all__`, no leading underscore).
- **Private helpers** (`_internal`, `_impl`) — comment is optional but recommended.
- **Comments must be placed as the first statement** in the class/function body (docstring).
- **Keep it concise** — max 8 lines per docstring. If you need more, your design is too complex.
- **Readability over brevity** — prefer clear variable names and explicit control flow over clever one-liners. Long-term maintenance wins.

---

## Code Style: Readability First

This project prioritizes **readability and long-term maintenance** over brevity.

### Principles

1. **Names > Comments** — if a variable needs a comment to explain it, rename it.
2. **Explicit > Clever** — `if pool.status == PoolStatus.ACTIVE` beats `if pool.is_active`.
3. **Short functions** — max 30 lines. If longer, extract.
4. **Single Responsibility** — one class does one thing. If you use "and" to describe it, split it.
5. **No magic numbers** — extract to named constants with units: `MAX_SLIPPAGE_BPS = 50`.
6. **Type hints everywhere** — function signatures, return types, class attributes.
7. **Docstrings on all public APIs** — following the Architectural Comments format above.

### Forbidden Patterns

```python
# ❌ Clever one-liner
x = [p for p in pools if p.tvl > 1e6 and p.volatility > 0.1]

# ✅ Readable
high_value_pools = [
    pool
    for pool in pools
    if pool.tvl > MIN_TVL_USD
    and pool.volatility > VOLATILITY_THRESHOLD
]

# ❌ Magic number
if time.time() - last_update > 300:

# ✅ Named constant
POOL_STALENESS_SECONDS = 300  # 5 minutes
if time.time() - last_update > POOL_STALENESS_SECONDS:
```

---

## File: docs/architecture.md

**Why this file exists:**
This is the authoritative source of truth for how Liquidity OS is structured. It defines component boundaries, dependency rules, and communication patterns. Every developer (human or AI) must read this before modifying any code.

**Who references it:**
- `docs/roadmap.md` — milestones reference this for context
- Every `README.md` in apps/ and agents/ should link here
- CI lint rules can enforce import graph (future)
