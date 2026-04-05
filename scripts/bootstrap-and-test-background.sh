#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
orchestrator_dir="${repo_root}/apps/orchestrator"
worker_dir="${repo_root}/workers/ai-engine"
venv_dir="${worker_dir}/.venv"
logs_dir="${repo_root}/.logs"

base_url="${BASE_URL:-http://localhost:3000}"
organization_id="${ORGANIZATION_ID:-org-demo}"
campaign_name="${CAMPAIGN_NAME:-Spring Launch}"
niche="${NICHE:-remote accounting}"
docker_compose_file="${repo_root}/infra/docker/docker-compose.yml"
orchestrator_log="${logs_dir}/orchestrator.log"
worker_log="${logs_dir}/ai-engine.log"

orchestrator_pid=""
worker_pid=""

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

cleanup() {
  local exit_code=$?

  if [ -n "${worker_pid}" ] && kill -0 "${worker_pid}" >/dev/null 2>&1; then
    kill "${worker_pid}" >/dev/null 2>&1 || true
    wait "${worker_pid}" 2>/dev/null || true
  fi

  if [ -n "${orchestrator_pid}" ] && kill -0 "${orchestrator_pid}" >/dev/null 2>&1; then
    kill "${orchestrator_pid}" >/dev/null 2>&1 || true
    wait "${orchestrator_pid}" 2>/dev/null || true
  fi

  exit "${exit_code}"
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

    if ! kill -0 "${orchestrator_pid}" >/dev/null 2>&1; then
      echo "Orchestrator exited early. Check ${orchestrator_log}" >&2
      return 1
    fi

    if [ "${attempt}" -lt "${attempts}" ]; then
      printf 'Waiting for orchestrator health endpoint (%s/%s)\n' "${attempt}" "${attempts}"
      sleep "${delay}"
    fi
  done

  echo "Timed out waiting for ${base_url}/health" >&2
  return 1
}

require_command cp
require_command pnpm
require_command python3
require_command curl
require_command docker

trap cleanup EXIT INT TERM

cd "${repo_root}"
mkdir -p "${logs_dir}"

if [ ! -f "${repo_root}/.env" ]; then
  cp "${repo_root}/.env.example" "${repo_root}/.env"
  echo "Created .env from .env.example"
else
  echo ".env already exists, leaving it unchanged"
fi

set -a
source "${repo_root}/.env"
set +a

echo "Installing Node dependencies"
CI=true pnpm install

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

echo "Starting orchestrator in background"
(
  cd "${orchestrator_dir}"
  pnpm --filter @lce/orchestrator dev
) >"${orchestrator_log}" 2>&1 &
orchestrator_pid=$!
printf 'Orchestrator PID: %s\n' "${orchestrator_pid}"
printf 'Orchestrator log: %s\n' "${orchestrator_log}"

echo "Starting worker in background"
(
  cd "${worker_dir}"
  source "${venv_dir}/bin/activate"
  PYTHONPATH="${worker_dir}/src" python -m ai_engine.main
) >"${worker_log}" 2>&1 &
worker_pid=$!
printf 'Worker PID: %s\n' "${worker_pid}"
printf 'Worker log: %s\n' "${worker_log}"

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
print("Background bootstrap smoke test passed.")
' "${topics_response}"
