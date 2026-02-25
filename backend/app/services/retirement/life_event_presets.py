"""Life event preset definitions for retirement planning.

Each preset provides sensible default values that users can customize.
"""

from decimal import Decimal
from typing import Optional

from app.models.retirement import LifeEventCategory


# Preset definitions: key -> preset config
LIFE_EVENT_PRESETS: dict[str, dict] = {
    # --- Children ---
    "child_daycare": {
        "name": "Child - Daycare",
        "category": LifeEventCategory.CHILD,
        "description": "Daycare/preschool costs for ages 0-5",
        "annual_cost": Decimal("15000"),
        "duration_years": 5,
        "use_medical_inflation": False,
        "icon": "baby",
    },
    "child_activities": {
        "name": "Child - Activities & School",
        "category": LifeEventCategory.CHILD,
        "description": "Sports, activities, school expenses ages 5-18",
        "annual_cost": Decimal("5000"),
        "duration_years": 13,
        "use_medical_inflation": False,
        "icon": "school",
    },
    "child_college_public": {
        "name": "Child - College (Public)",
        "category": LifeEventCategory.CHILD,
        "description": "In-state public university tuition + room & board",
        "annual_cost": Decimal("25000"),
        "duration_years": 4,
        "use_medical_inflation": False,
        "icon": "graduation",
    },
    "child_college_private": {
        "name": "Child - College (Private)",
        "category": LifeEventCategory.CHILD,
        "description": "Private university tuition + room & board",
        "annual_cost": Decimal("60000"),
        "duration_years": 4,
        "use_medical_inflation": False,
        "icon": "graduation",
    },
    # --- Pets ---
    "pet_dog": {
        "name": "Dog",
        "category": LifeEventCategory.PET,
        "description": "Annual dog ownership costs (food, vet, grooming)",
        "annual_cost": Decimal("3000"),
        "duration_years": 12,
        "use_medical_inflation": False,
        "icon": "dog",
    },
    "pet_cat": {
        "name": "Cat",
        "category": LifeEventCategory.PET,
        "description": "Annual cat ownership costs (food, vet, litter)",
        "annual_cost": Decimal("1500"),
        "duration_years": 15,
        "use_medical_inflation": False,
        "icon": "cat",
    },
    # --- Home ---
    "home_purchase": {
        "name": "Home Purchase",
        "category": LifeEventCategory.HOME_PURCHASE,
        "description": "Down payment and closing costs for home purchase",
        "one_time_cost": Decimal("100000"),
        "use_medical_inflation": False,
        "icon": "home",
    },
    "home_renovation": {
        "name": "Major Home Renovation",
        "category": LifeEventCategory.HOME_PURCHASE,
        "description": "Kitchen, bathroom, or whole-home renovation",
        "one_time_cost": Decimal("50000"),
        "use_medical_inflation": False,
        "icon": "hammer",
    },
    "home_downsize": {
        "name": "Home Downsize",
        "category": LifeEventCategory.HOME_DOWNSIZE,
        "description": "Net proceeds from downsizing (reduces costs)",
        "income_change": Decimal("150000"),
        "use_medical_inflation": False,
        "icon": "home_small",
    },
    # --- Career ---
    "career_sabbatical": {
        "name": "Sabbatical / Career Break",
        "category": LifeEventCategory.CAREER_CHANGE,
        "description": "Year without income for sabbatical or career change",
        "income_change": Decimal("-50000"),
        "duration_years": 1,
        "use_medical_inflation": False,
        "icon": "briefcase",
    },
    "career_raise": {
        "name": "Expected Raise / Promotion",
        "category": LifeEventCategory.BONUS,
        "description": "Anticipated salary increase",
        "income_change": Decimal("20000"),
        "duration_years": None,  # Permanent
        "use_medical_inflation": False,
        "icon": "trending_up",
    },
    "one_time_bonus": {
        "name": "One-Time Bonus / Windfall",
        "category": LifeEventCategory.BONUS,
        "description": "One-time bonus, inheritance, or windfall",
        "income_change": Decimal("50000"),
        "use_medical_inflation": False,
        "icon": "cash",
    },
    # --- Healthcare ---
    "healthcare_pre65": {
        "name": "Pre-65 Health Insurance",
        "category": LifeEventCategory.HEALTHCARE,
        "description": "ACA marketplace insurance before Medicare eligibility",
        "annual_cost": Decimal("7200"),
        "use_medical_inflation": True,
        "icon": "hospital",
    },
    "healthcare_ltc": {
        "name": "Long-Term Care",
        "category": LifeEventCategory.HEALTHCARE,
        "description": "Long-term care costs (home care + facility)",
        "annual_cost": Decimal("60000"),
        "duration_years": 3,
        "use_medical_inflation": True,
        "icon": "medical",
    },
    "healthcare_major_procedure": {
        "name": "Major Medical Procedure",
        "category": LifeEventCategory.HEALTHCARE,
        "description": "Surgery, dental work, or other major procedure",
        "one_time_cost": Decimal("15000"),
        "use_medical_inflation": True,
        "icon": "hospital",
    },
    # --- Travel ---
    "travel_moderate": {
        "name": "Annual Travel Budget",
        "category": LifeEventCategory.TRAVEL,
        "description": "Moderate annual travel (domestic + occasional international)",
        "annual_cost": Decimal("10000"),
        "use_medical_inflation": False,
        "icon": "plane",
    },
    "travel_premium": {
        "name": "Premium Travel Budget",
        "category": LifeEventCategory.TRAVEL,
        "description": "Premium travel with international destinations",
        "annual_cost": Decimal("25000"),
        "use_medical_inflation": False,
        "icon": "globe",
    },
    # --- Vehicles ---
    "vehicle_replacement": {
        "name": "Vehicle Replacement",
        "category": LifeEventCategory.VEHICLE,
        "description": "New or used vehicle purchase",
        "one_time_cost": Decimal("35000"),
        "use_medical_inflation": False,
        "icon": "car",
    },
    "vehicle_annual": {
        "name": "Vehicle Expenses",
        "category": LifeEventCategory.VEHICLE,
        "description": "Insurance, maintenance, fuel, registration",
        "annual_cost": Decimal("5000"),
        "use_medical_inflation": False,
        "icon": "car",
    },
    # --- Elder Care ---
    "elder_care_parent": {
        "name": "Parent Elder Care",
        "category": LifeEventCategory.ELDER_CARE,
        "description": "Financial support for aging parent(s)",
        "annual_cost": Decimal("25000"),
        "duration_years": 5,
        "use_medical_inflation": True,
        "icon": "elderly",
    },
}


