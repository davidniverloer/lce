# Phase 2 — Deliverables

## Worker engine
- workers/ai-engine runtime is fully operational
- RabbitMQ consumer for generation tasks
- SQLAlchemy or SQLModel persistence layer
- environment-driven configuration

## Agentic execution
- CrewAI installed and wired into the worker
- deterministic flow definition
- typed flow state with Pydantic
- generation task handler

## Agents
- Content Generation Agent
- QA & Compliance Agent

## Domain persistence
- article draft persistence
- revision persistence
- compliance / QA feedback persistence
- repository article persistence for approved content

## Event integration
- generation request event contract
- consumed-event idempotency using processed_event_log
- emitted completion / approval event if implemented in this phase

## Developer experience
- local run instructions
- debug configuration for worker flow
- basic test path for manual topic generation