import logging

import redis.asyncio as aioredis
import sqlalchemy as sa
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import router as v1_router
from app.core.config import settings

# ── Logging ────────────────────────────────────────────────────────────────────
# Keep SQLAlchemy query logging at WARNING so email bodies never appear in logs.
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="MailKnowledge API",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router, prefix="/api/v1")


# ── Health ─────────────────────────────────────────────────────────────────────
@app.get("/health", tags=["health"], summary="Liveness + dependency health check")
async def health() -> JSONResponse:
    """
    Returns HTTP 200 when all dependencies are reachable, 503 otherwise.
    Safe to poll from container orchestrators and load-balancers.
    """
    from app.db.session import engine  # local import avoids circular at module load

    checks: dict[str, str] = {}

    # ── database ──────────────────────────────────────────────────────────────
    try:
        async with engine.connect() as conn:
            await conn.execute(sa.text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:  # noqa: BLE001
        logger.warning("Health: DB check failed: %s", exc)
        checks["database"] = "error"

    # ── redis ─────────────────────────────────────────────────────────────────
    try:
        r: aioredis.Redis = aioredis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.aclose()
        checks["redis"] = "ok"
    except Exception as exc:  # noqa: BLE001
        logger.warning("Health: Redis check failed: %s", exc)
        checks["redis"] = "error"

    ok = all(v == "ok" for v in checks.values())
    return JSONResponse(
        status_code=200 if ok else 503,
        content={"status": "ok" if ok else "degraded", "checks": checks},
    )
