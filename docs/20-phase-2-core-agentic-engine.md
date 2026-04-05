# Phase 2 — Core Agentic Engine

## Goal
Introduce the first real AI execution path in LCE.

## Scope
Phase 2 includes:
- Python Worker Engine running in isolation
- CrewAI deterministic flow orchestration
- Pydantic flow state
- Content Generation Agent
- QA & Compliance Agent
- iterative revision loop
- persistence of draft state and revisions
- storage of approved content in repository

## Input model
Phase 2 starts from a manually provided topic.
This phase does not include topic discovery or topic qualification from external market sources.

## Required flow
1. API receives a generation request with a manual topic.
2. Orchestrator persists the task and emits the appropriate event through the outbox.
3. Worker consumes the event.
4. Worker runs the generation flow.
5. Content Generation Agent creates a first draft.
6. QA & Compliance Agent evaluates the draft.
7. If QA fails, revision is requested and generation repeats.
8. If QA passes, approved content is stored in repository.

## Required persistence
- flow state must be typed and durable
- draft revisions must be traceable
- final approved article must be stored separately from draft workflow state

## Explicitly out of scope
- Trend Analysis Agent
- Social Listening Agent
- SEO Gap Agent
- Structure & Style Agent
- Sitemap Ingestor Agent
- DataForSEO
- Reddit
- Google Trends
- external publishing