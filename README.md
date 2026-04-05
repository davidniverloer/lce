# Lonnser Content Engine

Phase 1 foundation bootstrap for the Lonnser Content Engine (LCE): a pnpm monorepo with a Node.js orchestrator, a Python worker, PostgreSQL, RabbitMQ, Redis, isolated PostgreSQL schemas, and a deterministic organization/campaign event backbone.

## What is included

- `apps/orchestrator`: Express + TypeScript API, Prisma schema, and an outbox relay.
- `workers/ai-engine`: Python 3.11+ worker using SQLAlchemy, RabbitMQ, and idempotent audit receipts.
- `packages/shared-types`: shared `OrganizationCreated` and `CampaignCreated` event contracts.
- `infra/docker`: PostgreSQL, RabbitMQ, and Redis compose stack.

## Prerequisites

- Node.js 20+ and `pnpm`
- Python 3.11+
- Docker Desktop

## Setup

1. Copy the environment file:

```bash
cp .env.example .env
```

2. Install Node dependencies:

```bash
pnpm install
```

3. Create a Python virtual environment and install the worker:

```bash
python3 -m venv workers/ai-engine/.venv
source workers/ai-engine/.venv/bin/activate
pip install -e workers/ai-engine
```

4. Start infrastructure:

```bash
docker compose -f infra/docker/docker-compose.yml up -d
```

5. Generate the Prisma client and apply the initial migration:

```bash
pnpm db:generate
pnpm db:migrate
```

## Run the Phase 1 slice

Start the orchestrator:

```bash
pnpm dev:orchestrator
```

In a second terminal, start the worker:

```bash
source workers/ai-engine/.venv/bin/activate
PYTHONPATH=workers/ai-engine/src python -m ai_engine.main
```

## Smoke path

### Option 1: Full bootstrap in separate macOS Terminal windows

This path handles first-time setup, infrastructure, migrations, launches the orchestrator and worker in separate Terminal windows, then runs the end-to-end API check:

```bash
bash scripts/bootstrap-and-test-macos.sh
```

### Option 2: Full bootstrap in one terminal with background services

This path handles first-time setup, infrastructure, migrations, starts both services in the background in the same terminal, then runs the end-to-end API check:

```bash
bash scripts/bootstrap-and-test-background.sh
```

Service logs are written to:

```bash
.logs/orchestrator.log
.logs/ai-engine.log
```

### Option 3: Lightweight smoke test when services are already running

If Docker, the orchestrator, and the worker are already running, use the lightweight smoke script:

```bash
bash scripts/smoke-topic-flow.sh
```

### Manual API flow

Create an organization:

```bash
curl -s \
  -X POST http://localhost:3000/organizations \
  -H 'content-type: application/json' \
  -d '{"name":"Acme"}'
```

Create a campaign inside that organization:

```bash
curl -s \
  -X POST http://localhost:3000/organizations/<organization-id>/campaigns \
  -H 'content-type: application/json' \
  -d '{"name":"Spring Launch"}'
```

Read campaigns for the organization:

```bash
curl -s \
  http://localhost:3000/organizations/<organization-id>/campaigns
```

## Validation commands

```bash
pnpm build
pnpm typecheck
python -m compileall workers/ai-engine/src
```

## CI/CD Phase 1

Phase 1 includes a minimal GitHub Actions workflow for foundation validation in [.github/workflows/phase-1-foundation.yml](/Users/davidniverloer/Desktop/Lonnser%20Content%20Engine/lce/.github/workflows/phase-1-foundation.yml). It verifies:

- workspace install
- Python worker install
- Prisma client generation
- TypeScript build
- TypeScript typecheck
- Python compile check
- Docker-backed smoke flow for the Phase 1 slice

Run the same path locally with:

```bash
pnpm ci:dev-setup
```

## Useful endpoints

- API health: `http://localhost:3000/health`
- RabbitMQ UI: `http://localhost:15672` with `guest / guest`
