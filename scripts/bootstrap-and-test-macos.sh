#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
orchestrator_dir="${repo_root}/apps/orchestrator"
worker_dir="${repo_root}/workers/ai-engine"
venv_dir="${worker_dir}/.venv"

base_url="${BASE_URL:-http://localhost:3000}"
organization_id="${ORGANIZATION_ID:-org-demo}"
campaign_name="${CAMPAIGN_NAME:-Spring Launch}"
niche="${NICHE:-remote accounting}"
docker_compose_file="${repo_root}/infra/docker/docker-compose.yml"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

wait_for_health() {
  local attempts=30
  local delay=2
  local response=""

  for attempt in $(seq 1 "${attempts}"); do
    if response="$(curl -sS "${base_url}/health" 2>/dev/null)"; then
      if [ "${response}" = '{"status":"ok"}' ]; then
        printf 'Health response: %s\n' "${response}"
        return 0
      fi
    fi

    if [ "${attempt}" -lt "${attempts}" ]; then
      printf 'Waiting for orchestrator health endpoint (%s/%s)\n' "${attempt}" "${attempts}"
      sleep "${delay}"
    fi
  done

  echo "Timed out waiting for ${base_url}/health" >&2
  return 1
}

start_in_terminal() {
  local window_title="$1"
  local command_text="$2"

  osascript <<EOF >/dev/null
tell application "Terminal"
  activate
  do script "printf '\\\\e]1;${window_title}\\\\a'; cd $(printf '%q' "${repo_root}"); ${command_text}"
end tell
EOF
}

require_command cp
require_command pnpm
require_command python3
require_command curl
require_command docker
require_command osascript

cd "${repo_root}"

if [ ! -f "${repo_root}/.env" ]; then
  cp "${repo_root}/.env.example" "${repo_root}/.env"
  echo "Created .env from .env.example"
else
  echo ".env already exists, leaving it unchanged"
fi

echo "Installing Node dependencies"
pnpm install

if [ ! -d "${venv_dir}" ]; then
  echo "Creating Python virtual environment"
  python3 -m venv "${venv_dir}"
fi

echo "Installing Python worker dependencies"
"${venv_dir}/bin/pip" install -e "${worker_dir}"

echo "Generating Prisma client"
pnpm db:generate

echo "Starting Docker infrastructure"
docker compose -f "${docker_compose_file}" up -d

echo "Applying database migration"
pnpm db:migrate

echo "Starting orchestrator in a new Terminal window"
start_in_terminal \
  "LCE Orchestrator" \
  "cd $(printf '%q' "${orchestrator_dir}") && pnpm --filter @lce/orchestrator dev"

echo "Starting worker in a new Terminal window"
start_in_terminal \
  "LCE AI Engine" \
  "cd $(printf '%q' "${worker_dir}") && source $(printf '%q' "${venv_dir}/bin/activate") && PYTHONPATH=$(printf '%q' "${worker_dir}/src") python -m ai_engine.main"

wait_for_health

campaign_response="$(curl -sS \
  -X POST "${base_url}/campaigns" \
  -H "content-type: application/json" \
  -H "x-organization-id: ${organization_id}" \
  -d "{\"name\":\"${campaign_name}\",\"niche\":\"${niche}\"}")"
printf 'Campaign response: %s\n' "${campaign_response}"

campaign_id="$(printf '%s' "${campaign_response}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
printf 'Campaign id: %s\n' "${campaign_id}"

topic_generation_response="$(curl -sS \
  -X POST "${base_url}/campaigns/${campaign_id}/topic-generation" \
  -H "x-organization-id: ${organization_id}")"
printf 'Topic generation response: %s\n' "${topic_generation_response}"

echo "Waiting 3 seconds for async processing"
sleep 3

topics_response="$(curl -sS \
  "${base_url}/campaigns/${campaign_id}/topics" \
  -H "x-organization-id: ${organization_id}")"
printf 'Topics response: %s\n' "${topics_response}"

python3 -c '
import json
import sys

topics = json.loads(sys.argv[1]).get("topics", [])
if not topics:
    raise SystemExit("Expected at least one topic, got none")
print("Automated bootstrap smoke test passed.")
' "${topics_response}"
