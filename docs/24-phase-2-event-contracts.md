# Phase 2 — Event Contracts

## General event format
All events must include:
- eventId
- eventType
- version
- timestamp
- payload

## Primary incoming event for Phase 2
GenerationRequested

Suggested payload:
- organizationId
- campaignId
- taskId
- topic
- targetAudience
- outputFormats

## Primary workflow outcome events
Use one or more of the following if implemented:
- DraftGenerated
- DraftRevisionRequested
- ContentApproved
- ArticleStored

## Rules
- Events are immutable.
- Schema evolution must be additive where possible.
- Breaking changes require a version bump.
- Event publication must still go through the outbox.
- Consumer processing must still record processed_event_log before business handling.

## Phase boundary rule
Do not introduce TopicQualified or market-analysis event complexity unless Phase 3 work is explicitly requested.