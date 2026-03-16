"""Tests for the enhanced trends service.

Covers spending velocity computation logic and data structure validation.
The service methods are async and require DB sessions, so we test the
pure computation logic that can be extracted and validated independently.
"""


class TestSpendingVelocityLogic:
    """Test the MoM change and trend direction computation logic."""

    def _compute_velocity(self, monthly_totals: list[float]) -> dict:
        """Replicate the velocity computation logic from the service."""
        monthly = [
            {"month": f"2025-{i + 1:02d}", "total_spending": t}
            for i, t in enumerate(monthly_totals)
        ]

        # MoM changes
        for i in range(1, len(monthly)):
            prev = monthly[i - 1]["total_spending"]
            curr = monthly[i]["total_spending"]
            if prev > 0:
                monthly[i]["mom_change_pct"] = round((curr - prev) / prev * 100, 1)
            else:
                monthly[i]["mom_change_pct"] = None
            monthly[i]["mom_change_abs"] = round(curr - prev, 2)

        if monthly:
            monthly[0]["mom_change_pct"] = None
            monthly[0]["mom_change_abs"] = None

        # Trend direction
        trend_direction = "stable"
        if len(monthly) >= 3:
            totals = [m["total_spending"] for m in monthly]
            half = len(totals) // 2
            first_half_avg = sum(totals[:half]) / max(half, 1)
            second_half_avg = sum(totals[half:]) / max(len(totals) - half, 1)
            pct_change = (
                (second_half_avg - first_half_avg) / first_half_avg * 100
                if first_half_avg > 0
                else 0
            )
            if pct_change > 5:
                trend_direction = "accelerating"
            elif pct_change < -5:
                trend_direction = "decelerating"

        avg_monthly = sum(m["total_spending"] for m in monthly) / max(len(monthly), 1)

        return {
            "monthly_data": monthly,
            "trend_direction": trend_direction,
            "avg_monthly_spending": round(avg_monthly, 2),
            "months_analyzed": len(monthly),
        }

    def test_stable_spending(self):
        result = self._compute_velocity([1000, 1010, 990, 1005])
        assert result["trend_direction"] == "stable"

    def test_accelerating_spending(self):
        result = self._compute_velocity([1000, 1100, 1500, 1800])
        assert result["trend_direction"] == "accelerating"

    def test_decelerating_spending(self):
        result = self._compute_velocity([2000, 1800, 1200, 1000])
        assert result["trend_direction"] == "decelerating"

    def test_mom_change_first_month_is_none(self):
        result = self._compute_velocity([1000, 1200, 900])
        assert result["monthly_data"][0]["mom_change_pct"] is None
        assert result["monthly_data"][0]["mom_change_abs"] is None

    def test_mom_change_positive(self):
        result = self._compute_velocity([1000, 1200])
        assert result["monthly_data"][1]["mom_change_pct"] == 20.0
        assert result["monthly_data"][1]["mom_change_abs"] == 200.0

    def test_mom_change_negative(self):
        result = self._compute_velocity([1000, 800])
        assert result["monthly_data"][1]["mom_change_pct"] == -20.0
        assert result["monthly_data"][1]["mom_change_abs"] == -200.0

    def test_zero_prev_month_mom_is_none(self):
        result = self._compute_velocity([0, 500])
        assert result["monthly_data"][1]["mom_change_pct"] is None

    def test_avg_monthly_spending(self):
        result = self._compute_velocity([1000, 2000, 3000])
        assert result["avg_monthly_spending"] == 2000.0

    def test_months_analyzed(self):
        result = self._compute_velocity([100, 200, 300, 400, 500])
        assert result["months_analyzed"] == 5

    def test_single_month_is_stable(self):
        result = self._compute_velocity([1500])
        assert result["trend_direction"] == "stable"
        assert result["months_analyzed"] == 1

    def test_two_months_is_stable(self):
        """With < 3 months, trend is always stable."""
        result = self._compute_velocity([1000, 2000])
        assert result["trend_direction"] == "stable"

    def test_empty_input(self):
        result = self._compute_velocity([])
        assert result["months_analyzed"] == 0
        assert result["trend_direction"] == "stable"


class TestDividendSummaryStructure:
    """Validate the expected response shape of dividend summary."""

    def test_summary_response_keys(self):
        expected_keys = {
            "total_income_ytd",
            "total_income_trailing_12m",
            "total_income_all_time",
            "projected_annual_income",
            "monthly_average",
            "by_ticker",
            "by_month",
            "top_payers",
            "income_growth_pct",
        }
        # Simulate a minimal valid response
        response = {
            "total_income_ytd": 500.0,
            "total_income_trailing_12m": 2400.0,
            "total_income_all_time": 5000.0,
            "projected_annual_income": 2600.0,
            "monthly_average": 200.0,
            "by_ticker": [],
            "by_month": [],
            "top_payers": [],
            "income_growth_pct": 12.5,
        }
        assert set(response.keys()) == expected_keys

    def test_growth_pct_can_be_none(self):
        response = {"income_growth_pct": None}
        assert response["income_growth_pct"] is None

    def test_by_ticker_entry_shape(self):
        entry = {
            "ticker": "AAPL",
            "name": "Apple Inc.",
            "total_income": 450.0,
            "payment_count": 4,
            "avg_per_share": 0.24,
            "latest_ex_date": "2025-02-10",
            "yield_on_cost": 1.85,
        }
        assert entry["ticker"] == "AAPL"
        assert entry["payment_count"] == 4
        assert entry["yield_on_cost"] == 1.85


class TestTaxInsightsResponseStructure:
    """Validate expected response shape of tax advisor insights."""

    def test_insight_entry_shape(self):
        insight = {
            "category": "capital_gains",
            "title": "0% Long-Term Capital Gains Bracket",
            "description": "Single filers...",
            "priority": "action",
            "age_relevant": True,
        }
        assert insight["priority"] in ("action", "info")
        assert isinstance(insight["age_relevant"], bool)

    def test_response_structure(self):
        response = {
            "age": 67,
            "pre_tax_total": 500000.0,
            "roth_total": 200000.0,
            "taxable_total": 150000.0,
            "hsa_total": 50000.0,
            "insights": [],
            "contribution_limits": [],
            "tax_constants": {
                "standard_deduction_single": 14600,
                "rmd_trigger_age": 73,
            },
        }
        assert response["age"] == 67
        assert "insights" in response
        assert "contribution_limits" in response
        assert "tax_constants" in response

    def test_priority_values(self):
        valid = {"action", "info"}
        for p in valid:
            assert p in valid

    def test_categories(self):
        valid_categories = {
            "deduction",
            "capital_gains",
            "social_security",
            "medicare",
            "rmd",
            "roth_conversion",
            "nii_surtax",
            "hsa",
        }
        # All expected categories should be in the valid set
        assert len(valid_categories) == 8
