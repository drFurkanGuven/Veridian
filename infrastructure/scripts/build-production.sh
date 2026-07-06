#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

# Production URL'leri — .env'deki localhost değerlerini build sırasında override et
if [[ -f "${ROOT_DIR}/.env.production.example" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ROOT_DIR}/.env.production.example"
  set +a
fi

if [[ -f "${ROOT_DIR}/.env" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ROOT_DIR}/.env"
  set +a
fi

export NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-https://api.veridian.furkanguven.space}"
export NEXT_PUBLIC_WS_URL="${NEXT_PUBLIC_WS_URL:-wss://api.veridian.furkanguven.space}"

# .env hâlâ localhost içeriyorsa production URL kullan
if [[ "${NEXT_PUBLIC_API_URL}" == *"localhost"* ]]; then
  echo "⚠ .env has localhost API URL — using production URL for build"
  export NEXT_PUBLIC_API_URL="https://api.veridian.furkanguven.space"
  export NEXT_PUBLIC_WS_URL="wss://api.veridian.furkanguven.space"
fi

echo "Building Veridian for production..."
echo "  API URL: ${NEXT_PUBLIC_API_URL}"

CI=true pnpm install --frozen-lockfile 2>/dev/null || CI=true pnpm install

export NODE_ENV=production

pnpm --filter @veridian/shared-types build
pnpm --filter @veridian/web build

STANDALONE_ROOT="apps/web/.next/standalone"
STANDALONE="${STANDALONE_ROOT}/apps/web"

if [[ ! -f "${STANDALONE}/server.js" ]]; then
  echo "✗ Standalone server.js not found at ${STANDALONE}/server.js"
  exit 1
fi

mkdir -p "${STANDALONE}/.next"
mkdir -p "${STANDALONE}/public"

if [[ -d apps/web/public ]] && [[ -n "$(ls -A apps/web/public 2>/dev/null)" ]]; then
  cp -r apps/web/public/. "${STANDALONE}/public/"
fi

cp -r apps/web/.next/static "${STANDALONE}/.next/static"

echo ""
echo "✅ Build complete."
echo "   Standalone: ${STANDALONE_ROOT}"
echo ""
echo "Next:"
echo "  sudo bash infrastructure/scripts/setup-systemd.sh"
echo "  sudo systemctl restart veridian-web veridian-api"
