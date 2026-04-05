#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
input_path="${PHASE35_INPUT_PATH:-}"
output_path="${PHASE35_OUTPUT_PATH:-$(mktemp "${TMPDIR:-/tmp}/phase35-artifacts.XXXXXX")}"

cleanup() {
  if [ -z "${input_path}" ]; then
    rm -f "${output_path}"
  fi
}

trap cleanup EXIT INT TERM

if [ -z "${input_path}" ]; then
  echo "Running deterministic Phase 3.5 integration validation"
  POST_SMOKE_SCRIPT="bash scripts/validate-phase35-artifacts.sh" \
  PHASE35_OUTPUT_PATH="${output_path}" \
  SMOKE_OUTPUT_PATH="${output_path}" \
  bash "${repo_root}/scripts/bootstrap-and-test-background.sh"
  exit 0
fi

python3 - "${input_path}" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as handle:
    payload = json.load(handle)

qualified_topics = payload["qualifiedTopicsResponse"].get("qualifiedTopics", [])
if not qualified_topics:
    raise SystemExit("No qualified topics were produced.")

qualified_topic = qualified_topics[0]
source_metadata = qualified_topic.get("sourceMetadata", {})
discovery = source_metadata.get("discovery") or source_metadata.get("discoveryStatus") or {}
qualification_status = source_metadata.get("status", {}).get("qualification", {})

if not discovery.get("sources") and not discovery.get("discoverySources"):
    raise SystemExit("Qualified topic is missing discovery source attribution.")
if qualification_status.get("confidenceScore") is None:
    raise SystemExit("Qualified topic is missing confidenceScore.")
if qualification_status.get("confidenceBand") is None:
    raise SystemExit("Qualified topic is missing confidenceBand.")
if qualification_status.get("fallbackWeightShare") is None:
    raise SystemExit("Qualified topic is missing fallbackWeightShare.")

blueprints = payload["blueprintsResponse"].get("blueprints", [])
if not blueprints:
    raise SystemExit("No blueprints were produced.")

blueprint = blueprints[0].get("blueprint", {})
required_blueprint_fields = [
    "differentiationAngle",
    "differentiationRationale",
    "targetDelta",
    "siteContext",
    "status",
]
for field in required_blueprint_fields:
    if field not in blueprint:
        raise SystemExit(f"Blueprint is missing {field}.")

if blueprint["status"].get("differentiationReady") is not True:
    raise SystemExit("Blueprint status does not show differentiationReady=true.")

task_status = payload["taskStatusResponse"].get("statusArtifact", {})
if not task_status.get("discovery"):
    raise SystemExit("Task status surface is missing discovery status.")
if not task_status.get("qualification"):
    raise SystemExit("Task status surface is missing qualification status.")
if not task_status.get("blueprint"):
    raise SystemExit("Task status surface is missing blueprint status.")
if not task_status.get("generation"):
    raise SystemExit("Task status surface is missing generation status.")
if not task_status.get("qa"):
    raise SystemExit("Task status surface is missing QA status.")
if not task_status.get("infra", {}).get("relay"):
    raise SystemExit("Task status surface is missing relay status.")

qa = task_status["qa"]
if qa.get("issues") is None:
    raise SystemExit("QA status artifact is missing issues.")
if qa.get("revisionInstructions") is None:
    raise SystemExit("QA status artifact is missing revisionInstructions.")
if qa.get("rubric") is None:
    raise SystemExit("QA status artifact is missing rubric.")

campaign_summary = payload["campaignStatusSummaryResponse"].get("summaries", [])
if not campaign_summary:
    raise SystemExit("Campaign status summary surface returned no summaries.")

summary_item = campaign_summary[0]
if summary_item.get("taskId") != payload["taskStatusResponse"].get("taskId"):
    raise SystemExit("Campaign status summary taskId does not match the completed task.")
if summary_item.get("confidenceBand") != qualification_status.get("confidenceBand"):
    raise SystemExit("Campaign status summary confidenceBand is inconsistent.")
if summary_item.get("confidenceScore") != qualification_status.get("confidenceScore"):
    raise SystemExit("Campaign status summary confidenceScore is inconsistent.")
if summary_item.get("fallbackWeightShare") != qualification_status.get("fallbackWeightShare"):
    raise SystemExit("Campaign status summary fallbackWeightShare is inconsistent.")
