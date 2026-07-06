#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"

echo "Veridian — host PostgreSQL setup"
echo ""
echo "Creates user 'veridian' and database 'veridian' on the system PostgreSQL."
echo ""

if ! command -v psql >/dev/null 2>&1 && ! sudo -u postgres psql -c "SELECT 1" >/dev/null 2>&1; then
  echo "Error: PostgreSQL client or postgres system user not found."
  exit 1
fi

run_psql() {
  if sudo -u postgres psql -c "SELECT 1" >/dev/null 2>&1; then
    sudo -u postgres psql -v ON_ERROR_STOP=1 "$@"
  else
    psql -U postgres -v ON_ERROR_STOP=1 "$@"
  fi
}

run_psql <<'SQL'
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'veridian') THEN
    CREATE ROLE veridian WITH LOGIN PASSWORD 'veridian';
  END IF;
END
$$;

SELECT 'CREATE DATABASE veridian OWNER veridian'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'veridian')\gexec

GRANT ALL PRIVILEGES ON DATABASE veridian TO veridian;
SQL

echo ""
echo "✅ Database ready."
echo "   DATABASE_URL=postgresql+asyncpg://veridian:veridian@localhost:5432/veridian"
echo ""
echo "Next: pnpm db:migrate"
