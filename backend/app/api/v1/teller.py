"""Teller integration API endpoints."""

import hashlib
import hmac
import json
import logging
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.account import Account, TellerEnrollment
from app.models.notification import NotificationType, NotificationPriority
from app.services.notification_service import notification_service
from app.services.rate_limit_service import rate_limit_service
from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


def verify_teller_webhook_signature(
    signature_header: str,
    webhook_body: bytes,
    secret: str,
) -> bool:
    """
    Verify Teller webhook signature using HMAC-SHA256.

    Teller sends webhooks with a 'Teller-Signature' header containing an HMAC signature.
    The signature is computed as HMAC-SHA256(webhook_secret, request_body).

    Args:
        signature_header: Value of 'Teller-Signature' header
        webhook_body: Raw webhook request body as bytes
        secret: Webhook secret key

    Returns:
        True if signature is valid, raises HTTPException otherwise

    Security Note:
        Webhook signature verification is REQUIRED for production.
        In development with DEBUG=True, signature verification is logged but not enforced.
    """
    if not secret:
        if settings.DEBUG:
            logger.warning("⚠️  TELLER_WEBHOOK_SECRET not set - webhook verification disabled in DEBUG mode")
            return True
        else:
            raise HTTPException(
                status_code=500,
                detail="Webhook verification secret not configured. Set TELLER_WEBHOOK_SECRET for security."
            )

    if not signature_header:
        if settings.DEBUG:
            logger.warning("⚠️  Missing Teller-Signature header - allowing in DEBUG mode")
            return True
        else:
            raise HTTPException(
                status_code=401,
                detail="Missing Teller-Signature header"
            )

    try:
        # Compute expected signature using HMAC-SHA256
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            webhook_body,
            hashlib.sha256
        ).hexdigest()

        # Compare signatures using constant-time comparison to prevent timing attacks
        is_valid = hmac.compare_digest(expected_signature, signature_header)

        if not is_valid:
            if settings.DEBUG:
                logger.warning("⚠️  Teller webhook signature mismatch - allowing in DEBUG mode")
                logger.debug(f"Expected: {expected_signature[:16]}... Got: {signature_header[:16]}...")
                return True
            else:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid webhook signature"
                )

        if settings.DEBUG:
            logger.info("✅ Teller webhook signature verified")
        return True

    except Exception as e:
        if settings.DEBUG:
            logger.warning(f"⚠️  Webhook verification error in DEBUG mode: {str(e)}")
            return True
        else:
            logger.error(f"❌ Webhook verification error: {str(e)}")
            raise HTTPException(
                status_code=401,
                detail="Webhook verification failed"
            )


