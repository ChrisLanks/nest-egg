"""Weekly financial recap Celery task.

Generates a narrative summary of each household's financial week and
delivers it as an in-app notification (+ email if configured).

Runs every Monday at 8 AM UTC so users start the week with last week's summary.
"""

import asyncio
import logging
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import and_, func, select

from app.models.account import Account, AccountCategory
from app.models.notification import NotificationPriority, NotificationType
from app.models.transaction import Transaction
from app.models.user import Organization, User
from app.services.notification_service import NotificationService
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="send_weekly_recaps")
def send_weekly_recaps_task():
    """Send weekly financial recap to all active households."""
    asyncio.run(_send_weekly_recaps_async())


async def _send_weekly_recaps_async():
    """Async implementation."""
    from app.workers.utils import get_celery_session

    async with get_celery_session() as db:
        # Get all active organizations
        orgs_result = await db.execute(select(Organization).where(Organization.is_active.is_(True)))
        orgs = orgs_result.scalars().all()

        failed = []
        for org in orgs:
            try:
                await _generate_org_recap(db, org)
            except Exception as exc:
                logger.error(
                    "weekly_recap_failed",
                    extra={"org_id": str(org.id), "error": str(exc)},
                    exc_info=True,
                )
                failed.append(str(org.id))

        if failed:
            raise RuntimeError(
                f"weekly_recap failed for {len(failed)} org(s): {', '.join(failed)}"
            )


async def _generate_org_recap(db, org) -> None:
    """Generate and send a recap for one organization."""
    today = date.today()
    week_start = today - timedelta(days=7)
    week_end = today - timedelta(days=1)

    # Get all active accounts for the org
    accounts_result = await db.execute(
        select(Account).where(
            Account.organization_id == org.id,
            Account.is_active.is_(True),
        )
    )
    accounts = accounts_result.scalars().all()

    if not accounts:
        return

    account_ids = [a.id for a in accounts]

    # --- Spending and income for the week ---
    txn_result = await db.execute(
        select(
            func.sum(
                func.case(
                    (Transaction.amount < 0, func.abs(Transaction.amount)),
                    else_=Decimal("0"),
                )
            ).label("total_spending"),
            func.sum(
                func.case(
                    (Transaction.amount > 0, Transaction.amount),
                    else_=Decimal("0"),
                )
            ).label("total_income"),
            func.count(Transaction.id).label("txn_count"),
        ).where(
            and_(
                Transaction.organization_id == org.id,
                Transaction.account_id.in_(account_ids),
                Transaction.date >= week_start,
                Transaction.date <= week_end,
                Transaction.is_transfer.is_(False),
            )
        )
    )
    row = txn_result.one()
    total_spending = float(row.total_spending or 0)
    total_income = float(row.total_income or 0)
    txn_count = int(row.txn_count or 0)

    # --- Top spending category ---
    cat_result = await db.execute(
        select(
            Transaction.category_primary,
            func.sum(func.abs(Transaction.amount)).label("cat_total"),
        )
        .where(
            and_(
                Transaction.organization_id == org.id,
                Transaction.account_id.in_(account_ids),
                Transaction.date >= week_start,
                Transaction.date <= week_end,
                Transaction.amount < 0,
                Transaction.is_transfer.is_(False),
                Transaction.category_primary.isnot(None),
            )
        )
        .group_by(Transaction.category_primary)
        .order_by(func.sum(func.abs(Transaction.amount)).desc())
        .limit(1)
    )
    top_cat_row = cat_result.one_or_none()
    top_category = top_cat_row[0] if top_cat_row else None
    top_category_amount = float(top_cat_row[1]) if top_cat_row else 0.0

    # --- Net worth delta (compare current balance totals vs last week) ---
    # Use current balances as a proxy since we may not have two snapshots
    asset_accounts = [a for a in accounts if a.account_type.category == AccountCategory.ASSET]
    debt_accounts = [a for a in accounts if a.account_type.category != AccountCategory.ASSET]
    total_assets = sum(float(a.current_balance or 0) for a in asset_accounts)
    total_debts = sum(float(a.current_balance or 0) for a in debt_accounts)
    net_worth = total_assets - total_debts

    # --- Build message ---
    net = total_income - total_spending
    net_sign = "+" if net >= 0 else ""
    fmt = lambda v: f"${v:,.0f}"  # noqa: E731

    lines = [
        f"Week of {week_start.strftime('%b %d')} – {week_end.strftime('%b %d')}",
        "",
        f"💰 Income: {fmt(total_income)}",
        f"💸 Spending: {fmt(total_spending)}",
        f"📊 Net: {net_sign}{fmt(net)}",
        f"🔢 Transactions: {txn_count}",
    ]
    if top_category:
        lines.append(f"🏆 Top category: {top_category} ({fmt(top_category_amount)})")
    lines.append(f"📈 Net worth: {fmt(net_worth)}")

    message = "\n".join(lines)
    title = f"Your weekly recap: {net_sign}{fmt(net)} net"

    # --- Deliver to each user in the org ---
    users_result = await db.execute(
        select(User).where(
            User.organization_id == org.id,
            User.is_active.is_(True),
        )
    )
    users = users_result.scalars().all()

    for user in users:
        # Respect the user's weekly_recap preference (default on)
        prefs = user.notification_preferences or {}
        if prefs.get("weekly_recap") is False:
            continue

        await NotificationService.create_notification(
            db=db,
            organization_id=org.id,
            user_id=user.id,
            type=NotificationType.WEEKLY_RECAP,
            title=title,
            message=message,
            priority=NotificationPriority.LOW,
            action_url="/transactions",
            action_label="View Transactions",
            expires_in_days=14,
        )

    await db.commit()
    logger.info(
        "weekly_recap_sent",
        extra={"org_id": str(org.id), "user_count": len(users)},
    )
