#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
worker_dir="${repo_root}/workers/ai-engine"
venv_dir="${worker_dir}/.venv"
docker_compose_file="${repo_root}/infra/docker/docker-compose.yml"
python_bin=""
ci_env_file="${repo_root}/.env.ci.$$"
lock_dir="${repo_root}/.ci-dev-setup.lock"

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

  rm -f "${ci_env_file}"
  rmdir "${lock_dir}" >/dev/null 2>&1 || true

  exit "${exit_code}"
}

read_env_value() {
  local key="$1"
  python3 - "$repo_root/.env" "$key" <<'PY'
import pathlib
import sys

env_path = pathlib.Path(sys.argv[1])
key = sys.argv[2]

if not env_path.exists():
    sys.exit(0)

for raw_line in env_path.read_text().splitlines():
    line = raw_line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    current_key, value = line.split("=", 1)
    if current_key.strip() != key:
        continue
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    sys.stdout.write(value)
    break
PY
}

read_env_or_default() {
  local key="$1"
  local fallback="$2"
  local value
  value="$(read_env_value "${key}")"

  if [ -n "${value}" ]; then
    printf '%s' "${value}"
    return 0
  fi

  printf '%s' "${fallback}"
}

quote_for_shell() {
  python3 -c 'import shlex,sys; print(shlex.quote(sys.argv[1]))' "$1"
}

write_ci_env() {
  cat > "${ci_env_file}" <<EOF
DATABASE_URL=$(quote_for_shell "$(read_env_value DATABASE_URL)")
RABBITMQ_URL=$(quote_for_shell "$(read_env_value RABBITMQ_URL)")
RABBITMQ_EXCHANGE=$(quote_for_shell "$(read_env_or_default RABBITMQ_EXCHANGE lce.events)")
RABBITMQ_GENERATION_QUEUE=$(quote_for_shell "$(read_env_or_default RABBITMQ_GENERATION_QUEUE content.generation-requests)")
OUTBOX_POLL_INTERVAL_MS=$(quote_for_shell "$(read_env_or_default OUTBOX_POLL_INTERVAL_MS 2000)")
ORCHESTRATOR_PORT=$(quote_for_shell "$(read_env_or_default ORCHESTRATOR_PORT 3000)")
REDIS_URL=$(quote_for_shell "$(read_env_or_default REDIS_URL redis://localhost:6379)")
AI_ENGINE_LLM_MODE='stub'
LCE_MARKET_MODE='stub'
LCE_DISCOVERY_MODE='stub'
LCE_QUALIFICATION_MODE='stub'
LCE_TREND_PROVIDER_MODE='stub'
LCE_SOCIAL_PROVIDER_MODE='stub'
LCE_SEO_PROVIDER_MODE='stub'
CREWAI_RUNTIME_HOME=$(quote_for_shell "${repo_root}/.crewai-home")
EOF
}

run_with_ci_env() {
  (
    set -a
    source "${ci_env_file}"
    set +a
    "$@"
  )
}

require_command pnpm
require_command curl
require_command docker
require_command lsof
require_command pgrep
resolve_python_bin

if ! mkdir "${lock_dir}" >/dev/null 2>&1; then
  echo "Another ci-dev-setup run appears to be in progress. Remove ${lock_dir} if no run is active." >&2
  exit 1
fi

trap cleanup EXIT INT TERM

cd "${repo_root}"

stop_existing_processes

if [ ! -f "${repo_root}/.env" ]; then
  cp "${repo_root}/.env.example" "${repo_root}/.env"
fi

write_ci_env

CI=true pnpm install

if [ ! -d "${venv_dir}" ]; then
  "${python_bin}" -m venv "${venv_dir}"
fi

"${venv_dir}/bin/pip" install -e "${worker_dir}"

pnpm db:generate
pnpm build
pnpm typecheck
"${venv_dir}/bin/python" -m compileall "${worker_dir}/src"

docker compose -f "${docker_compose_file}" down -v >/dev/null 2>&1 || true
docker compose -f "${docker_compose_file}" up -d
run_with_ci_env pnpm db:migrate

(
  cd "${repo_root}/apps/orchestrator"
  DOTENV_CONFIG_PATH="${ci_env_file}" pnpm --filter @lce/orchestrator dev
) > "${repo_root}/.logs-ci-orchestrator.log" 2>&1 &
ORCHESTRATOR_PID=$!

(
  cd "${worker_dir}"
  source "${venv_dir}/bin/activate"
  unset OPENAI_API_KEY OPENAI_BASE_URL AI_ENGINE_LLM_API_KEY AI_ENGINE_LLM_API_BASE AI_ENGINE_LLM_MODEL
  DOTENV_CONFIG_PATH="${ci_env_file}" PYTHONPATH="${worker_dir}/src" python -m ai_engine.main
) > "${repo_root}/.logs-ci-worker.log" 2>&1 &
WORKER_PID=$!

wait_for_url "http://localhost:3000/health" "orchestrator health endpoint"

bash "${repo_root}/scripts/smoke-topic-flow.sh"
