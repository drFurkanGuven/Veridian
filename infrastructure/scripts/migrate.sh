#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
API_DIR="${ROOT_DIR}/apps/api"
ENV_FILE="${ROOT_DIR}/.env"

cd "${API_DIR}"

if [[ -f "${ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
fi

if [[ -d "${API_DIR}/.venv" ]]; then
  # shellcheck disable=SC1091
  source "${API_DIR}/.venv/bin/activate"
fi

alembic upgrade head
