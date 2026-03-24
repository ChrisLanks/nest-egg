"""Federal Reserve Survey of Consumer Finances (SCF) benchmark scraper.

Responsibilities
----------------
1. Attempt to scrape the latest SCF net-worth table from the Fed website.
2. Cache results in ``backend/app/constants/scf_cache.json`` so subsequent
   calls are instant.
3. Fall back to the hardcoded ``NET_WORTH_BENCHMARKS`` table in
   ``financial.py`` when scraping fails or the cache is absent.
4. Expose ``get_benchmarks()`` — the single function callers use.

Cache lifecycle
---------------
- Fresh if: cache exists AND ``survey_year >= current_year - 3``.
- Stale if: survey_year is more than 3 years behind current year.
- The ``is_stale`` flag is returned to callers so the UI can show a notice.

Scrape strategy
---------------
The Fed publishes SCF data as HTML tables at:
    https://www.federalreserve.gov/econres/scfindex.htm

The scraper looks for table rows keyed by the same age-bucket strings used
in ``NET_WORTH_BENCHMARKS.MEDIAN``.  If parsing fails for any reason the
service logs a warning and returns the static fallback — it never raises.

CLI usage (for manual refresh)
-------------------------------
    python -m app.services.scf_benchmark_service --scrape
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Path to the JSON cache file (sibling of financial.py)
_CACHE_PATH = Path(__file__).parent.parent / "constants" / "scf_cache.json"

# Age buckets in the order the SCF table uses them
_AGE_BUCKETS = ["under 35", "35-44", "45-54", "55-64", "65-74", "75+"]

# How many years before data is considered stale
_STALE_AFTER_YEARS = 3


# ── Public API ────────────────────────────────────────────────────────────


def get_benchmarks() -> dict:
    """Return the best available benchmark data.

    Priority:
      1. Valid cache file (survey_year within 3 years)
      2. Live scrape (attempted when cache is stale or missing)
      3. Static fallback from financial.py

    Always returns a dict with keys:
        survey_year  – int: year the SCF survey was conducted
        scraped_at   – str | None: ISO-8601 timestamp of last scrape
        median       – Dict[str, float]: median net worth by age bucket
        mean         – Dict[str, float]: mean net worth by age bucket
        is_stale     – bool: True when data is more than 3 years old
        source       – str: "cache" | "live_scrape" | "static_fallback"
    """
    # 1. Try cache
    cached = _load_cache()
    if cached and not _is_stale(cached["survey_year"]):
        cached["is_stale"] = False
        cached["source"] = "cache"
        return cached

    # 2. Try live scrape
    scraped = _scrape()
    if scraped:
        _save_cache(scraped)
        scraped["is_stale"] = _is_stale(scraped["survey_year"])
        scraped["source"] = "live_scrape"
        return scraped

    # 3. Static fallback
    if cached:
        # Return stale cache rather than the even-older static table
        cached["is_stale"] = True
        cached["source"] = "cache"
        logger.warning(
            "scf_benchmark_service: scrape failed, returning stale cache (year=%s)",
            cached["survey_year"],
        )
        return cached

    return _static_fallback()


# ── Cache helpers ─────────────────────────────────────────────────────────


def _load_cache() -> Optional[dict]:
    try:
        if _CACHE_PATH.exists():
            return json.loads(_CACHE_PATH.read_text())
    except Exception:
        logger.warning("scf_benchmark_service: failed to read cache", exc_info=True)
    return None


def _save_cache(data: dict) -> None:
    try:
        _CACHE_PATH.write_text(json.dumps(data, indent=2))
        logger.info(
            "scf_benchmark_service: cache written (year=%s)", data.get("survey_year")
        )
    except Exception:
        logger.warning("scf_benchmark_service: failed to write cache", exc_info=True)


def _is_stale(survey_year: int) -> bool:
    return date.today().year - survey_year > _STALE_AFTER_YEARS


# ── Scraper ───────────────────────────────────────────────────────────────


def _scrape() -> Optional[dict]:
    """Attempt to scrape the latest SCF net-worth table from the Fed website.

    Returns a benchmark dict on success, None on any failure.
    """
    try:
        import urllib.request

        from app.constants.financial import NET_WORTH_BENCHMARKS

        logger.info("scf_benchmark_service: attempting live scrape of %s", NET_WORTH_BENCHMARKS.SCF_URL)

        req = urllib.request.Request(
            NET_WORTH_BENCHMARKS.SCF_URL,
            headers={"User-Agent": "NestEggApp/1.0 (financial data refresh; see source)"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        median, mean, survey_year = _parse_scf_html(html)
        if not median:
            logger.warning("scf_benchmark_service: could not parse net worth table from Fed page")
            return None

        from datetime import datetime, timezone

        return {
            "survey_year": survey_year,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "median": median,
            "mean": mean,
        }
    except Exception:
        logger.warning("scf_benchmark_service: live scrape failed", exc_info=True)
        return None


def _parse_scf_html(html: str) -> tuple[dict, dict, int]:
    """Extract median/mean net worth by age from raw SCF HTML.

    The Fed page structure changes occasionally, so this parser is
    deliberately loose: it looks for numeric patterns near the known
    age-bucket labels rather than relying on specific tag paths.

    Returns (median_dict, mean_dict, survey_year).
    All three will be empty/0 on parse failure.
    """
    median: dict[str, float] = {}
    mean: dict[str, float] = {}
    survey_year = 0

    # Try to extract survey year from page title / headings
    year_match = re.search(r"20(2[2-9]|[3-9]\d)", html)
    if year_match:
        survey_year = int(year_match.group(0))

    # Look for a table section containing "Net Worth" and age rows.
    # The SCF summary tables embed values like "409.9" (meaning $409,900).
    # We search for rows that contain an age bucket label followed by numbers.
    for bucket in _AGE_BUCKETS:
        # Build a pattern: age label, then capture two numbers (median, mean)
        # Numbers may be formatted as "247.2" (thousands) or "247,200"
        pattern = re.compile(
            re.escape(bucket) + r"[^0-9]*?(\d[\d,\.]+)[^0-9]*?(\d[\d,\.]+)",
            re.IGNORECASE,
        )
        m = pattern.search(html)
        if m:
            median[bucket] = _parse_dollar(m.group(1))
            mean[bucket] = _parse_dollar(m.group(2))

    if len(median) < 4:
        # Not enough buckets found — unreliable parse
        return {}, {}, 0

    return median, mean, survey_year or date.today().year


def _parse_dollar(raw: str) -> float:
    """Parse a dollar string which may be in thousands (e.g. '409.9' → 409_900)."""
    cleaned = raw.replace(",", "")
    try:
        value = float(cleaned)
    except ValueError:
        return 0.0
    # SCF tables typically express values in thousands
    if value < 10_000:
        value *= 1_000
    return round(value)


# ── Static fallback ───────────────────────────────────────────────────────


def _static_fallback() -> dict:
    """Return the hardcoded SCF 2022 data from financial.py."""
    from app.constants.financial import NET_WORTH_BENCHMARKS

    return {
        "survey_year": NET_WORTH_BENCHMARKS.SURVEY_YEAR,
        "scraped_at": NET_WORTH_BENCHMARKS.SCRAPED_AT,
        "median": dict(NET_WORTH_BENCHMARKS.MEDIAN),
        "mean": dict(NET_WORTH_BENCHMARKS.MEAN),
        "is_stale": _is_stale(NET_WORTH_BENCHMARKS.SURVEY_YEAR),
        "source": "static_fallback",
    }


# ── Age-bucket helpers used by the insight check ─────────────────────────


def age_bucket(age: int) -> str:
    """Map an integer age to the SCF age-bucket label."""
    if age < 35:
        return "under 35"
    if age < 45:
        return "35-44"
    if age < 55:
        return "45-54"
    if age < 65:
        return "55-64"
    if age < 75:
        return "65-74"
    return "75+"


def fidelity_target(age: int, annual_income: float) -> Optional[float]:
    """Return the Fidelity salary-multiple target net worth for a given age.

    Picks the milestone whose age is closest to (but not above) the user's
    age.  Returns None when income is unknown (≤ 0).
    """
    if annual_income <= 0:
        return None

    from app.constants.financial import NET_WORTH_BENCHMARKS

    milestones = NET_WORTH_BENCHMARKS.FIDELITY_MILESTONES
    applicable_ages = sorted(a for a in milestones if a <= age)
    if not applicable_ages:
        return None
    closest = applicable_ages[-1]
    return milestones[closest] * annual_income


# ── CLI entrypoint ────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    import sys

    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="SCF benchmark scraper")
    parser.add_argument("--scrape", action="store_true", help="Force a live scrape and update cache")
    args = parser.parse_args()

    if args.scrape:
        result = _scrape()
        if result:
            _save_cache(result)
            print(f"✓ Scraped SCF {result['survey_year']} data — cache updated.")
            print(json.dumps(result, indent=2))
        else:
            print("✗ Scrape failed — static fallback data unchanged.", file=sys.stderr)
            sys.exit(1)
    else:
        data = get_benchmarks()
        print(f"Source: {data['source']}  |  Year: {data['survey_year']}  |  Stale: {data['is_stale']}")
        print(json.dumps(data, indent=2))
