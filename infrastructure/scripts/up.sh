#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="${ROOT_DIR}/infrastructure/docker-compose.yml"
ENV_FILE="${ROOT_DIR}/.env"

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

echo "Starting Veridian infrastructure..."
docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d

echo ""
echo "Waiting for services to become healthy..."
"${ROOT_DIR}/infrastructure/scripts/wait-for-services.sh"

echo ""
"${ROOT_DIR}/infrastructure/scripts/verify-services.sh"
