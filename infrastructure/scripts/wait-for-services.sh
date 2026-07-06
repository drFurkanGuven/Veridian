#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="${ROOT_DIR}/infrastructure/docker-compose.yml"
ENV_FILE="${ROOT_DIR}/.env"

if [[ -f "${ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
fi

POSTGRES_PORT="${POSTGRES_PORT:-5432}"
REDIS_PORT="${REDIS_PORT:-6379}"
RABBITMQ_PORT="${RABBITMQ_PORT:-5672}"
MINIO_API_PORT="${MINIO_API_PORT:-9000}"
TIMEOUT="${WAIT_TIMEOUT:-120}"

wait_for_port() {
  local name="$1"
  local host="$2"
  local port="$3"
  local elapsed=0

  echo -n "Waiting for ${name}..."
  while ! (echo >"/dev/tcp/${host}/${port}") >/dev/null 2>&1; do
    if [[ "${elapsed}" -ge "${TIMEOUT}" ]]; then
      echo " timeout"
      return 1
    fi
    sleep 2
    elapsed=$((elapsed + 2))
    echo -n "."
  done
  echo " ready"
}

echo "Waiting for infrastructure services (timeout: ${TIMEOUT}s)..."

wait_for_port "PostgreSQL" "localhost" "${POSTGRES_PORT}"
wait_for_port "Redis" "localhost" "${REDIS_PORT}"
wait_for_port "RabbitMQ" "localhost" "${RABBITMQ_PORT}"
wait_for_port "MinIO" "localhost" "${MINIO_API_PORT}"

echo "All services are accepting connections."
