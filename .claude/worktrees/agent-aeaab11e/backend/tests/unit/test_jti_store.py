"""Unit tests for the Redis-backed JTI revocation store.

Tests cover all four public functions using a mock Redis client so no
real Redis instance is needed.  The key contracts verified:

- store_jti  : writes jti:{jti} and adds to user_jtis:{user_id} set
- verify_jti : returns True when key exists, False when missing
- delete_jti : removes jti key and cleans up secondary index
- delete_all_jtis_for_user : removes every JTI for a user atomically

Failure/degradation paths are also covered:
- Redis unavailable → all functions return gracefully (non-fatal)
- ENFORCE_JTI_REDIS_CHECK=False → all functions are no-ops (dev mode)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── helpers ──────────────────────────────────────────────────────────────────


def _make_redis(exists_return=1, smembers_return=None):
    """Return a mock Redis client with sensible defaults."""
    client = AsyncMock()
    client.exists = AsyncMock(return_value=exists_return)
    client.get = AsyncMock(return_value="user-123")
    client.smembers = AsyncMock(return_value=smembers_return or set())
    pipeline = AsyncMock()
    pipeline.set = MagicMock(return_value=pipeline)
    pipeline.sadd = MagicMock(return_value=pipeline)
    pipeline.expire = MagicMock(return_value=pipeline)
    pipeline.delete = MagicMock(return_value=pipeline)
    pipeline.srem = MagicMock(return_value=pipeline)
    pipeline.execute = AsyncMock(return_value=[True])
    client.pipeline = MagicMock(return_value=pipeline)
    return client, pipeline


# ── store_jti ─────────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestStoreJti:
    @pytest.mark.asyncio
    async def test_stores_jti_key_and_user_index(self):
        """store_jti writes jti:{jti} and adds to user_jtis set."""
        redis, pipe = _make_redis()
        with (
            patch("app.core.jti_store._get_redis", AsyncMock(return_value=redis)),
        ):
            from app.core.jti_store import store_jti

            await store_jti("test-jti-1", "user-abc", 2592000)

        pipe.set.assert_called_once_with("jti:test-jti-1", "user-abc", ex=2592000)
        pipe.sadd.assert_called_once_with("user_jtis:user-abc", "test-jti-1")
        pipe.expire.assert_called_once()
        pipe.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_op_when_redis_unavailable(self):
        """store_jti is a no-op and does not raise when Redis returns None."""
        with patch("app.core.jti_store._get_redis", AsyncMock(return_value=None)):
            from app.core.jti_store import store_jti

            # Should not raise
            await store_jti("jti", "user", 1000)

    @pytest.mark.asyncio
    async def test_non_fatal_on_redis_error(self):
        """store_jti swallows Redis exceptions."""
        redis, pipe = _make_redis()
        pipe.execute = AsyncMock(side_effect=Exception("Redis timeout"))
        with patch("app.core.jti_store._get_redis", AsyncMock(return_value=redis)):
            from app.core.jti_store import store_jti

            await store_jti("jti", "user", 1000)  # Must not raise


# ── verify_jti ────────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestVerifyJti:
    @pytest.mark.asyncio
    async def test_returns_true_when_jti_exists(self):
        redis, _ = _make_redis(exists_return=1)
        with patch("app.core.jti_store._get_redis", AsyncMock(return_value=redis)):
            from app.core.jti_store import verify_jti

            result = await verify_jti("live-jti")

        assert result is True
        redis.exists.assert_called_once_with("jti:live-jti")

    @pytest.mark.asyncio
    async def test_returns_false_when_jti_missing(self):
        redis, _ = _make_redis(exists_return=0)
        with patch("app.core.jti_store._get_redis", AsyncMock(return_value=redis)):
            from app.core.jti_store import verify_jti

            result = await verify_jti("revoked-jti")

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_true_when_redis_unavailable(self):
        """Graceful degradation: allow request when Redis is down."""
        with patch("app.core.jti_store._get_redis", AsyncMock(return_value=None)):
            from app.core.jti_store import verify_jti

            result = await verify_jti("any-jti")

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_true_on_redis_error(self):
        """Redis errors degrade gracefully — DB check is the safety net."""
        redis, _ = _make_redis()
        redis.exists = AsyncMock(side_effect=Exception("connection refused"))
        with patch("app.core.jti_store._get_redis", AsyncMock(return_value=redis)):
            from app.core.jti_store import verify_jti

            result = await verify_jti("jti")

        assert result is True


# ── delete_jti ────────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestDeleteJti:
    @pytest.mark.asyncio
    async def test_deletes_jti_key_and_removes_from_set(self):
        redis, pipe = _make_redis()
        redis.get = AsyncMock(return_value="user-xyz")
        with patch("app.core.jti_store._get_redis", AsyncMock(return_value=redis)):
            from app.core.jti_store import delete_jti

            await delete_jti("logout-jti")

        pipe.delete.assert_any_call("jti:logout-jti")
        pipe.srem.assert_called_once_with("user_jtis:user-xyz", "logout-jti")
        pipe.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_deletes_jti_key_even_if_no_user_in_redis(self):
        """When jti key has expired, still deletes what we can."""
        redis, pipe = _make_redis()
        redis.get = AsyncMock(return_value=None)  # Already expired
        with patch("app.core.jti_store._get_redis", AsyncMock(return_value=redis)):
            from app.core.jti_store import delete_jti

            await delete_jti("expired-jti")

        pipe.delete.assert_called_with("jti:expired-jti")
        pipe.srem.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_op_when_redis_unavailable(self):
        with patch("app.core.jti_store._get_redis", AsyncMock(return_value=None)):
            from app.core.jti_store import delete_jti

            await delete_jti("jti")  # Must not raise

    @pytest.mark.asyncio
    async def test_non_fatal_on_redis_error(self):
        redis, pipe = _make_redis()
        pipe.execute = AsyncMock(side_effect=Exception("Redis down"))
        with patch("app.core.jti_store._get_redis", AsyncMock(return_value=redis)):
            from app.core.jti_store import delete_jti

            await delete_jti("jti")  # Must not raise


# ── delete_all_jtis_for_user ──────────────────────────────────────────────────


@pytest.mark.unit
class TestDeleteAllJtisForUser:
    @pytest.mark.asyncio
    async def test_deletes_all_jtis_for_user(self):
        redis, pipe = _make_redis(smembers_return={"jti-1", "jti-2", "jti-3"})
        with patch("app.core.jti_store._get_redis", AsyncMock(return_value=redis)):
            from app.core.jti_store import delete_all_jtis_for_user

            await delete_all_jtis_for_user("user-abc")

        # Each individual JTI key deleted
        delete_calls = [call[0][0] for call in pipe.delete.call_args_list]
        for jti in ("jti-1", "jti-2", "jti-3"):
            assert f"jti:{jti}" in delete_calls
        # The user set itself deleted
        assert "user_jtis:user-abc" in delete_calls
        pipe.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_jtis_in_set_still_deletes_set(self):
        redis, pipe = _make_redis(smembers_return=set())
        with patch("app.core.jti_store._get_redis", AsyncMock(return_value=redis)):
            from app.core.jti_store import delete_all_jtis_for_user

            await delete_all_jtis_for_user("user-empty")

        redis.delete.assert_called_once_with("user_jtis:user-empty")

    @pytest.mark.asyncio
    async def test_no_op_when_redis_unavailable(self):
        with patch("app.core.jti_store._get_redis", AsyncMock(return_value=None)):
            from app.core.jti_store import delete_all_jtis_for_user

            await delete_all_jtis_for_user("user")  # Must not raise

    @pytest.mark.asyncio
    async def test_non_fatal_on_redis_error(self):
        redis, _ = _make_redis()
        redis.smembers = AsyncMock(side_effect=Exception("timeout"))
        with patch("app.core.jti_store._get_redis", AsyncMock(return_value=redis)):
            from app.core.jti_store import delete_all_jtis_for_user

            await delete_all_jtis_for_user("user")  # Must not raise


# ── dev mode (ENFORCE_JTI_REDIS_CHECK=False) ─────────────────────────────────


@pytest.mark.unit
class TestDevMode:
    """In dev mode ENFORCE_JTI_REDIS_CHECK=False, all operations are no-ops."""

    @pytest.mark.asyncio
    async def test_store_is_noop_in_dev(self):
        with patch("app.core.jti_store._get_redis", AsyncMock(return_value=None)) as mock_get:
            from app.core.jti_store import store_jti

            await store_jti("jti", "user", 1000)
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_returns_true_in_dev(self):
        with patch("app.core.jti_store._get_redis", AsyncMock(return_value=None)):
            from app.core.jti_store import verify_jti

            assert await verify_jti("jti") is True
