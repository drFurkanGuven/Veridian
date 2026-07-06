#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DOMAIN="veridian.furkanguven.space"
API_DOMAIN="api.veridian.furkanguven.space"
NGINX_CONF_DIR="/etc/nginx/conf.d"
WEBROOT="/var/www/certbot"

echo "=== Veridian production setup ==="
echo "  Frontend: https://${DOMAIN}"
echo "  API:      https://${API_DOMAIN}"
echo ""

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run as root: sudo bash infrastructure/scripts/setup-production.sh"
  exit 1
fi

# DNS check
echo "Checking DNS..."
for host in "${DOMAIN}" "${API_DOMAIN}"; do
  if getent hosts "${host}" >/dev/null 2>&1; then
    echo "  ✓ ${host} resolves"
  else
    echo "  ✗ ${host} does NOT resolve — add A records before continuing"
    echo "    ${DOMAIN}     → server IP"
    echo "    ${API_DOMAIN} → server IP"
    exit 1
  fi
done

# Certbot webroot
mkdir -p "${WEBROOT}"

# Nginx site configs
cp "${ROOT_DIR}/infrastructure/nginx/veridian.furkanguven.space.conf" \
  "${NGINX_CONF_DIR}/veridian.conf"
cp "${ROOT_DIR}/infrastructure/nginx/api.veridian.furkanguven.space.conf" \
  "${NGINX_CONF_DIR}/veridian-api.conf"

nginx -t
systemctl reload nginx

# SSL certificates
if ! command -v certbot >/dev/null 2>&1; then
  echo "Installing certbot..."
  dnf install -y certbot python3-certbot-nginx
fi

certbot --nginx \
  -d "${DOMAIN}" \
  -d "${API_DOMAIN}" \
  --non-interactive \
  --agree-tos \
  --register-unsafely-without-email \
  --redirect \
  || {
    echo ""
    echo "Certbot failed. Ensure ports 80/443 are open and DNS points to this server."
    echo "Retry manually: certbot --nginx -d ${DOMAIN} -d ${API_DOMAIN}"
    exit 1
  }

# Systemd services
cp "${ROOT_DIR}/infrastructure/systemd/veridian-api.service" /etc/systemd/system/
cp "${ROOT_DIR}/infrastructure/systemd/veridian-web.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable veridian-api veridian-web
systemctl restart veridian-api veridian-web

echo ""
echo "✅ Production setup complete."
echo ""
echo "  https://${DOMAIN}"
echo "  https://${API_DOMAIN}/health"
echo "  https://${API_DOMAIN}/docs"
echo ""
systemctl status veridian-api --no-pager -l | head -5
systemctl status veridian-web --no-pager -l | head -5
