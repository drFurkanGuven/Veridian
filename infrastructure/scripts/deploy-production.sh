#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"

echo "=== Veridian production deploy ==="
cd "${ROOT_DIR}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "✗ ${ENV_FILE} missing — run: bash infrastructure/scripts/setup-env.sh"
  exit 1
fi

if ! grep -q '^API_CORS_ORIGINS=.*veridian' "${ENV_FILE}" 2>/dev/null \
  && ! grep -q '^APP_URL=https://veridian' "${ENV_FILE}" 2>/dev/null; then
  echo "⚠ Check API_CORS_ORIGINS / APP_URL in .env for production domain"
fi

git pull

cd apps/api
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -e .

cd "${ROOT_DIR}"
pnpm db:migrate
pnpm build:prod

if [[ "$(id -u)" -eq 0 ]]; then
  systemctl restart veridian-api veridian-web
else
  echo "Restart services as root:"
  echo "  sudo systemctl restart veridian-api veridian-web"
fi

sleep 2
echo ""
curl -sf --max-time 5 http://127.0.0.1:8000/health && echo "✓ API health OK" || echo "✗ API health failed"
curl -sf --max-time 5 -o /dev/null -w "Frontend HTTP %{http_code}\n" http://127.0.0.1:3000/ || true
