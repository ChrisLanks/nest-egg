"""Reports API endpoints."""

import re
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import (
    get_all_household_accounts,
    get_current_user,
    get_user_accounts,
    verify_household_member,
)
from app.models.account import Account, AccountType
from app.models.report_template import ReportTemplate
from app.models.user import User
from app.schemas.tax_harvesting import (
    TaxLossHarvestingSummaryResponse,
    TaxLossOpportunityResponse,
)
from app.services.deduplication_service import DeduplicationService
from app.services.report_service import ReportService
from app.services.tax_loss_harvesting_service import tax_loss_harvesting_service
from app.utils.datetime_utils import utc_now

# Allowed characters in Content-Disposition filenames
_SAFE_FILENAME_RE = re.compile(r"[^a-zA-Z0-9_.\-]")

_GUEST_USER_ID_FILTER_FORBIDDEN = HTTPException(
    status_code=403,
    detail="Guests cannot filter reports by individual member",
)

router = APIRouter()
deduplication_service = DeduplicationService()


# Pydantic schemas


VALID_REPORT_TYPES = {
    "income_expense",
    "cash_flow",
    "net_worth",
    "category_breakdown",
    "tax_summary",
    "investment_performance",
    "custom",
}

VALID_DELIVERY_FREQUENCIES = {"daily", "weekly", "monthly"}


class ReportTemplateCreate(BaseModel):
    """Schema for creating a report template."""

    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    report_type: str
    config: Dict[str, Any]
    is_shared: bool = False

    @field_validator("report_type")
    @classmethod
    def validate_report_type(cls, v: str) -> str:
        """Validate report_type is a known type."""
        if v not in VALID_REPORT_TYPES:
            raise ValueError(
                f"report_type must be one of: {', '.join(sorted(VALID_REPORT_TYPES))}"
            )
        return v


