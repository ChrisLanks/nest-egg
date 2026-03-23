"""Tests for PM audit round 11 fixes.

Covers:
- Scenario hash now includes spouse SS fields, capital_gains_rate, current_annual_income
  so that cached simulation results are properly invalidated when these fields change.
"""

import hashlib
from unittest.mock import MagicMock


def _make_scenario(**overrides):
    """Build a minimal mock RetirementScenario for hash testing."""
    s = MagicMock()
    s.retirement_age = 65
    s.life_expectancy = 90
    s.annual_spending_retirement = 60000
    s.pre_retirement_return = 7.0
    s.post_retirement_return = 5.0
    s.volatility = 12.0
    s.inflation_rate = 3.0
    s.medical_inflation_rate = 5.0
    s.social_security_monthly = 2000
    s.social_security_start_age = 67
    s.use_estimated_pia = False
    s.current_annual_income = 100000
    s.spouse_social_security_monthly = None
    s.spouse_social_security_start_age = None
    s.withdrawal_strategy = "proportional"
    s.withdrawal_rate = 4.0
    s.federal_tax_rate = 22.0
    s.state_tax_rate = 5.0
    s.capital_gains_rate = 15.0
    s.num_simulations = 1000
    s.distribution_type = "normal"
    s.healthcare_pre65_override = None
    s.healthcare_medicare_override = None
    s.healthcare_ltc_override = None
    s.spending_phases = []
    s.include_all_members = False
    s.household_member_ids = None
    s.household_member_hash = None
    s.life_events = []
    for k, v in overrides.items():
        setattr(s, k, v)
    return s


def _hash(scenario):
    from app.services.retirement.monte_carlo_service import _compute_scenario_hash
    return _compute_scenario_hash(scenario)


# ---------------------------------------------------------------------------
# Fields included in hash
# ---------------------------------------------------------------------------


def test_hash_changes_on_spouse_ss_monthly():
    """Changing spouse_social_security_monthly must produce a different hash."""
    s1 = _make_scenario(spouse_social_security_monthly=None)
    s2 = _make_scenario(spouse_social_security_monthly=800)
    assert _hash(s1) != _hash(s2), (
        "spouse_social_security_monthly must be part of the scenario hash"
    )


def test_hash_changes_on_spouse_ss_start_age():
    """Changing spouse_social_security_start_age must produce a different hash."""
    s1 = _make_scenario(spouse_social_security_start_age=None)
    s2 = _make_scenario(spouse_social_security_start_age=62)
    assert _hash(s1) != _hash(s2), (
        "spouse_social_security_start_age must be part of the scenario hash"
    )


def test_hash_changes_on_capital_gains_rate():
    """Changing capital_gains_rate must produce a different hash."""
    s1 = _make_scenario(capital_gains_rate=15.0)
    s2 = _make_scenario(capital_gains_rate=20.0)
    assert _hash(s1) != _hash(s2), (
        "capital_gains_rate must be part of the scenario hash"
    )


def test_hash_changes_on_current_annual_income():
    """Changing current_annual_income must produce a different hash.

    This field drives estimated PIA when use_estimated_pia=True.
    """
    s1 = _make_scenario(current_annual_income=100000)
    s2 = _make_scenario(current_annual_income=120000)
    assert _hash(s1) != _hash(s2), (
        "current_annual_income must be part of the scenario hash (affects estimated PIA)"
    )


def test_hash_stable_for_identical_scenarios():
    """Two identical scenarios must produce the same hash."""
    s1 = _make_scenario()
    s2 = _make_scenario()
    assert _hash(s1) == _hash(s2)


def test_hash_changes_on_retirement_age():
    """Sanity: existing field (retirement_age) still changes the hash."""
    s1 = _make_scenario(retirement_age=65)
    s2 = _make_scenario(retirement_age=62)
    assert _hash(s1) != _hash(s2)


def test_hash_returns_hex_string():
    """Hash must be a 64-char hex string (SHA-256)."""
    h = _hash(_make_scenario())
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


def test_hash_includes_all_expected_fields():
    """Spot-check source: all four previously-missing fields are now in _compute_scenario_hash."""
    import inspect
    from app.services.retirement import monte_carlo_service

    source = inspect.getsource(monte_carlo_service._compute_scenario_hash)
    for field in [
        "spouse_social_security_monthly",
        "spouse_social_security_start_age",
        "capital_gains_rate",
        "current_annual_income",
    ]:
        assert field in source, (
            f"_compute_scenario_hash must include scenario.{field}"
        )
