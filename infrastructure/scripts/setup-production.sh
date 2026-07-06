#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "=== Veridian production setup ==="
echo ""

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run as root: sudo bash infrastructure/scripts/setup-production.sh"
  exit 1
fi

# 1. Nginx — güvenli mod (diğer config'lere dokunmaz)
bash "${ROOT_DIR}/infrastructure/scripts/setup-nginx.sh" install
bash "${ROOT_DIR}/infrastructure/scripts/setup-nginx.sh" ssl

# 2. Systemd servisleri
bash "${ROOT_DIR}/infrastructure/scripts/setup-systemd.sh"

echo ""
echo "✅ Production setup complete."
echo "   Other nginx sites were NOT modified."
echo ""
bash "${ROOT_DIR}/infrastructure/scripts/setup-nginx.sh" status
