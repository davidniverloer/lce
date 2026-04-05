# LCE agent instructions

## Mission
Bootstrap the Lonnser Content Engine from scratch on macOS using VS Code and Codex.

## Source of truth
Read these first:
- docs/00-project-overview.md
- docs/01-architecture-rules.md
- docs/02-day-1-bootstrap.md
- docs/03-bounded-contexts.md
- docs/04-event-contracts.md
- docs/05-data-persistence-rules.md

## Hard constraints
- Use a pnpm monorepo.
- apps/orchestrator is Node.js + TypeScript.
- workers/ai-engine is Python 3.11+.
- Infra must include PostgreSQL, RabbitMQ, Redis.
- Never write directly to RabbitMQ from REST controllers.
- Use transactional outbox for producers.
- Consumers must be idempotent using processed_event_log.
- No cross-bounded-context DB writes.
- Every aggregate root must include organizationId.
- Prefer the thinnest vertical slice first.

## Day 1 target
Deliver:
- infra/docker/docker-compose.yml
- root workspace files
- minimal orchestrator with /health
- minimal ai-engine worker skeleton
- shared event contract for TopicGenerationRequested
- initial Prisma schema
- bootstrap README with exact run commands

## Working style
- Plan before coding for large tasks.
- Make small commits.
- Run lint/build/tests before declaring success.
- If architecture is ambiguous, follow docs/01-architecture-rules.md.