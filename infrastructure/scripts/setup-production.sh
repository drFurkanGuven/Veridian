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
cp "${ROOT_DIR}/infrastructure/systemd/veridian-api.service" /etc/systemd/system/
cp "${ROOT_DIR}/infrastructure/systemd/veridian-web.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable veridian-api veridian-web
systemctl restart veridian-api veridian-web

echo ""
echo "✅ Production setup complete."
echo "   Other nginx sites were NOT modified."
echo ""
bash "${ROOT_DIR}/infrastructure/scripts/setup-nginx.sh" status
