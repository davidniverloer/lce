# Phase 2 — Acceptance Criteria

Phase 2 is complete only when all criteria below are satisfied.

## Triggering
- A POST request to /tasks/generate with a manual topic is accepted.
- The request causes a worker execution to start asynchronously.

## Worker
- The Python worker consumes the generation task from RabbitMQ.
- The worker uses CrewAI flow orchestration with typed state.

## Generation
- The Content Generation Agent produces a first draft.

## QA loop
- The QA & Compliance Agent evaluates the draft.
- If the draft is insufficient, a revision is requested.
- At least one revision loop is supported by the architecture.

## Persistence
- Draft workflow state is persisted.
- Revisions are stored as traceable history, not overwritten blindly.
- Final approved content is stored in the repository schema with status completed.

## Architecture compliance
- No direct controller-to-worker coupling exists.
- All async integration still respects outbox/inbox rules.
- Multi-tenancy is preserved across task, draft, revision, and repository data.

## Definition of done
- A manual topic can travel end to end:
  request -> event -> worker -> draft -> QA -> optional revision -> approved article stored