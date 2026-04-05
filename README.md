# Lonnser Content Engine

Phase 2 bootstrap for the Lonnser Content Engine (LCE): a pnpm monorepo with a Node.js orchestrator, a Python ai-engine worker, PostgreSQL, RabbitMQ, Redis, transactional outbox publication, and the first bounded AI execution loop.

## What is included

- `apps/orchestrator`: Express + TypeScript API, Prisma schema, and an outbox relay.
- `workers/ai-engine`: Python 3.11+ worker using RabbitMQ, SQLAlchemy, CrewAI Flow, and idempotent event consumption.
- `packages/shared-types`: shared integration event contracts.
- `infra/docker`: PostgreSQL, RabbitMQ, and Redis compose stack.

## Phase 2 slice

This repo now proves the smallest complete Phase 2 flow:

- `POST /tasks/generate` accepts a manual topic.
- The orchestrator persists the task and writes `GenerationRequested` to the transactional outbox.
- The outbox relay publishes the event to RabbitMQ.
- The Python worker consumes the event idempotently.
- A deterministic CrewAI Flow runs exactly 2 agents:
  - Content Generation Agent
  - QA & Compliance Agent
- The worker uses a local LLM abstraction with a deterministic `stub` mode and an optional LiteLLM-backed mode.
- QA can fail once and trigger exactly 1 bounded revision.
- Draft revisions, QA feedback, run state, and the final approved article are persisted.
- The final article is stored in the repository model with status `completed`.

## Prerequisites

- Node.js 20+ and `pnpm`
- Python 3.11+, preferably Python 3.13, 3.12, or 3.11 for CrewAI compatibility
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
python3.13 -m venv workers/ai-engine/.venv
source workers/ai-engine/.venv/bin/activate
pip install -e workers/ai-engine
```

4. Start infrastructure:

```bash
docker compose -f infra/docker/docker-compose.yml up -d
```

5. Generate the Prisma client and apply the migrations:

```bash
pnpm db:generate
pnpm db:migrate
```

## Run the Phase 2 slice

Start the orchestrator:

```bash
pnpm dev:orchestrator
```

In a second terminal, start the worker:

```bash
source workers/ai-engine/.venv/bin/activate
CREWAI_RUNTIME_HOME="$(pwd)/.crewai-home" PYTHONPATH=workers/ai-engine/src python -m ai_engine.main
```

## Worker LLM modes

The worker defaults to a deterministic stub so local smoke tests stay runnable without an external model key:

```bash
AI_ENGINE_LLM_MODE=stub
```

To use LiteLLM directly in the worker for the two Phase 2 agents, set env vars like:

```bash
AI_ENGINE_LLM_MODE=litellm
AI_ENGINE_LLM_MODEL=openai/gpt-4.1-mini
AI_ENGINE_LLM_API_KEY=<provider-api-key>
```

For an explicit OpenAI path, you can now use:

```bash
AI_ENGINE_LLM_MODE=openai
OPENAI_API_KEY=<your-openai-api-key>
AI_ENGINE_LLM_MODEL=openai/gpt-4.1-mini
```

Optional LiteLLM settings:

```bash
AI_ENGINE_LLM_API_BASE=
AI_ENGINE_LLM_TEMPERATURE=0.2
AI_ENGINE_LLM_TIMEOUT_SECONDS=30
OPENAI_BASE_URL=
```

This Phase 2 slice uses LiteLLM as a direct Python SDK integration only. Proxy deployment, virtual keys, spend controls, and provider governance are intentionally deferred.

## Smoke paths

### Option 1: Full bootstrap in separate macOS Terminal windows

```bash
bash scripts/bootstrap-and-test-macos.sh
```

### Option 2: Full bootstrap in one terminal with background services

```bash
bash scripts/bootstrap-and-test-background.sh
```

Service logs are written to:

```bash
.logs/orchestrator.log
.logs/ai-engine.log
```

### Option 3: Lightweight smoke test when services are already running

```bash
bash scripts/smoke-topic-flow.sh
```

## Manual API flow

Create an organization:

```bash
curl -s \
  -X POST http://localhost:3000/organizations \
  -H 'content-type: application/json' \
  -d '{"name":"Acme"}'
```

Create a campaign:

```bash
curl -s \
  -X POST http://localhost:3000/organizations/<organization-id>/campaigns \
  -H 'content-type: application/json' \
  -d '{"name":"Spring Launch"}'
```

Create a generation task from a manual topic:

```bash
curl -s \
  -X POST http://localhost:3000/tasks/generate \
  -H 'content-type: application/json' \
  -d '{
    "organizationId":"<organization-id>",
    "campaignId":"<campaign-id>",
    "topic":"deterministic content operations",
    "targetAudience":"operations leaders",
    "outputFormats":["markdown_article"]
  }'
```

Read the task status and repository article summary:

```bash
curl -s \
  http://localhost:3000/tasks/<task-id>
```

## Validation commands

```bash
pnpm build
pnpm typecheck
workers/ai-engine/.venv/bin/python -m compileall workers/ai-engine/src
bash scripts/smoke-topic-flow.sh
```

## CI/CD

Phase validation includes:

- workspace install
- Python worker install
- Prisma client generation
- TypeScript build
- TypeScript typecheck
- Python compile check
- Docker-backed smoke flow for the Phase 2 slice

Run the same path locally with:

```bash
pnpm ci:dev-setup
```

## Useful endpoints

- API health: `http://localhost:3000/health`
- RabbitMQ UI: `http://localhost:15672` with `guest / guest`
