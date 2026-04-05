# Phase 1 — Deliverables

## Monorepo
- root package.json
- pnpm-workspace.yaml
- .gitignore
- .env.example
- README.md

## Infrastructure
- infra/docker/docker-compose.yml or equivalent infra compose file
- local scripts or Make targets to start and stop infra

## Orchestrator
- apps/orchestrator
- TypeScript runtime
- health endpoint
- organization and campaign endpoints
- Prisma or Drizzle setup
- migration support

## Workers / background processes
- relay engine or equivalent outbox relay process
- optional minimal consumer skeleton only if needed to validate idempotency

## Shared contracts
- event schemas in packages/shared-types

## Data layer
- isolated schemas and tables required for:
  - IAM
  - Campaign Management
  - Market
  - Content
  - Repository
  - Audit
- outbox_events
- processed_event_log

## Developer experience
- VS Code debug config
- run instructions
- seed support if included