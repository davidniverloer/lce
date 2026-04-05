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

## Market intelligence modes

Market discovery and qualification are now environment-driven:

```bash
LCE_MARKET_MODE=stub|mixed|live
LCE_DISCOVERY_MODE=stub|live
LCE_QUALIFICATION_MODE=stub|mixed|live
LCE_TREND_PROVIDER_MODE=stub|live
LCE_SOCIAL_PROVIDER_MODE=stub|live
LCE_SEO_PROVIDER_MODE=stub|live
```

CI is always deterministic. When `CI=true`, the worker forces all market intelligence providers into stub mode regardless of other env values.

Recommended local live-discovery setup:

```bash
LCE_DISCOVERY_MODE=live
LCE_QUALIFICATION_MODE=mixed
LCE_TREND_PROVIDER_MODE=live
LCE_SOCIAL_PROVIDER_MODE=live
LCE_SEO_PROVIDER_MODE=stub
```

Live discovery currently uses a small Google News RSS-backed adapter, while qualification supports stub, mixed, and live-ready provider modes. DataForSEO remains live-ready but still falls back to deterministic scoring unless stable credentials and a full provider implementation are wired in.

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

Live discovery smoke path outside CI:

```bash
LCE_DISCOVERY_MODE=live \
LCE_QUALIFICATION_MODE=mixed \
LCE_TREND_PROVIDER_MODE=live \
LCE_SOCIAL_PROVIDER_MODE=live \
LCE_SEO_PROVIDER_MODE=stub \
SEED_TOPIC='' \
MARKET_INDUSTRY='healthcare' \
bash scripts/smoke-topic-flow.sh
```

Live SEO smoke path outside CI:

```bash
LCE_DISCOVERY_MODE=stub \
LCE_QUALIFICATION_MODE=mixed \
LCE_SEO_PROVIDER_MODE=live \
DATAFORSEO_LOGIN=<your-dataforseo-login> \
DATAFORSEO_PASSWORD=<your-dataforseo-password> \
DATAFORSEO_LOCATION_CODE=2840 \
DATAFORSEO_LANGUAGE_CODE=en \
SEED_TOPIC='ambient ai scribes in healthcare' \
bash scripts/smoke-topic-flow.sh
```

This uses DataForSEO API v3 live SEO signals for qualification. If some SEO components fail outside CI, the worker records `mode: "mixed"` and falls back only for those components. If no useful live SEO component succeeds, it records `mode: "stub_fallback"` and uses the deterministic fallback score. For page-level overlap, the worker now tries DataForSEO page intersection on the top two organic SERP URLs with `intersect` first and retries `union` before falling back.

For headline-style discovered topics, the worker derives a small normalized SEO lookup query for DataForSEO while preserving the original topic for persistence and ranking. Inspect:
- `seoQuery`
- `rawComponents.normalizedSeoQuery`
- `componentQueries`
- `componentModes`
- `componentFallbackReasons`

in qualified topic metadata to confirm which SEO inputs were live versus fallback.

The enriched live SEO path now combines:
- DataForSEO v3 keyword overview
- DataForSEO v3 keyword ideas
- DataForSEO v3 related keywords
- DataForSEO v3 SERP competitors
- DataForSEO v3 top organic SERP results
- DataForSEO v3 page intersection keywords

and normalizes them into one explainable `seo_score`.

Local bootstrap now waits for RabbitMQ startup before launching the orchestrator and worker, and both runtimes use bounded retry/backoff so transient broker readiness issues are logged as retryable startup conditions rather than hard failures.
RabbitMQ now uses an explicit named Docker volume, and the local bootstrap removes any stale `lce-rabbitmq` container state before bringing the stack back up.

Market scoring calibration remains env-driven and deterministic in structure:
- `LCE_MARKET_TREND_WEIGHT`
- `LCE_MARKET_SOCIAL_WEIGHT`
- `LCE_MARKET_SEO_WEIGHT`
- `LCE_MARKET_MIN_QUALIFIED_SCORE`
- `LCE_MARKET_NOVELTY_THRESHOLD`
- `LCE_MARKET_MAX_NOVELTY_PENALTY`

Validate the Market Intelligence score model locally with:

```bash
PYTHONPATH=$PWD/workers/ai-engine/src workers/ai-engine/.venv/bin/python -m pytest \
  workers/ai-engine/tests/test_market_modes.py \
  workers/ai-engine/tests/test_dataforseo_adapter.py \
  workers/ai-engine/tests/test_market_scoring_pipeline.py
```

## Phase 3.5 quality surfaces

Phase 3.5 adds richer internal artifacts without changing the orchestration contract:

- discovery metadata now records:
  - `discoverySources`
  - `sourceConfidence`
  - source-family samples and hints
- blueprint artifacts now include:
  - `differentiationAngle`
  - `differentiationRationale`
  - `targetDelta`
  - `audienceShift`
  - `siteContext`
- qualification metadata now includes:
  - confidence markers
  - fallback influence
  - a structured `status` artifact
- generation run state now includes structured QA results and a persisted `statusArtifact`

Inspect the unified task status surface with:

```bash
curl -s http://localhost:3000/tasks/<task-id>/status | jq
```

This additive endpoint summarizes:
- discovery and qualification status
- blueprint readiness and differentiation presence
- generation / QA outcomes
- relay health as exposed by the orchestrator

Validate these Phase 3.5 artifacts end to end with the deterministic integration harness:

```bash
bash scripts/validate-phase35-artifacts.sh
```

This reuses the existing pipeline shape and asserts:
- discovery source attribution
- fallback / confidence markers
- blueprint differentiation and site context
- structured QA artifact survival
- `GET /tasks/:taskId/status` programmatic inspectability

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
