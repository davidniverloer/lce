# Lonnser Content Engine — Project Overview

## Mission
Build an event-driven, multi-tenant SaaS platform that orchestrates AI agents to generate SEO-optimized content autonomously.

## Delivery strategy
The system is delivered in sequential phases:
1. Phase 1 — Foundation & Persistence
2. Phase 2 — Core Agentic Engine
3. Phase 3 — Market & Semantic Intelligence
4. Phase 4 — Multi-Tenant SaaS & Dashboard
5. Phase 5 — Ecosystem & Extensibility

## Core principle
The system follows a stateful decoupling architecture:
- user interaction is separate from long-running execution
- asynchronous work continues independently
- state is persisted and observable

## Core runtime
- Orchestrator: Node.js / TypeScript
- Workers: Python 3.11+
- Database: PostgreSQL
- Broker: RabbitMQ
- State / cache: Redis

## Current phase
Phase 3 — Market & Semantic Intelligence

## Phase 3 summary
Add topic discovery, topic qualification, sitemap intelligence, and article planning on top of the existing generation engine.

## What Phase 3 is not
- not dashboard productization
- not full SaaS quota/role UX rollout
- not SSE, CLI, or MCP
- not publishing connectors