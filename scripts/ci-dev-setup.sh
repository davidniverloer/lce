#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
worker_dir="${repo_root}/workers/ai-engine"
venv_dir="${worker_dir}/.venv"
docker_compose_file="${repo_root}/infra/docker/docker-compose.yml"
python_bin=""

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

wait_for_url() {
  local url="$1"
  local label="$2"
  local attempts="${3:-30}"
  local delay="${4:-2}"

  for attempt in $(seq 1 "${attempts}"); do
    if curl -fsS "${url}" >/dev/null 2>&1; then
      echo "${label} is ready"
      return 0
    fi

    if [ "${attempt}" -lt "${attempts}" ]; then
      printf 'Waiting for %s (%s/%s)\n' "${label}" "${attempt}" "${attempts}"
      sleep "${delay}"
    fi
  done

  echo "Timed out waiting for ${label}" >&2
  return 1
}

cleanup() {
  local exit_code=$?

  if [ -n "${WORKER_PID:-}" ] && kill -0 "${WORKER_PID}" >/dev/null 2>&1; then
    kill "${WORKER_PID}" >/dev/null 2>&1 || true
    wait "${WORKER_PID}" 2>/dev/null || true
  fi

  if [ -n "${ORCHESTRATOR_PID:-}" ] && kill -0 "${ORCHESTRATOR_PID}" >/dev/null 2>&1; then
    kill "${ORCHESTRATOR_PID}" >/dev/null 2>&1 || true
    wait "${ORCHESTRATOR_PID}" 2>/dev/null || true
  fi

  if command -v docker >/dev/null 2>&1; then
    docker compose -f "${docker_compose_file}" down -v >/dev/null 2>&1 || true
  fi

  exit "${exit_code}"
}

require_command pnpm
require_command curl
require_command docker
resolve_python_bin

trap cleanup EXIT INT TERM

cd "${repo_root}"

if [ ! -f "${repo_root}/.env" ]; then
  cp "${repo_root}/.env.example" "${repo_root}/.env"
fi

set -a
source "${repo_root}/.env"
set +a

CI=true pnpm install

if [ ! -d "${venv_dir}" ]; then
  "${python_bin}" -m venv "${venv_dir}"
fi

"${venv_dir}/bin/pip" install -e "${worker_dir}"

pnpm db:generate
pnpm build
pnpm typecheck
"${venv_dir}/bin/python" -m compileall "${worker_dir}/src"

docker compose -f "${docker_compose_file}" up -d
pnpm db:migrate

(
  cd "${repo_root}/apps/orchestrator"
  pnpm --filter @lce/orchestrator dev
) > "${repo_root}/.logs-ci-orchestrator.log" 2>&1 &
ORCHESTRATOR_PID=$!

(
  cd "${worker_dir}"
  source "${venv_dir}/bin/activate"
  CREWAI_RUNTIME_HOME="${repo_root}/.crewai-home" PYTHONPATH="${worker_dir}/src" python -m ai_engine.main
) > "${repo_root}/.logs-ci-worker.log" 2>&1 &
WORKER_PID=$!

wait_for_url "http://localhost:3000/health" "orchestrator health endpoint"

bash "${repo_root}/scripts/smoke-topic-flow.sh"
