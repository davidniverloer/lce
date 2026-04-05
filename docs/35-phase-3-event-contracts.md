# Phase 3 — Event Contracts

## General event format
All integration events must include:
- eventId
- eventType
- version
- timestamp
- payload

## Core Phase 3 events
Use and/or implement the following event flow:
- TopicGenerationRequested
- TopicQualified
- SitemapUpdated
- BlueprintValidated

## Event flow intent
- TopicGenerationRequested starts market analysis for a campaign.
- TopicQualified signals that a topic passed qualification and is ready for planning.
- SitemapUpdated signals that sitemap knowledge is available for planning and linking.
- BlueprintValidated signals that planning output is complete and safe to hand to generation.

## Rules
- Events are immutable.
- Event schema evolution should be additive where possible.
- Event publication must still go through the outbox.
- Consumer processing must remain idempotent with processed_event_log.

## Phase boundary rule
Do not introduce Phase 4 or Phase 5 event concerns unless explicitly requested.