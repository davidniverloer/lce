# Lonnser Content Engine (LCE) — Project Overview

## Mission
Build an event-driven SaaS platform that autonomously generates SEO-optimized content using multi-agent AI orchestration.

## Core Idea
Transform:
Market data → Topics → Article Plan → Draft → QA → Published content

## System Architecture (High-Level)
- Orchestrator (Node.js / TypeScript)
- Worker Engine (Python / CrewAI)
- Message Broker (RabbitMQ)
- State Store (Redis)
- Database (PostgreSQL)

## Key Principle
Stateful Decoupling:
- UI is separated from execution
- Long-running processes continue independently

## Execution Model
Event-driven system:
- Commands → Events → Workers → New Events

## First Goal (Day 1)
Implement a minimal vertical slice:
- Create Campaign
- Emit TopicGenerationRequested
- Worker consumes event
- Store Topic
- Retrieve Topic via API

## Non-Goals (Day 1)
- No UI
- No LLM calls
- No full agent system
- No IAM
- No publishing integrations

## Success Criteria
System can:
1. Accept a request
2. Emit an event
3. Process it asynchronously
4. Persist result
5. Return result via API