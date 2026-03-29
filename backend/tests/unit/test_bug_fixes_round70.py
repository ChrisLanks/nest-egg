"""Round 70 bug fix tests: imprecise age calculation."""

from datetime import date


class TestCalculateAgeCorrectness:
    """Ensure calculate_age is used instead of days//365 in age-gated logic."""

    def test_calculate_age_birthday_today(self):
        """Age on exact birthday should be exact year."""
        from app.utils.rmd_calculator import calculate_age

        birthdate = date(1960, 6, 15)
        as_of = date(2026, 6, 15)
        assert calculate_age(birthdate, as_of_date=as_of) == 66

    def test_calculate_age_day_before_birthday(self):
        """Age day before birthday should still be previous year."""
        from app.utils.rmd_calculator import calculate_age

        birthdate = date(1960, 6, 15)
        as_of = date(2026, 6, 14)
        assert calculate_age(birthdate, as_of_date=as_of) == 65

    def test_calculate_age_day_after_birthday(self):
        """Age day after birthday should be new year."""
        from app.utils.rmd_calculator import calculate_age

        birthdate = date(1960, 6, 15)
        as_of = date(2026, 6, 16)
        assert calculate_age(birthdate, as_of_date=as_of) == 66

    def test_days_365_formula_wrong_near_birthday(self):
        """Demonstrate that days//365 gives wrong answer near birthday boundaries."""
        birthdate = date(1961, 12, 31)
        # Day before 65th birthday - should be 64
        as_of = date(2026, 12, 30)

        # Wrong formula (days // 365) - can give 65 when person is still 64
        days_formula = (as_of - birthdate).days // 365

        from app.utils.rmd_calculator import calculate_age

        correct_age = calculate_age(birthdate, as_of_date=as_of)

        assert correct_age == 64
        # The days formula gives 65 (wrong) due to leap years
        assert days_formula == 65  # documents the bug we fixed

    def test_calculate_age_leap_year_birthday(self):
        """Age calculation correct for Feb 29 birthdays."""
        from app.utils.rmd_calculator import calculate_age

        birthdate = date(1960, 2, 29)
        # Non-leap year: birthday doesn't occur, so still previous age on Feb 28
        as_of = date(2026, 2, 28)
        assert calculate_age(birthdate, as_of_date=as_of) == 65

        # Non-leap year: March 1 is after Feb 28/29, so birthday has "passed"
        as_of = date(2026, 3, 1)
        assert calculate_age(birthdate, as_of_date=as_of) == 66


class TestSmartInsightsServiceUsesCalculateAge:
    """Verify smart_insights_service.py imports and uses calculate_age."""

    def test_calculate_age_imported(self):
        import inspect

        import app.services.smart_insights_service as svc

        src = inspect.getsource(svc)
        assert "from app.utils.rmd_calculator import calculate_age" in src

    def test_no_days_365_age_calc(self):
        """No imprecise .days // 365 age calculations should remain."""
        import inspect

        import app.services.smart_insights_service as svc

        src = inspect.getsource(svc)
        assert ".days // 365" not in src

    def test_smart_insights_api_no_days_365(self):
        import inspect

        import app.api.v1.smart_insights as api

        src = inspect.getsource(api)
        assert ".days // 365" not in src

    def test_savings_goals_no_days_365(self):
        import inspect

        import app.api.v1.savings_goals as api

        src = inspect.getsource(api)
        assert ".days // 365" not in src
        assert ".days / 365" not in src


class TestSavingsGoalsTargetAge:
    """Verify savings_goals uses calculate_age(birthdate, as_of_date=target_date)."""

    def test_target_age_uses_calculate_age(self):
        import inspect

        import app.api.v1.savings_goals as api

        src = inspect.getsource(api)
        assert "calculate_age(current_user.birthdate, as_of_date=goal.target_date)" in src
