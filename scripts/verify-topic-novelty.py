from __future__ import annotations

import json

from ai_engine.agents import QualifiedTopicCandidate
import ai_engine.handler as handler


class FakeSession:
    pass


def build_candidate(
    *,
    topic: str,
    total_score: float,
) -> QualifiedTopicCandidate:
    return QualifiedTopicCandidate(
        topic=topic,
        trend_score=80.0,
        social_score=79.0,
        seo_score=78.0,
        total_score=total_score,
        qualification_note="Baseline qualification note.",
        source_metadata={"provider": "verification-script"},
    )


def main() -> None:
    prior_texts = [
        "ambient AI scribes in healthcare",
        "Ambient AI scribes in healthcare can reduce documentation time for clinical teams.",
        "Remote patient monitoring reimbursement trends in modern care delivery",
    ]

    candidates = [
        build_candidate(topic="ambient AI scribes in healthcare", total_score=91.0),
        build_candidate(
            topic="ambient AI scribes in healthcare operations",
            total_score=89.0,
        ),
        build_candidate(
            topic="remote patient monitoring reimbursement playbook",
            total_score=88.0,
        ),
        build_candidate(
            topic="prior authorization automation in healthcare",
            total_score=86.0,
        ),
    ]

    original = handler._prior_topic_and_article_texts
    handler._prior_topic_and_article_texts = lambda **_: prior_texts
    try:
        reranked = handler._apply_novelty_rules(
            session=FakeSession(),
            organization_id="org-demo",
            candidates=candidates,
        )
    finally:
        handler._prior_topic_and_article_texts = original

    topics = [candidate.topic for candidate in reranked]
    if "ambient AI scribes in healthcare" in topics:
        raise SystemExit("Exact duplicate topic was not filtered out.")

    reranked_by_topic = {candidate.topic: candidate for candidate in reranked}
    semantically_close = reranked_by_topic["ambient AI scribes in healthcare operations"]
    novel_candidate = reranked_by_topic["prior authorization automation in healthcare"]

    close_penalty = semantically_close.source_metadata["novelty"]["noveltyPenalty"]
    novel_penalty = novel_candidate.source_metadata["novelty"]["noveltyPenalty"]

    if close_penalty <= 0:
        raise SystemExit("Expected a novelty penalty for the semantically similar topic.")

    if semantically_close.total_score >= novel_candidate.total_score:
        raise SystemExit("Expected the more novel topic to outrank the semantically similar one.")

    result = {
        "remainingTopics": topics,
        "semanticallyClosePenalty": close_penalty,
        "novelCandidatePenalty": novel_penalty,
        "topTopic": reranked[0].topic if reranked else None,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
