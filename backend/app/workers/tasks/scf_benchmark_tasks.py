"""Celery task: auto-refresh SCF net-worth benchmark data.

Runs annually on Jan 1 at 5am UTC.  Checks whether the cached SCF data is
stale (survey_year more than 3 years behind today) and, if so, attempts a
live scrape of the Federal Reserve SCF page.

If the scrape succeeds the cache is updated and the new survey_year is logged.
If it fails (network error, page layout changed, etc.) the task logs a warning
but does NOT raise — the app continues serving the static fallback table from
financial.py uninterrupted.

Manual trigger (dev / ops)
--------------------------
    python -m app.services.scf_benchmark_service --scrape
"""

import logging

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="refresh_scf_benchmarks")
def refresh_scf_benchmarks():
    """Attempt to refresh SCF net-worth benchmark data if stale.

    Runs annually — see beat_schedule in celery_app.py.
    """
    try:
        from app.services.scf_benchmark_service import (
            _is_stale,
            _load_cache,
            _save_cache,
            _scrape,
            _static_fallback,
        )

        # Determine current survey_year from cache or static fallback
        cached = _load_cache()
        current_year = (cached or _static_fallback())["survey_year"]

        if not _is_stale(current_year):
            logger.info(
                "refresh_scf_benchmarks: data is current (year=%s) — no update needed",
                current_year,
            )
            return

        logger.info(
            "refresh_scf_benchmarks: data is stale (year=%s) — attempting live scrape",
            current_year,
        )

        result = _scrape()
        if result:
            _save_cache(result)
            logger.info(
                "refresh_scf_benchmarks: successfully updated to survey_year=%s",
                result["survey_year"],
            )
        else:
            logger.warning(
                "refresh_scf_benchmarks: live scrape failed — "
                "app will continue serving static fallback (year=%s). "
                "Run `python -m app.services.scf_benchmark_service --scrape` "
                "to retry manually, or update financial.py with the latest SCF data.",
                current_year,
            )

    except Exception:
        logger.exception("refresh_scf_benchmarks: unexpected error — task will not retry")
