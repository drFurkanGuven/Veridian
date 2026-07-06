#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run as root: sudo bash infrastructure/scripts/setup-systemd.sh"
  exit 1
fi

find_uvicorn() {
  if [[ -x "${ROOT_DIR}/apps/api/.venv/bin/uvicorn" ]]; then
    echo "${ROOT_DIR}/apps/api/.venv/bin/uvicorn"
  elif [[ -x "${ROOT_DIR}/.venv/bin/uvicorn" ]]; then
    echo "${ROOT_DIR}/.venv/bin/uvicorn"
  else
    echo ""
  fi
}

UVICORN="$(find_uvicorn)"
if [[ -z "${UVICORN}" ]]; then
  echo "✗ uvicorn not found. Create venv first:"
  echo "  cd ${ROOT_DIR}/apps/api"
  echo "  python3 -m venv .venv"
  echo "  source .venv/bin/activate && pip install -e ."
  exit 1
fi

STANDALONE_DIR="${ROOT_DIR}/apps/web/.next/standalone"
if [[ ! -f "${STANDALONE_DIR}/apps/web/server.js" ]]; then
  echo "✗ Next.js standalone build not found."
  echo "  Run: pnpm build:prod"
  exit 1
fi

if [[ ! -f "${ROOT_DIR}/.env" ]]; then
  echo "⚠ ${ROOT_DIR}/.env missing — copy from .env.production.example"
fi

echo "=== Installing Veridian systemd services ==="
echo "  uvicorn: ${UVICORN}"
echo "  web:     ${STANDALONE_DIR}/apps/web/server.js"
echo ""

# API service — venv yolunu sunucuya göre ayarla
sed "s|ExecStart=.*|ExecStart=${UVICORN} veridian_api.main:app --host 127.0.0.1 --port 8000 --workers 2|" \
  "${ROOT_DIR}/infrastructure/systemd/veridian-api.service" \
  > /etc/systemd/system/veridian-api.service

cp "${ROOT_DIR}/infrastructure/systemd/veridian-web.service" /etc/systemd/system/

systemctl daemon-reload
systemctl enable veridian-api veridian-web
systemctl restart veridian-api veridian-web

echo ""
systemctl --no-pager status veridian-api veridian-web || true

echo ""
echo "✅ Systemd services installed and started."
echo "   curl http://127.0.0.1:3000"
echo "   curl http://127.0.0.1:8000/health"
