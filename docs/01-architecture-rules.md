# Architecture Rules (STRICT)

## 1. System Structure
- Monorepo (pnpm workspaces)
- apps/
  - orchestrator (Node.js)
- workers/
  - ai-engine (Python)
- packages/
  - shared-types
- infra/

## 2. Core Components
- Orchestrator = API + coordination
- Worker = execution (AI / async jobs)
- RabbitMQ = communication backbone
- Redis = ephemeral state
- PostgreSQL = source of truth

## 3. Communication Rules
- NEVER call workers directly
- ALWAYS use events via RabbitMQ
- REST = commands only (no business logic execution)

## 4. Event-Driven Only
Flow:
Controller → Command → DB + Outbox → Event → Worker → DB

## 5. No Direct Broker Writes
Controllers MUST NOT publish to RabbitMQ directly  
→ Use Transactional Outbox Pattern

## 6. Bounded Context Isolation
- No cross-context DB writes
- Communication ONLY via events
- Each context owns its tables

## 7. Multi-Tenancy
- Every Aggregate MUST include:
  - organizationId
- ALL queries must filter by organizationId

## 8. Technology Constraints
- Orchestrator: Node.js + TypeScript
- Worker: Python 3.11+
- ORM:
  - Node: Prisma
  - Python: SQLAlchemy

## 9. Async First
- All long processes must be async
- No blocking HTTP flows

## 10. First Slice Priority
Build:
Event pipeline > business logic > UI