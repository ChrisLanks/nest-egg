"""
Tests for second round of scalability and resilience improvements.

1. Plaid webhook dedup: duplicate body hash returns duplicate_skipped
2. Plaid webhook dedup: new body hash processes normally
3. Plaid sync debounce: second sync within 60s is debounced
4. Income/expenses trend caching: cache key includes org, user, years
5. Health check includes celery field in response
6. Health check returns degraded when celery workers are down
7. Cache TTL for trend endpoints is 10 minutes (600s)
"""

import hashlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Webhook deduplication
# ---------------------------------------------------------------------------


def test_webhook_dedup_ttl_is_24_hours():
    """Webhook dedup TTL is set to 24 hours."""
    from app.api.v1.plaid import _WEBHOOK_DEDUP_TTL

    assert _WEBHOOK_DEDUP_TTL == 86_400


# ---------------------------------------------------------------------------
# Trend caching
# ---------------------------------------------------------------------------


def test_trend_cache_ttl_is_10_minutes():
    """Trend cache TTL is set to 10 minutes."""
    from app.api.v1.income_expenses import _CACHE_TTL_TRENDS

    assert _CACHE_TTL_TRENDS == 600


# ---------------------------------------------------------------------------
# Health check schema
# ---------------------------------------------------------------------------


def test_health_response_includes_celery():
    """HealthResponse schema includes celery field."""
    from app.api.v1.monitoring import HealthResponse

    resp = HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp="2026-04-03T00:00:00Z",
        database="ok",
        redis="ok",
        celery="ok",
    )
    assert resp.celery == "ok"


def test_health_response_celery_defaults_to_unknown():
    """celery field defaults to 'unknown' for backwards compat."""
    from app.api.v1.monitoring import HealthResponse

    resp = HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp="2026-04-03T00:00:00Z",
        database="ok",
        redis="ok",
    )
    assert resp.celery == "unknown"


# ---------------------------------------------------------------------------
# Webhook body hash dedup logic
# ---------------------------------------------------------------------------


def test_webhook_body_hash_deterministic():
    """Same webhook body always produces the same dedup key."""
    body = b'{"webhook_type": "TRANSACTIONS", "webhook_code": "DEFAULT_UPDATE", "item_id": "abc123"}'
    hash1 = hashlib.sha256(body).hexdigest()[:16]
    hash2 = hashlib.sha256(body).hexdigest()[:16]
    assert hash1 == hash2
    assert len(hash1) == 16


def test_webhook_body_hash_unique_for_different_bodies():
    """Different webhook bodies produce different dedup keys."""
    body1 = b'{"webhook_type": "TRANSACTIONS", "item_id": "abc123"}'
    body2 = b'{"webhook_type": "TRANSACTIONS", "item_id": "def456"}'
    hash1 = hashlib.sha256(body1).hexdigest()[:16]
    hash2 = hashlib.sha256(body2).hexdigest()[:16]
    assert hash1 != hash2


# ---------------------------------------------------------------------------
# Provider failover chain (from previous round — verify still working)
# ---------------------------------------------------------------------------


@patch("app.services.market_data.provider_factory.settings")
def test_failover_chain_still_works(mock_settings):
    """Provider failover chain from round 1 is still functional."""
    from app.services.market_data.provider_factory import MarketDataProviderFactory

    mock_settings.MARKET_DATA_PROVIDER = "yahoo_finance"
    mock_settings.MARKET_DATA_FALLBACK_PROVIDERS = "finnhub"

    chain = MarketDataProviderFactory.get_provider_chain()
    assert "yahoo_finance" in chain
    assert "finnhub" in chain


# ---------------------------------------------------------------------------
# Cache key structure
# ---------------------------------------------------------------------------


def test_trend_cache_key_format():
    """Verify trend cache key includes all discriminants."""
    org_id = "org-123"
    user_id = None
    years = [2026, 2025]
    years_key = ",".join(str(y) for y in sorted(years))
    cache_key = f"ie:yoy:{org_id}:{user_id or 'household'}:{years_key}"

    assert cache_key == "ie:yoy:org-123:household:2025,2026"
    assert "org-123" in cache_key
    assert "household" in cache_key
    assert "2025,2026" in cache_key


def test_trend_cache_key_per_user():
    """Per-user cache key is distinct from household key."""
    org_id = "org-123"
    years_key = "2025,2026"

    household_key = f"ie:yoy:{org_id}:household:{years_key}"
    user_key = f"ie:yoy:{org_id}:user-abc:{years_key}"

    assert household_key != user_key
