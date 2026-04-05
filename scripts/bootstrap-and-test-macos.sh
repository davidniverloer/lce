#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
orchestrator_dir="${repo_root}/apps/orchestrator"
worker_dir="${repo_root}/workers/ai-engine"
venv_dir="${worker_dir}/.venv"
python_bin=""

base_url="${BASE_URL:-http://localhost:3000}"
organization_name="${ORGANIZATION_NAME:-Demo Org}"
campaign_name="${CAMPAIGN_NAME:-Spring Launch}"
seed_topic="${SEED_TOPIC:-deterministic content operations}"
docker_compose_file="${repo_root}/infra/docker/docker-compose.yml"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

resolve_python_bin() {
  for candidate in python3.13 python3.12 python3.11 python3; do
    if command -v "${candidate}" >/dev/null 2>&1; then
      python_bin="${candidate}"
      return 0
    fi
  done

  echo "Missing required Python interpreter (expected python3.11+)." >&2
  exit 1
}

stop_existing_processes() {
  local port_pids
  port_pids="$(lsof -ti tcp:3000 || true)"

  if [ -n "${port_pids}" ]; then
    echo "Stopping existing process(es) on port 3000: ${port_pids}"
    kill ${port_pids} >/dev/null 2>&1 || true
  fi

  local worker_pids
  worker_pids="$(pgrep -f 'python -m ai_engine.main' || true)"

  if [ -n "${worker_pids}" ]; then
    echo "Stopping existing ai_engine worker process(es): ${worker_pids}"
    kill ${worker_pids} >/dev/null 2>&1 || true
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
require_command curl
require_command docker
require_command osascript
require_command lsof
require_command pgrep
resolve_python_bin

cd "${repo_root}"

stop_existing_processes

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
  "${python_bin}" -m venv "${venv_dir}"
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
  "cd $(printf '%q' "${worker_dir}") && source $(printf '%q' "${venv_dir}/bin/activate") && CREWAI_RUNTIME_HOME=$(printf '%q' "${repo_root}/.crewai-home") PYTHONPATH=$(printf '%q' "${worker_dir}/src") python -m ai_engine.main"

wait_for_health

organization_response="$(curl -sS \
  -X POST "${base_url}/organizations" \
  -H "content-type: application/json" \
  -d "{\"name\":\"${organization_name}\"}")"
printf 'Organization response: %s\n' "${organization_response}"

organization_id="$(printf '%s' "${organization_response}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
printf 'Organization id: %s\n' "${organization_id}"

campaign_response="$(curl -sS \
  -X POST "${base_url}/organizations/${organization_id}/campaigns" \
  -H "content-type: application/json" \
  -d "{\"name\":\"${campaign_name}\"}")"
printf 'Campaign response: %s\n' "${campaign_response}"

campaign_id="$(printf '%s' "${campaign_response}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
printf 'Campaign id: %s\n' "${campaign_id}"

echo "Running Phase 3 smoke validation"
SEED_TOPIC="${seed_topic}" bash "${repo_root}/scripts/smoke-topic-flow.sh"
