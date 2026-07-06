#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

if [[ -f "${ROOT_DIR}/.env" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ROOT_DIR}/.env"
  set +a
fi

export NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-https://api.veridian.furkanguven.space}"
export NEXT_PUBLIC_WS_URL="${NEXT_PUBLIC_WS_URL:-wss://api.veridian.furkanguven.space}"

echo "Building Veridian for production..."
echo "  API URL: ${NEXT_PUBLIC_API_URL}"

# devDependencies (tsup, typescript, next toolchain) gerekli — NODE_ENV=production ÖNCE set etme
CI=true pnpm install --frozen-lockfile 2>/dev/null || CI=true pnpm install

export NODE_ENV=production

pnpm --filter @veridian/shared-types build
pnpm --filter @veridian/web build

STANDALONE="apps/web/.next/standalone/apps/web"
mkdir -p "${STANDALONE}/.next"
cp -r apps/web/public "${STANDALONE}/public"
cp -r apps/web/.next/static "${STANDALONE}/.next/static"

echo ""
echo "✅ Build complete."
echo ""
echo "Next:"
echo "  sudo bash infrastructure/scripts/setup-systemd.sh"
echo "  sudo systemctl restart veridian-web veridian-api"
