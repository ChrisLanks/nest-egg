"""Unit tests for scf_benchmark_service.

Tests all pure functions — no network calls, no filesystem I/O.
"""

import json
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from app.services.scf_benchmark_service import (
    _is_stale,
    _parse_dollar,
    _parse_scf_html,
    _static_fallback,
    age_bucket,
    fidelity_target,
    get_benchmarks,
)


# ===========================================================================
# _is_stale
# ===========================================================================


@pytest.mark.unit
class TestIsStale:
    def test_current_year_is_not_stale(self):
        assert _is_stale(date.today().year) is False

    def test_one_year_old_is_not_stale(self):
        assert _is_stale(date.today().year - 1) is False

    def test_three_years_old_is_not_stale(self):
        assert _is_stale(date.today().year - 3) is False

    def test_four_years_old_is_stale(self):
        assert _is_stale(date.today().year - 4) is True

    def test_ten_years_old_is_stale(self):
        assert _is_stale(date.today().year - 10) is True


# ===========================================================================
# age_bucket
# ===========================================================================


@pytest.mark.unit
class TestAgeBucket:
    def test_under_35(self):
        assert age_bucket(20) == "under 35"
        assert age_bucket(34) == "under 35"

    def test_35_44(self):
        assert age_bucket(35) == "35-44"
        assert age_bucket(44) == "35-44"

    def test_45_54(self):
        assert age_bucket(45) == "45-54"
        assert age_bucket(54) == "45-54"

    def test_55_64(self):
        assert age_bucket(55) == "55-64"
        assert age_bucket(64) == "55-64"

    def test_65_74(self):
        assert age_bucket(65) == "65-74"
        assert age_bucket(74) == "65-74"

    def test_75_plus(self):
        assert age_bucket(75) == "75+"
        assert age_bucket(100) == "75+"


# ===========================================================================
# _parse_dollar
# ===========================================================================


@pytest.mark.unit
class TestParseDollar:
    def test_small_value_scaled_by_thousand(self):
        # 409.9 → 409,900 (SCF tables express values in thousands)
        assert _parse_dollar("409.9") == 409_900

    def test_large_value_not_scaled(self):
        # 500,000 (already in full dollars, above 10k threshold)
        assert _parse_dollar("500,000") == 500_000

    def test_comma_in_thousands_stripped(self):
        result = _parse_dollar("1,234.5")
        # 1234.5 < 10_000 → scaled: 1_234_500
        assert result == 1_234_500

    def test_value_exactly_10000_not_scaled(self):
        # Boundary: value == 10_000 is NOT scaled
        assert _parse_dollar("10000") == 10_000

    def test_invalid_string_returns_zero(self):
        assert _parse_dollar("n/a") == 0.0
        assert _parse_dollar("") == 0.0


# ===========================================================================
# _parse_scf_html
# ===========================================================================


@pytest.mark.unit
class TestParseScfHtml:
    def _make_html(self, rows: dict[str, tuple[str, str]], year: int = 2022) -> str:
        """Build a minimal fake SCF HTML page."""
        rows_html = ""
        for bucket, (median, mean) in rows.items():
            rows_html += f"<tr><td>{bucket}</td><td>{median}</td><td>{mean}</td></tr>\n"
        return f"<html><head><title>SCF {year}</title></head><body>{rows_html}</body></html>"

    def test_extracts_all_six_buckets(self):
        html = self._make_html(
            {
                "under 35": ("50.0", "120.0"),
                "35-44": ("135.0", "370.0"),
                "45-54": ("247.0", "730.0"),
                "55-64": ("364.0", "1030.0"),
                "65-74": ("409.0", "1060.0"),
                "75+": ("335.0", "976.0"),
            }
        )
        median, mean, year = _parse_scf_html(html)
        assert len(median) == 6
        assert "under 35" in median
        assert "75+" in median

    def test_median_and_mean_are_different(self):
        html = self._make_html(
            {
                "under 35": ("50.0", "120.0"),
                "35-44": ("135.0", "370.0"),
                "45-54": ("247.0", "730.0"),
                "55-64": ("364.0", "1030.0"),
                "65-74": ("409.0", "1060.0"),
                "75+": ("335.0", "976.0"),
            }
        )
        median, mean, _ = _parse_scf_html(html)
        assert median["under 35"] != mean["under 35"]

    def test_extracts_survey_year_from_title(self):
        html = self._make_html(
            {
                "under 35": ("50.0", "120.0"),
                "35-44": ("135.0", "370.0"),
                "45-54": ("247.0", "730.0"),
                "55-64": ("364.0", "1030.0"),
                "65-74": ("409.0", "1060.0"),
                "75+": ("335.0", "976.0"),
            },
            year=2025,
        )
        _, _, year = _parse_scf_html(html)
        assert year == 2025

    def test_returns_empty_when_fewer_than_4_buckets(self):
        # Only 3 age buckets — should fail gracefully
        html = self._make_html(
            {
                "under 35": ("50.0", "120.0"),
                "35-44": ("135.0", "370.0"),
                "45-54": ("247.0", "730.0"),
            }
        )
        median, mean, year = _parse_scf_html(html)
        assert median == {}
        assert mean == {}
        assert year == 0

    def test_empty_html_returns_empty(self):
        median, mean, year = _parse_scf_html("")
        assert median == {}
        assert mean == {}
        assert year == 0


