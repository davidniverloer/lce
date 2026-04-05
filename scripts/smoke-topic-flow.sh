#!/usr/bin/env bash

set -euo pipefail

base_url="${BASE_URL:-http://localhost:3000}"
organization_id="${ORGANIZATION_ID:-org-smoke}"
max_attempts="${MAX_ATTEMPTS:-15}"
poll_interval_seconds="${POLL_INTERVAL_SECONDS:-2}"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

require_command curl
require_command python3

health_response="$(curl -sS "${base_url}/health")"
printf 'Health response: %s\n' "${health_response}"

campaign_response="$(curl -s \
  -X POST "${base_url}/campaigns" \
  -H "content-type: application/json" \
  -H "x-organization-id: ${organization_id}" \
  -d '{"name":"Smoke Campaign","niche":"b2b saas"}')"

printf 'Campaign response: %s\n' "${campaign_response}"

campaign_id="$(printf '%s' "${campaign_response}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"

topic_generation_response="$(curl -s \
  -X POST "${base_url}/campaigns/${campaign_id}/topic-generation" \
  -H "x-organization-id: ${organization_id}")"

printf 'Topic generation response: %s\n' "${topic_generation_response}"

for attempt in $(seq 1 "${max_attempts}"); do
  topics_response="$(curl -s \
    "${base_url}/campaigns/${campaign_id}/topics" \
    -H "x-organization-id: ${organization_id}")"

  topics_count="$(printf '%s' "${topics_response}" | python3 -c 'import json,sys; print(len(json.load(sys.stdin).get("topics", [])))')"

  if [ "${topics_count}" -gt 0 ]; then
    printf 'Topics response: %s\n' "${topics_response}"
    echo "Smoke test passed."
    exit 0
  fi

  if [ "${attempt}" -lt "${max_attempts}" ]; then
    printf 'Topics not ready yet, retrying in %ss (%s/%s)\n' "${poll_interval_seconds}" "${attempt}" "${max_attempts}"
    sleep "${poll_interval_seconds}"
  fi
done

printf 'Topics response after timeout: %s\n' "${topics_response}"
echo "Smoke test failed: no topics were created in time." >&2
exit 1
