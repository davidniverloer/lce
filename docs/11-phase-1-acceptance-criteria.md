# Phase 1 — Acceptance Criteria

Phase 1 is complete only when all criteria below are satisfied.

## Infrastructure
- The full foundation stack starts successfully with docker compose.
- PostgreSQL, RabbitMQ, and Redis are reachable locally.

## Persistence
- PostgreSQL schemas exist for the bounded contexts required by the architecture.
- Migrations run successfully.

## Orchestrator
- The Node.js orchestrator starts locally.
- Basic health endpoint works.
- API can create an organization.
- API can create a campaign.

## Messaging reliability
- A business event is persisted to the local outbox table in the same transaction as the domain change.
- A relay process can publish that event from the outbox to RabbitMQ.
- Consumer idempotency is implemented with processed_event_log.

## Architecture compliance
- No direct controller-to-RabbitMQ publishing exists.
- No cross-bounded-context table writes exist.
- All domain data includes organization scoping.

## Definition of done
- A create-organization or create-campaign action results in a persisted domain change and a corresponding event published through the outbox flow.