def get_all_presets() -> list[dict]:
    """Return all presets formatted for the API response."""
    presets = []
    for key, config in LIFE_EVENT_PRESETS.items():
        presets.append({
            "key": key,
            "name": config["name"],
            "category": config["category"].value,
            "description": config["description"],
            "annual_cost": float(config.get("annual_cost") or 0) or None,
            "one_time_cost": float(config.get("one_time_cost") or 0) or None,
            "income_change": float(config.get("income_change") or 0) or None,
            "duration_years": config.get("duration_years"),
            "use_medical_inflation": config.get("use_medical_inflation", False),
            "icon": config.get("icon", "event"),
        })
    return presets


def create_life_event_from_preset(
    preset_key: str,
    start_age: int,
    end_age_override: Optional[int] = None,
) -> Optional[dict]:
    """Create life event data from a preset key.

    Args:
        preset_key: The preset identifier
        start_age: Starting age for the event
        end_age_override: Optional override for end age

    Returns:
        Dict of life event fields suitable for creating a LifeEvent, or None if preset not found.
    """
    preset = LIFE_EVENT_PRESETS.get(preset_key)
    if not preset:
        return None

    duration = preset.get("duration_years")
    end_age = end_age_override
    if end_age is None and duration is not None:
        end_age = start_age + duration

    return {
        "name": preset["name"],
        "category": preset["category"],
        "start_age": start_age,
        "end_age": end_age,
        "annual_cost": preset.get("annual_cost"),
        "one_time_cost": preset.get("one_time_cost"),
        "income_change": preset.get("income_change"),
        "use_medical_inflation": preset.get("use_medical_inflation", False),
        "is_preset": True,
        "preset_key": preset_key,
    }
