# MailKnowledge Monorepo

Intelligent email management and knowledge extraction system.

## Stack
- **Backend**: FastAPI, SQLAlchemy 2 (Async), Alembic, Pydantic (w/ settings), pgvector
- **Worker**: Celery, Redis
- **Frontend**: Next.js (App Router), TypeScript, Tailwind CSS
- **Database**: PostgreSQL 17 + pgvector + pg_trgm (using `pgvector/pgvector:pg17` image)
- **Infrastructure**: Docker Compose (Dev & Prod)

## Directory Structure
```
/backend   - FastAPI app
/frontend  - Next.js app
/infra     - Docker Compose & Config
/docs      - Documentation
/worker    - Celery worker
```

## Local Development

### Prerequisites
- Docker & Docker Compose
- Make (optional, but recommended)

### Getting Started

1.  **Configure Environment**
    ```bash
    cp infra/.env.example infra/.env
    # Edit infra/.env (e.g. OLLAMA_HOST)
    ```

2.  **Start Services** (Hot reload enabled)
    ```bash
    make dev-up
    # View logs
    make dev-logs
    ```

    - Frontend: http://localhost:3000
    - Backend API Docs: http://localhost:8000/docs
    - Backend Health: http://localhost:8000/health

3.  **Run Migrations**
    ```bash
    make migrate
    ```

4.  **Stop Services**
    ```bash
    make dev-down
    ```

## Production (Unraid)

1.  **Setup Directories** on Unraid
    ```bash
    mkdir -p /mnt/user/appdata/mailknowledge/{postgres,uploads,redis}
    ```

2.  **Configure Environment**
    - Copy `infra/.env.example` to `infra/.env` on your Unraid share.
    - Set `UNRAID_APPDATA=/mnt/user/appdata/mailknowledge`.
    - Set `OLLAMA_HOST` to your Unraid server IP (e.g. `http://192.168.1.10:11434`).

3.  **Deploy**
    ```bash
    # From the repo root on Unraid terminal
    make prod-up
    ```

## Makefile Targets

| Target | Description |
| :--- | :--- |
| `make dev-up` | Start dev environment with hot-reload |
| `make dev-down` | Stop dev environment |
| `make dev-logs` | Tail dev logs |
| `make prod-up` | Start prod environment (detached) |
| `make prod-down` | Stop prod environment |
| `make migrate` | Run alembic upgrade head (on dev container) |
| `make migrate-new msg="..."` | Generate new migration (on dev container) |
| `make shell-backend` | Shell into dev backend container |
