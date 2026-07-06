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
elif [[ -d "${ROOT_DIR}/.venv" ]]; then
  # shellcheck disable=SC1091
  source "${ROOT_DIR}/.venv/bin/activate"
fi

if ! command -v alembic >/dev/null 2>&1; then
  echo "Error: alembic not found."
  echo ""
  echo "Run these commands first:"
  echo "  cd ${API_DIR}"
  echo "  python3 -m venv .venv"
  echo "  source .venv/bin/activate"
  echo "  pip install -e \".[dev]\""
  echo "  cd ${ROOT_DIR} && pnpm db:migrate"
  exit 1
fi

alembic upgrade head
