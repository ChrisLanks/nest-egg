"""Settings API endpoints for user profile and organization preferences."""

import csv
import io
import zipfile
from typing import Any, List, Literal, Optional
from uuid import UUID
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user
from app.core.security import hash_password, verify_password
from app.models.account import Account
from app.models.holding import Holding
from app.models.transaction import Transaction
from app.models.user import User, Organization
from app.schemas.user import UserUpdate, OrganizationUpdate
from app.services.email_service import email_service, create_verification_token
from app.services.password_validation_service import password_validation_service
from app.services.rate_limit_service import get_rate_limit_service

router = APIRouter()
rate_limit_service = get_rate_limit_service()


class UserProfileResponse(BaseModel):
    """User profile response."""

    id: UUID
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    birth_day: Optional[int] = None
    birth_month: Optional[int] = None
    birth_year: Optional[int] = None
    is_org_admin: bool
    dashboard_layout: Optional[List[Any]] = None

    model_config = {"from_attributes": True}


class DashboardLayoutUpdate(BaseModel):
    """Request body for updating dashboard widget layout."""

    layout: List[Any]  # list of {id: str, span: 1|2} objects


class ChangePasswordRequest(BaseModel):
    """Request to change password."""

    current_password: str
    new_password: str = Field(
        ...,
        min_length=12,
        description="Password must be at least 12 characters and include uppercase, lowercase, digit, and special character",
    )


class OrganizationPreferencesResponse(BaseModel):
    """Organization preferences response."""

    id: UUID
    name: str
    monthly_start_day: int
    custom_month_end_day: int
    timezone: str

    model_config = {"from_attributes": True}


@router.get("/profile", response_model=UserProfileResponse)
async def get_user_profile(
    current_user: User = Depends(get_current_user),
):
    """Get current user's profile."""
    return UserProfileResponse(
        id=current_user.id,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        display_name=current_user.display_name,
        birth_day=current_user.birthdate.day if current_user.birthdate else None,
        birth_month=current_user.birthdate.month if current_user.birthdate else None,
        birth_year=current_user.birthdate.year if current_user.birthdate else None,
        is_org_admin=current_user.is_org_admin,
        dashboard_layout=current_user.dashboard_layout,
    )


