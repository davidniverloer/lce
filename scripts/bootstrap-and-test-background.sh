#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
orchestrator_dir="${repo_root}/apps/orchestrator"
worker_dir="${repo_root}/workers/ai-engine"
venv_dir="${worker_dir}/.venv"
logs_dir="${repo_root}/.logs"
python_bin=""

base_url="${BASE_URL:-http://localhost:3000}"
organization_name="${ORGANIZATION_NAME:-Demo Org}"
campaign_name="${CAMPAIGN_NAME:-Spring Launch}"
seed_topic="${SEED_TOPIC:-deterministic content operations}"
market_industry="${MARKET_INDUSTRY:-}"
content_language="${CONTENT_LANGUAGE:-English}"
geo_context="${GEO_CONTEXT:-}"
docker_compose_file="${repo_root}/infra/docker/docker-compose.yml"
orchestrator_log="${logs_dir}/orchestrator.log"
worker_log="${logs_dir}/ai-engine.log"
post_smoke_script="${POST_SMOKE_SCRIPT:-}"
smoke_output_path="${SMOKE_OUTPUT_PATH:-}"

orchestrator_pid=""
worker_pid=""

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

source_env_defaults() {
  local env_file="$1"
  local env_line=""
  local env_key=""
  local -a preserved_keys=()
  local -a preserved_values=()
  local preserved_index=0

  while IFS= read -r env_line || [ -n "${env_line}" ]; do
    case "${env_line}" in
      ''|\#*)
        continue
        ;;
    esac

    env_key="${env_line%%=*}"
    env_key="${env_key#export }"
    env_key="${env_key%%[[:space:]]*}"

    if [ -n "${env_key}" ] && [ -n "${!env_key+x}" ]; then
      preserved_keys[${preserved_index}]="${env_key}"
      preserved_values[${preserved_index}]="${!env_key}"
      preserved_index=$((preserved_index + 1))
    fi
  done < "${env_file}"

  set -a
  source "${env_file}"
  set +a

  for preserved_index in "${!preserved_keys[@]}"; do
    export "${preserved_keys[${preserved_index}]}=${preserved_values[${preserved_index}]}"
  done
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
  worker_pids="$(pgrep -f 'ai_engine.main' || true)"

  if [ -n "${worker_pids}" ]; then
    echo "Stopping existing ai_engine worker process(es): ${worker_pids}"
    kill ${worker_pids} >/dev/null 2>&1 || true
  fi

  local orchestrator_pids
  orchestrator_pids="$(pgrep -f 'pnpm --filter @lce/orchestrator dev|tsx watch src/server.ts' || true)"

  if [ -n "${orchestrator_pids}" ]; then
    echo "Stopping existing orchestrator process(es): ${orchestrator_pids}"
    kill ${orchestrator_pids} >/dev/null 2>&1 || true
  fi

  sleep 1
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
      if printf '%s' "${response}" | python3 -c 'import json,sys
try:
    data=json.load(sys.stdin)
    print("ok" if data.get("status") == "ok" else "not-ok")
except Exception:
    print("not-ok")' | grep -qx "ok"; then
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

wait_for_rabbitmq() {
  local attempts=30
  local delay=2

  for attempt in $(seq 1 "${attempts}"); do
    if docker exec lce-rabbitmq rabbitmqctl await_startup >/dev/null 2>&1; then
      echo "RabbitMQ is ready"
      return 0
    fi

    if [ "${attempt}" -lt "${attempts}" ]; then
      printf 'Waiting for RabbitMQ readiness (%s/%s)\n' "${attempt}" "${attempts}"
      sleep "${delay}"
    fi
  done

  echo "Timed out waiting for RabbitMQ readiness" >&2
  return 1
}

require_command cp
require_command pnpm
require_command curl
require_command docker
require_command lsof
require_command pgrep
resolve_python_bin

trap cleanup EXIT INT TERM

cd "${repo_root}"
mkdir -p "${logs_dir}"

stop_existing_processes

if [ ! -f "${repo_root}/.env" ]; then
  cp "${repo_root}/.env.example" "${repo_root}/.env"
  echo "Created .env from .env.example"
else
  echo ".env already exists, leaving it unchanged"
fi

source_env_defaults "${repo_root}/.env"

RABBITMQ_GENERATION_QUEUE="${RABBITMQ_GENERATION_QUEUE:-${RABBITMQ_TOPIC_GENERATION_QUEUE:-content.generation-requests}}"
export RABBITMQ_GENERATION_QUEUE

if [ -d "${repo_root}/node_modules" ]; then
  echo "Node dependencies already installed, skipping pnpm install"
else
  echo "Installing Node dependencies"
  CI=true pnpm install
fi

if [ ! -d "${venv_dir}" ]; then
  echo "Creating Python virtual environment"
  "${python_bin}" -m venv "${venv_dir}"
fi

if [ -x "${venv_dir}/bin/python" ] && \
   PYTHONPATH="${worker_dir}/src" "${venv_dir}/bin/python" -c "import ai_engine" >/dev/null 2>&1; then
  echo "Python worker dependencies already installed, skipping pip install"
else
  echo "Installing Python worker dependencies"
  "${venv_dir}/bin/pip" install -e "${worker_dir}"
fi

echo "Generating Prisma client"
pnpm db:generate

echo "Starting Docker infrastructure"
docker compose -f "${docker_compose_file}" down -v >/dev/null 2>&1 || true
docker rm -fv lce-rabbitmq >/dev/null 2>&1 || true
docker compose -f "${docker_compose_file}" up -d
wait_for_rabbitmq

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
  CREWAI_RUNTIME_HOME="${repo_root}/.crewai-home" PYTHONPATH="${worker_dir}/src" python -m ai_engine.main
) >"${worker_log}" 2>&1 &
worker_pid=$!
printf 'Worker PID: %s\n' "${worker_pid}"
printf 'Worker log: %s\n' "${worker_log}"

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
SMOKE_OUTPUT_PATH="${smoke_output_path}" SEED_TOPIC="${seed_topic}" MARKET_INDUSTRY="${market_industry}" CONTENT_LANGUAGE="${content_language}" GEO_CONTEXT="${geo_context}" bash "${repo_root}/scripts/smoke-topic-flow.sh"

if [ -n "${post_smoke_script}" ]; then
  echo "Running post-smoke validation"
  SMOKE_OUTPUT_PATH="${smoke_output_path}" PHASE35_INPUT_PATH="${smoke_output_path}" /bin/zsh -lc "${post_smoke_script}"
fi
