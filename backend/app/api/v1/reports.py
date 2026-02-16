"""Reports API endpoints."""

from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, Query
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import (
    get_current_user,
    verify_household_member,
    get_user_accounts,
    get_all_household_accounts
)
from app.models.user import User
from app.models.report_template import ReportTemplate
from app.services.report_service import ReportService
from app.services.deduplication_service import DeduplicationService

router = APIRouter()
deduplication_service = DeduplicationService()


# Pydantic schemas

class ReportTemplateCreate(BaseModel):
    """Schema for creating a report template."""
    name: str
    description: Optional[str] = None
    report_type: str
    config: Dict[str, Any]
    is_shared: bool = False


class ReportTemplateUpdate(BaseModel):
    """Schema for updating a report template."""
    name: Optional[str] = None
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    is_shared: Optional[bool] = None


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

    class Config:
        from_attributes = True


class ExecuteReportRequest(BaseModel):
    """Schema for executing a report."""
    config: Dict[str, Any]


# Endpoints

@router.get("/templates", response_model=List[ReportTemplateResponse])
async def list_report_templates(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all report templates for the organization.

    Returns templates created by the current user and shared templates.
    """
    result = await db.execute(
        select(ReportTemplate)
        .where(
            and_(
                ReportTemplate.organization_id == current_user.organization_id,
                (
                    (ReportTemplate.created_by_user_id == current_user.id) |
                    (ReportTemplate.is_shared == True)
                )
            )
        )
        .order_by(ReportTemplate.updated_at.desc())
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
    from datetime import datetime

    template = ReportTemplate(
        organization_id=current_user.organization_id,
        name=template_data.name,
        description=template_data.description,
        report_type=template_data.report_type,
        config=template_data.config,
        is_shared=template_data.is_shared,
        created_by_user_id=current_user.id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
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
                ReportTemplate.organization_id == current_user.organization_id
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
    )


@router.patch("/templates/{template_id}", response_model=ReportTemplateResponse)
async def update_report_template(
    template_id: UUID,
    template_data: ReportTemplateUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a report template."""
    from datetime import datetime

    result = await db.execute(
        select(ReportTemplate).where(
            and_(
                ReportTemplate.id == template_id,
                ReportTemplate.organization_id == current_user.organization_id
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

    template.updated_at = datetime.utcnow()

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
                ReportTemplate.organization_id == current_user.organization_id
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
                ReportTemplate.organization_id == current_user.organization_id
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
        }
    }


@router.get("/templates/{template_id}/export")
async def export_report_csv(
    template_id: UUID,
    user_id: Optional[UUID] = Query(None, description="Filter by user"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export a saved report as CSV."""
    # Get accounts based on user filter
    if user_id:
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
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Load template for filename
    result = await db.execute(
        select(ReportTemplate).where(ReportTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()

    filename = f"{template.name.lower().replace(' ', '_')}_report.csv" if template else "report.csv"

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )
