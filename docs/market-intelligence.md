# Market Intelligence

## Purpose
The Market Intelligence domain is responsible for discovering, qualifying, ranking, and selecting topics with real market potential before planning and generation begin.

It is a core domain of LCE and must remain isolated from Content Intelligence and Content Repository except through explicit contracts and events.

## Domain ownership
Market Intelligence owns:
- Topic
- TopicScore
- topic qualification logic
- candidate ranking
- duplicate filtering rules within market scope
- novelty-aware reranking inputs and outcomes
- persistence of qualified topics and their scoring metadata

Market Intelligence does not own:
- ArticleBlueprint
- ArticleDraft
- final Article
- internal linking constraints as final planning artifacts

Those belong to Content Intelligence or Repository. 

## Strategic role
Market Intelligence is the first intelligence-bearing stage in the long-running content saga.

High-level saga flow:
1. TopicGenerationRequested
2. Market Intelligence analyzes and qualifies topics
3. TopicQualified
4. Content Intelligence performs planning
5. BlueprintValidated
6. Generation and QA continue downstream

This matches the DDD saga and event flow. :contentReference[oaicite:1]{index=1}

## Core objective
Guarantee that the topic handed to planning is not arbitrary.

A valid selected topic should be:
- relevant to the campaign niche
- supported by market evidence
- differentiated enough from prior content
- ranked through an explainable scoring process
- persisted with enough metadata to justify selection

## Market pipeline
The Market Intelligence pipeline must always follow this structure:

1. Discover candidate topics
2. Qualify each candidate with structured signals
3. Remove exact duplicates
4. Apply semantic novelty penalty
5. Rerank by adjusted score
6. Persist all qualified topics
7. Select the top candidate for planning

Do not bypass this structure.

## Discovery
Discovery creates candidate topics.

### Production intent
In Phase 3 and later, discovery should support live market-aware topic discovery outside CI by using real external signals and provider-backed inputs.

### CI rule
In CI, discovery must remain stubbed and deterministic so tests are reproducible and do not depend on network conditions or changing live data. :contentReference[oaicite:2]{index=2}

### Acceptable discovery inputs
Depending on environment and implementation maturity, discovery may use:
- Google Trends via pytrends
- Reddit social signals
- DataForSEO opportunity inputs
- semantic extraction/crawling inputs
- campaign niche and editorial constraints
- existing sitemap or domain knowledge where relevant

The Blueprint describes Market Awareness as a live sequence combining trends, social listening, and SEO/content-gap analysis. 

### Discovery output contract
Discovery must output structured candidate topics, not free-form text blobs.

Each candidate should be representable with at least:
- organization_id / organizationId
- campaign_id / campaignId
- candidate title or topic string
- discovery source metadata
- discovery mode: stub or live
- timestamp

## Qualification
Qualification is a distinct step after discovery.

It evaluates each candidate topic using structured signals and produces a comparable score.

### Required signal categories
Each candidate should receive:
- trend score
- social score
- SEO score

These map naturally to the Market Awareness agents:
- Trend Analysis Agent
- Social Listening Agent
- SEO Gap Agent :contentReference[oaicite:4]{index=4}

### Qualification contract
Qualification may use:
- stub providers
- mixed providers
- live providers

But its pipeline shape must remain stable across environments.

### Explainability rule
Qualification must never be a black box.
For each candidate, the system must preserve enough information to explain:
- why it scored well or poorly
- which provider or mode produced each signal
- how the aggregate score was computed

## TopicScore
TopicScore is a Market Intelligence value object.

It should encapsulate the scoring inputs and the qualification decision boundary rather than scattering that logic across the codebase. The DDD explicitly models TopicScore as a composite of search volume, content gap, trend signal, and social buzz, and Topic qualification is governed by a TopicQualificationSpec. :contentReference[oaicite:5]{index=5}

Recommended conceptual fields:
- trend_score
- social_score
- seo_score
- weighted_total_score
- qualification_status
- score_metadata

## Duplicate filtering
Before final selection, Market Intelligence must remove exact duplicates.

At minimum, exact duplicates should be checked against:
- previously qualified topics in Market Intelligence
- existing stored articles in Repository

This is consistent with the DDD’s TopicDeduplicationService and repository/query boundaries. :contentReference[oaicite:6]{index=6}

## Novelty filtering
Market Intelligence must penalize candidates that are semantically too close to prior qualified topics or previously stored articles.

Novelty logic should:
- compare candidates to relevant historical content
- compute similarity or proximity
- apply a novelty penalty
- preserve the original score and the adjusted score

### Rule
Novelty affects ranking, not the existence of the original score.
The system should preserve:
- raw weighted score
- novelty penalty
- adjusted final score

## Final selection
After scoring, dedupe, and novelty adjustment:
- all qualified topics must be persisted
- only the top adjusted candidate advances to planning

This keeps downstream planning deterministic in structure while still being informed by live market evidence.

## Environment modes
Market Intelligence must be environment-aware.

### CI
- discovery = stub
- qualification = stub
- no live external calls
- fully reproducible outputs

### Local development
- stub, mixed, or live depending on configuration

### Staging
- prefer live discovery
- mixed or live qualification

### Production
- prefer live discovery
- prefer live qualification where providers are configured and healthy

## Recommended configuration
Suggested environment variables:
- LCE_MARKET_MODE=stub|mixed|live
- LCE_DISCOVERY_MODE=stub|live
- LCE_QUALIFICATION_MODE=stub|mixed|live
- LCE_TREND_PROVIDER_MODE=stub|live
- LCE_SOCIAL_PROVIDER_MODE=stub|live
- LCE_SEO_PROVIDER_MODE=stub|live

Override rule:
- CI=true forces all provider modes to stub

This follows the project’s environment-driven configuration model and deterministic CI guidance. 

## Persistence rules
Market Intelligence persistence must follow the global data architecture:
- each bounded context owns its own data
- no cross-domain direct writes
- async cross-domain changes happen via events
- all rows must remain tenant-scoped via organization_id
- writes and event publication must respect transaction boundaries and outbox rules :contentReference[oaicite:8]{index=8}

Recommended persisted fields for qualified topics:
- id
- organization_id
- campaign_id
- title
- discovery_mode
- qualification_mode
- trend_score
- social_score
- seo_score
- weighted_total_score
- novelty_penalty
- adjusted_score
- ranking_position
- selected_for_blueprint
- metadata JSONB
- created_at

## Observability
For every candidate and qualified topic, record enough information to support:
- debugging
- replay analysis
- score explainability
- provider health diagnosis
- ranking audits

At minimum capture:
- discovery source(s)
- stub/live mode per signal
- raw scores
- weighted total
- novelty penalty
- final adjusted score
- final rank
- selected flag

Structured logging and correlation IDs should be used throughout the flow. 

## Anti-patterns
Do not:
- treat discovery as the same thing as qualification
- bypass dedupe or novelty before selecting a winner
- hide score composition entirely inside prompts
- write directly into Content Intelligence tables
- let CI depend on live APIs
- make ranking non-explainable

## Done criteria
Market Intelligence is functioning correctly when:
- candidate topics can be discovered in a structured way
- qualification produces explainable scores
- duplicates are removed
- novelty penalties are applied
- all qualified topics are persisted
- one top candidate is selected and handed to planning
- CI remains deterministic
- non-CI environments can use live market evidence