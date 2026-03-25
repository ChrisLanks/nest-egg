"""Estate and beneficiary planning API endpoints."""

import logging
from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.beneficiary import Beneficiary
from app.models.estate_document import EstateDocument
from app.models.user import User
from app.services.estate_planning_service import EstatePlanningService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Estate Planning"])


# ── Pydantic schemas ──────────────────────────────────────────────────────────


class BeneficiaryCreate(BaseModel):
    account_id: Optional[UUID] = None
    name: str
    relationship: str
    designation_type: str  # "primary" or "contingent"
    percentage: Decimal
    dob: Optional[date] = None
    notes: Optional[str] = None


class EstateDocumentUpsert(BaseModel):
    document_type: str  # will/trust/poa/healthcare_directive/beneficiary_form
    last_reviewed_date: Optional[date] = None
    notes: Optional[str] = None


# ── Calculation endpoints ─────────────────────────────────────────────────────


@router.get(
    "/tax-exposure",
    summary="Federal estate tax exposure",
    description="Estimates federal estate tax above the exemption threshold.",
)
async def get_tax_exposure(
    net_worth: float = Query(..., description="Total net worth (USD)"),
    filing_status: str = Query("single", description="single or married"),
    current_user: User = Depends(get_current_user),
):
    """Returns estate tax exposure above the federal exemption."""
    return EstatePlanningService.calculate_estate_tax_exposure(
        net_worth=Decimal(str(net_worth)),
        filing_status=filing_status,
    )


@router.get(
    "/coverage-summary",
    summary="Beneficiary coverage summary",
    description="Returns what percentage of account value has a primary beneficiary.",
)
async def get_coverage_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Summarizes beneficiary coverage across all accounts."""
    from app.models.account import Account

    acct_result = await db.execute(
        select(Account).where(
            Account.organization_id == current_user.organization_id,
            Account.is_active == True,
        )
    )
    accounts = acct_result.scalars().all()

    ben_result = await db.execute(
        select(Beneficiary).where(
            Beneficiary.organization_id == current_user.organization_id,
        )
    )
    beneficiaries = ben_result.scalars().all()

    acct_dicts = [{"id": a.id, "balance": float(a.balance or 0)} for a in accounts]
    ben_dicts = [
        {"account_id": b.account_id, "designation_type": b.designation_type}
        for b in beneficiaries
    ]

    return EstatePlanningService.get_beneficiary_coverage_summary(acct_dicts, ben_dicts)


# ── Beneficiary CRUD ──────────────────────────────────────────────────────────


@router.get("/beneficiaries", summary="List beneficiaries")
async def list_beneficiaries(
    account_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Beneficiary).where(
        Beneficiary.organization_id == current_user.organization_id,
    )
    if account_id:
        stmt = stmt.where(Beneficiary.account_id == account_id)
    stmt = stmt.order_by(Beneficiary.designation_type, Beneficiary.name)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [
        {
            "id": str(b.id),
            "account_id": str(b.account_id) if b.account_id else None,
            "name": b.name,
            "relationship": b.relationship,
            "designation_type": b.designation_type,
            "percentage": float(b.percentage),
            "dob": b.dob.isoformat() if b.dob else None,
            "notes": b.notes,
        }
        for b in rows
    ]


@router.post("/beneficiaries", summary="Add beneficiary", status_code=201)
async def create_beneficiary(
    body: BeneficiaryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ben = Beneficiary(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        account_id=body.account_id,
        name=body.name,
        relationship=body.relationship,
        designation_type=body.designation_type,
        percentage=body.percentage,
        dob=body.dob,
        notes=body.notes,
    )
    db.add(ben)
    await db.commit()
    await db.refresh(ben)
    return {"id": str(ben.id), "name": ben.name, "percentage": float(ben.percentage)}


@router.delete("/beneficiaries/{beneficiary_id}", summary="Remove beneficiary", status_code=204)
async def delete_beneficiary(
    beneficiary_id: UUID = Path(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Beneficiary).where(
            Beneficiary.id == beneficiary_id,
            Beneficiary.organization_id == current_user.organization_id,
        )
    )
    ben = result.scalar_one_or_none()
    if not ben:
        raise HTTPException(status_code=404, detail="Beneficiary not found")
    await db.delete(ben)
    await db.commit()


# ── Estate documents ──────────────────────────────────────────────────────────


@router.get("/documents", summary="List estate planning documents")
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(EstateDocument).where(
            EstateDocument.organization_id == current_user.organization_id,
            EstateDocument.user_id == current_user.id,
        )
    )
    docs = result.scalars().all()
    return [
        {
            "id": str(d.id),
            "document_type": d.document_type,
            "last_reviewed_date": d.last_reviewed_date.isoformat() if d.last_reviewed_date else None,
            "notes": d.notes,
            "created_at": d.created_at.isoformat(),
        }
        for d in docs
    ]


@router.post("/documents", summary="Create or update estate document record", status_code=201)
async def upsert_document(
    body: EstateDocumentUpsert,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Upsert by document_type per user
    result = await db.execute(
        select(EstateDocument).where(
            EstateDocument.organization_id == current_user.organization_id,
            EstateDocument.user_id == current_user.id,
            EstateDocument.document_type == body.document_type,
        )
    )
    doc = result.scalar_one_or_none()
    if doc:
        doc.last_reviewed_date = body.last_reviewed_date
        doc.notes = body.notes
    else:
        doc = EstateDocument(
            organization_id=current_user.organization_id,
            user_id=current_user.id,
            document_type=body.document_type,
            last_reviewed_date=body.last_reviewed_date,
            notes=body.notes,
        )
        db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return {
        "id": str(doc.id),
        "document_type": doc.document_type,
        "last_reviewed_date": doc.last_reviewed_date.isoformat() if doc.last_reviewed_date else None,
    }
