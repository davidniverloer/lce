# AGENTS.md

## Project Overview
Lonnser Content Engine (LCE) is a multi-agent, event-driven SaaS system that transforms market signals into SEO-optimized content via deterministic orchestration and adaptive intelligence.

This repository is currently in **Phase 3: Stub-to-Live Market Intelligence Migration**.

## Core Principle

Separate **deterministic orchestration** from **non-deterministic intelligence**.

- Orchestration MUST remain deterministic
- Market discovery MAY become non-deterministic outside CI
- CI MUST remain fully deterministic

---

## Phase Context (CRITICAL)

You are operating in:

→ Phase 3: Market & Semantic Intelligence

Goal:
- Transition from stubbed discovery → real market-aware discovery
- Introduce live providers WITHOUT breaking determinism guarantees

---

## Non-Negotiable Invariants

### Architecture
- Event-driven (RabbitMQ)
- Outbox pattern for producers
- Inbox/idempotency for consumers
- No cross-domain DB writes
- CQRS separation enforced

### Ownership
- Market Intelligence owns topics
- Content Intelligence owns blueprints/drafts
- Repository owns final articles

### Determinism Boundaries
- Flows (CrewAI) are deterministic
- Event contracts are deterministic
- Persistence is deterministic
- ONLY signal acquisition may be non-deterministic

---

## Discovery & Intelligence Rules

### Discovery (Phase 3 CHANGE)

Discovery is now:

- ❌ NOT strictly deterministic anymore
- ✅ Allowed to use live market signals outside CI

Sources may include:
- Trends APIs
- Social APIs
- SEO APIs
- Crawling / extraction systems

However:
- Output schema MUST remain deterministic
- Pipeline structure MUST remain deterministic

---

### Qualification

Qualification is a structured scoring pipeline:

Inputs:
- trend_score
- social_score
- seo_score

Then:
1. Aggregate score
2. Deduplication
3. Novelty filtering
4. Final reranking

This pipeline MUST remain deterministic in structure.

---

### Selection Pipeline (MANDATORY)

ALWAYS follow:

1. Discover candidates
2. Qualify candidates
3. Remove duplicates
4. Apply novelty penalty
5. Rerank
6. Persist ALL qualified topics
7. Select TOP candidate

Never shortcut this pipeline.

---

## Environment Modes

### CI (STRICT)

CI MUST ALWAYS:

- Use stub discovery
- Use stub qualification
- Avoid ALL external APIs
- Produce identical outputs across runs

Override rule:
CI=true → FORCE stub mode everywhere

---

### Local Development

Allowed:
- stub
- mixed
- live

---

### Staging

Preferred:
- live discovery
- mixed qualification

---

### Production

Target:
- live discovery
- live qualification (when stable)

---

## Configuration Contract

Use env-driven behavior:

LCE_MARKET_MODE=stub|mixed|live
LCE_DISCOVERY_MODE=stub|live
LCE_QUALIFICATION_MODE=stub|mixed|live


CI override:

CI=true → ALL = stub


---

## Fallback Rules

### Non-CI environments

If provider fails:
- fallback to stub OR
- fail explicitly (depending on policy)

Consistency is REQUIRED.

---

## Observability (MANDATORY)

Every topic MUST record:

- discovery_mode (stub|live)
- provider_sources
- raw_scores
- weighted_score
- novelty_penalty
- final_score
- selection_rank

No black-box scoring allowed.

---

## Agent Behavior Rules

Agents MUST:

- Respect domain boundaries
- Never bypass orchestration
- Never directly publish to broker
- Never mutate external domain data
- Always emit structured outputs

Agents MUST NOT:

- Hardcode provider logic into domain layer
- Mix stub and live logic without config
- Skip ranking pipeline

---

## Implementation Guidelines

### DO

- Keep discovery modular (provider adapters)
- Keep scoring deterministic in structure
- Use feature flags via env
- Log everything

### DO NOT

- Embed randomness in pipeline logic
- Break reproducibility in CI
- Couple provider logic with domain logic

---

## Testing Rules

### CI tests MUST:

- Run fully stubbed
- Assert deterministic outputs
- Validate pipeline correctness

### Integration tests MAY:

- Use live providers (optional)
- Validate scoring realism

---

## Migration Definition of Done

Phase 3 is complete when:

- Discovery runs live outside CI
- CI remains deterministic
- Qualification supports stub/mixed/live
- Pipeline invariants remain intact
- Topics persist correctly
- Observability is complete

---

## Progressive Disclosure

For deeper rules, see:

- docs/36-phase-3-stub-to-live-rules.md
- docs/market-intelligence.md
- docs/event-contracts.md