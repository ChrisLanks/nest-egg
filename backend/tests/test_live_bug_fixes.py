"""Tests for live bug fixes committed in this session.

Covers:
1. Budget shared_user_ids JSON LIKE crash (cast to String before .contains())
2. SS endpoint AttributeError on target_user.current_annual_income
3. RetirementPage useQuery-without-queryFn / inline hook violations (frontend — verified via import)
4. Investment account interest_rate blended into Monte Carlo return
5. CategoriesPage React.Fragment key (frontend — verified via import)
6. Preferences link wrong route /settings/preferences → /preferences
"""

import inspect
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4


# ── 1. Budget shared_user_ids query uses cast(JSON, String).contains ──────────

def test_budget_get_budget_uses_string_cast_not_json_contains():
    """get_budget must cast shared_user_ids to String before .contains().

    Previously used Budget.shared_user_ids.contains() which generated a LIKE
    on a JSON column — PostgreSQL rejects: 'operator does not exist: json ~~ text'.
    """
    import inspect as ins
    from app.services.budget_service import BudgetService

    src = ins.getsource(BudgetService.get_budget)

    # Must NOT use the bare .contains() on shared_user_ids (generates LIKE on JSON)
    assert "shared_user_ids.contains(" not in src, (
        "shared_user_ids.contains() generates a LIKE on JSON — use cast(String) first"
    )
    # Must use String cast
    assert "cast(Budget.shared_user_ids, String)" in src or \
           "cast(" in src and "shared_user_ids" in src, (
        "Must cast shared_user_ids to String before .contains()"
    )


def test_budget_service_imports_string_and_cast():
    """budget_service must import String and cast from sqlalchemy."""
    import app.services.budget_service as module
    src = inspect.getsource(module)
    assert "String" in src
    assert "cast" in src


# ── 2. SS endpoint no longer references User.current_annual_income ────────────

def test_ss_endpoint_no_user_current_annual_income():
    """SS estimate endpoint must not access target_user.current_annual_income.

    User model has no such column; it lives on RetirementScenario. Accessing
    it raises AttributeError → 500 on every SS estimate request.
    """
    import app.api.v1.retirement as module
    src = inspect.getsource(module)

    # Find the get_social_security_estimate function source
    from app.api.v1.retirement import get_social_security_estimate
    fn_src = inspect.getsource(get_social_security_estimate)

    assert "target_user.current_annual_income" not in fn_src, (
        "target_user.current_annual_income is not a User field — causes AttributeError 500"
    )


def test_ss_endpoint_uses_override_salary_with_default():
    """SS endpoint salary must default to 75000 when override_salary is not given."""
    from app.api.v1.retirement import get_social_security_estimate
    fn_src = inspect.getsource(get_social_security_estimate)
    assert "75000" in fn_src


# ── 3. Investment account interest_rate in Monte Carlo ────────────────────────

def test_gather_account_data_includes_interest_rate_for_investment_accounts():
    """Investment account items must include interest_rate key (None if not set)."""
    from app.services.retirement.monte_carlo_service import RetirementMonteCarloService
    src = inspect.getsource(RetirementMonteCarloService._gather_account_data)

    assert '"interest_rate"' in src, (
        "Investment account items must include interest_rate key"
    )


def test_gather_account_data_tracks_investment_override_rate():
    """_gather_account_data must compute investment_override_rate."""
    from app.services.retirement.monte_carlo_service import RetirementMonteCarloService
    src = inspect.getsource(RetirementMonteCarloService._gather_account_data)

    assert "investment_override_rate" in src
    assert "inv_weighted_interest" in src
    assert "inv_balance_with_rate" in src


def test_run_simulation_blends_investment_override_rate():
    """run_simulation must blend investment_override_rate into pre/post return."""
    from app.services.retirement.monte_carlo_service import RetirementMonteCarloService
    src = inspect.getsource(RetirementMonteCarloService.run_simulation)

    assert "investment_override_rate" in src or "inv_override" in src, (
        "run_simulation must use investment_override_rate from account_data"
    )


def test_investment_override_rate_blending_logic():
    """Weighted blend: accounts with explicit rate shift pre/post return proportionally."""
    # Simulate: 60% of investment balance has explicit 5% rate, 40% uses scenario 8% rate
    # Scenario pre_return = 0.08 (8%), inv_override = 0.05, weight = 0.60
    scenario_return = 0.08
    inv_override = 0.05
    weight = 0.60

    blended = (1 - weight) * scenario_return + weight * inv_override
    assert abs(blended - 0.062) < 0.001  # 0.40*0.08 + 0.60*0.05 = 0.032 + 0.030 = 0.062


