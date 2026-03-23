"""Tests for PM audit round 18 fixes.

Covers:
- run_retirement_simulation celery task: missing cross-org guard.
  Scenario and user could belong to different organizations — task would
  silently run the simulation with cross-org data. Added org membership check
  that logs a warning and returns early if orgs don't match.
"""

import inspect
from uuid import uuid4


def test_retirement_task_has_org_check():
    """run_retirement_simulation must verify scenario.organization_id == user.organization_id."""
    from app.workers.tasks import retirement_tasks

    source = inspect.getsource(retirement_tasks.run_retirement_simulation)
    assert "organization_id != user.organization_id" in source or \
           "organization_id == user.organization_id" in source, (
        "run_retirement_simulation must check that scenario and user share organization_id"
    )


def test_retirement_task_returns_on_org_mismatch():
    """Source must contain an early return when orgs don't match."""
    from app.workers.tasks import retirement_tasks

    source = inspect.getsource(retirement_tasks.run_retirement_simulation)
    # The guard must log a warning and return
    assert "organization_id != user.organization_id" in source, (
        "Must use != to detect mismatch"
    )
    # There must be a return after the mismatch log
    lines = source.splitlines()
    mismatch_idx = next(
        i for i, l in enumerate(lines) if "organization_id != user.organization_id" in l
    )
    # Within 10 lines of the check there should be a return
    nearby = "\n".join(lines[mismatch_idx: mismatch_idx + 10])
    assert "return" in nearby, "Must return early on org mismatch"


def test_retirement_task_logs_warning_on_mismatch():
    """Must log a warning (not silently skip) on org mismatch."""
    from app.workers.tasks import retirement_tasks

    source = inspect.getsource(retirement_tasks.run_retirement_simulation)
    lines = source.splitlines()
    mismatch_idx = next(
        i for i, l in enumerate(lines) if "organization_id != user.organization_id" in l
    )
    nearby = "\n".join(lines[mismatch_idx: mismatch_idx + 15])
    assert "logger.warning" in nearby, "Must log a warning when org mismatch detected"


def test_retirement_task_org_check_before_simulation():
    """The org check must appear BEFORE the monte carlo simulation call."""
    from app.workers.tasks import retirement_tasks

    source = inspect.getsource(retirement_tasks.run_retirement_simulation)
    org_check_pos = source.find("organization_id != user.organization_id")
    simulation_pos = source.find("run_simulation")
    assert org_check_pos != -1, "Org check must exist"
    assert simulation_pos != -1, "run_simulation call must exist"
    assert org_check_pos < simulation_pos, (
        "Org ownership check must come before run_simulation call"
    )
