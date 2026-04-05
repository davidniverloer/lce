# LCE Agent Instructions

## Mission
Build the Lonnser Content Engine incrementally, phase by phase, following the roadmap and architecture documents.

## Source of truth
Always read these first:
- docs/00-project-overview.md
- docs/01-global-architecture-rules.md
- docs/30-phase-3-market-semantic-intelligence.md
- docs/31-phase-3-acceptance-criteria.md
- docs/32-phase-3-deliverables.md
- docs/33-phase-3-market-rules.md
- docs/34-phase-3-planning-rules.md
- docs/35-phase-3-event-contracts.md
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
Phase 3 — Market & Semantic Intelligence

## Phase 3 objective
Deliver intelligent topic discovery and planning:
- Market Awareness Crew
- qualified topic scoring
- sitemap ingestion
- internal linking constraints
- article blueprint / content plan generation
- integration with the existing Phase 2 generation pipeline

## Out of scope unless explicitly requested
- dashboard productization
- full CQRS UX work
- SaaS quota/billing expansion beyond what already exists
- SSE
- CLI
- MCP
- publishing connectors
- WordPress / Shopify / Notion / Medium integrations