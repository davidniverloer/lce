# Phase 3 — Stub-to-Live Rules

## Purpose
Define how Phase 3 moves from stubbed market intelligence toward live market intelligence without breaking architecture, reproducibility, or CI determinism.

## Core rule
Discovery should no longer be permanently deterministic.

Phase 3 must support live topic discovery in non-CI environments using real market signals and external providers.

However:
- CI must remain fully deterministic
- orchestration must remain deterministic
- ranking pipeline structure must remain deterministic
- persistence and event contracts must remain deterministic and testable

## Why
Phase 3 is the Market & Semantic Intelligence phase.
Its purpose is to add real Market Awareness and planning capabilities, including external APIs and topic qualification before generation.

Therefore:
- live discovery is in scope for Phase 3
- live qualification is in scope for Phase 3
- deterministic-only discovery is no longer the target architecture
- deterministic execution is still required for CI and reliability-sensitive validation

## Separation of concerns

### 1. Discovery
Discovery is responsible for producing candidate topics from market evidence.

In non-CI environments, discovery should use live providers and real inputs where configured.

Examples of live discovery inputs:
- Google Trends / pytrends
- Reddit API
- DataForSEO-derived opportunities
- semantic extraction / crawling if enabled

Discovery may still support stub mode for tests, CI, and local fallback, but stub mode is no longer the intended default architecture for Phase 3 production behavior.

### 2. Qualification
Qualification remains a distinct step after discovery.

Qualification is responsible for:
- trend scoring
- social scoring
- SEO scoring
- weighted ranking inputs

Qualification may run in:
- stub mode
- mixed mode
- live mode

depending on environment and provider readiness.

### 3. Novelty and selection
Novelty filtering and final selection remain deterministic in structure.

Pipeline shape:
1. discover candidate topics
2. qualify candidates
3. remove exact duplicates
4. apply semantic similarity / novelty penalty
5. rerank by adjusted score
6. persist all qualified topics
7. select the top candidate for blueprinting and generation

The scoring sources may be live, but the pipeline contract must remain stable.

## Environment rules

### CI
CI must always be fully deterministic.

CI requirements:
- discovery uses stub mode only
- qualification uses stub mode only
- no live external API calls
- outputs must remain reproducible across runs
- tests must not depend on network availability, provider latency, or changing live market data

CI override rule:
- if CI=true, all market intelligence providers must run in stub mode regardless of other settings

### Local development
Local development may use:
- stub mode
- mixed mode
- live mode

Developers must be able to switch providers independently without changing business logic.

### Staging / manual validation
Staging or manual validation environments should prefer mixed mode first:
- discovery may be live
- one or more qualification providers may be live
- fallback to stub mode is allowed where provider readiness is incomplete

### Production
Production should prefer live discovery and live qualification where providers are configured and healthy.

Fallback behavior may be used for resilience, but live provider-backed market intelligence is the target operating mode.

## Configuration model

Use environment-driven configuration.

Recommended variables:
- LCE_MARKET_MODE=stub|mixed|live
- LCE_DISCOVERY_MODE=stub|live
- LCE_QUALIFICATION_MODE=stub|mixed|live
- LCE_TREND_PROVIDER_MODE=stub|live
- LCE_SOCIAL_PROVIDER_MODE=stub|live
- LCE_SEO_PROVIDER_MODE=stub|live

Recommended override:
- CI=true forces all of the above to stub

## Discovery rules

### Live discovery target
Discovery should gather real candidate topics from external signals instead of relying only on seeded deterministic patterns.

### Acceptable implementation path
Discovery may evolve in stages:

#### Stage A
Stub-only discovery for CI and safety fallback

#### Stage B
Hybrid discovery:
- seeded deterministic candidates
- plus provider-backed enrichment / expansion

#### Stage C
Primary live discovery:
- provider-backed candidate generation is the default outside CI
- deterministic discovery remains only as fallback or test support

### Discovery quality requirements
Live discovery must:
- preserve organization and campaign context
- respect campaign niche and editorial constraints
- emit structured candidate topics
- remain observable and debuggable
- fail safely when providers time out or return empty results

## Qualification rules

Qualification should remain provider-abstracted.

Each signal source must support:
- a stub implementation
- a live implementation

Applicable components:
- TrendAnalysisAgent
- SocialListeningAgent
- SeoGapAgent

The weighted aggregate contract must remain stable even when signal providers become live.

## Fallback rules

### CI
No fallback needed because CI is always stubbed.

### Non-CI
If a live provider fails, the implementation may:
- fall back to stub mode for that provider, or
- fail according to the explicit environment policy

Choose one policy and apply it consistently.
The smallest safe default is:
- fallback allowed in local/staging
- explicit policy for production

## Observability rules

For every discovered and/or qualified topic, capture enough metadata to explain the result.

At minimum record:
- whether discovery was stub or live
- whether each qualification signal was stub or live
- raw trend/social/SEO scores
- weighted total score
- novelty penalty
- adjusted score
- final ranking position
- whether the topic advanced to blueprinting

This metadata should be persisted or logged in a structured way.

## Architectural invariants
These rules never change:
- no direct controller-to-broker publishing
- outbox pattern for produced events
- idempotent consumers using processed_event_log
- no cross-bounded-context database writes
- market data belongs to Market Intelligence
- blueprint data belongs to Content Intelligence
- event schemas remain versioned and additive where possible

## Definition of done for stub-to-live migration
The migration is acceptable when all of the following are true:

1. Discovery can run live outside CI
2. CI remains fully deterministic
3. Qualification can run in stub, mixed, or live mode without changing the pipeline contract
4. All qualified topics are still persisted
5. Duplicate filtering and novelty reranking still work
6. The top selected topic still feeds blueprinting correctly
7. Logs or persisted metadata make it clear which signals were live vs stubbed

## Non-goals
This document does not authorize:
- Phase 4 dashboard productization work
- SaaS quota UI work
- SSE
- CLI
- MCP
- publishing connectors

## Practical operating principle
Use live market evidence in real environments.
Use deterministic stubs in CI.
Keep the orchestration backbone and pipeline structure stable in all environments.