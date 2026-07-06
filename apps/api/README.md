# Veridian API

FastAPI backend for Veridian — the cloud IDE for HDL.

## Development

```bash
# From monorepo root
cp .env.example .env
pnpm infra:up

# Create virtual environment
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Apply database migrations
pnpm db:migrate

# Run API server
veridian-api
# or: uvicorn veridian_api.main:app --reload --port 8000

# Run tests
pytest
```

## Database Migrations

```bash
# From monorepo root
pnpm db:migrate
pnpm db:alembic -- current
pnpm db:alembic -- history
```

## API Documentation

When `API_DEBUG=true`, OpenAPI docs are available at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
