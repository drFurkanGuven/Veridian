# Veridian — Docker Infrastructure

Local development stack: PostgreSQL, Redis, RabbitMQ, and MinIO.

## Quick Start

From the monorepo root:

```bash
cp .env.example .env
pnpm infra:up
pnpm infra:verify
```

## Services

| Service | Port | URL / Access |
|---|---|---|
| PostgreSQL | 5432 | `postgresql://veridian:veridian@localhost:5432/veridian` |
| Redis | 6379 | `redis://localhost:6379/0` |
| RabbitMQ AMQP | 5672 | `amqp://veridian:veridian@localhost:5672//` |
| RabbitMQ UI | 15672 | http://localhost:15672 (veridian / veridian) |
| MinIO API | 9000 | http://localhost:9000 |
| MinIO Console | 9001 | http://localhost:9001 (minioadmin / minioadmin) |

## Commands

```bash
pnpm infra:up        # Start all infrastructure services
pnpm infra:down      # Stop and remove containers
pnpm infra:logs      # Tail service logs
pnpm infra:verify    # Check all services are reachable
pnpm infra:reset     # Destroy volumes and restart fresh
```

## Production Overlay

```bash
docker compose -f infrastructure/docker-compose.yml \
               -f infrastructure/docker-compose.prod.yml up -d
```

## Data Volumes

Persistent data is stored in named Docker volumes:

- `veridian_postgres_data`
- `veridian_redis_data`
- `veridian_rabbitmq_data`
- `veridian_minio_data`

To reset all data: `pnpm infra:reset`
