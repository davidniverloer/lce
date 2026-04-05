# Phase 1 — Foundation & Persistence

## Goal
Establish the technical foundation of LCE without introducing AI agent complexity.

## Scope
Phase 1 includes:
- local and containerized infrastructure
- PostgreSQL as primary database
- Redis
- RabbitMQ
- Node.js orchestrator
- isolated database schemas by bounded context
- outbox/inbox reliability mechanisms
- basic REST endpoints for organization and campaign management

## Required infrastructure
- PostgreSQL 16+
- RabbitMQ
- Redis

## Required backend
- Orchestrator in Node.js + TypeScript
- ORM and migrations
- basic authentication scaffolding only if needed for endpoint structure
- CRUD foundations for organizations and campaigns

## Must-have reliability patterns
- Transactional Outbox Pattern
- consumer idempotency via processed_event_log

## Explicitly out of scope
- CrewAI flows
- content generation
- QA agent
- market intelligence APIs
- sitemap ingestion
- dashboard
- SSE
- CLI
- MCP
- external publishing connectors