"""Tests for life event presets.

Covers:
- Preset listing
- Preset creation with correct fields
- Invalid preset handling
- Cost and duration defaults
"""

import pytest
from app.services.retirement.life_event_presets import (
    LIFE_EVENT_PRESETS,
    create_life_event_from_preset,
    get_all_presets,
)


# ── get_all_presets ───────────────────────────────────────────────────────────


class TestGetAllPresets:
    def test_returns_all_presets(self):
        presets = get_all_presets()
        assert len(presets) == len(LIFE_EVENT_PRESETS)

    def test_has_required_fields(self):
        presets = get_all_presets()
        for preset in presets:
            assert "key" in preset
            assert "name" in preset
            assert "category" in preset
            assert "description" in preset
            assert isinstance(preset["key"], str)
            assert isinstance(preset["name"], str)

    def test_costs_are_float_or_none(self):
        presets = get_all_presets()
        for preset in presets:
            for field in ("annual_cost", "one_time_cost", "income_change"):
                val = preset[field]
                assert val is None or isinstance(val, float), (
                    f"Preset {preset['key']} {field} = {val} ({type(val)})"
                )

    def test_known_preset_values(self):
        """Spot-check a few known presets."""
        presets = {p["key"]: p for p in get_all_presets()}

        assert presets["child_daycare"]["annual_cost"] == 15000
        assert presets["child_college_public"]["annual_cost"] == 25000
        assert presets["child_college_private"]["annual_cost"] == 60000
        assert presets["home_purchase"]["one_time_cost"] == 100000
        assert presets["vehicle_replacement"]["one_time_cost"] == 35000
        assert presets["elder_care_parent"]["annual_cost"] == 25000

    def test_medical_inflation_flag(self):
        presets = {p["key"]: p for p in get_all_presets()}
        # Healthcare presets should use medical inflation
        assert presets["healthcare_pre65"]["use_medical_inflation"] is True
        assert presets["healthcare_ltc"]["use_medical_inflation"] is True
        # Non-medical presets should not
        assert presets["child_daycare"]["use_medical_inflation"] is False
        assert presets["travel_moderate"]["use_medical_inflation"] is False


# ── create_life_event_from_preset ─────────────────────────────────────────────


class TestCreateLifeEventFromPreset:
    def test_valid_preset(self):
        event = create_life_event_from_preset("child_daycare", start_age=35)
        assert event is not None
        assert event["name"] == "Child - Daycare"
        assert event["start_age"] == 35
        assert event["end_age"] == 40  # 35 + 5 years
        assert event["is_preset"] is True
        assert event["preset_key"] == "child_daycare"

    def test_invalid_preset_returns_none(self):
        assert create_life_event_from_preset("nonexistent_preset", start_age=35) is None

    def test_one_time_cost_no_end_age(self):
        """One-time events (no duration) should have no end_age."""
        event = create_life_event_from_preset("home_purchase", start_age=40)
        assert event is not None
        assert event["one_time_cost"] is not None
        assert event["end_age"] is None

    def test_end_age_override(self):
        event = create_life_event_from_preset("child_daycare", start_age=35, end_age_override=38)
        assert event["end_age"] == 38

    def test_income_change_event(self):
        event = create_life_event_from_preset("home_downsize", start_age=70)
        assert event is not None
        assert event["income_change"] is not None

    def test_category_set(self):
        event = create_life_event_from_preset("travel_moderate", start_age=65)
        assert event["category"] is not None

    def test_all_presets_create_successfully(self):
        """Every preset in the registry should create a valid event."""
        for key in LIFE_EVENT_PRESETS:
            event = create_life_event_from_preset(key, start_age=65)
            assert event is not None, f"Preset {key} failed to create"
            assert event["name"], f"Preset {key} has no name"
            assert event["start_age"] == 65

    def test_permanent_event_no_end_age(self):
        """Career raise has duration_years=None → no end_age."""
        event = create_life_event_from_preset("career_raise", start_age=40)
        assert event is not None
        assert event["end_age"] is None
