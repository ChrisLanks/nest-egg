"""Service for detecting net worth milestones and all-time highs."""

import logging
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.net_worth_snapshot import NetWorthSnapshot
from app.models.notification import NotificationPriority, NotificationType
from app.services.notification_service import NotificationService
from app.utils.datetime_utils import utc_now

logger = logging.getLogger(__name__)

# Net worth milestone thresholds (in dollars)
MILESTONE_THRESHOLDS = [
    10_000,
    25_000,
    50_000,
    100_000,
    250_000,
    500_000,
    750_000,
    1_000_000,
    2_500_000,
    5_000_000,
    10_000_000,
]


def _format_milestone(value: int) -> str:
    """Format a milestone value for display (e.g. 1000000 -> '$1,000,000')."""
    if value >= 1_000_000 and value % 1_000_000 == 0:
        millions = value // 1_000_000
        return f"${millions}M"
    if value >= 1_000 and value % 1_000 == 0:
        return f"${value:,}"
    return f"${value:,}"


async def check_milestones(
    db: AsyncSession,
    organization_id: UUID,
    current_net_worth: Decimal,
) -> List[Dict]:
    """
    Check if the current net worth has crossed any milestone thresholds
    or reached an all-time high.

    Args:
        db: Database session
        organization_id: Organization ID
        current_net_worth: Current net worth value

    Returns:
        List of milestone dicts that were hit
    """
    milestones_hit: List[Dict] = []
    current_value = float(current_net_worth)

    # Get the previous household snapshot (excluding today)
    today = utc_now().date()
    prev_query = (
        select(NetWorthSnapshot.total_net_worth)
        .where(
            and_(
                NetWorthSnapshot.organization_id == organization_id,
                NetWorthSnapshot.user_id.is_(None),
                NetWorthSnapshot.snapshot_date < today,
            )
        )
        .order_by(NetWorthSnapshot.snapshot_date.desc())
        .limit(1)
    )
    result = await db.execute(prev_query)
    prev_row = result.scalar_one_or_none()
    previous_net_worth = float(prev_row) if prev_row is not None else 0.0

    # Check milestone crossings: previous < threshold <= current
    # Only notify for the highest crossed threshold to avoid notification spam
    # (e.g. jumping from $5K to $1M should only celebrate $1M, not every step)
    highest_crossed: Optional[int] = None
    for threshold in MILESTONE_THRESHOLDS:
        if previous_net_worth < threshold <= current_value:
            milestones_hit.append(
                {
                    "type": "milestone",
                    "threshold": threshold,
                    "label": _format_milestone(threshold),
                    "net_worth": current_value,
                    "date": today.isoformat(),
                }
            )
            highest_crossed = threshold

    if highest_crossed is not None:
        milestone_label = _format_milestone(highest_crossed)
        await NotificationService.create_notification(
            db=db,
            organization_id=organization_id,
            type=NotificationType.MILESTONE,
            title=f"Milestone reached: {milestone_label}!",
            message=(
                f"Congratulations! Your household net worth has crossed "
                f"{milestone_label}. Current net worth: ${current_value:,.2f}."
            ),
            priority=NotificationPriority.LOW,
            action_url="/dashboard",
            action_label="View Dashboard",
            expires_in_days=30,
        )

        logger.info(
            "Milestone %s reached for org %s (net worth: $%s)",
            milestone_label,
            organization_id,
            f"{current_value:,.2f}",
        )

    # Check all-time high
    ath_query = select(func.max(NetWorthSnapshot.total_net_worth)).where(
        and_(
            NetWorthSnapshot.organization_id == organization_id,
            NetWorthSnapshot.user_id.is_(None),
            NetWorthSnapshot.snapshot_date < today,
        )
    )
    result = await db.execute(ath_query)
    previous_ath = result.scalar_one_or_none()
    previous_ath_value = float(previous_ath) if previous_ath is not None else None

    is_ath = (
        previous_ath_value is not None and current_value > previous_ath_value and current_value > 0
    )

    if is_ath:
        milestones_hit.append(
            {
                "type": "all_time_high",
                "net_worth": current_value,
                "previous_ath": previous_ath_value,
                "date": today.isoformat(),
            }
        )

        await NotificationService.create_notification(
            db=db,
            organization_id=organization_id,
            type=NotificationType.ALL_TIME_HIGH,
            title="New all-time high net worth!",
            message=(
                f"Your household net worth has reached a new all-time high "
                f"of ${current_value:,.2f}, surpassing the previous record "
                f"of ${previous_ath_value:,.2f}."
            ),
            priority=NotificationPriority.LOW,
            action_url="/dashboard",
            action_label="View Dashboard",
            expires_in_days=30,
        )

        logger.info(
            "All-time high net worth for org %s: $%s (previous: $%s)",
            organization_id,
            f"{current_value:,.2f}",
            f"{previous_ath_value:,.2f}",
        )

    return milestones_hit


async def get_milestone_summary(
    db: AsyncSession,
    organization_id: UUID,
) -> Dict:
    """
    Get milestone summary for an organization: achieved milestones,
    ATH info, and next milestone target.

    Args:
        db: Database session
        organization_id: Organization ID

    Returns:
        Dict with milestones_achieved, all_time_high, and next_milestone
    """
    # Get latest household snapshot for current net worth
    latest_query = (
        select(NetWorthSnapshot)
        .where(
            and_(
                NetWorthSnapshot.organization_id == organization_id,
                NetWorthSnapshot.user_id.is_(None),
            )
        )
        .order_by(NetWorthSnapshot.snapshot_date.desc())
        .limit(1)
    )
    result = await db.execute(latest_query)
    latest_snapshot = result.scalar_one_or_none()

    current_net_worth = float(latest_snapshot.total_net_worth) if latest_snapshot else 0.0

    # Determine achieved milestones
    milestones_achieved = []
    next_milestone: Optional[int] = None

    for threshold in MILESTONE_THRESHOLDS:
        if current_net_worth >= threshold:
            milestones_achieved.append(
                {
                    "threshold": threshold,
                    "label": _format_milestone(threshold),
                }
            )
        elif next_milestone is None:
            next_milestone = threshold

    # If all milestones achieved, no next milestone
    # If net worth is below all thresholds, next is the first one

    # Get all-time high
    ath_query = select(
        func.max(NetWorthSnapshot.total_net_worth).label("max_nw"),
    ).where(
        and_(
            NetWorthSnapshot.organization_id == organization_id,
            NetWorthSnapshot.user_id.is_(None),
        )
    )
    result = await db.execute(ath_query)
    max_nw = result.scalar_one_or_none()
    ath_value = float(max_nw) if max_nw is not None else 0.0

    # Get ATH date
    ath_date_query = (
        select(NetWorthSnapshot.snapshot_date)
        .where(
            and_(
                NetWorthSnapshot.organization_id == organization_id,
                NetWorthSnapshot.user_id.is_(None),
                NetWorthSnapshot.total_net_worth == max_nw,
            )
        )
        .order_by(NetWorthSnapshot.snapshot_date.desc())
        .limit(1)
    )
    result = await db.execute(ath_date_query)
    ath_date_row = result.scalar_one_or_none()

    is_current_ath = (
        latest_snapshot is not None
        and ath_date_row is not None
        and latest_snapshot.snapshot_date == ath_date_row
    )

    all_time_high = {
        "value": ath_value,
        "date": ath_date_row.isoformat() if ath_date_row else None,
        "is_current": is_current_ath,
    }

    return {
        "milestones_achieved": milestones_achieved,
        "all_time_high": all_time_high,
        "next_milestone": next_milestone,
    }
