# LCE Agent Instructions

## Mission
Build the Lonnser Content Engine incrementally, phase by phase, following the roadmap and architecture documents.

## Source of truth
Always read these first:
- docs/00-project-overview.md
- docs/01-global-architecture-rules.md
- docs/10-phase-1-foundation-persistence.md
- docs/11-phase-1-acceptance-criteria.md
- docs/12-phase-1-deliverables.md
- docs/13-phase-1-event-and-data-rules.md

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
- Keep implementation deterministic, observable, and easy to test.

## Working style
- Plan before coding for large tasks.
- Prefer small vertical slices.
- Prefer explicit and maintainable code over abstraction-heavy code.
- Run build, lint, and tests before claiming completion.
- If a requirement is ambiguous, choose the smallest implementation that satisfies the roadmap and architecture docs.

## Current delivery phase
Phase 1 — Foundation & Persistence

## Phase 1 objective
Deliver the deterministic platform backbone:
- infrastructure
- database schemas
- orchestrator
- basic REST endpoints
- outbox/inbox reliability
- event publication through RabbitMQ

## Out of scope unless explicitly requested by the active phase docs
- CrewAI flows
- LLM calls
- topic discovery
- planning agents
- dashboard UI
- SSE
- CLI
- MCP
- publishing connectors