if summary_item.get("differentiationReady") != blueprint["status"].get("differentiationReady"):
    raise SystemExit("Campaign status summary differentiationReady is inconsistent.")
if summary_item.get("siteAware") != blueprint["status"].get("siteAware"):
    raise SystemExit("Campaign status summary siteAware is inconsistent.")
if summary_item.get("qaStatus") != task_status["generation"].get("qaStatus"):
    raise SystemExit("Campaign status summary qaStatus is inconsistent.")
if summary_item.get("qaPassed") != task_status["generation"].get("qaPassed"):
    raise SystemExit("Campaign status summary qaPassed is inconsistent.")

campaign_trends = payload["campaignStatusTrendsResponse"].get("metrics", {})
if campaign_trends.get("totalTasks") != len(campaign_summary):
    raise SystemExit("Campaign status trends totalTasks does not match summary count.")
if campaign_trends.get("articleCompletedCount") != 1:
    raise SystemExit("Campaign status trends articleCompletedCount is inconsistent.")
if campaign_trends.get("qaPassCount") != 1:
    raise SystemExit("Campaign status trends qaPassCount is inconsistent.")
if campaign_trends.get("qaPassRate") != 1:
    raise SystemExit("Campaign status trends qaPassRate is inconsistent.")
if campaign_trends.get("differentiationReadyCount") != 1:
    raise SystemExit("Campaign status trends differentiationReadyCount is inconsistent.")
if campaign_trends.get("siteAwareCount") != 1:
    raise SystemExit("Campaign status trends siteAwareCount is inconsistent.")
if campaign_trends.get("averageConfidenceScore") != qualification_status.get("confidenceScore"):
    raise SystemExit("Campaign status trends averageConfidenceScore is inconsistent.")
if campaign_trends.get("averageFallbackWeightShare") != qualification_status.get("fallbackWeightShare"):
    raise SystemExit("Campaign status trends averageFallbackWeightShare is inconsistent.")

campaign_compare = payload["campaignStatusCompareResponse"]
latest = campaign_compare.get("latest", {})
previous = campaign_compare.get("previous", {})
delta = campaign_compare.get("delta", {})
if campaign_compare.get("windowSize") != 1:
    raise SystemExit("Campaign status compare windowSize is inconsistent.")
if latest.get("taskCount") != 1:
    raise SystemExit("Campaign status compare latest taskCount is inconsistent.")
if latest.get("articleCompletedCount") != 1:
    raise SystemExit("Campaign status compare latest articleCompletedCount is inconsistent.")
if latest.get("averageConfidenceScore") != qualification_status.get("confidenceScore"):
    raise SystemExit("Campaign status compare latest averageConfidenceScore is inconsistent.")
if latest.get("averageFallbackWeightShare") != qualification_status.get("fallbackWeightShare"):
    raise SystemExit("Campaign status compare latest averageFallbackWeightShare is inconsistent.")
if latest.get("qaPassRate") != 1:
    raise SystemExit("Campaign status compare latest qaPassRate is inconsistent.")
if previous.get("taskCount") != 0:
    raise SystemExit("Campaign status compare previous taskCount should be zero for a single-task run.")
if delta.get("averageConfidenceScoreChange") is not None:
    raise SystemExit("Campaign status compare confidence delta should be null without a previous window.")
if delta.get("qaPassRateChange") is not None:
    raise SystemExit("Campaign status compare qaPassRateChange should be null without a previous window.")

print("Phase 3.5 artifact validation passed.")
print(json.dumps(
    {
        "qualifiedTopicId": qualified_topic.get("id"),
        "blueprintId": blueprints[0].get("id"),
        "taskId": payload.get("taskId") or payload["taskStatusResponse"].get("taskId"),
        "confidenceBand": qualification_status.get("confidenceBand"),
        "discoverySources": discovery.get("sources") or discovery.get("discoverySources"),
        "differentiationAngle": blueprint.get("differentiationAngle"),
        "qaStatus": task_status["generation"].get("qaStatus"),
        "summaryTaskCount": len(campaign_summary),
        "trendsTotalTasks": campaign_trends.get("totalTasks"),
        "compareWindowSize": campaign_compare.get("windowSize"),
    },
    indent=2,
))
PY
