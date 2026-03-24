"""Unit tests for the refresh_scf_benchmarks Celery task.

All external calls (_load_cache, _scrape, _save_cache, _is_stale) are patched
so these tests are pure unit tests with no filesystem or network I/O.
"""

from datetime import date
from unittest.mock import call, patch

import pytest


@pytest.mark.unit
class TestRefreshScfBenchmarksTask:
    """Tests for the refresh_scf_benchmarks Celery task."""

    def _run(self, *, cached, is_stale, scrape_result):
        """Helper: patch internals and execute the task synchronously."""
        from app.workers.tasks.scf_benchmark_tasks import refresh_scf_benchmarks

        current_year = (cached or {"survey_year": date.today().year - 5})["survey_year"]

        with (
            patch(
                "app.workers.tasks.scf_benchmark_tasks.refresh_scf_benchmarks.__wrapped__",
                create=True,
            ),
            patch(
                "app.services.scf_benchmark_service._load_cache",
                return_value=cached,
            ),
            patch(
                "app.services.scf_benchmark_service._is_stale",
                return_value=is_stale,
            ),
            patch(
                "app.services.scf_benchmark_service._scrape",
                return_value=scrape_result,
            ) as mock_scrape,
            patch(
                "app.services.scf_benchmark_service._save_cache",
            ) as mock_save,
            patch(
                "app.services.scf_benchmark_service._static_fallback",
                return_value={
                    "survey_year": date.today().year - 5,
                    "scraped_at": None,
                    "median": {},
                    "mean": {},
                },
            ),
        ):
            refresh_scf_benchmarks()
            return mock_scrape, mock_save

    # ------------------------------------------------------------------
    # Happy path: data is current — no scrape needed
    # ------------------------------------------------------------------

    def test_no_scrape_when_data_is_current(self):
        cache = {"survey_year": date.today().year, "scraped_at": None, "median": {}, "mean": {}}
        mock_scrape, mock_save = self._run(
            cached=cache, is_stale=False, scrape_result=None
        )
        mock_scrape.assert_not_called()
        mock_save.assert_not_called()

    # ------------------------------------------------------------------
    # Stale data + successful scrape
    # ------------------------------------------------------------------

    def test_scrapes_when_stale(self):
        old_cache = {"survey_year": date.today().year - 5, "scraped_at": None, "median": {}, "mean": {}}
        fresh = {"survey_year": date.today().year, "scraped_at": "2025-01-01T00:00:00Z", "median": {}, "mean": {}}
        mock_scrape, mock_save = self._run(
            cached=old_cache, is_stale=True, scrape_result=fresh
        )
        mock_scrape.assert_called_once()

    def test_saves_cache_after_successful_scrape(self):
        old_cache = {"survey_year": date.today().year - 5, "scraped_at": None, "median": {}, "mean": {}}
        fresh = {"survey_year": date.today().year, "scraped_at": "2025-01-01T00:00:00Z", "median": {}, "mean": {}}
        mock_scrape, mock_save = self._run(
            cached=old_cache, is_stale=True, scrape_result=fresh
        )
        mock_save.assert_called_once_with(fresh)

    # ------------------------------------------------------------------
    # Stale data + scrape fails — must not raise
    # ------------------------------------------------------------------

    def test_does_not_raise_when_scrape_fails(self):
        old_cache = {"survey_year": date.today().year - 5, "scraped_at": None, "median": {}, "mean": {}}
        # Should complete without exception even when scrape returns None
        mock_scrape, mock_save = self._run(
            cached=old_cache, is_stale=True, scrape_result=None
        )
        mock_save.assert_not_called()

    # ------------------------------------------------------------------
    # No cache available — use static fallback year for staleness check
    # ------------------------------------------------------------------

    def test_uses_static_fallback_year_when_no_cache(self):
        # When cached=None the task must not crash — static fallback provides year
        from app.workers.tasks.scf_benchmark_tasks import refresh_scf_benchmarks

        with (
            patch("app.services.scf_benchmark_service._load_cache", return_value=None),
            patch("app.services.scf_benchmark_service._is_stale", return_value=True),
            patch("app.services.scf_benchmark_service._scrape", return_value=None),
            patch(
                "app.services.scf_benchmark_service._static_fallback",
                return_value={
                    "survey_year": date.today().year - 5,
                    "scraped_at": None,
                    "median": {},
                    "mean": {},
                },
            ),
            patch("app.services.scf_benchmark_service._save_cache"),
        ):
            # Must not raise
            refresh_scf_benchmarks()

    # ------------------------------------------------------------------
    # Unexpected exception inside task — must not propagate
    # ------------------------------------------------------------------

    def test_unexpected_exception_is_swallowed(self):
        """The task wraps everything in try/except — exceptions must not bubble up."""
        from app.workers.tasks.scf_benchmark_tasks import refresh_scf_benchmarks

        with patch(
            "app.services.scf_benchmark_service._load_cache",
            side_effect=RuntimeError("unexpected DB failure"),
        ):
            # Must complete without raising
            refresh_scf_benchmarks()
