# Veridian

**The cloud IDE for HDL** — develop FPGA projects entirely from your browser. No Vivado or Quartus installation required.

## Features (Roadmap)

- HDL editing (Verilog, SystemVerilog, VHDL) with Monaco Editor
- AI-assisted development
- Server-side synthesis (Yosys, nextpnr) and simulation (Icarus, Verilator, GHDL)
- Live build logs, waveform viewer, and bitstream download
- VS Code-like interface with terminal, explorer, and panels

## Architecture

```
veridian/
├── apps/
│   ├── web/          # Next.js frontend
│   └── api/          # FastAPI backend
├── packages/
│   └── shared-types/ # Shared TypeScript API contracts
├── workers/          # Docker-based tool workers (Phase 13+)
├── docker/           # Dockerfiles (Phase 2+)
└── infrastructure/   # docker-compose, nginx (Phase 2+)
```

| Layer | Technology |
|---|---|
| Frontend | Next.js, TypeScript, TailwindCSS, Monaco, Zustand, React Query |
| Backend | FastAPI, PostgreSQL, Redis, Celery, RabbitMQ |
| Workers | Docker containers (Icarus, Verilator, GHDL, Yosys, nextpnr) |
| Storage | PostgreSQL (metadata) + MinIO/S3 (files) |

## Prerequisites

- **Node.js** ≥ 20
- **pnpm** ≥ 9
- **Python** ≥ 3.9 (for API; 3.12+ recommended)
- **Docker** (for infrastructure, Phase 2+)

### Installing pnpm (if `corepack` is not available)

`corepack` ships with Node.js 16.13+, but many servers omit it. Use one of these instead:

```bash
# Option A — via npm (simplest if Node is already installed)
npm install -g pnpm@9.15.0

# Option B — official standalone installer (no npm required)
curl -fsSL https://get.pnpm.io/install.sh | sh -
# Then reload shell: source ~/.bashrc  (or ~/.zshrc)

# Option C — corepack (only if the command exists)
corepack enable
corepack prepare pnpm@9.15.0 --activate
```

Verify: `pnpm --version` (should print 9.x)

## Getting Started

### 1. Clone and install

```bash
git clone <repo-url> veridian
cd veridian
pnpm install
```

### 2. Environment

```bash
cp .env.example .env
# Edit .env with your secrets (JWT, OAuth keys, etc.)
```

### 3. Start infrastructure

```bash
pnpm infra:up        # PostgreSQL, Redis, RabbitMQ, MinIO
pnpm infra:verify    # Confirm all services are healthy
```

### 4. Build

```bash
pnpm build
```

### 5. Development

```bash
# Terminal 1 — frontend + shared-types watch
pnpm dev

# Terminal 2 — API
cd apps/api
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
veridian-api
```

Open http://localhost:3000 — the landing page shows frontend and API health status.

### 6. API tests

```bash
cd apps/api
pytest
```

### 7. Database migrations

```bash
pnpm infra:up          # Start PostgreSQL
pnpm db:migrate        # Apply Alembic migrations
```

Other database commands:

```bash
pnpm db:alembic current     # Show current revision
pnpm db:alembic history     # Show migration history
pnpm db:alembic downgrade -1  # Roll back one revision
```

## Monorepo Scripts

| Command | Description |
|---|---|
| `pnpm build` | Build all TypeScript packages |
| `pnpm dev` | Start dev servers (web + shared-types) |
| `pnpm lint` | Lint all packages |
| `pnpm typecheck` | Type-check all packages |
| `pnpm format` | Format with Prettier |
| `pnpm infra:up` | Start Docker infrastructure |
| `pnpm infra:down` | Stop infrastructure |
| `pnpm infra:verify` | Verify service connectivity |
| `pnpm infra:logs` | Tail infrastructure logs |
| `pnpm infra:reset` | Destroy volumes and reset data |
| `pnpm db:migrate` | Apply database migrations |
| `pnpm db:alembic` | Run Alembic CLI (pass args after `--`) |

## Implementation Phases

| Phase | Module | Status |
|---|---|---|
| 0 | Monorepo scaffolding | ✅ Complete |
| 1 | Shared types package | ✅ Complete |
| 2 | Infrastructure / Docker | ✅ Complete |
| 3 | Database + migrations | ✅ Complete |
| 4 | Backend core | ✅ Complete |
| 5 | Authentication | ✅ Complete |
| 6 | Projects | ✅ Complete |
| 7 | File tree | ✅ Complete |
| ... | See architecture doc | Pending |

## License

Proprietary — all rights reserved.
