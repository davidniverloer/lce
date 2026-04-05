# Phase 3 — Market & Semantic Intelligence

## Goal
Enable LCE to discover qualified topics and generate a structured article plan before content drafting.

## Scope
Phase 3 includes:
- Market Awareness Crew
- Trend Analysis Agent
- Social Listening Agent
- SEO Gap Agent
- topic qualification and TopicScore computation
- sitemap ingestion
- extraction of internal linking constraints
- Planning Crew
- Structure & Style Agent
- Sitemap Ingestor Agent
- ArticleBlueprint generation
- integration of planning outputs with the existing Phase 2 generation pipeline

## Required APIs and tools
- Google Trends / pytrends
- Reddit API
- DataForSEO
- sitemap parsing
- semantic extraction and crawling where needed

## Required new API surface
- POST /market/analyze
- POST /sitemap/ingest
- any minimal read endpoints needed to inspect generated topics or indexed pages

## Required output
Phase 3 must produce:
- qualified topics with scores
- planning-ready topic output
- sitemap-derived link candidates / constraints
- an article blueprint that can be handed to the Phase 2 generation flow

## Explicitly out of scope
- dashboard-heavy UX expansion
- full SaaS admin/productization work
- SSE
- CLI
- MCP
- publishing connectors