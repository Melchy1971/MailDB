from fastapi import APIRouter

from app.api.v1.endpoints.config import router as config_router
from app.api.v1.endpoints.jobs import router as jobs_router
from app.api.v1.endpoints.sources import router as sources_router

router = APIRouter()


@router.get("/status", tags=["status"])
async def status() -> dict:
    return {"status": "ok", "service": "mailknowledge-api", "version": "0.1.0"}


router.include_router(config_router)
router.include_router(sources_router)
router.include_router(jobs_router)
