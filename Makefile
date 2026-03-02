.PHONY: dev-up dev-down dev-logs prod-up prod-down \
        migrate migrate-new seed \
        shell-backend shell-worker shell-db

# ── Dev Utils ─────────────────────────────────────────────────────────────────
dev-up:
	docker compose -f infra/docker-compose.dev.yml up --build -d

dev-down:
	docker compose -f infra/docker-compose.dev.yml down

dev-logs:
	docker compose -f infra/docker-compose.dev.yml logs -f

# ── Prod Utils ────────────────────────────────────────────────────────────────
prod-up:
	docker compose -f infra/docker-compose.prod.yml up -d --build

prod-down:
	docker compose -f infra/docker-compose.prod.yml down

# ── DB Utils ──────────────────────────────────────────────────────────────────
migrate:
	docker compose -f infra/docker-compose.dev.yml exec backend alembic upgrade head

migrate-new:
	@test -n "$(msg)" || (echo "Usage: make migrate-new msg='describe change'" && exit 1)
	docker compose -f infra/docker-compose.dev.yml exec backend alembic revision --autogenerate -m "$(msg)"

seed:
	# Add seed script or command here if available
	@echo "Seeding not implemented yet"

shell-backend:
	docker compose -f infra/docker-compose.dev.yml exec backend bash

shell-worker:
	docker compose -f infra/docker-compose.dev.yml exec worker bash

shell-db:
	docker compose -f infra/docker-compose.dev.yml exec postgres psql -U $${POSTGRES_USER:-mail} $${POSTGRES_DB:-mailknowledge}
