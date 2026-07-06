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

VERIDIAN_FILES=(
  "zz-veridian-upstreams.conf"
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

prepare_webroot() {
  mkdir -p "${WEBROOT}/.well-known/acme-challenge"
  chmod -R 755 "${WEBROOT}"
  if id nginx >/dev/null 2>&1; then
    chown -R nginx:nginx "${WEBROOT}"
  elif id www-data >/dev/null 2>&1; then
    chown -R www-data:www-data "${WEBROOT}"
  fi

  # Fedora/RHEL SELinux — 403'un en sık nedeni
  if command -v getenforce >/dev/null 2>&1 && [[ "$(getenforce)" != "Disabled" ]]; then
    if command -v chcon >/dev/null 2>&1; then
      chcon -Rt httpd_sys_content_t "${WEBROOT}" 2>/dev/null || true
    fi
    if command -v semanage >/dev/null 2>&1; then
      semanage fcontext -a -t httpd_sys_content_t "${WEBROOT}(/.*)?" 2>/dev/null || true
      restorecon -Rv "${WEBROOT}" 2>/dev/null || true
    fi
    echo "  ✓ SELinux context applied to ${WEBROOT}"
  fi
}

dns_has_a_record() {
  local host="$1"
  local ip=""

  if command -v dig >/dev/null 2>&1; then
    # Yerel resolver (systemd-resolved negatif cache tutabilir)
    ip="$(dig +short A "${host}" 2>/dev/null | grep -E '^[0-9]+\.' | head -1 || true)"
    if [[ -n "${ip}" ]]; then
      return 0
    fi
    # Önbelleği bypass et — doğrudan public DNS
    ip="$(dig +short A "${host}" @8.8.8.8 2>/dev/null | grep -E '^[0-9]+\.' | head -1 || true)"
    if [[ -n "${ip}" ]]; then
      return 0
    fi
    # Authoritative (Namecheap)
    ip="$(dig +short A "${host}" @dns1.registrar-servers.com 2>/dev/null | grep -E '^[0-9]+\.' | head -1 || true)"
    [[ -n "${ip}" ]]
    return
  fi

  if command -v host >/dev/null 2>&1; then
    host -t A "${host}" 2>/dev/null | grep -q "has address"
    return
  fi

  getent ahosts "${host}" 2>/dev/null | grep -q STREAM
}

dns_lookup_ip() {
  local host="$1"
  local ip=""
  if command -v dig >/dev/null 2>&1; then
    ip="$(dig +short A "${host}" 2>/dev/null | grep -E '^[0-9]+\.' | head -1 || true)"
    [[ -n "${ip}" ]] && echo "${ip}" && return
    ip="$(dig +short A "${host}" @8.8.8.8 2>/dev/null | grep -E '^[0-9]+\.' | head -1 || true)"
    [[ -n "${ip}" ]] && echo "${ip}" && return
    dig +short A "${host}" @dns1.registrar-servers.com 2>/dev/null | grep -E '^[0-9]+\.' | head -1
  fi
}

server_name_pattern() {
  local name="$1"
  local escaped="${name//./\\.}"
  echo "server_name[[:space:]]+${escaped}[[:space:];]"
}

count_server_name_blocks() {
  local name="$1"
  nginx -T 2>/dev/null | grep -cE "$(server_name_pattern "${name}")" || true
}

list_server_name_configs() {
  local name="$1"
  local pattern
  pattern="$(server_name_pattern "${name}")"
  grep -rlE "${pattern}" /etc/nginx/ 2>/dev/null || true
}

check_duplicate_server_name() {
  local name="$1"
  local files external=0
  files="$(list_server_name_configs "${name}")"

  while IFS= read -r f; do
    [[ -z "${f}" ]] && continue
    if [[ "${f}" != *"zz-veridian"* ]]; then
      echo "  ⚠ WARNING: '${name}' also defined in ${f}"
      external=1
    fi
  done <<< "${files}"

  return "${external}"
}

report_server_name_blocks() {
  local host="$1"
  local files count
  files="$(list_server_name_configs "${host}")"
  count="$(echo "${files}" | grep -c . || true)"

  if [[ "${count}" -eq 0 ]]; then
    echo "  ✗ ${host} (no nginx block)"
    return
  fi

  if check_duplicate_server_name "${host}"; then
    if [[ "${count}" -le 2 ]]; then
      echo "  ✓ ${host} (HTTP + HTTPS — normal)"
    else
      echo "  ? ${host} (${count} blocks)"
    fi
  else
    echo "  ✗ ${host} (conflict with another site config)"
  fi

  echo "${files}" | sed 's/^/      /'
}

test_acme_webroot() {
  local host="$1"
  local token="veridian-test-$(date +%s)"
  local path="${WEBROOT}/.well-known/acme-challenge/${token}"

  echo "test-ok" > "${path}"
  chmod 644 "${path}"

  local code
  code="$(curl -sS -o /dev/null -w '%{http_code}' "http://${host}/.well-known/acme-challenge/${token}" || echo "000")"
  rm -f "${path}"

  if [[ "${code}" == "200" ]]; then
    echo "  ✓ ACME webroot OK for ${host} (HTTP ${code})"
    return 0
  fi

  echo "  ✗ ACME webroot FAILED for ${host} (HTTP ${code}, expected 200)"
  echo "    Likely causes: duplicate server_name, SELinux, firewall, wrong nginx block"
  return 1
}

install_upstreams() {
  cp "${SITES_SRC}/veridian-upstreams.conf" \
    "${NGINX_CONF_DIR}/zz-veridian-upstreams.conf"
}

cmd_install() {
  require_root
  echo "=== Veridian nginx install (safe mode) ==="
  echo "  Adds ONLY new files to ${NGINX_CONF_DIR}/"
  echo "  Does NOT modify nginx.conf or other site configs"
  echo ""

  prepare_webroot
  install_upstreams

  cp "${SITES_SRC}/veridian-frontend-http.conf" \
    "${NGINX_CONF_DIR}/zz-veridian-frontend-http.conf"
  cp "${SITES_SRC}/veridian-api-http.conf" \
    "${NGINX_CONF_DIR}/zz-veridian-api-http.conf"

  echo "Installed:"
  for f in zz-veridian-upstreams.conf zz-veridian-frontend-http.conf zz-veridian-api-http.conf; do
    echo "  ${NGINX_CONF_DIR}/${f}"
  done
  echo ""

  nginx_test_reload

  echo ""
  echo "✅ HTTP proxy active (SSL not yet enabled)."
  echo "   http://${DOMAIN}"
  echo "   http://${API_DOMAIN}/health"
  echo ""
  echo "Before SSL, add DNS:"
  echo "   ${DOMAIN}     A → server IP"
  echo "   ${API_DOMAIN} A → server IP"
  echo ""
  echo "Then: sudo bash infrastructure/scripts/setup-nginx.sh diagnose"
  echo "      sudo bash infrastructure/scripts/setup-nginx.sh ssl"
}

use_acme_configs() {
  cp "${SITES_SRC}/veridian-frontend-acme.conf" \
    "${NGINX_CONF_DIR}/zz-veridian-frontend-http.conf"
  cp "${SITES_SRC}/veridian-api-acme.conf" \
    "${NGINX_CONF_DIR}/zz-veridian-api-http.conf"
  nginx_test_reload
}

restore_http_configs() {
  cp "${SITES_SRC}/veridian-frontend-http.conf" \
    "${NGINX_CONF_DIR}/zz-veridian-frontend-http.conf"
  cp "${SITES_SRC}/veridian-api-http.conf" \
    "${NGINX_CONF_DIR}/zz-veridian-api-http.conf"
  nginx_test_reload
}

install_ssl_configs() {
  cp "${SITES_SRC}/veridian-frontend-http-redirect.conf" \
    "${NGINX_CONF_DIR}/zz-veridian-frontend-http.conf"
  cp "${SITES_SRC}/veridian-api-http-redirect.conf" \
    "${NGINX_CONF_DIR}/zz-veridian-api-http.conf"
  cp "${SITES_SRC}/veridian-frontend-ssl.conf" \
    "${NGINX_CONF_DIR}/zz-veridian-frontend-ssl.conf"
  cp "${SITES_SRC}/veridian-api-ssl.conf" \
    "${NGINX_CONF_DIR}/zz-veridian-api-ssl.conf"
}

run_certbot() {
  local -a domains=("$@")
  local -a cert_args=()

  for d in "${domains[@]}"; do
    cert_args+=(-d "${d}")
  done

  certbot certonly --webroot \
    -w "${WEBROOT}" \
    "${cert_args[@]}" \
    --non-interactive \
    --agree-tos \
    --register-unsafely-without-email \
    --keep-until-expiring
}

ensure_ssl_options() {
  if [[ ! -f /etc/letsencrypt/options-ssl-nginx.conf ]]; then
    curl -sS https://raw.githubusercontent.com/certbot/certbot/master/certbot-nginx/certbot_nginx/_internal/tls_configs/options-ssl-nginx.conf \
      -o /etc/letsencrypt/options-ssl-nginx.conf || true
  fi
  if [[ ! -f /etc/letsencrypt/ssl-dhparams.pem ]]; then
    openssl dhparam -out /etc/letsencrypt/ssl-dhparams.pem 2048 2>/dev/null || true
  fi
}

cmd_ssl() {
  require_root
  echo "=== Veridian SSL (webroot — does not touch other configs) ==="

  if ! command -v certbot >/dev/null 2>&1; then
    echo "Installing certbot..."
    dnf install -y certbot || apt-get install -y certbot
  fi

  prepare_webroot
  install_upstreams

  echo ""
  echo "Checking DNS..."
  if ! dns_has_a_record "${DOMAIN}"; then
    echo "  ✗ No A record for ${DOMAIN}"
    echo "    Add DNS A record pointing to this server's public IP."
    exit 1
  fi
  echo "  ✓ ${DOMAIN} resolves"

  local api_dns_ok=0
  if dns_has_a_record "${API_DOMAIN}"; then
    echo "  ✓ ${API_DOMAIN} resolves"
    api_dns_ok=1
  else
    echo "  ✗ ${API_DOMAIN} has no A record (NXDOMAIN)"
    echo "    Will request certificate for ${DOMAIN} only."
    echo "    After adding API DNS: sudo bash infrastructure/scripts/setup-nginx.sh ssl-api"
  fi

  echo ""
  echo "Checking nginx server_name conflicts..."
  check_duplicate_server_name "${DOMAIN}" || true
  if [[ "${api_dns_ok}" -eq 1 ]]; then
    check_duplicate_server_name "${API_DOMAIN}" || true
  fi

  echo ""
  echo "Switching to ACME-only configs (no proxy during validation)..."
  use_acme_configs

  echo ""
  if ! test_acme_webroot "${DOMAIN}"; then
    echo ""
    echo "Fix the webroot issue before running certbot."
    echo "Run: sudo bash infrastructure/scripts/setup-nginx.sh diagnose"
    restore_http_configs
    exit 1
  fi

  if [[ "${api_dns_ok}" -eq 1 ]]; then
    if ! test_acme_webroot "${API_DOMAIN}"; then
      echo "  API subdomain webroot failed — cert will be main domain only."
      api_dns_ok=0
    fi
  fi

  echo ""
  echo "Requesting certificate..."
  if [[ "${api_dns_ok}" -eq 1 ]]; then
    run_certbot "${DOMAIN}" "${API_DOMAIN}"
  else
    run_certbot "${DOMAIN}"
  fi

  ensure_ssl_options
  install_ssl_configs
  nginx_test_reload

  echo ""
  echo "✅ SSL enabled for https://${DOMAIN}"
  if [[ "${api_dns_ok}" -eq 1 ]]; then
    echo "   https://${API_DOMAIN}/health"
  else
    echo ""
    echo "API subdomain not in certificate yet."
    echo "1. Add DNS: ${API_DOMAIN} A → server IP"
    echo "2. Run: sudo bash infrastructure/scripts/setup-nginx.sh ssl-api"
  fi
}

cmd_ssl_api() {
  require_root
  echo "=== Expand certificate to include API subdomain ==="

  if [[ ! -f /etc/letsencrypt/live/${DOMAIN}/fullchain.pem ]]; then
    echo "No certificate yet. Run: setup-nginx.sh ssl"
    exit 1
  fi

  if ! dns_has_a_record "${API_DOMAIN}"; then
    echo "  ✗ ${API_DOMAIN} still has no A record."
    exit 1
  fi

  prepare_webroot
  install_upstreams
  use_acme_configs

  if ! test_acme_webroot "${API_DOMAIN}"; then
    restore_http_configs
    exit 1
  fi

  certbot certonly --webroot \
    -w "${WEBROOT}" \
    -d "${DOMAIN}" \
    -d "${API_DOMAIN}" \
    --expand \
    --non-interactive \
    --agree-tos \
    --register-unsafely-without-email

  install_ssl_configs
  nginx_test_reload

  echo ""
  echo "✅ Certificate expanded. https://${API_DOMAIN}/health"
}

cmd_diagnose() {
  require_root
  echo "=== Veridian nginx diagnostics ==="
  echo ""

  echo "DNS:"
  for host in "${DOMAIN}" "${API_DOMAIN}"; do
    if dns_has_a_record "${host}"; then
      local ip
      ip="$(dns_lookup_ip "${host}")"
      echo "  ✓ ${host} → ${ip:-?}"
    else
      echo "  ✗ ${host} — no A record (local resolver)"
      if command -v dig >/dev/null 2>&1; then
        local pub_ip
        pub_ip="$(dig +short A "${host}" @8.8.8.8 2>/dev/null | grep -E '^[0-9]+\.' | head -1 || true)"
        if [[ -n "${pub_ip}" ]]; then
          echo "    (public DNS @8.8.8.8 sees: ${pub_ip} — local cache stale, ssl-api will still work)"
        fi
      fi
    fi
  done

  echo ""
  echo "Webroot (${WEBROOT}):"
  ls -laZ "${WEBROOT}/.well-known/acme-challenge/" 2>/dev/null || echo "  (directory missing — run install)"

  echo ""
  echo "Veridian nginx files:"
  for f in "${VERIDIAN_FILES[@]}"; do
    [[ -f "${NGINX_CONF_DIR}/${f}" ]] && echo "  ✓ ${f}" || echo "  ✗ ${f}"
  done

  echo ""
  echo "server_name blocks:"
  report_server_name_blocks "${DOMAIN}"
  report_server_name_blocks "${API_DOMAIN}"

  echo ""
  echo "ACME webroot test:"
  prepare_webroot
  install_upstreams 2>/dev/null || true
  test_acme_webroot "${DOMAIN}" || true
  if dns_has_a_record "${API_DOMAIN}"; then
    test_acme_webroot "${API_DOMAIN}" || true
  fi

  echo ""
  if [[ -f /etc/letsencrypt/live/${DOMAIN}/fullchain.pem ]]; then
    echo "Certificate: ✓ exists"
    openssl x509 -in "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" -noout -dates 2>/dev/null || true
    echo "SANs:"
    openssl x509 -in "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" -noout -text 2>/dev/null \
      | grep -A1 "Subject Alternative Name" || true
  else
    echo "Certificate: ✗ not installed"
  fi
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
  install)   cmd_install ;;
  ssl)       cmd_ssl ;;
  ssl-api)   cmd_ssl_api ;;
  diagnose)  cmd_diagnose ;;
  remove)    cmd_remove ;;
  status)    cmd_status ;;
  *)
    echo "Usage: setup-nginx.sh {install|ssl|ssl-api|diagnose|remove|status}"
    echo ""
    echo "  install   — add HTTP proxy (safe, no other configs touched)"
    echo "  ssl       — certbot webroot + HTTPS (main domain; API if DNS ready)"
    echo "  ssl-api   — expand cert after api.* DNS is added"
    echo "  diagnose  — DNS, webroot, duplicate server_name checks"
    echo "  remove    — remove only Veridian configs"
    echo "  status    — show Veridian nginx file status"
    exit 1
    ;;
esac
