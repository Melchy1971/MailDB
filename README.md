# MailKnowledge

Intelligent email management and knowledge extraction.

## Stack

| Layer     | Technology                               |
|-----------|------------------------------------------|
| Backend   | FastAPI · SQLAlchemy 2 (async) · Alembic |
| Worker    | Celery 5 · Redis                         |
| Frontend  | Next.js 15 (App Router) · TypeScript · Tailwind CSS |
| Database  | PostgreSQL 17 + pgvector                 |
| Broker    | Redis 7                                  |
| Runtime   | Docker / Docker Compose v2               |

> **Postgres version note:** The compose file uses `pgvector/pgvector:pg17` (stable).
> Swap to `ankane/pgvector:pg18` or `postgres:18` in `infra/docker-compose.yml` once a
> production-ready pg18 image with pgvector is available.

---

## Quick Start

```bash
# 1. Copy and fill in secrets
cp infra/.env.example infra/.env
$EDITOR infra/.env

# 2. Build and start all services
make build
make up

# 3. Run database migrations
make migrate

# 4. Open in browser
#   Frontend  → http://localhost:3000
#   API docs  → http://localhost:8000/api/docs
#   Health    → http://localhost:8000/health
```

---

## Directory Structure

```
MailKnowledge/
├── backend/                  FastAPI application
│   ├── app/
│   │   ├── api/v1/router.py  API routes
│   │   ├── core/config.py    Pydantic settings
│   │   ├── db/               SQLAlchemy engine + session
│   │   └── models/           ORM models (add yours here)
│   ├── alembic/              Migrations
│   ├── alembic.ini
│   ├── Dockerfile
│   └── requirements.txt
├── worker/                   Celery worker
│   ├── app/
│   │   ├── celery_app.py     Celery instance
│   │   ├── core/config.py    Worker settings
│   │   └── tasks/sample.py   Example task
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                 Next.js app
│   ├── src/app/              App Router pages
│   ├── Dockerfile
│   └── package.json
├── infra/
│   ├── docker-compose.yml    Full-stack orchestration
│   └── .env.example
├── Makefile                  Convenience targets
└── README.md
```

---

## Volumes

| Named volume    | Purpose                  | Default container path |
|-----------------|--------------------------|------------------------|
| `postgres_data` | Postgres data directory  | `/var/lib/postgresql/data` |
| `uploads_data`  | Uploaded files           | `/uploads` (backend **and** worker) |
| `redis_data`    | Redis persistence        | `/data` |

---

## Unraid Setup

### Using the Docker Compose Manager plugin

1. Install **Docker Compose Manager** from Community Applications.
2. Place this repo (or just the `infra/` folder) on a share,
   e.g. `/mnt/user/appdata/mailknowledge/`.
3. Copy `infra/.env.example` → `infra/.env` and set real values.
4. **(Optional)** Replace named volumes with bind-mounts for easier access
   from the Unraid file manager. Edit `infra/docker-compose.yml`:

   ```yaml
   volumes:
     postgres_data:
       driver: local
       driver_opts:
         type: none
         o: bind
         device: /mnt/user/appdata/mailknowledge/postgres

     uploads_data:
       driver: local
       driver_opts:
         type: none
         o: bind
         device: /mnt/user/appdata/mailknowledge/uploads

     redis_data:
       driver: local
       driver_opts:
         type: none
         o: bind
         device: /mnt/user/appdata/mailknowledge/redis
   ```

   Create the directories first:
   ```bash
   mkdir -p /mnt/user/appdata/mailknowledge/{postgres,uploads,redis}
   ```

5. In Docker Compose Manager, point it at `infra/docker-compose.yml` and click **Up**.

### Port mapping

| Service  | Internal | Host (default) |
|----------|----------|----------------|
| Frontend | 3000     | 3000           |
| Backend  | 8000     | 8000           |

Override `FRONTEND_PORT` / `BACKEND_PORT` in `infra/.env` to avoid collisions.

---

## Development Workflow

```bash
# Watch logs for all services
make logs

# Open a Python shell inside the backend container
make shell-backend

# Generate a new migration after editing models
make migrate-new msg="add email table"

# Apply migrations
make migrate

# Open psql
make shell-db

# Install frontend deps locally (for IDE support)
make frontend-install
cd frontend && npm run dev
```

---

## PST Conversion

PST parsing requires **libpff**, which must be compiled from source and is
not included in the default worker image.  The reliable, always-supported
path is to convert your PST to MBOX first, then import the MBOX.

### Recommended: readpst (libpst)

```bash
# Install on Debian/Ubuntu
apt-get install readpst

# Convert — each top-level Outlook folder becomes a separate MBOX file
readpst -o /tmp/mbox-export/ /path/to/mailbox.pst

# You'll get files like:
#   /tmp/mbox-export/Inbox.mbox
#   /tmp/mbox-export/Sent Items.mbox
#   ...

# Register each MBOX with the API
curl -X POST http://localhost:8000/api/v1/sources/mbox \
  -F "name=Inbox" \
  -F "file=@/tmp/mbox-export/Inbox.mbox"

# Or if the file is already on the server volume (/uploads)
curl -X POST http://localhost:8000/api/v1/sources/mbox \
  -F "name=Inbox" \
  -F "path=/uploads/Inbox.mbox"
```

### Alternative: EML export

Outlook and many other clients can export individual messages as `.eml`
files.  Place them in a directory tree (sub-folder names become mailbox
folders) and register via `POST /api/v1/sources/eml`.

```bash
curl -X POST http://localhost:8000/api/v1/sources/eml \
  -F "name=My Export" \
  -F "path=/uploads/eml-export/"
```

### Best-effort: direct PST (pypff)

If you can provide a pre-built `libpff-python` wheel for Linux/amd64,
add it to `worker/requirements.txt` and rebuild the worker image.
The worker will automatically use `PstParser` for `source_type = pst`.

```bash
# worker/requirements.txt — uncomment:
# libpff-python

make rebuild
```

Without the wheel, registering a PST source and triggering an import will
set the job to `failure` with a clear message directing you to convert first.

---

## Health Checks

| Endpoint                     | Expected response         |
|------------------------------|---------------------------|
| `GET /health`                | `{"status":"ok"}`         |
| `GET /api/v1/status`         | `{"status":"ok",...}`     |
| `redis-cli ping` (in container) | `PONG`               |
| `pg_isready` (in container)  | `accepting connections`   |

---

## Environment Variables

### Backend / Worker

| Variable       | Default                                              | Description            |
|----------------|------------------------------------------------------|------------------------|
| `DATABASE_URL` | `postgresql+asyncpg://mail:mail@postgres:5432/...`   | Async Postgres DSN     |
| `REDIS_URL`    | `redis://redis:6379/0`                               | Redis DSN              |
| `UPLOADS_DIR`  | `/uploads`                                           | Shared upload path     |
| `SECRET_KEY`   | `change-me-in-production`                            | App secret             |
| `DEBUG`        | `false`                                              | SQLAlchemy echo        |

### Frontend

| Variable              | Default                  | Description          |
|-----------------------|--------------------------|----------------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000`  | Backend base URL     |