# ===========================================================================
# fidelity_target
# ===========================================================================


@pytest.mark.unit
class TestFidelityTarget:
    def test_zero_income_returns_none(self):
        assert fidelity_target(40, 0) is None

    def test_negative_income_returns_none(self):
        assert fidelity_target(40, -50_000) is None

    def test_age_30_returns_1x_salary(self):
        result = fidelity_target(30, 100_000)
        assert result == 100_000  # 1x at age 30

    def test_age_40_returns_3x_salary(self):
        result = fidelity_target(40, 100_000)
        assert result == 300_000  # 3x at age 40

    def test_age_50_returns_6x_salary(self):
        result = fidelity_target(50, 100_000)
        assert result == 600_000  # 6x at age 50

    def test_age_60_returns_8x_salary(self):
        result = fidelity_target(60, 100_000)
        assert result == 800_000  # 8x at age 60

    def test_age_67_returns_10x_salary(self):
        result = fidelity_target(67, 100_000)
        assert result == 1_000_000  # 10x at age 67

    def test_age_25_below_first_milestone_returns_none(self):
        # Before the earliest milestone age, there's no applicable target
        result = fidelity_target(25, 100_000)
        assert result is None

    def test_non_round_income(self):
        result = fidelity_target(40, 85_000)
        assert result == pytest.approx(255_000)  # 3x


# ===========================================================================
# _static_fallback
# ===========================================================================


@pytest.mark.unit
class TestStaticFallback:
    def test_returns_required_keys(self):
        fb = _static_fallback()
        for key in ("survey_year", "scraped_at", "median", "mean", "is_stale", "source"):
            assert key in fb, f"missing key: {key}"

    def test_source_is_static_fallback(self):
        assert _static_fallback()["source"] == "static_fallback"

    def test_median_has_six_age_buckets(self):
        fb = _static_fallback()
        assert len(fb["median"]) == 6

    def test_mean_has_six_age_buckets(self):
        fb = _static_fallback()
        assert len(fb["mean"]) == 6

    def test_survey_year_is_integer(self):
        assert isinstance(_static_fallback()["survey_year"], int)

    def test_is_stale_is_boolean(self):
        assert isinstance(_static_fallback()["is_stale"], bool)


# ===========================================================================
# get_benchmarks — priority logic
# ===========================================================================


@pytest.mark.unit
class TestGetBenchmarks:
    def _fresh_cache(self, year: int | None = None) -> dict:
        y = year or date.today().year
        return {
            "survey_year": y,
            "scraped_at": "2025-01-01T00:00:00+00:00",
            "median": {"under 35": 50_000},
            "mean": {"under 35": 120_000},
        }

    def test_returns_cache_when_fresh(self):
        cache = self._fresh_cache()
        with (
            patch("app.services.scf_benchmark_service._load_cache", return_value=cache),
            patch("app.services.scf_benchmark_service._scrape") as mock_scrape,
        ):
            result = get_benchmarks()
        assert result["source"] == "cache"
        assert result["is_stale"] is False
        mock_scrape.assert_not_called()

    def test_scrapes_when_cache_is_stale(self):
        old_cache = self._fresh_cache(date.today().year - 5)
        fresh_scrape = self._fresh_cache(date.today().year)
        with (
            patch("app.services.scf_benchmark_service._load_cache", return_value=old_cache),
            patch("app.services.scf_benchmark_service._scrape", return_value=fresh_scrape),
            patch("app.services.scf_benchmark_service._save_cache"),
        ):
            result = get_benchmarks()
        assert result["source"] == "live_scrape"

    def test_falls_back_to_stale_cache_when_scrape_fails(self):
        old_cache = self._fresh_cache(date.today().year - 5)
        with (
            patch("app.services.scf_benchmark_service._load_cache", return_value=old_cache),
            patch("app.services.scf_benchmark_service._scrape", return_value=None),
        ):
            result = get_benchmarks()
        assert result["source"] == "cache"
        assert result["is_stale"] is True

    def test_falls_back_to_static_when_no_cache_and_scrape_fails(self):
        with (
            patch("app.services.scf_benchmark_service._load_cache", return_value=None),
            patch("app.services.scf_benchmark_service._scrape", return_value=None),
        ):
            result = get_benchmarks()
        assert result["source"] == "static_fallback"

    def test_saves_cache_after_successful_scrape(self):
        fresh = self._fresh_cache()
        with (
            patch("app.services.scf_benchmark_service._load_cache", return_value=None),
            patch("app.services.scf_benchmark_service._scrape", return_value=fresh),
            patch("app.services.scf_benchmark_service._save_cache") as mock_save,
        ):
            get_benchmarks()
        mock_save.assert_called_once_with(fresh)

    def test_result_always_has_is_stale_key(self):
        with (
            patch("app.services.scf_benchmark_service._load_cache", return_value=None),
            patch("app.services.scf_benchmark_service._scrape", return_value=None),
        ):
            result = get_benchmarks()
        assert "is_stale" in result

    def test_result_always_has_source_key(self):
        cache = self._fresh_cache()
        with (
            patch("app.services.scf_benchmark_service._load_cache", return_value=cache),
            patch("app.services.scf_benchmark_service._scrape"),
        ):
            result = get_benchmarks()
        assert "source" in result
