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
RABBITMQ_MANAGEMENT_PORT="${RABBITMQ_MANAGEMENT_PORT:-15672}"

check_tcp() {
  local name="$1"
  local host="$2"
  local port="$3"

  if (echo >"/dev/tcp/${host}/${port}") >/dev/null 2>&1; then
    echo "  ✓ ${name} (${host}:${port})"
    return 0
  fi

  echo "  ✗ ${name} (${host}:${port}) — not reachable"
  return 1
}

check_http() {
  local name="$1"
  local url="$2"
  local retries="${3:-10}"
  local delay="${4:-3}"

  for ((i = 1; i <= retries; i++)); do
    if curl -sf "${url}" >/dev/null 2>&1; then
      echo "  ✓ ${name} (${url})"
      return 0
    fi
    if [[ "${i}" -lt "${retries}" ]]; then
      sleep "${delay}"
    fi
  done

  echo "  ✗ ${name} (${url}) — not reachable"
  return 1
}

echo "Verifying Veridian infrastructure services..."
echo ""

failed=0

check_tcp "PostgreSQL" "localhost" "${POSTGRES_PORT}" || failed=$((failed + 1))
check_tcp "Redis" "localhost" "${REDIS_PORT}" || failed=$((failed + 1))
check_tcp "RabbitMQ AMQP" "localhost" "${RABBITMQ_PORT}" || failed=$((failed + 1))
check_tcp "MinIO API" "localhost" "${MINIO_API_PORT}" || failed=$((failed + 1))
check_http "RabbitMQ Management" "http://localhost:${RABBITMQ_MANAGEMENT_PORT}" 20 3 || failed=$((failed + 1))
check_http "MinIO Health" "http://localhost:${MINIO_API_PORT}/minio/health/live" || failed=$((failed + 1))

echo ""

if [[ "${failed}" -gt 0 ]]; then
  echo "❌ ${failed} service(s) failed verification."
  echo "   Run: pnpm infra:up"
  exit 1
fi

echo "✅ All infrastructure services are healthy."

if docker compose -f "${COMPOSE_FILE}" ps --status running 2>/dev/null | grep -q minio-init; then
  :
else
  bucket="${S3_BUCKET:-veridian}"
  if docker run --rm --network veridian-net minio/mc:latest \
    /bin/sh -c "mc alias set local http://minio:9000 ${S3_ACCESS_KEY:-minioadmin} ${S3_SECRET_KEY:-minioadmin} && mc ls local/${bucket}" \
    >/dev/null 2>&1; then
    echo "  ✓ MinIO bucket '${bucket}' exists"
  else
    echo "  ⚠ MinIO bucket '${bucket}' could not be verified (minio-init may still be running)"
  fi
fi
