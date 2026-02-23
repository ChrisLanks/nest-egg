"""Simple Redis cache wrapper."""

import json
import logging
from typing import Optional, Any

from app.config import settings

try:
    import redis.asyncio as redis

    # Create Redis client
    redis_client = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
except Exception as e:
    logging.warning(f"Redis not available: {e}")
    redis_client = None


async def get(key: str) -> Optional[Any]:
    """Get value from cache."""
    if not redis_client:
        return None

    try:
        value = await redis_client.get(key)
        if value:
            return json.loads(value)
    except Exception as e:
        logging.error(f"Cache get error: {e}")

    return None


async def setex(key: str, ttl: int, value: Any) -> bool:
    """Set value in cache with expiration."""
    if not redis_client:
        return False

    try:
        await redis_client.setex(key, ttl, json.dumps(value))
        return True
    except Exception as e:
        logging.error(f"Cache set error: {e}")
        return False