@router.post("/webhook")
async def handle_teller_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Handle webhook notifications from Teller.

    Teller sends webhooks for various events:
    - enrollment.connected: New enrollment created
    - enrollment.disconnected: User disconnected
    - account.opened: New account detected
    - account.closed: Account closed
    - transaction.posted: New transaction posted
    - transaction.pending: New pending transaction
    - balance.updated: Balance changed

    Rate limited to 20 requests per minute.
    """
    await rate_limit_service.check_rate_limit(
        request=request,
        max_requests=20,
        window_seconds=60,
    )

    try:
        # Get raw body for signature verification (must be done before parsing JSON)
        raw_body = await request.body()

        # Verify webhook signature
        teller_signature = request.headers.get("Teller-Signature")
        verify_teller_webhook_signature(
            signature_header=teller_signature,
            webhook_body=raw_body,
            secret=settings.TELLER_WEBHOOK_SECRET,
        )

        # Now parse the JSON body
        webhook_data: Dict[str, Any] = json.loads(raw_body.decode('utf-8'))

        event_type = webhook_data.get("event")
        payload = webhook_data.get("payload", {})
        enrollment_id = payload.get("enrollment_id")

        logger.info(f"Teller webhook received: {event_type}")

        if not enrollment_id:
            logger.warning("Webhook missing enrollment_id")
            return {"status": "acknowledged"}

        # Get TellerEnrollment
        result = await db.execute(
            select(TellerEnrollment).where(TellerEnrollment.enrollment_id == enrollment_id)
        )
        enrollment = result.scalar_one_or_none()

        if not enrollment:
            logger.warning(f"TellerEnrollment not found for enrollment_id: {enrollment_id}")
            return {"status": "enrollment_not_found"}

        # Handle different webhook types
        if event_type == "enrollment.connected":
            await _handle_enrollment_connected(db, enrollment, payload)
        elif event_type == "enrollment.disconnected":
            await _handle_enrollment_disconnected(db, enrollment, payload)
        elif event_type == "account.opened":
            await _handle_account_opened(db, enrollment, payload)
        elif event_type == "account.closed":
            await _handle_account_closed(db, enrollment, payload)
        elif event_type == "transaction.posted":
            await _handle_transaction_posted(db, enrollment, payload)
        elif event_type == "transaction.pending":
            await _handle_transaction_pending(db, enrollment, payload)
        elif event_type == "balance.updated":
            await _handle_balance_updated(db, enrollment, payload)
        else:
            logger.info(f"Unhandled webhook type: {event_type}")

        return {"status": "acknowledged"}

    except Exception as e:
        logger.error(f"Webhook error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def _handle_enrollment_connected(
    db: AsyncSession,
    enrollment: TellerEnrollment,
    payload: Dict[str, Any],
):
    """Handle enrollment.connected webhook."""
    logger.info(f"Enrollment connected: {enrollment.enrollment_id}")

    # Create notification
    await notification_service.create_notification(
        db=db,
        organization_id=enrollment.organization_id,
        user_id=enrollment.user_id,
        type=NotificationType.ACCOUNT_CONNECTED,
        title=f"Connected to {enrollment.institution_name}",
        message=f"Your {enrollment.institution_name} accounts are now syncing.",
        priority=NotificationPriority.LOW,
        expires_in_days=7,
    )


async def _handle_enrollment_disconnected(
    db: AsyncSession,
    enrollment: TellerEnrollment,
    payload: Dict[str, Any],
):
    """Handle enrollment.disconnected webhook."""
    logger.info(f"Enrollment disconnected: {enrollment.enrollment_id}")

    # Mark enrollment as inactive
    enrollment.is_active = False
    enrollment.last_error_code = "DISCONNECTED"
    enrollment.last_error_message = "User disconnected their bank connection"
    await db.commit()

    # Create notification
    await notification_service.create_notification(
        db=db,
        organization_id=enrollment.organization_id,
        user_id=enrollment.user_id,
        type=NotificationType.ACCOUNT_ERROR,
        title=f"Connection Lost: {enrollment.institution_name}",
        message=f"Your {enrollment.institution_name} connection was disconnected. Reconnect to continue syncing.",
        priority=NotificationPriority.HIGH,
        related_entity_type="teller_enrollment",
        related_entity_id=enrollment.id,
        action_url="/accounts",
        action_label="Reconnect",
        expires_in_days=30,
    )


async def _handle_account_opened(
    db: AsyncSession,
    enrollment: TellerEnrollment,
    payload: Dict[str, Any],
):
    """Handle account.opened webhook - trigger account sync."""
    logger.info(f"New account detected for enrollment: {enrollment.enrollment_id}")

    # Trigger account sync in background
    from app.services.teller_service import get_teller_service

    teller_service = get_teller_service()
    new_accounts = await teller_service.sync_accounts(db, enrollment)

    # Create notification
    if new_accounts:
        await notification_service.create_notification(
            db=db,
            organization_id=enrollment.organization_id,
            user_id=enrollment.user_id,
            type=NotificationType.ACCOUNT_CONNECTED,
            title="New Account Detected",
            message=f"Found {len(new_accounts)} new account(s) at {enrollment.institution_name}",
            priority=NotificationPriority.LOW,
            expires_in_days=7,
        )


async def _handle_account_closed(
    db: AsyncSession,
    enrollment: TellerEnrollment,
    payload: Dict[str, Any],
):
    """Handle account.closed webhook - mark account as inactive."""
    account_id = payload.get("account_id")

    if not account_id:
        logger.warning("account.closed webhook missing account_id")
        return

    # Find account
    result = await db.execute(
        select(Account).where(
            Account.teller_enrollment_id == enrollment.id,
            Account.external_account_id == account_id,
        )
    )
    account = result.scalar_one_or_none()

    if account:
        logger.info(f"Marking account as inactive: {account.name}")
        account.is_active = False
        await db.commit()

        # Create notification
        await notification_service.create_notification(
            db=db,
            organization_id=enrollment.organization_id,
            user_id=enrollment.user_id,
            type=NotificationType.ACCOUNT_ERROR,
            title=f"Account Closed: {account.name}",
            message=f"Your {account.name} account has been closed.",
            priority=NotificationPriority.MEDIUM,
            expires_in_days=30,
        )


async def _handle_transaction_posted(
    db: AsyncSession,
    enrollment: TellerEnrollment,
    payload: Dict[str, Any],
):
    """Handle transaction.posted webhook - trigger transaction sync."""
    account_id = payload.get("account_id")

    if not account_id:
        logger.warning("transaction.posted webhook missing account_id")
        return

    # Find account
    result = await db.execute(
        select(Account).where(
            Account.teller_enrollment_id == enrollment.id,
            Account.external_account_id == account_id,
        )
    )
    account = result.scalar_one_or_none()

    if account:
        logger.info(f"New transaction posted for account: {account.name}")

        # Trigger transaction sync
        from app.services.teller_service import get_teller_service

        teller_service = get_teller_service()
        await teller_service.sync_transactions(db, account, days_back=7)


async def _handle_transaction_pending(
    db: AsyncSession,
    enrollment: TellerEnrollment,
    payload: Dict[str, Any],
):
    """Handle transaction.pending webhook - trigger transaction sync."""
    account_id = payload.get("account_id")

    if not account_id:
        logger.warning("transaction.pending webhook missing account_id")
        return

    # Find account
    result = await db.execute(
        select(Account).where(
            Account.teller_enrollment_id == enrollment.id,
            Account.external_account_id == account_id,
        )
    )
    account = result.scalar_one_or_none()

    if account:
        logger.info(f"Pending transaction for account: {account.name}")

        # Trigger transaction sync
        from app.services.teller_service import get_teller_service

        teller_service = get_teller_service()
        await teller_service.sync_transactions(db, account, days_back=7)


async def _handle_balance_updated(
    db: AsyncSession,
    enrollment: TellerEnrollment,
    payload: Dict[str, Any],
):
    """Handle balance.updated webhook - update account balance."""
    account_id = payload.get("account_id")
    new_balance = payload.get("balance", {}).get("available")

    if not account_id or new_balance is None:
        logger.warning("balance.updated webhook missing account_id or balance")
        return

    # Find account
    result = await db.execute(
        select(Account).where(
            Account.teller_enrollment_id == enrollment.id,
            Account.external_account_id == account_id,
        )
    )
    account = result.scalar_one_or_none()

    if account:
        from decimal import Decimal
        from app.utils.datetime_utils import utc_now

        logger.info(f"Updating balance for account: {account.name}")
        account.current_balance = Decimal(str(new_balance))
        account.balance_as_of = utc_now()
        await db.commit()
