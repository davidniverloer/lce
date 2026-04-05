# Day 1 Bootstrap Plan

## Objective
Create a minimal working system end-to-end.

## Step 1 — Monorepo
Create:
- apps/orchestrator
- workers/ai-engine
- packages/shared-types
- infra/docker

## Step 2 — Infrastructure
Docker services:
- PostgreSQL
- RabbitMQ
- Redis

Verify:
- RabbitMQ UI accessible
- DB connection works

## Step 3 — Orchestrator
Create:
- Express server
- /health endpoint

Add:
- Prisma setup
- DB connection

## Step 4 — Database Schema
Create tables:
- campaigns
- topics
- outbox_events
- processed_event_log

## Step 5 — Command Flow
Endpoint:
POST /campaigns
→ creates campaign

POST /campaigns/:id/topic-generation
→ inserts event in outbox_events

## Step 6 — Outbox Relay
Process:
- reads outbox_events
- publishes to RabbitMQ
- marks event as sent

## Step 7 — Worker
Python service:
- connect to RabbitMQ
- consume TopicGenerationRequested
- insert Topic

## Step 8 — Read API
GET /campaigns/:id/topics

## Step 9 — Validation
End-to-end test:
- create campaign
- trigger event
- worker processes
- topic stored
- API returns topic

## Done When
Full async loop works without errors