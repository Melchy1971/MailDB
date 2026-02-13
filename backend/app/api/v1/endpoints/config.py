"""GET /config – fetch all runtime config.
POST /config – upsert one or more key/value pairs (merge, not replace).
"""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.db.session import get_db
from app.models.app_config import AppConfig

router = APIRouter(prefix="/config", tags=["config"])


async def _all_config(db: AsyncSession) -> dict[str, Any]:
    rows = (await db.execute(select(AppConfig))).scalars().all()
    return {r.key: r.value for r in rows}


@router.get("", summary="Return all runtime configuration")
async def get_config(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await _all_config(db)


@router.post("", summary="Upsert one or more config keys")
async def patch_config(
    data: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Merges the supplied key/value pairs into `app_config`.
    Existing keys are updated; new keys are inserted; absent keys are untouched.
    Values may be any JSON-serialisable type.
    """
    if not data:
        return await _all_config(db)

    for key, value in data.items():
        stmt = pg_insert(AppConfig).values(key=key, value=value)
        await db.execute(
            stmt.on_conflict_do_update(
                index_elements=["key"],
                set_={"value": stmt.excluded.value, "updated_at": func.now()},
            )
        )

    await db.commit()
    return await _all_config(db)
