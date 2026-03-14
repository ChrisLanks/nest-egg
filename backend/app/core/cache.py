"""Simple Redis cache wrapper."""

import json
import logging
from typing import Any, Optional

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


async def delete(key: str) -> bool:
    """Delete a specific cache key."""
    if not redis_client:
        return False
    try:
        await redis_client.delete(key)
        return True
    except Exception as e:
        logging.error(f"Cache delete error: {e}")
        return False


async def delete_pattern(pattern: str) -> int:
    """Delete all keys matching a pattern. Returns count of deleted keys."""
    if not redis_client:
        return 0
    try:
        cursor = 0
        deleted = 0
        while True:
            cursor, keys = await redis_client.scan(cursor, match=pattern, count=100)
            if keys:
                await redis_client.delete(*keys)
                deleted += len(keys)
            if cursor == 0:
                break
        return deleted
    except Exception as e:
        logging.error(f"Cache delete_pattern error: {e}")
        return 0
