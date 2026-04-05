#!/usr/bin/env bash

set -euo pipefail

base_url="${BASE_URL:-http://localhost:3000}"
organization_name="${ORGANIZATION_NAME:-Smoke Org}"
campaign_name="${CAMPAIGN_NAME:-Smoke Campaign}"
max_attempts="${MAX_ATTEMPTS:-15}"
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

campaigns_response="$(curl -sS "${base_url}/organizations/${organization_id}/campaigns")"
printf 'Campaign listing response: %s\n' "${campaigns_response}"

for attempt in $(seq 1 "${max_attempts}"); do
  receipt_count="$(docker exec "${postgres_container}" psql -U postgres -d lce -t -A -c "SELECT count(*) FROM audit.event_receipts WHERE organization_id = '${organization_id}';" | tr -d '[:space:]')"
  processed_count="$(docker exec "${postgres_container}" psql -U postgres -d lce -t -A -c "SELECT count(*) FROM audit.processed_event_log WHERE organization_id = '${organization_id}';" | tr -d '[:space:]')"

  if [ "${receipt_count:-0}" -ge 2 ] && [ "${processed_count:-0}" -ge 2 ]; then
    printf 'Audit receipts for organization %s: %s\n' "${organization_id}" "${receipt_count}"
    printf 'Processed events for organization %s: %s\n' "${organization_id}" "${processed_count}"
    printf 'Created campaign id: %s\n' "${campaign_id}"
    echo "Smoke test passed."
    exit 0
  fi

  if [ "${attempt}" -lt "${max_attempts}" ]; then
    printf 'Waiting for outbox relay and idempotent consumer receipts (%s/%s)\n' "${attempt}" "${max_attempts}"
    sleep "${poll_interval_seconds}"
  fi
done

echo "Smoke test failed: expected audit receipts and processed events were not created in time." >&2
exit 1
