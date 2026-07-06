#!/usr/bin/env bash
set -euo pipefail

echo "=== Docker containers ==="
docker ps -a --filter "name=veridian-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || true

echo ""
echo "=== Port check ==="
for port in 5432 6379 5672 15672 9000 8000; do
  if (echo >"/dev/tcp/localhost/${port}") >/dev/null 2>&1; then
    echo "  ✓ ${port} open"
  else
    echo "  ✗ ${port} closed"
  fi
done

echo ""
echo "=== API health ==="
if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
  curl -s http://localhost:8000/health
  echo ""
else
  echo "  API not responding on :8000 (start with: veridian-api)"
fi

echo ""
echo "=== Readiness ==="
if curl -sf http://localhost:8000/health/ready >/dev/null 2>&1; then
  curl -s http://localhost:8000/health/ready | head -c 500
  echo ""
else
  code=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health/ready 2>/dev/null || echo "000")
  echo "  /health/ready → HTTP ${code}"
fi
