#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
API_DIR="${ROOT_DIR}/apps/api"

cd "${API_DIR}"

if [[ -d "${API_DIR}/.venv" ]]; then
  # shellcheck disable=SC1091
  source "${API_DIR}/.venv/bin/activate"
fi

alembic "$@"