@router.patch("/profile", response_model=UserProfileResponse)
async def update_user_profile(
    update_data: UserUpdate,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update current user's profile.
    Rate limited to 10 updates per hour to prevent abuse.
    """
    # Rate limit: 10 profile updates per hour per IP
    await rate_limit_service.check_rate_limit(
        request=http_request,
        max_requests=10,
        window_seconds=3600,  # 1 hour
    )

    # Update fields
    if update_data.first_name is not None:
        current_user.first_name = update_data.first_name
    if update_data.last_name is not None:
        current_user.last_name = update_data.last_name
    if update_data.display_name is not None:
        current_user.display_name = update_data.display_name

    # Update birthday (requires day, month, and year together)
    birthday_fields = (update_data.birth_day, update_data.birth_month, update_data.birth_year)
    if all(f is not None for f in birthday_fields):
        try:
            current_user.birthdate = date(update_data.birth_year, update_data.birth_month, update_data.birth_day)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid birthday")
    elif any(f is not None for f in birthday_fields):
        raise HTTPException(status_code=400, detail="birth_day, birth_month, and birth_year must all be provided together")

    # Email update — track whether it changed so we can send verification afterwards
    email_changed = False
    if update_data.email is not None and update_data.email != current_user.email:
        # Check if email is already taken
        result = await db.execute(select(User).where(User.email == update_data.email))
        existing_user = result.scalar_one_or_none()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already in use")
        current_user.email = update_data.email
        current_user.email_verified = False  # Require re-verification
        email_changed = True

    await db.commit()
    await db.refresh(current_user)

    # If email was changed, send a verification email to the new address
    if email_changed:
        try:
            raw_token = await create_verification_token(db, current_user.id)
            await email_service.send_verification_email(
                to_email=current_user.email,
                token=raw_token,
                display_name=current_user.display_name or current_user.first_name or current_user.email,
            )
        except Exception:
            pass  # Never fail a profile update because of email sending

    return UserProfileResponse(
        id=current_user.id,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        display_name=current_user.display_name,
        birth_day=current_user.birthdate.day if current_user.birthdate else None,
        birth_month=current_user.birthdate.month if current_user.birthdate else None,
        birth_year=current_user.birthdate.year if current_user.birthdate else None,
        is_org_admin=current_user.is_org_admin,
        dashboard_layout=current_user.dashboard_layout,
    )


@router.put("/dashboard-layout", status_code=204)
async def update_dashboard_layout(
    body: DashboardLayoutUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save the user's customized dashboard widget layout."""
    current_user.dashboard_layout = body.layout
    await db.commit()
    return Response(status_code=204)


@router.post("/profile/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Change user's password with strength validation.
    Rate limited to 10 password changes per hour to allow for legitimate
    retries (wrong current password, validation failures) while preventing abuse.
    """
    # Rate limit: 10 password changes per hour per IP
    await rate_limit_service.check_rate_limit(
        request=http_request,
        max_requests=10,
        window_seconds=3600,  # 1 hour
    )

    # Verify current password
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    # Validate new password strength and check for breaches
    await password_validation_service.validate_and_raise_async(
        password_data.new_password, check_breach=True
    )

    # Update password
    current_user.password_hash = hash_password(password_data.new_password)
    await db.commit()

    return {"message": "Password changed successfully"}


@router.get("/organization", response_model=OrganizationPreferencesResponse)
async def get_organization_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get organization preferences."""
    result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    org = result.scalar_one_or_none()

    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    return OrganizationPreferencesResponse(
        id=org.id,
        name=org.name,
        monthly_start_day=org.monthly_start_day,
        custom_month_end_day=org.custom_month_end_day,
        timezone=org.timezone,
    )


@router.patch("/organization", response_model=OrganizationPreferencesResponse)
async def update_organization_preferences(
    update_data: OrganizationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update organization preferences. Requires org admin."""
    if not current_user.is_org_admin:
        raise HTTPException(
            status_code=403, detail="Only organization admins can update preferences"
        )

    result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    org = result.scalar_one_or_none()

    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Update fields
    if update_data.name is not None:
        org.name = update_data.name
    if update_data.monthly_start_day is not None:
        org.monthly_start_day = update_data.monthly_start_day
    if update_data.custom_month_end_day is not None:
        org.custom_month_end_day = update_data.custom_month_end_day
    if update_data.timezone is not None:
        org.timezone = update_data.timezone

    await db.commit()
    await db.refresh(org)

    return OrganizationPreferencesResponse(
        id=org.id,
        name=org.name,
        monthly_start_day=org.monthly_start_day,
        custom_month_end_day=org.custom_month_end_day,
        timezone=org.timezone,
    )


@router.get("/export")
async def export_data(
    http_request: Request,
    format: Literal["csv"] = Query("csv"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Export all data as a ZIP archive containing CSV files.

    Rate limited to 5 exports per hour.
    """
    await rate_limit_service.check_rate_limit(
        request=http_request,
        max_requests=5,
        window_seconds=3600,
    )

    org_id = current_user.organization_id

    # --- Fetch data ---
    accounts_result = await db.execute(
        select(Account).where(Account.organization_id == org_id).order_by(Account.name)
    )
    accounts = list(accounts_result.scalars().all())

    txn_result = await db.execute(
        select(Transaction)
        .where(Transaction.organization_id == org_id)
        .order_by(Transaction.date.desc())
    )
    transactions = list(txn_result.scalars().all())

    # Build account name lookup
    account_names = {str(a.id): a.name for a in accounts}

    holdings_result = await db.execute(
        select(Holding).where(Holding.organization_id == org_id).order_by(Holding.ticker)
    )
    holdings = list(holdings_result.scalars().all())

    # --- Build in-memory ZIP ---
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:

        # accounts.csv
        acc_buf = io.StringIO()
        acc_writer = csv.writer(acc_buf)
        acc_writer.writerow([
            "id", "name", "type", "institution", "balance",
            "currency", "is_active", "created_at",
        ])
        for a in accounts:
            acc_writer.writerow([
                str(a.id), a.name,
                a.account_type.value if a.account_type else "",
                a.institution_name or "",
                str(a.current_balance),
                a.currency or "USD",
                a.is_active,
                a.created_at.date() if a.created_at else "",
            ])
        zf.writestr("accounts.csv", acc_buf.getvalue())

        # transactions.csv
        txn_buf = io.StringIO()
        txn_writer = csv.writer(txn_buf)
        txn_writer.writerow([
            "id", "date", "merchant_name", "amount", "currency",
            "category", "account", "notes", "is_manual",
        ])
        for t in transactions:
            txn_writer.writerow([
                str(t.id),
                str(t.date),
                t.merchant_name or "",
                str(t.amount),
                t.currency or "USD",
                t.category_primary or "",
                account_names.get(str(t.account_id), ""),
                t.notes or "",
                t.is_manual,
            ])
        zf.writestr("transactions.csv", txn_buf.getvalue())

        # holdings.csv (only if any exist)
        if holdings:
            hld_buf = io.StringIO()
            hld_writer = csv.writer(hld_buf)
            hld_writer.writerow([
                "ticker", "name", "shares", "cost_basis_per_share",
                "current_price", "account",
            ])
            for h in holdings:
                hld_writer.writerow([
                    h.ticker, h.name or "",
                    str(h.shares),
                    str(h.cost_basis_per_share) if h.cost_basis_per_share else "",
                    str(h.current_price) if h.current_price else "",
                    account_names.get(str(h.account_id), ""),
                ])
            zf.writestr("holdings.csv", hld_buf.getvalue())

    zip_buffer.seek(0)
    filename = f"nest-egg-export-{date.today()}.zip"
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


class DeleteAccountRequest(BaseModel):
    """Request body for permanent account deletion (GDPR Article 17)."""

    password: str


@router.delete("/account", status_code=204)
async def delete_account(
    data: DeleteAccountRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Permanently delete the current user's account and all associated data.

    Implements GDPR Article 17 (Right to Erasure). Requires password confirmation.

    - If the current user is the sole member of their organization, the entire
      organization (and all cascading data) is deleted.
    - If other members exist in the organization, only this user account is deleted.

    Rate limited to 3 attempts per hour.
    """
    await rate_limit_service.check_rate_limit(
        request=http_request,
        max_requests=3,
        window_seconds=3600,
    )

    if not verify_password(data.password, current_user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect password")

    # Count active members in the organization
    count_result = await db.execute(
        select(func.count()).select_from(User).where(
            User.organization_id == current_user.organization_id
        )
    )
    member_count = count_result.scalar()

    if member_count == 1:
        # Sole member — delete entire organization; FK CASCADE removes all data
        org = await db.get(Organization, current_user.organization_id)
        if org:
            await db.delete(org)
    else:
        # Household member — delete only this user account
        await db.delete(current_user)

    await db.commit()
    return Response(status_code=204)
