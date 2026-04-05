# Phase 2 — Worker and Flow Rules

## Worker responsibility
The worker is responsible for executing AI logic only.
It must not absorb orchestrator responsibilities such as HTTP handling, tenant administration, or direct UI concerns.

## Flow-first rule
The core of the worker is a deterministic flow, not a free-form agent swarm.
Agents operate inside the flow.
The flow defines order, state, retries, and transitions.

## State model
- Flow state must be explicitly typed.
- Use Pydantic for flow state.
- State must be persistable and recoverable.
- Avoid hidden mutable state.

## Agent set for Phase 2
Only these agents are allowed:
- Content Generation Agent
- QA & Compliance Agent

## Revision model
- Draft content must not be destructively overwritten without trace.
- Revisions must be append-oriented and reviewable.
- QA feedback must be explicit enough to drive another generation pass.

## Reliability rules
- Consumer must be idempotent.
- Duplicate messages must be ignored safely.
- Worker failures must not corrupt draft state.
- Flow progress should be restartable from persisted state where feasible.

## LLM integration
- Use LiteLLM abstraction if LLM wiring is included.
- Keep provider choice abstracted from agent logic.
- Avoid hard-coding provider-specific SDK behavior into core domain logic.

## Boundaries
- Worker may write only to the tables owned by its relevant bounded contexts.
- Cross-context transitions occur via events, not direct writes across contexts.