#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"
EXAMPLE="${ROOT_DIR}/.env.production.example"

if [[ ! -f "${EXAMPLE}" ]]; then
  echo "✗ ${EXAMPLE} not found"
  exit 1
fi

cp -f "${EXAMPLE}" "${ENV_FILE}"
echo "✅ Wrote ${ENV_FILE} from .env.production.example"
echo ""
echo "Edit JWT_SECRET and OAuth keys before going live:"
echo "  nano ${ENV_FILE}"
