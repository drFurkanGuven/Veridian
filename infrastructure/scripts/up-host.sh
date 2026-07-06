#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="${ROOT_DIR}/infrastructure/docker-compose.host.yml"
ENV_FILE="${ROOT_DIR}/.env"
export COMPOSE_PROJECT_NAME=veridian

cd "${ROOT_DIR}"

if ! command -v docker >/dev/null 2>&1; then
  echo "Error: Docker is not installed or not in PATH."
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Error: Docker daemon is not running."
  exit 1
fi

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "No .env found — copying from .env.example"
  cp "${ROOT_DIR}/.env.example" "${ENV_FILE}"
fi

echo "Starting Veridian infrastructure (host PG/Redis mode)..."
echo "  PostgreSQL → host localhost:5432 (system service)"
echo "  Redis      → host localhost:6379 (system service)"
echo "  RabbitMQ   → Docker"
echo "  MinIO      → Docker"
echo ""
echo "  NOTE: Do NOT run 'pnpm infra:up' on this server — use 'pnpm infra:up:host' only."
echo ""

container_running() {
  docker ps --format '{{.Names}}' | grep -qx "$1"
}

container_exists() {
  docker ps -a --format '{{.Names}}' | grep -qx "$1"
}

start_if_stopped() {
  local name="$1"
  if container_running "${name}"; then
    echo "  ✓ ${name} already running"
    return 0
  fi
  if container_exists "${name}"; then
    echo "  ↻ Starting existing container ${name}..."
    docker start "${name}" >/dev/null
    return 0
  fi
  return 1
}

needs_compose=false
for c in veridian-rabbitmq veridian-minio; do
  if ! start_if_stopped "${c}"; then
    needs_compose=true
  fi
done

if [[ "${needs_compose}" == "true" ]]; then
  echo ""
  echo "Creating Docker services via compose..."
  docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d
else
  echo ""
  echo "Reusing existing Docker containers (no recreate)."
  # Ensure one-shot bucket init runs if needed
  if ! container_exists veridian-minio-init; then
    docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d minio-init || true
  fi
fi

echo ""
HOST_INFRA=true "${ROOT_DIR}/infrastructure/scripts/wait-for-services.sh"

echo ""
"${ROOT_DIR}/infrastructure/scripts/verify-services.sh"
