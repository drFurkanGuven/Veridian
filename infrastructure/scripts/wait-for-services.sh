#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
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
RABBITMQ_MANAGEMENT_PORT="${RABBITMQ_MANAGEMENT_PORT:-15672}"
MINIO_API_PORT="${MINIO_API_PORT:-9000}"
TIMEOUT="${WAIT_TIMEOUT:-120}"
HOST_INFRA="${HOST_INFRA:-false}"

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

wait_for_http() {
  local name="$1"
  local url="$2"
  local elapsed=0

  echo -n "Waiting for ${name}..."
  while ! curl -sf "${url}" >/dev/null 2>&1; do
    if [[ "${elapsed}" -ge "${TIMEOUT}" ]]; then
      echo " timeout"
      return 1
    fi
    sleep 3
    elapsed=$((elapsed + 3))
    echo -n "."
  done
  echo " ready"
}

echo "Waiting for infrastructure services (timeout: ${TIMEOUT}s)..."

if [[ "${HOST_INFRA}" == "true" ]]; then
  wait_for_port "PostgreSQL (host)" "localhost" "${POSTGRES_PORT}"
  wait_for_port "Redis (host)" "localhost" "${REDIS_PORT}"
else
  wait_for_port "PostgreSQL" "localhost" "${POSTGRES_PORT}"
  wait_for_port "Redis" "localhost" "${REDIS_PORT}"
fi

wait_for_port "RabbitMQ AMQP" "localhost" "${RABBITMQ_PORT}"
wait_for_http "RabbitMQ Management" "http://localhost:${RABBITMQ_MANAGEMENT_PORT}"
wait_for_port "MinIO API" "localhost" "${MINIO_API_PORT}"

echo "All services are accepting connections."
