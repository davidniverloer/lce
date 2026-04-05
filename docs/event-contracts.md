# Event Contracts

## Purpose
This document defines the public asynchronous contracts used between LCE bounded contexts.

All inter-domain asynchronous communication must use explicit versioned event contracts. Direct cross-domain writes are not allowed. The DDD event catalog and persistence spec make these contracts the public integration boundary between contexts. 

## Global rules

### Standard event envelope
Every integration event must include:
- eventId
- eventType
- version
- timestamp
- payload

This is a hard rule in the DDD and persistence specification. 

### Versioning
- Event schemas must be versioned semantically.
- Additive change is preferred.
- Renaming or removing fields requires a major version bump.
- When breaking changes occur, overlapping support windows should be maintained where practical. :contentReference[oaicite:12]{index=12}

### Delivery model
- Events are published asynchronously through RabbitMQ.
- Producers must use the Transactional Outbox Pattern.
- Consumers must be idempotent using processed_event_log.
- RabbitMQ delivery is at-least-once, so duplicates must be handled safely. 

### Multi-tenancy
All payloads crossing bounded contexts must preserve tenant scoping through organizationId.

## Canonical event envelope

```json
{
  "eventId": "uuid-v4",
  "eventType": "EventName",
  "version": "1.0",
  "timestamp": "2026-04-04T10:00:00Z",
  "payload": {}
}