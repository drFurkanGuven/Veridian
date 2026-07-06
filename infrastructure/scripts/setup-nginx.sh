#!/usr/bin/env bash
set -euo pipefail

# Güvenli nginx kurulumu — SADECE Veridian site dosyalarını ekler/kaldırır.
# /etc/nginx/nginx.conf ve diğer site config'lerine dokunmaz.
# certbot --nginx KULLANMAZ (mevcut config'leri değiştirebilir).

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SITES_SRC="${ROOT_DIR}/infrastructure/nginx/sites"
NGINX_CONF_DIR="/etc/nginx/conf.d"
WEBROOT="/var/www/certbot"

DOMAIN="veridian.furkanguven.space"
API_DOMAIN="api.veridian.furkanguven.space"

# Sadece bu dosyalar yönetilir — başka hiçbir conf'a dokunulmaz
VERIDIAN_FILES=(
  "zz-veridian-frontend-http.conf"
  "zz-veridian-frontend-ssl.conf"
  "zz-veridian-api-http.conf"
  "zz-veridian-api-ssl.conf"
)

require_root() {
  if [[ "$(id -u)" -ne 0 ]]; then
    echo "Run as root: sudo bash infrastructure/scripts/setup-nginx.sh $*"
    exit 1
  fi
}

nginx_test_reload() {
  echo "Testing nginx config..."
  nginx -t
  systemctl reload nginx
  echo "  ✓ nginx reloaded"
}

cmd_install() {
  require_root
  echo "=== Veridian nginx install (safe mode) ==="
  echo "  Adds ONLY new files to ${NGINX_CONF_DIR}/"
  echo "  Does NOT modify nginx.conf or other site configs"
  echo ""

  mkdir -p "${WEBROOT}"

  cp "${SITES_SRC}/veridian-frontend-http.conf" \
    "${NGINX_CONF_DIR}/zz-veridian-frontend-http.conf"
  cp "${SITES_SRC}/veridian-api-http.conf" \
    "${NGINX_CONF_DIR}/zz-veridian-api-http.conf"

  echo "Installed:"
  echo "  ${NGINX_CONF_DIR}/zz-veridian-frontend-http.conf"
  echo "  ${NGINX_CONF_DIR}/zz-veridian-api-http.conf"
  echo ""

  nginx_test_reload

  echo ""
  echo "✅ HTTP proxy active (SSL not yet enabled)."
  echo "   http://${DOMAIN}"
  echo "   http://${API_DOMAIN}/health"
  echo ""
  echo "Next: sudo bash infrastructure/scripts/setup-nginx.sh ssl"
}

cmd_ssl() {
  require_root
  echo "=== Veridian SSL (webroot — does not touch other configs) ==="

  if ! command -v certbot >/dev/null 2>&1; then
    echo "Installing certbot..."
    dnf install -y certbot
  fi

  mkdir -p "${WEBROOT}"

  # certonly + webroot: mevcut nginx config'lerini DEĞİŞTİRMEZ
  certbot certonly --webroot \
    -w "${WEBROOT}" \
    -d "${DOMAIN}" \
    -d "${API_DOMAIN}" \
    --non-interactive \
    --agree-tos \
    --register-unsafely-without-email \
    --keep-until-expiring \
    || {
      echo ""
      echo "Certbot failed. Check DNS and port 80."
      exit 1
    }

  # Let's Encrypt SSL options (certbot oluşturur, diğer sitelere dokunmaz)
  if [[ ! -f /etc/letsencrypt/options-ssl-nginx.conf ]]; then
    curl -sS https://raw.githubusercontent.com/certbot/certbot/master/certbot-nginx/certbot_nginx/_internal/tls_configs/options-ssl-nginx.conf \
      -o /etc/letsencrypt/options-ssl-nginx.conf || true
  fi
  if [[ ! -f /etc/letsencrypt/ssl-dhparams.pem ]]; then
    openssl dhparam -out /etc/letsencrypt/ssl-dhparams.pem 2048 2>/dev/null || true
  fi

  # HTTP → redirect, HTTPS ekle
  cp "${SITES_SRC}/veridian-frontend-http-redirect.conf" \
    "${NGINX_CONF_DIR}/zz-veridian-frontend-http.conf"
  cp "${SITES_SRC}/veridian-api-http-redirect.conf" \
    "${NGINX_CONF_DIR}/zz-veridian-api-http.conf"
  cp "${SITES_SRC}/veridian-frontend-ssl.conf" \
    "${NGINX_CONF_DIR}/zz-veridian-frontend-ssl.conf"
  cp "${SITES_SRC}/veridian-api-ssl.conf" \
    "${NGINX_CONF_DIR}/zz-veridian-api-ssl.conf"

  nginx_test_reload

  echo ""
  echo "✅ SSL enabled."
  echo "   https://${DOMAIN}"
  echo "   https://${API_DOMAIN}/health"
}

cmd_remove() {
  require_root
  echo "=== Removing ONLY Veridian nginx configs ==="

  for f in "${VERIDIAN_FILES[@]}"; do
    if [[ -f "${NGINX_CONF_DIR}/${f}" ]]; then
      rm -f "${NGINX_CONF_DIR}/${f}"
      echo "  removed ${NGINX_CONF_DIR}/${f}"
    fi
  done

  nginx_test_reload
  echo "✅ Veridian nginx configs removed. Other sites unchanged."
}

cmd_status() {
  echo "Veridian nginx files in ${NGINX_CONF_DIR}:"
  for f in "${VERIDIAN_FILES[@]}"; do
    if [[ -f "${NGINX_CONF_DIR}/${f}" ]]; then
      echo "  ✓ ${f}"
    else
      echo "  ✗ ${f} (not installed)"
    fi
  done
  echo ""
  echo "Other nginx configs are NOT managed by this script."
  ls -1 "${NGINX_CONF_DIR}/" 2>/dev/null | grep -v '^zz-veridian' || true
}

case "${1:-}" in
  install) cmd_install ;;
  ssl)     cmd_ssl ;;
  remove)  cmd_remove ;;
  status)  cmd_status ;;
  *)
    echo "Usage: setup-nginx.sh {install|ssl|remove|status}"
    echo ""
    echo "  install  — add HTTP proxy (safe, no other configs touched)"
    echo "  ssl      — certbot webroot + HTTPS (safe, no certbot --nginx)"
    echo "  remove   — remove only Veridian configs"
    echo "  status   — show Veridian nginx file status"
    exit 1
    ;;
esac
