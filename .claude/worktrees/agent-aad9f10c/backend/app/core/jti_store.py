"""Redis-backed JTI (JWT ID) revocation store.

Provides O(1) token revocation checks on the /refresh hot path.
The Postgres RefreshToken table remains the source of truth; this
Redis layer is an additive fast-path that can be bypassed safely
when Redis is unavailable (the DB check still runs).

Dev / test environments skip all Redis writes and reads so the
feature does not require a running Redis instance locally.

Data layout
-----------
``jti:{jti}``              STRING  value=user_id  TTL=token_expiry_seconds
``user_jtis:{user_id}``    SET     member=jti     TTL=max_token_expiry_seconds
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_redis_client = None


async def _get_redis():
    """Return a shared Redis client, or None if unavailable / disabled."""
    from app.config import settings

    if not settings.ENFORCE_JTI_REDIS_CHECK:
        return None

    global _redis_client
    if _redis_client is None:
        try:
            import redis.asyncio as aioredis

            client = aioredis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
            await client.ping()
            _redis_client = client
            logger.debug("jti_store: Redis connection established")
        except Exception as exc:
            logger.warning("jti_store: Redis unavailable, skipping JTI Redis check: %s", exc)
            return None
    return _redis_client


async def store_jti(jti: str, user_id: str, ttl_seconds: int) -> None:
    """Record a newly-issued refresh token JTI in Redis.

    Called immediately after creating a RefreshToken DB record so the
    two stores stay in sync.  Failures are non-fatal — the DB record
    is the authoritative revocation check.
    """
    redis = await _get_redis()
    if redis is None:
        return
    try:
        pipe = redis.pipeline()
        # Primary key: jti → user_id (for verify_jti)
        pipe.set(f"jti:{jti}", user_id, ex=ttl_seconds)
        # Secondary index: user → set of jtis (for delete_all_jtis_for_user)
        pipe.sadd(f"user_jtis:{user_id}", jti)
        # Expire the set slightly beyond the token lifetime so it cleans up
        pipe.expire(f"user_jtis:{user_id}", ttl_seconds + 3600)
        await pipe.execute()
    except Exception as exc:
        logger.warning("jti_store.store_jti failed (non-fatal): %s", exc)


async def verify_jti(jti: str) -> bool:
    """Return True if the JTI exists in Redis (token is still live).

    A False result means the token was revoked via logout or logout-all.
    When Redis is unavailable, returns True so the DB check governs.
    """
    redis = await _get_redis()
    if redis is None:
        return True  # Degrade gracefully — DB check still runs
    try:
        exists = await redis.exists(f"jti:{jti}")
        return bool(exists)
    except Exception as exc:
        logger.warning("jti_store.verify_jti failed (non-fatal), allowing: %s", exc)
        return True  # Fail open; DB is the safety net


async def delete_jti(jti: str) -> None:
    """Remove a single JTI from Redis (single-device logout)."""
    redis = await _get_redis()
    if redis is None:
        return
    try:
        # Read user_id so we can remove from the secondary index too
        user_id: Optional[str] = await redis.get(f"jti:{jti}")
        pipe = redis.pipeline()
        pipe.delete(f"jti:{jti}")
        if user_id:
            pipe.srem(f"user_jtis:{user_id}", jti)
        await pipe.execute()
    except Exception as exc:
        logger.warning("jti_store.delete_jti failed (non-fatal): %s", exc)


async def delete_all_jtis_for_user(user_id: str) -> None:
    """Remove every live JTI for a user (logout-all-devices).

    Iterates the ``user_jtis:{user_id}`` set and deletes each JTI key,
    then removes the set itself.
    """
    redis = await _get_redis()
    if redis is None:
        return
    try:
        set_key = f"user_jtis:{user_id}"
        jtis = await redis.smembers(set_key)
        if jtis:
            pipe = redis.pipeline()
            for jti in jtis:
                pipe.delete(f"jti:{jti}")
            pipe.delete(set_key)
            await pipe.execute()
        else:
            await redis.delete(set_key)
    except Exception as exc:
        logger.warning("jti_store.delete_all_jtis_for_user failed (non-fatal): %s", exc)
