#!/usr/bin/env bash
set -euo pipefail

# Veridian infrastructure ports — check for conflicts before `pnpm infra:up`

PORTS=(
  "5432:PostgreSQL"
  "6379:Redis"
  "5672:RabbitMQ AMQP"
  "15672:RabbitMQ Management UI"
  "9000:MinIO API"
  "9001:MinIO Console"
  "8000:API (veridian-api)"
  "3000:Web (Next.js)"
)

echo "Checking port availability..."
echo ""

in_use=0

for entry in "${PORTS[@]}"; do
  port="${entry%%:*}"
  name="${entry#*:}"

  if command -v ss >/dev/null 2>&1; then
    if ss -tuln | awk '{print $5}' | grep -qE ":${port}$"; then
      process=$(ss -tulnp 2>/dev/null | grep ":${port} " | head -1 || true)
      echo "  ✗ ${port} (${name}) — IN USE"
      [[ -n "${process}" ]] && echo "      ${process}"
      in_use=$((in_use + 1))
    else
      echo "  ✓ ${port} (${name}) — free"
    fi
  elif command -v lsof >/dev/null 2>&1; then
    if lsof -iTCP:"${port}" -sTCP:LISTEN -P -n 2>/dev/null | grep -q .; then
      echo "  ✗ ${port} (${name}) — IN USE"
      lsof -iTCP:"${port}" -sTCP:LISTEN -P -n 2>/dev/null | tail -n +2 | sed 's/^/      /'
      in_use=$((in_use + 1))
    else
      echo "  ✓ ${port} (${name}) — free"
    fi
  else
  echo "  ? ${port} (${name}) — install 'ss' or 'lsof' to check"
  fi
done

echo ""
if [[ "${in_use}" -gt 0 ]]; then
  echo "⚠ ${in_use} port(s) in use. Change ports in .env or stop conflicting services."
  echo ""
  echo "List all listening ports:"
  echo "  sudo ss -tulnp"
  echo "  sudo lsof -i -P -n | grep LISTEN"
  exit 1
fi

echo "✅ All default Veridian ports are free."
