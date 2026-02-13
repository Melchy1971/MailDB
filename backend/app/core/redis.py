from collections.abc import AsyncGenerator

import redis.asyncio as aioredis

from app.core.config import settings


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    client: aioredis.Redis = aioredis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
    )
    try:
        yield client
    finally:
        await client.aclose()
