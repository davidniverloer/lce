# Phase 1 — Event and Data Rules

## Data ownership
- Each bounded context owns its own tables.
- No context may write directly into another context's tables.

## Schemas
Use isolated schemas aligned to bounded contexts:
- iam
- campaign
- market
- content
- repository
- audit

## Event contract minimum fields
All integration events must include:
- eventId
- eventType
- timestamp
- version
- payload

## Transaction rule
A domain change and its integration event must be stored in the same local transaction.

## Outbox rule
Produced events are first written to outbox_events.
A relay publishes them to RabbitMQ asynchronously.

## Idempotency rule
Consumers must attempt to register event_id in processed_event_log before processing.
If insertion fails because the event already exists, the event must be acknowledged and ignored safely.

## Multi-tenant rule
All aggregates and domain rows must include organization_id.
All queries must filter by organization_id.

## Read-side rule
Read models are allowed later, but Phase 1 must not bypass domain ownership boundaries to fake them.