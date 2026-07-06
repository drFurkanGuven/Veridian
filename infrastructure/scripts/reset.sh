#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="${ROOT_DIR}/infrastructure/docker-compose.yml"

echo "WARNING: This will destroy all infrastructure data volumes."
read -r -p "Continue? [y/N] " confirm

if [[ "${confirm}" != "y" && "${confirm}" != "Y" ]]; then
  echo "Aborted."
  exit 0
fi

docker compose -f "${COMPOSE_FILE}" down -v --remove-orphans
echo "Infrastructure reset complete."