class ReportTemplateUpdate(BaseModel):
    """Schema for updating a report template."""

    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    is_shared: Optional[bool] = None
    scheduled_delivery: Optional[Dict[str, Any]] = None

    @field_validator("scheduled_delivery")
    @classmethod
    def validate_scheduled_delivery(cls, v: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Validate scheduled_delivery frequency when present."""
        if v is None:
            return v
        frequency = v.get("frequency")
        if frequency is not None and frequency not in VALID_DELIVERY_FREQUENCIES:
            raise ValueError(
                f"scheduled_delivery.frequency must be one of: {', '.join(sorted(VALID_DELIVERY_FREQUENCIES))}"
            )
        return v


class ReportTemplateResponse(BaseModel):
    """Schema for report template response."""

    id: str
    organization_id: str
    name: str
    description: Optional[str]
    report_type: str
    config: Dict[str, Any]
    is_shared: bool
    created_by_user_id: str
    created_at: str
    updated_at: str
    scheduled_delivery: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class ExecuteReportRequest(BaseModel):
    """Schema for executing a report."""

    config: Dict[str, Any]


# Endpoints


@router.get("/templates", response_model=List[ReportTemplateResponse])
async def list_report_templates(
    after: Optional[str] = Query(
        None, description="Cursor: return templates updated before this ISO datetime"
    ),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all report templates for the organization.

    Returns templates created by the current user and shared templates.
    Uses keyset pagination on updated_at (descending).
    """
    from datetime import datetime

    conditions = [
        ReportTemplate.organization_id == current_user.organization_id,
        (
            (ReportTemplate.created_by_user_id == current_user.id)
            | (ReportTemplate.is_shared.is_(True))
        ),
    ]
    if after:
        try:
            cursor_dt = datetime.fromisoformat(after)
        except ValueError:
            from fastapi import HTTPException

            raise HTTPException(status_code=400, detail="Invalid cursor format")
        conditions.append(ReportTemplate.updated_at < cursor_dt)

    result = await db.execute(
        select(ReportTemplate)
        .where(and_(*conditions))
        .order_by(ReportTemplate.updated_at.desc())
        .limit(limit)
    )

    templates = result.scalars().all()

    return [
        ReportTemplateResponse(
            id=str(template.id),
            organization_id=str(template.organization_id),
            name=template.name,
            description=template.description,
            report_type=template.report_type,
            config=template.config,
            is_shared=template.is_shared,
            created_by_user_id=str(template.created_by_user_id),
            created_at=template.created_at.isoformat(),
            updated_at=template.updated_at.isoformat(),
            scheduled_delivery=template.scheduled_delivery,
        )
        for template in templates
    ]


@router.post("/templates", response_model=ReportTemplateResponse, status_code=201)
async def create_report_template(
    template_data: ReportTemplateCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new report template."""
    template = ReportTemplate(
        organization_id=current_user.organization_id,
        name=template_data.name,
        description=template_data.description,
        report_type=template_data.report_type,
        config=template_data.config,
        is_shared=template_data.is_shared,
        created_by_user_id=current_user.id,
        created_at=utc_now(),
        updated_at=utc_now(),
    )

    db.add(template)
    await db.commit()
    await db.refresh(template)

    return ReportTemplateResponse(
        id=str(template.id),
        organization_id=str(template.organization_id),
        name=template.name,
        description=template.description,
        report_type=template.report_type,
        config=template.config,
        is_shared=template.is_shared,
        created_by_user_id=str(template.created_by_user_id),
        created_at=template.created_at.isoformat(),
        updated_at=template.updated_at.isoformat(),
        scheduled_delivery=template.scheduled_delivery,
    )


@router.get("/templates/{template_id}", response_model=ReportTemplateResponse)
async def get_report_template(
    template_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific report template."""
    result = await db.execute(
        select(ReportTemplate).where(
            and_(
                ReportTemplate.id == template_id,
                ReportTemplate.organization_id == current_user.organization_id,
            )
        )
    )

    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Report template not found")

    # Check access: must be creator or template must be shared
    if template.created_by_user_id != current_user.id and not template.is_shared:
        raise HTTPException(status_code=403, detail="Access denied")

    return ReportTemplateResponse(
        id=str(template.id),
        organization_id=str(template.organization_id),
        name=template.name,
        description=template.description,
        report_type=template.report_type,
        config=template.config,
        is_shared=template.is_shared,
        created_by_user_id=str(template.created_by_user_id),
        created_at=template.created_at.isoformat(),
        updated_at=template.updated_at.isoformat(),
        scheduled_delivery=template.scheduled_delivery,
    )


@router.patch("/templates/{template_id}", response_model=ReportTemplateResponse)
async def update_report_template(
    template_id: UUID,
    template_data: ReportTemplateUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a report template."""
    result = await db.execute(
        select(ReportTemplate).where(
            and_(
                ReportTemplate.id == template_id,
                ReportTemplate.organization_id == current_user.organization_id,
            )
        )
    )

    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Report template not found")

    # Only creator can update
    if template.created_by_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the creator can update this template")

    # Update fields
    if template_data.name is not None:
        template.name = template_data.name
    if template_data.description is not None:
        template.description = template_data.description
    if template_data.config is not None:
        template.config = template_data.config
    if template_data.is_shared is not None:
        template.is_shared = template_data.is_shared
    if template_data.scheduled_delivery is not None:
        template.scheduled_delivery = template_data.scheduled_delivery

    template.updated_at = utc_now()

    await db.commit()
    await db.refresh(template)

    return ReportTemplateResponse(
        id=str(template.id),
        organization_id=str(template.organization_id),
        name=template.name,
        description=template.description,
        report_type=template.report_type,
        config=template.config,
        is_shared=template.is_shared,
        created_by_user_id=str(template.created_by_user_id),
        created_at=template.created_at.isoformat(),
        updated_at=template.updated_at.isoformat(),
        scheduled_delivery=template.scheduled_delivery,
    )


@router.delete("/templates/{template_id}", status_code=204)
async def delete_report_template(
    template_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a report template."""
    result = await db.execute(
        select(ReportTemplate).where(
            and_(
                ReportTemplate.id == template_id,
                ReportTemplate.organization_id == current_user.organization_id,
            )
        )
    )

    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Report template not found")

    # Only creator can delete
    if template.created_by_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the creator can delete this template")

    await db.delete(template)
    await db.commit()


@router.post("/execute")
async def execute_report(
    request: ExecuteReportRequest,
    user_id: Optional[UUID] = Query(None, description="Filter by user"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Execute a report with given configuration.

    Does not save the report - use for preview/one-time reports.
    """
    # Get accounts based on user filter
    if user_id:
        if getattr(current_user, "_is_guest", False):
            raise _GUEST_USER_ID_FILTER_FORBIDDEN
        await verify_household_member(db, user_id, current_user.organization_id)
        accounts = await get_user_accounts(db, user_id, current_user.organization_id)
    else:
        accounts = await get_all_household_accounts(db, current_user.organization_id)
        accounts = deduplication_service.deduplicate_accounts(accounts)

    account_ids = [acc.id for acc in accounts]

    # Execute report
    result = await ReportService.execute_report(
        db,
        current_user.organization_id,
        request.config,
        user_id,
        account_ids,
    )

    return result


@router.get("/templates/{template_id}/execute")
async def execute_saved_report(
    template_id: UUID,
    user_id: Optional[UUID] = Query(None, description="Filter by user"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Execute a saved report template."""
    # Load template
    result = await db.execute(
        select(ReportTemplate).where(
            and_(
                ReportTemplate.id == template_id,
                ReportTemplate.organization_id == current_user.organization_id,
            )
        )
    )

    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Report template not found")

    # Check access
    if template.created_by_user_id != current_user.id and not template.is_shared:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get accounts based on user filter
    if user_id:
        if getattr(current_user, "_is_guest", False):
            raise _GUEST_USER_ID_FILTER_FORBIDDEN
        await verify_household_member(db, user_id, current_user.organization_id)
        accounts = await get_user_accounts(db, user_id, current_user.organization_id)
    else:
        accounts = await get_all_household_accounts(db, current_user.organization_id)
        accounts = deduplication_service.deduplicate_accounts(accounts)

    account_ids = [acc.id for acc in accounts]

    # Execute report
    report_result = await ReportService.execute_report(
        db,
        current_user.organization_id,
        template.config,
        user_id,
        account_ids,
    )

    return {
        **report_result,
        "template": {
            "id": str(template.id),
            "name": template.name,
            "description": template.description,
        },
    }


@router.get("/templates/{template_id}/export")
async def export_report_csv(
    template_id: UUID,
    user_id: Optional[UUID] = Query(None, description="Filter by user"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export a saved report as CSV."""
    # Load and authorize template first
    result = await db.execute(
        select(ReportTemplate).where(
            and_(
                ReportTemplate.id == template_id,
                ReportTemplate.organization_id == current_user.organization_id,
            )
        )
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Report template not found")

    # Check access: must be creator or template must be shared
    if template.created_by_user_id != current_user.id and not template.is_shared:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get accounts based on user filter
    if user_id:
        if getattr(current_user, "_is_guest", False):
            raise _GUEST_USER_ID_FILTER_FORBIDDEN
        await verify_household_member(db, user_id, current_user.organization_id)
        accounts = await get_user_accounts(db, user_id, current_user.organization_id)
    else:
        accounts = await get_all_household_accounts(db, current_user.organization_id)
        accounts = deduplication_service.deduplicate_accounts(accounts)

    account_ids = [acc.id for acc in accounts]

    # Generate CSV
    try:
        csv_data = await ReportService.generate_export_csv(
            db,
            current_user.organization_id,
            template_id,
            user_id,
            account_ids,
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Report template not found")

    # Sanitize filename for Content-Disposition header
    raw_name = template.name.lower().replace(" ", "_") if template else "report"
    safe_name = _SAFE_FILENAME_RE.sub("", raw_name)[:80] or "report"
    filename = f"{safe_name}_report.csv"

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/tax-loss-harvesting", response_model=TaxLossHarvestingSummaryResponse)
async def get_tax_loss_harvesting(
    user_id: Optional[UUID] = Query(
        None, description="Filter by user. None = combined household view"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get tax-loss harvesting opportunities."""
    account_ids = None
    if user_id:
        if getattr(current_user, "_is_guest", False):
            raise _GUEST_USER_ID_FILTER_FORBIDDEN
        await verify_household_member(db, user_id, current_user.organization_id)
        user_accounts = await get_user_accounts(db, user_id, current_user.organization_id)
        account_ids = {acc.id for acc in user_accounts}

    opportunities = await tax_loss_harvesting_service.get_opportunities(
        db=db,
        organization_id=current_user.organization_id,
        account_ids=account_ids,
    )

    total_losses = sum(o.unrealized_loss for o in opportunities)
    total_savings = sum(o.estimated_tax_savings for o in opportunities)

    return TaxLossHarvestingSummaryResponse(
        opportunities=[TaxLossOpportunityResponse(**vars(o)) for o in opportunities],
        total_harvestable_losses=total_losses,
        total_estimated_tax_savings=total_savings,
    )


@router.get("/household-summary")
async def get_household_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a household financial summary aggregating all members' accounts.

    Returns total net worth, assets, liabilities, member count,
    and a per-member breakdown.
    """
    org_id = current_user.organization_id

    # Debt account types for liability classification
    debt_types = {
        AccountType.CREDIT_CARD,
        AccountType.LOAN,
        AccountType.STUDENT_LOAN,
        AccountType.MORTGAGE,
    }

    # Fetch all active accounts for the household (organization)
    result = await db.execute(
        select(Account).where(
            and_(
                Account.organization_id == org_id,
                Account.is_active.is_(True),
            )
        )
    )
    accounts = result.scalars().all()

    # Get all household members
    member_result = await db.execute(
        select(User).where(
            and_(
                User.organization_id == org_id,
                User.is_active.is_(True),
            )
        )
    )
    members = member_result.scalars().all()

    # Aggregate per-member
    from collections import defaultdict
    from decimal import Decimal

    member_stats: Dict[UUID, Dict[str, Any]] = defaultdict(
        lambda: {"net_worth": Decimal("0"), "accounts_count": 0}
    )

    total_assets = Decimal("0")
    total_liabilities = Decimal("0")

    for account in accounts:
        balance = account.current_balance or Decimal("0")
        uid = account.user_id

        if account.account_type in debt_types:
            # Debt balances are stored as positive values but represent liabilities
            total_liabilities += abs(balance)
            member_stats[uid]["net_worth"] -= abs(balance)
        else:
            total_assets += balance
            member_stats[uid]["net_worth"] += balance

        member_stats[uid]["accounts_count"] += 1

    total_net_worth = total_assets - total_liabilities

    per_member_breakdown = []
    for member in members:
        stats = member_stats.get(member.id, {"net_worth": Decimal("0"), "accounts_count": 0})
        per_member_breakdown.append(
            {
                "user_id": str(member.id),
                "display_name": member.display_name or member.email,
                "net_worth": float(stats["net_worth"]),
                "accounts_count": stats["accounts_count"],
            }
        )

    return {
        "total_household_net_worth": float(total_net_worth),
        "total_household_assets": float(total_assets),
        "total_household_liabilities": float(total_liabilities),
        "member_count": len(members),
        "per_member_breakdown": per_member_breakdown,
    }
