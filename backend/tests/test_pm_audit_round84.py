"""
PM Audit Round 84 — Rate limits on remaining analytics routers + response model fixes.

Changes covered:
1. gift_tracker.py: router-level Depends(_rate_limit) — covers all 4 endpoints
2. tax_equiv_yield.py: router-level Depends(_rate_limit)
3. contribution_headroom.py: router-level Depends(_rate_limit)
4. calculator_prefill.py: router-level Depends(_rate_limit) + PrefillResponse model
5. credit_scores.py: router-level Depends(_rate_limit)
6. dividend_calendar.py: router-level Depends(_rate_limit)
7. market_data.py: Dict[str, QuoteResponse] for batch; HoldingRefreshResponse and
   HoldingRefreshAllResponse for the two refresh endpoints
"""

import inspect


# ---------------------------------------------------------------------------
# 1. gift_tracker.py — router-level rate limit
# ---------------------------------------------------------------------------

def test_gift_tracker_has_rate_limit():
    import app.api.v1.gift_tracker as mod
    src = inspect.getsource(mod)
    assert "rate_limit_service" in src
    assert "_rate_limit" in src


def test_gift_tracker_router_uses_rate_limit_dependency():
    import app.api.v1.gift_tracker as mod
    src = inspect.getsource(mod)
    assert 'dependencies=[Depends(_rate_limit)]' in src


def test_gift_tracker_rate_limit_uses_user_id():
    import app.api.v1.gift_tracker as mod
    src = inspect.getsource(mod._rate_limit)
    assert "current_user.id" in src


# ---------------------------------------------------------------------------
# 2. tax_equiv_yield.py — router-level rate limit
# ---------------------------------------------------------------------------

def test_tax_equiv_yield_router_uses_rate_limit_dependency():
    import app.api.v1.tax_equiv_yield as mod
    src = inspect.getsource(mod)
    assert 'dependencies=[Depends(_rate_limit)]' in src


# ---------------------------------------------------------------------------
# 3. contribution_headroom.py — router-level rate limit
# ---------------------------------------------------------------------------

def test_contribution_headroom_router_uses_rate_limit_dependency():
    import app.api.v1.contribution_headroom as mod
    src = inspect.getsource(mod)
    assert 'dependencies=[Depends(_rate_limit)]' in src


# ---------------------------------------------------------------------------
# 4. calculator_prefill.py — router-level rate limit + PrefillResponse
# ---------------------------------------------------------------------------

def test_calculator_prefill_router_uses_rate_limit_dependency():
    import app.api.v1.calculator_prefill as mod
    src = inspect.getsource(mod)
    assert 'dependencies=[Depends(_rate_limit)]' in src


def test_calculator_prefill_has_prefill_response_model():
    from app.api.v1.calculator_prefill import PrefillResponse
    assert hasattr(PrefillResponse, 'model_fields')
    assert 'calculator' in PrefillResponse.model_fields
    assert 'prefilled' in PrefillResponse.model_fields
    assert 'values' in PrefillResponse.model_fields
    assert 'note' in PrefillResponse.model_fields


def test_calculator_prefill_endpoint_has_response_model():
    import app.api.v1.calculator_prefill as mod
    src = inspect.getsource(mod)
    assert 'response_model=PrefillResponse' in src


# ---------------------------------------------------------------------------
# 5. credit_scores.py — router-level rate limit
# ---------------------------------------------------------------------------

def test_credit_scores_router_uses_rate_limit_dependency():
    import app.api.v1.credit_scores as mod
    src = inspect.getsource(mod)
    assert 'dependencies=[Depends(_rate_limit)]' in src


# ---------------------------------------------------------------------------
# 6. dividend_calendar.py — router-level rate limit
# ---------------------------------------------------------------------------

def test_dividend_calendar_router_uses_rate_limit_dependency():
    import app.api.v1.dividend_calendar as mod
    src = inspect.getsource(mod)
    assert 'dependencies=[Depends(_rate_limit)]' in src


# ---------------------------------------------------------------------------
# 7. market_data.py — typed response models
# ---------------------------------------------------------------------------

def test_market_data_batch_uses_typed_response_model():
    import app.api.v1.market_data as mod
    src = inspect.getsource(mod)
    assert 'response_model=Dict[str, QuoteResponse]' in src


def test_market_data_has_holding_refresh_response():
    from app.api.v1.market_data import HoldingRefreshResponse
    assert hasattr(HoldingRefreshResponse, 'model_fields')
    assert 'id' in HoldingRefreshResponse.model_fields
    assert 'current_price' in HoldingRefreshResponse.model_fields
    assert 'provider' in HoldingRefreshResponse.model_fields


def test_market_data_has_holding_refresh_all_response():
    from app.api.v1.market_data import HoldingRefreshAllResponse
    assert hasattr(HoldingRefreshAllResponse, 'model_fields')
    assert 'updated' in HoldingRefreshAllResponse.model_fields
    assert 'total' in HoldingRefreshAllResponse.model_fields
    assert 'provider' in HoldingRefreshAllResponse.model_fields


def test_market_data_refresh_price_endpoint_has_response_model():
    import app.api.v1.market_data as mod
    src = inspect.getsource(mod)
    assert 'response_model=HoldingRefreshResponse' in src


def test_market_data_refresh_all_endpoint_has_response_model():
    import app.api.v1.market_data as mod
    src = inspect.getsource(mod)
    assert 'response_model=HoldingRefreshAllResponse' in src
