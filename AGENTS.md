# LCE Agent Instructions

## Mission
Build the Lonnser Content Engine incrementally, phase by phase, following the roadmap and architecture documents.

## Source of truth
Always read these first:
- docs/00-project-overview.md
- docs/01-global-architecture-rules.md
- docs/20-phase-2-core-agentic-engine.md
- docs/21-phase-2-acceptance-criteria.md
- docs/22-phase-2-deliverables.md
- docs/23-phase-2-worker-and-flow-rules.md
- docs/24-phase-2-event-contracts.md
- docs/90-future-phases-summary.md

## Permanent architecture rules
- Use a pnpm monorepo.
- apps/orchestrator is Node.js + TypeScript.
- workers/ai-engine is Python 3.11+.
- Infrastructure includes PostgreSQL, RabbitMQ, and Redis.
- REST controllers must never publish directly to RabbitMQ.
- Produced events must use the Transactional Outbox Pattern.
- Consumers must be idempotent using processed_event_log.
- No cross-bounded-context database writes.
- Each bounded context owns its own data.
- Every aggregate root and domain row must include organizationId / organization_id.
- Prefer event-driven integration over direct coupling.
- Keep deterministic orchestration separate from adaptive AI logic.

## Working style
- Plan before coding for large tasks.
- Prefer small vertical slices.
- Prefer explicit and maintainable code over abstraction-heavy code.
- Run build, lint, and tests before claiming completion.
- If a requirement is ambiguous, choose the smallest implementation that satisfies the roadmap and architecture docs.

## Current delivery phase
Phase 2 — Core Agentic Engine

## Phase 2 objective
Deliver the first real AI execution loop:
- worker engine
- CrewAI flow with persistent typed state
- Content Generation Agent
- QA & Compliance Agent
- iterative revision loop
- approved content stored in repository

## Out of scope unless explicitly requested
- topic discovery / market awareness
- DataForSEO
- Reddit
- Google Trends
- sitemap ingestion
- Structure & Style Agent
- dashboard productization
- CQRS UI views beyond what already exists
- SSE
- CLI
- MCP
- publishing connectors