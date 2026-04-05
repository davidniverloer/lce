# Phase 3 — Planning Rules

## Ownership
Content Intelligence owns:
- ArticleBlueprint
- InternalLink
- planning constraints
- blueprint validation

## Agents in scope
- Structure & Style Agent
- Sitemap Ingestor Agent

## Required behavior
- Planning must occur before full article generation.
- The Structure & Style Agent defines structure, tone, and section guidance.
- The Sitemap Ingestor Agent extracts existing site knowledge and internal linking constraints.
- Planning output must be explicit enough to guide the generation flow deterministically.

## Sitemap behavior
- Parse sitemap XML.
- Extract indexed pages and relevant titles or categories where available.
- Build link candidates or internal linking constraints from the sitemap-derived knowledge set.

## Blueprint behavior
- Blueprint must include topic, structure, style guidance, and linking constraints.
- Blueprint should be validatable before generation begins.

## Boundaries
- Content Intelligence must not directly own Market topic scoring.
- Planning consumes qualified topic inputs but does not redefine market ownership.