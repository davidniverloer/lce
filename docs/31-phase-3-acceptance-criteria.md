# Phase 3 — Acceptance Criteria

Phase 3 is complete only when all criteria below are satisfied.

## Market analysis
- The API endpoint /market/analyze returns a list of qualified topics.
- Each returned topic includes meaningful market/SEO scoring information.

## Sitemap intelligence
- The API endpoint /sitemap/ingest accepts a sitemap URL.
- Sitemap ingestion produces valid indexed pages or link candidates.
- Internal linking constraints can be derived from sitemap data.

## Planning
- The planning layer can generate an ArticleBlueprint or equivalent content plan from a qualified topic.
- The blueprint includes structure and style guidance.
- The blueprint can carry internal linking constraints into generation.

## Pipeline integration
- The Phase 2 generation flow can accept planning output rather than only a raw manual topic.
- Generated content can respect planning and linking constraints.

## Architecture compliance
- Topic discovery belongs to Market Intelligence.
- Blueprint and linking logic belong to Content Intelligence.
- No cross-bounded-context direct writes exist.
- All async integration continues to respect outbox/inbox and idempotency rules.

## Definition of done
- A user can analyze the market, qualify a topic, ingest a sitemap, generate a blueprint, and pass that blueprint into the generation pipeline.