# Liquidity OS

**AI-Powered Liquidity Operating System for Meteora DLMM**

Liquidity OS is an intelligent, multi-agent orchestration platform purpose-built for managing concentrated liquidity positions on Meteora DLMM (Dynamic Liquidity Market Maker). It combines real-time data ingestion, predictive analytics, rule-based rebalancing, and multi-channel Telegram operations into a single cohesive operating system.

---

## Project Vision

Automated liquidity management today is fragmented — siloed scripts, manual Telegram pings, disconnected dashboards, and no unified intelligence. Liquidity OS solves this by providing:

- **Real-time collection** — On-chain and off-chain data pipelines with low-latency ingestion.
- **Multi-agent intelligence** — Specialized AI agents (Hermes, Luna, Aspro) that coordinate to monitor, analyze, and act.
- **Feature engineering at scale** — A dedicated feature store and rule engine for deriving and acting on market signals.
- **Omnichannel operations** — Telegram-native ops with support for alerts, approvals, and interactive commands.
- **Production-grade foundation** — Clean monorepo with Docker Compose, CI/CD, and observability from day one.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│                      LIQUIDITY OS                        │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐  │
│  │Collector │  │Analytics │  │Dashboard │  │Telegram │  │
│  │  App     │  │  App     │  │  App     │  │  App    │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬────┘  │
│       │              │             │              │       │
│  ┌────┴──────────────┴─────────────┴──────────────┴────┐  │
│  │                   PACKAGES LAYER                     │  │
│  │  ┌────────┐ ┌────────┐ ┌──────────┐ ┌───────────┐  │  │
│  │  │Database│ │ Shared │ │Feat.Store│ │Rule Engine│  │  │
│  │  └────────┘ └────────┘ └──────────┘ └───────────┘  │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐               │
│  │  Hermes  │  │   Luna   │  │  Aspro   │               │
│  │  Agent   │  │   Agent  │  │  Agent   │               │
│  └──────────┘  └──────────┘  └──────────┘               │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### Layers

| Layer | Description |
|-------|-------------|
| **Apps** | Runnable entrypoints — data collector, analytics engine, web dashboard, Telegram bot interface |
| **Agents** | Autonomous AI agents with distinct roles (Hermes as orchestrator, Luna as monitor, Aspro as executor) |
| **Packages** | Shared libraries — database access, common types, feature store, rule engine |
| **Infra** | Docker Compose orchestration, CI/CD pipelines, deployment scripts |

### Agents

| Agent  | Role |
|--------|------|
| **Hermes** | Orchestrator — coordinates tasks, delegates to sub-agents, manages workflows |
| **Luna**   | Monitor — tracks pool conditions, alerts on anomalies, generates reports |
| **Aspro**  | Executor — handles rebalancing, approvals, and transaction submission |

---

## Folder Structure

```
liquidity-os/
├── apps/                   # Runnable applications
│   ├── collector/          # Data ingestion pipelines (on-chain + off-chain)
│   ├── analytics/          # Analytics & ML inference service
│   ├── dashboard/          # Web dashboard (metrics, charts, controls)
│   └── telegram/           # Telegram bot interface
├── agents/                 # AI agent definitions & logic
│   ├── hermes/             # Hermes orchestrator agent
│   ├── luna/               # Luna monitoring agent
│   └── aspro/              # Aspro execution agent
├── packages/               # Shared libraries
│   ├── database/           # Database models, migrations, repositories
│   ├── shared/             # Common types, utilities, constants
│   ├── feature-store/      # Feature engineering & storage
│   └── rule-engine/        # Business rule definitions & evaluation
├── docs/                   # Documentation
├── scripts/                # Utility scripts (migration, seed, deploy)
├── docker/                 # Dockerfiles and container configs
├── .github/                # GitHub Actions workflows
├── README.md
├── .gitignore
├── LICENSE
├── docker-compose.yml
└── .env.example
```

---

## Development Roadmap

### Phase 1 — Foundation *(Current)*
- [x] Monorepo structure & architecture
- [ ] Database schema & migrations
- [ ] Shared package with core types
- [ ] Docker Compose with service stubs
- [ ] CI pipeline (lint, type-check, test)

### Phase 2 — Data Layer
- [ ] Collector app — Meteora DLMM pool data ingestion
- [ ] Feature store — price, volume, volatility features
- [ ] Database — persistent storage & indexing
- [ ] Historical data backfill pipeline

### Phase 3 — Intelligence
- [ ] Rule Engine — rebalancing rules & triggers
- [ ] Luna Agent — pool monitoring & anomaly detection
- [ ] Analytics service — metrics computation
- [ ] Alerting system

### Phase 4 — Automation
- [ ] Aspro Agent — rebalancing execution & approval flows
- [ ] Hermes Agent — multi-agent orchestration
- [ ] Telegram App — interactive bot with commands & notifications
- [ ] Dashboard — real-time visualization

### Phase 5 — Production Hardening
- [ ] Load testing & performance tuning
- [ ] Multi-pool support scaling
- [ ] Disaster recovery & failover
- [ ] Documentation & runbooks

---

## Getting Started

```bash
# Clone the repository
git clone https://github.com/your-org/liquidity-os.git
cd liquidity-os

# Copy environment file
cp .env.example .env

# Start all services
docker compose up -d

# Run database migrations
./scripts/migrate.sh
```

---

## License

MIT — see [LICENSE](LICENSE) for details.
