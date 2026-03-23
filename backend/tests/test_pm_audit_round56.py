"""
PM Audit Round 56 — fix:
PerformanceTrendsChart empty state: "portfolio snapshots are captured" is
developer/backend-speak — users don't think about their system "capturing
snapshots". Changed to plain English: "after your portfolio has been tracked
for a few days."
"""
from pathlib import Path

BACKEND = Path(__file__).parent.parent
FRONTEND = BACKEND.parent / "frontend/src"


def _perf_trends_src():
    return (
        FRONTEND
        / "features/investments/components/PerformanceTrendsChart.tsx"
    ).read_text()


# ── PerformanceTrendsChart empty-state copy ───────────────────────────────────


def test_perf_trends_no_snapshot_jargon():
    src = _perf_trends_src()
    assert "portfolio snapshots are captured" not in src


def test_perf_trends_uses_plain_english():
    src = _perf_trends_src()
    assert "after your portfolio has been tracked" in src