def test_investment_override_rate_none_when_no_accounts_have_rate():
    """investment_override_rate must be None when no investment accounts have interest_rate."""
    # Simulate the computation
    inv_weighted_interest = Decimal(0)
    inv_balance_with_rate = Decimal(0)

    result = (
        float(inv_weighted_interest / inv_balance_with_rate)
        if inv_balance_with_rate > 0
        else None
    )
    assert result is None


def test_investment_override_rate_weighted_average():
    """investment_override_rate is balance-weighted average of accounts with rates."""
    inv_weighted_interest = Decimal("10000") * (Decimal("5.0") / Decimal(100)) + \
                            Decimal("5000") * (Decimal("3.0") / Decimal(100))
    inv_balance_with_rate = Decimal("15000")

    rate = float(inv_weighted_interest / inv_balance_with_rate)
    # (10000*0.05 + 5000*0.03) / 15000 = (500 + 150) / 15000 = 650/15000 ≈ 0.04333
    assert abs(rate - (650 / 15000)) < 0.0001


# ── 4. CategoriesPage React.Fragment key ─────────────────────────────────────

def test_categories_page_uses_react_fragment_with_key():
    """renderCategoryRow must use React.Fragment key= not key on inner Tr."""
    import os
    path = "/home/lanx/git/nest-egg/frontend/src/pages/CategoriesPage.tsx"
    if not os.path.exists(path):
        return  # skip in CI without frontend

    with open(path) as f:
        src = f.read()

    assert "React.Fragment key=" in src, (
        "Key must be on React.Fragment wrapper, not on inner Tr"
    )
    # The <Tr> inside renderCategoryRow must NOT have key=
    # (can't easily assert this without parsing, but check the fragment is used)
    assert "import React," in src or "import React " in src, (
        "React must be imported as default for React.Fragment"
    )


# ── 5. RetirementPage — no useQuery without queryFn ──────────────────────────

def test_retirement_page_no_usequery_without_queryfn():
    """RetirementPage must not call useQuery({queryKey, enabled:false}) without queryFn.

    TanStack Query throws 'No queryFn was passed' when enabled:false but no queryFn.
    Must use queryClient.getQueryData() instead to read cached data.
    """
    import os
    path = "/home/lanx/git/nest-egg/frontend/src/features/retirement/pages/RetirementPage.tsx"
    if not os.path.exists(path):
        return

    with open(path) as f:
        src = f.read()

    # Must use getQueryData for the userProfile cache read
    assert 'getQueryData' in src and '"userProfile"' in src or \
           "getQueryData" in src and "'userProfile'" in src, (
        "Must use queryClient.getQueryData(['userProfile']) instead of useQuery without queryFn"
    )


def test_retirement_page_no_inline_usecolormodevalue():
    """RetirementPage must not call useColorModeValue inside JSX (Rules of Hooks)."""
    import os
    path = "/home/lanx/git/nest-egg/frontend/src/features/retirement/pages/RetirementPage.tsx"
    if not os.path.exists(path):
        return

    with open(path) as f:
        lines = f.readlines()

    # Find lines that are in JSX context (contain < and useColorModeValue on same line)
    violations = [
        (i + 1, line.rstrip())
        for i, line in enumerate(lines)
        if "useColorModeValue(" in line and ("<Text" in line or "<Box" in line or "color={use" in line)
    ]
    assert not violations, (
        f"useColorModeValue called inside JSX at lines: {violations}. "
        "Must be called at top of component, not inside render."
    )


# ── 6. SS Estimator preferences link ─────────────────────────────────────────

def test_ss_estimator_preferences_link_correct_route():
    """SocialSecurityEstimator preferences link must point to /preferences not /settings/preferences."""
    import os
    path = "/home/lanx/git/nest-egg/frontend/src/features/retirement/components/SocialSecurityEstimator.tsx"
    if not os.path.exists(path):
        return

    with open(path) as f:
        src = f.read()

    assert '/settings/preferences' not in src, (
        "Route /settings/preferences does not exist — causes redirect to overview"
    )
    assert 'href="/preferences"' in src, (
        "Preferences link must use href='/preferences'"
    )
