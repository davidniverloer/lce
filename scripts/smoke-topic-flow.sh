#!/usr/bin/env bash

set -euo pipefail

base_url="${BASE_URL:-http://localhost:3000}"
organization_name="${ORGANIZATION_NAME:-Smoke Org}"
campaign_name="${CAMPAIGN_NAME:-Smoke Campaign}"
seed_topic="${SEED_TOPIC:-deterministic content operations}"
market_industry="${MARKET_INDUSTRY:-}"
content_language="${CONTENT_LANGUAGE:-English}"
geo_context="${GEO_CONTEXT:-}"
max_attempts="${MAX_ATTEMPTS:-25}"
poll_interval_seconds="${POLL_INTERVAL_SECONDS:-2}"
sitemap_url="${SITEMAP_URL:-fixture://default-sitemap}"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

require_command curl
require_command python3

json_count() {
  local key="$1"
  python3 -c "import json,sys
try:
    data=json.load(sys.stdin)
    value=data.get('${key}', [])
    print(len(value) if isinstance(value, list) else 0)
except Exception:
    print(0)"
}

json_first_task_field() {
  local field="$1"
  python3 -c "import json,sys
try:
    data=json.load(sys.stdin)
    tasks=data.get('tasks', [])
    print(tasks[0].get('${field}', '') if tasks else '')
except Exception:
    print('')"
}

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

if [ -n "${market_industry}" ]; then
  market_payload="$(python3 -c 'import json,sys; print(json.dumps({
    "organizationId": sys.argv[1],
    "campaignId": sys.argv[2],
    "industry": sys.argv[3],
    "targetAudience": "operations leaders",
    "contentLanguage": sys.argv[4],
    "geoContext": sys.argv[5] or None,
  }))' "${organization_id}" "${campaign_id}" "${market_industry}" "${content_language}" "${geo_context}")"
else
  market_payload="$(python3 -c 'import json,sys; print(json.dumps({
    "organizationId": sys.argv[1],
    "campaignId": sys.argv[2],
    "seedTopic": sys.argv[3],
    "targetAudience": "operations leaders",
    "contentLanguage": sys.argv[4],
    "geoContext": sys.argv[5] or None,
  }))' "${organization_id}" "${campaign_id}" "${seed_topic}" "${content_language}" "${geo_context}")"
fi

market_response="$(curl -sS \
  -X POST "${base_url}/market/analyze" \
  -H "content-type: application/json" \
  -d "${market_payload}")"
printf 'Market analyze response: %s\n' "${market_response}"
analysis_request_id="$(printf '%s' "${market_response}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["analysisRequestId"])')"

sitemap_response="$(curl -sS \
  -X POST "${base_url}/sitemap/ingest" \
  -H "content-type: application/json" \
  -d "{\"organizationId\":\"${organization_id}\",\"campaignId\":\"${campaign_id}\",\"sitemapUrl\":\"${sitemap_url}\"}")"
printf 'Sitemap response: %s\n' "${sitemap_response}"
sitemap_ingestion_id="$(printf '%s' "${sitemap_response}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["sitemapIngestionId"])')"

for attempt in $(seq 1 "${max_attempts}"); do
  qualified_topics_response="$(curl -sS "${base_url}/market/analyze?organizationId=${organization_id}&campaignId=${campaign_id}")"
  indexed_pages_response="$(curl -sS "${base_url}/campaigns/${campaign_id}/indexed-pages?organizationId=${organization_id}")"
  blueprints_response="$(curl -sS "${base_url}/campaigns/${campaign_id}/blueprints?organizationId=${organization_id}")"
  tasks_response="$(curl -sS "${base_url}/campaigns/${campaign_id}/tasks?organizationId=${organization_id}")"

  qualified_topic_count="$(printf '%s' "${qualified_topics_response}" | json_count qualifiedTopics)"
  indexed_page_count="$(printf '%s' "${indexed_pages_response}" | json_count indexedPages)"
  blueprint_count="$(printf '%s' "${blueprints_response}" | json_count blueprints)"
  task_id="$(printf '%s' "${tasks_response}" | json_first_task_field id)"
  task_status="$(printf '%s' "${tasks_response}" | json_first_task_field status)"

  if [ "${qualified_topic_count:-0}" -ge 1 ] && \
     [ "${indexed_page_count:-0}" -ge 1 ] && \
     [ "${blueprint_count:-0}" -ge 1 ] && \
     [ -n "${task_id:-}" ] && \
     [ "${task_status:-}" = "completed" ]; then
    task_response="$(curl -sS "${base_url}/tasks/${task_id}")"
    printf 'Qualified topics response: %s\n' "${qualified_topics_response}"
    printf 'Indexed pages response: %s\n' "${indexed_pages_response}"
    printf 'Blueprints response: %s\n' "${blueprints_response}"
    printf 'Campaign tasks response: %s\n' "${tasks_response}"
    printf 'Task response: %s\n' "${task_response}"
    printf 'Qualified topics stored: %s\n' "${qualified_topic_count}"
    printf 'Indexed pages stored: %s\n' "${indexed_page_count}"
    printf 'Blueprints stored: %s\n' "${blueprint_count}"
    echo "Smoke test passed."
    exit 0
  fi

  if [ "${attempt}" -lt "${max_attempts}" ]; then
    printf 'Waiting for Phase 3 flow completion (%s/%s)\n' "${attempt}" "${max_attempts}"
    sleep "${poll_interval_seconds}"
  fi
done

echo "Smoke test failed: the Phase 3 market and planning flow did not complete in time." >&2
exit 1
