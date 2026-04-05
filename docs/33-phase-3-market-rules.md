# Phase 3 — Market Intelligence Rules

## Ownership
Market Intelligence owns:
- Topic
- TopicScore
- topic qualification logic

## Agents in scope
- Trend Analysis Agent
- Social Listening Agent
- SEO Gap Agent

## Required behavior
- Topic qualification must combine trend, social, and SEO signals.
- Topic scoring must be explicit and inspectable.
- Topic qualification rules should remain testable and configurable.
- Avoid hiding qualification logic entirely inside prompts.

## External sources
- Google Trends / pytrends
- Reddit API
- DataForSEO

## Boundaries
- Market Intelligence must not write directly into Content Intelligence tables.
- Transition from qualified topic to planning must occur via event or clearly bounded application handoff.

## Quality rules
- Prefer deterministic scoring wrappers around external signals where feasible.
- Preserve enough raw metadata to explain why a topic was qualified.