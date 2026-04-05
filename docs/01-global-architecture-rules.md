# Global Architecture Rules

## System structure
- Monorepo with apps, workers, packages, infra, docs
- apps/orchestrator = Node.js API
- workers = asynchronous execution engines
- packages = shared contracts and utilities
- infra = Docker, scripts, deployment configuration

## Communication model
- Event-driven architecture only for async integration
- REST starts commands
- RabbitMQ carries integration events
- Redis stores ephemeral state and cache
- PostgreSQL is the primary system of record

## Hard rules
- Never publish directly to RabbitMQ from a REST controller
- Always use the Transactional Outbox Pattern for produced events
- Consumers must be idempotent using processed_event_log
- No cross-bounded-context writes
- Each bounded context owns its tables
- Every aggregate root must include organizationId
- All queries must enforce organization scoping

## Coding bias
- prefer explicit, boring, maintainable code
- prefer simple vertical slices
- avoid premature abstractions
- keep deterministic platform behavior separate from adaptive AI logic