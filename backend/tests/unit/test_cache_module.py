"""Tests for app.core.cache module."""

import json
from unittest.mock import AsyncMock, patch

import pytest


class TestCacheGet:
    """Tests for the cache get function."""

    @pytest.mark.asyncio
    async def test_returns_none_when_no_redis_client(self):
        with patch("app.core.cache.redis_client", None):
            from app.core.cache import get

            result = await get("some_key")
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_parsed_json_on_hit(self):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value='{"foo": "bar"}')
        with patch("app.core.cache.redis_client", mock_client):
            from app.core.cache import get

            result = await get("some_key")
            assert result == {"foo": "bar"}
            mock_client.get.assert_called_once_with("some_key")

    @pytest.mark.asyncio
    async def test_returns_none_on_cache_miss(self):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=None)
        with patch("app.core.cache.redis_client", mock_client):
            from app.core.cache import get

            result = await get("missing_key")
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_exception(self):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("Redis down"))
        with patch("app.core.cache.redis_client", mock_client):
            from app.core.cache import get

            result = await get("some_key")
            assert result is None


class TestCacheSetex:
    """Tests for the cache setex function."""

    @pytest.mark.asyncio
    async def test_returns_false_when_no_redis_client(self):
        with patch("app.core.cache.redis_client", None):
            from app.core.cache import setex

            result = await setex("key", 60, {"data": 1})
            assert result is False

    @pytest.mark.asyncio
    async def test_returns_true_on_success(self):
        mock_client = AsyncMock()
        mock_client.setex = AsyncMock()
        with patch("app.core.cache.redis_client", mock_client):
            from app.core.cache import setex

            result = await setex("key", 300, {"data": "value"})
            assert result is True
            mock_client.setex.assert_called_once_with("key", 300, json.dumps({"data": "value"}))

    @pytest.mark.asyncio
    async def test_returns_false_on_exception(self):
        mock_client = AsyncMock()
        mock_client.setex = AsyncMock(side_effect=Exception("Redis error"))
        with patch("app.core.cache.redis_client", mock_client):
            from app.core.cache import setex

            result = await setex("key", 60, "val")
            assert result is False
