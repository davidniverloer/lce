#!/usr/bin/env bash

set -euo pipefail

base_url="${BASE_URL:-http://localhost:3000}"
organization_name="${ORGANIZATION_NAME:-Smoke Org}"
campaign_name="${CAMPAIGN_NAME:-Smoke Campaign}"
manual_topic="${MANUAL_TOPIC:-deterministic content operations}"
max_attempts="${MAX_ATTEMPTS:-20}"
poll_interval_seconds="${POLL_INTERVAL_SECONDS:-2}"
postgres_container="${POSTGRES_CONTAINER:-lce-postgres}"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

require_command curl
require_command python3
require_command docker

health_response="$(curl -sS "${base_url}/health")"
printf 'Health response: %s\n' "${health_response}"

organization_response="$(curl -sS \
  -X POST "${base_url}/organizations" \
  -H "content-type: application/json" \
  -d "{\"name\":\"${organization_name}\"}")"
printf 'Organization response: %s\n' "${organization_response}"
organization_id="$(printf '%s' "${organization_response}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"

campaign_response="$(curl -sS \
  -X POST "${base_url}/organizations/${organization_id}/campaigns" \
  -H "content-type: application/json" \
  -d "{\"name\":\"${campaign_name}\"}")"
printf 'Campaign response: %s\n' "${campaign_response}"
campaign_id="$(printf '%s' "${campaign_response}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"

task_response="$(curl -sS \
  -X POST "${base_url}/tasks/generate" \
  -H "content-type: application/json" \
  -d "{\"organizationId\":\"${organization_id}\",\"campaignId\":\"${campaign_id}\",\"topic\":\"${manual_topic}\",\"targetAudience\":\"operations leaders\",\"outputFormats\":[\"markdown_article\"]}")"
printf 'Task response: %s\n' "${task_response}"
task_id="$(printf '%s' "${task_response}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["taskId"])')"

for attempt in $(seq 1 "${max_attempts}"); do
  task_status="$(docker exec "${postgres_container}" psql -U postgres -d lce -t -A -c "SELECT status FROM content.generation_tasks WHERE id = '${task_id}';" | tr -d '[:space:]')"
  article_count="$(docker exec "${postgres_container}" psql -U postgres -d lce -t -A -c "SELECT count(*) FROM repository.articles WHERE task_id = '${task_id}' AND status = 'completed';" | tr -d '[:space:]')"
  draft_count="$(docker exec "${postgres_container}" psql -U postgres -d lce -t -A -c "SELECT count(*) FROM content.draft_revisions WHERE task_id = '${task_id}';" | tr -d '[:space:]')"
  qa_count="$(docker exec "${postgres_container}" psql -U postgres -d lce -t -A -c "SELECT count(*) FROM content.qa_feedback WHERE task_id = '${task_id}';" | tr -d '[:space:]')"

  if [ "${task_status:-}" = "completed" ] && [ "${article_count:-0}" -ge 1 ] && [ "${draft_count:-0}" -ge 2 ] && [ "${qa_count:-0}" -ge 2 ]; then
    final_task_response="$(curl -sS "${base_url}/tasks/${task_id}")"
    printf 'Task status response: %s\n' "${final_task_response}"
    printf 'Draft revisions stored: %s\n' "${draft_count}"
    printf 'QA feedback entries stored: %s\n' "${qa_count}"
    printf 'Completed articles stored: %s\n' "${article_count}"
    echo "Smoke test passed."
    exit 0
  fi

  if [ "${attempt}" -lt "${max_attempts}" ]; then
    printf 'Waiting for generation flow completion (%s/%s)\n' "${attempt}" "${max_attempts}"
    sleep "${poll_interval_seconds}"
  fi
done

echo "Smoke test failed: the Phase 2 generation flow did not complete in time." >&2
exit 1
