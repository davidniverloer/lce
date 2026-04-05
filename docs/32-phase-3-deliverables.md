# Phase 3 — Deliverables

## Market Awareness
- Trend Analysis Agent
- Social Listening Agent
- SEO Gap Agent
- topic scoring logic
- persistence for qualified topics and their scores

## Semantic / planning intelligence
- Structure & Style Agent
- Sitemap Ingestor Agent
- sitemap parsing and indexed-page persistence
- internal link candidate or constraint generation
- ArticleBlueprint persistence

## API
- /market/analyze
- /sitemap/ingest
- any minimal supporting endpoints needed to inspect outputs

## Integration
- event contracts and handlers connecting topic qualification to planning
- event contracts and handlers connecting blueprint validation / planning output into the Phase 2 generation path

## Developer experience
- local run instructions for external API-backed market analysis
- test or smoke path for analyze -> blueprint -> generate