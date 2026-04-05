# Data & Persistence Rules

## 1. Source of Truth
- PostgreSQL is the primary database
- Each context has its own tables

## 2. No Cross-Domain Writes
- NEVER write into another context's tables

## 3. Transaction Boundaries
- One transaction = one aggregate change
- Event must be stored in same transaction

## 4. Outbox Pattern (MANDATORY)

Flow:
1. Update domain entity
2. Insert event into outbox_events
3. Commit transaction
4. Async relay publishes event

## 5. Inbox / Idempotency

Each consumer MUST:
- insert eventId into processed_event_log
- if duplicate → ignore

## 6. Tables (Day 1)

campaigns
- id
- organization_id
- name

topics
- id
- organization_id
- campaign_id
- title

outbox_events
- id
- event_type
- payload (JSONB)
- processed (boolean)

processed_event_log
- event_id
- timestamp

## 7. Multi-Tenant Rule
ALL tables must include:
- organization_id

ALL queries must filter by:
- organization_id

## 8. Read Models (Later)
- Separate tables for fast queries
- Built from events (CQRS)

## 9. Indexing
- primary key: id
- composite: (organization_id, id)

## 10. Reliability
System must tolerate:
- duplicate events
- delayed processing
- worker restarts