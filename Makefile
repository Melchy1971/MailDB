.PHONY: up down build rebuild logs ps \
        migrate migrate-new \
        shell-backend shell-worker shell-db \
        frontend-install

COMPOSE = docker compose -f infra/docker-compose.yml

# ── Compose lifecycle ─────────────────────────────────────────────────────────
up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

build:
	$(COMPOSE) build

rebuild:
	$(COMPOSE) build --no-cache

logs:
	$(COMPOSE) logs -f

ps:
	$(COMPOSE) ps

# ── Database migrations ───────────────────────────────────────────────────────
migrate:
	$(COMPOSE) exec backend alembic upgrade head

migrate-new:
	@test -n "$(msg)" || (echo "Usage: make migrate-new msg='describe change'" && exit 1)
	$(COMPOSE) exec backend alembic revision --autogenerate -m "$(msg)"

# ── Shells ────────────────────────────────────────────────────────────────────
shell-backend:
	$(COMPOSE) exec backend bash

shell-worker:
	$(COMPOSE) exec worker bash

shell-db:
	$(COMPOSE) exec postgres psql -U $${POSTGRES_USER:-mail} $${POSTGRES_DB:-mailknowledge}

# ── Frontend local dev ────────────────────────────────────────────────────────
frontend-install:
	cd frontend && npm install
