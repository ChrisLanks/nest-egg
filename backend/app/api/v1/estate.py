"""Estate and beneficiary planning API endpoints."""

import logging
from datetime import date
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.account import Account
from app.models.beneficiary import Beneficiary
from app.models.estate_document import EstateDocument
from app.models.user import User
from app.services.estate_planning_service import EstatePlanningService
from app.utils.account_type_groups import CORE_RETIREMENT_TYPES

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


# ── Beneficiary audit ────────────────────────────────────────────────────────


@router.get("/beneficiary-audit", summary="Per-account beneficiary coverage audit")
async def get_beneficiary_audit(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Audit every account for missing or incomplete beneficiary designations."""
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

    # Group beneficiaries by account_id
    bens_by_account: dict = {}
    for b in beneficiaries:
        bens_by_account.setdefault(str(b.account_id), []).append(b)

    # Account types that require beneficiary designations
    _BENEFICIARY_RELEVANT = {
        "retirement_401k", "retirement_ira", "retirement_roth_ira",
        "retirement_403b", "retirement_457b", "retirement_sep_ira",
        "retirement_simple_ira", "retirement_roth", "brokerage",
        "life_insurance",
    }

    audit_accounts = []
    total_audited = 0
    fully_covered = 0
    missing_primary = 0
    missing_contingent = 0
    pct_issues = 0

    for acct in accounts:
        acct_type = acct.account_type.value if hasattr(acct.account_type, "value") else str(acct.account_type)
        if acct_type not in _BENEFICIARY_RELEVANT:
            continue

        total_audited += 1
        account_bens = bens_by_account.get(str(acct.id), [])
        primary_bens = [b for b in account_bens if b.designation_type == "primary"]
        contingent_bens = [b for b in account_bens if b.designation_type == "contingent"]

        issues = []
        if not primary_bens:
            issues.append("missing_primary")
            missing_primary += 1
        else:
            primary_total = sum(float(b.percentage) for b in primary_bens)
            if abs(primary_total - 100.0) > 0.5:
                issues.append("primary_pct_not_100")
                pct_issues += 1
        if not contingent_bens:
            issues.append("missing_contingent")
            missing_contingent += 1
        for b in primary_bens + contingent_bens:
            if b.dob and (date.today().year - b.dob.year) < 18 and not any(
                d in (b.notes or "") for d in ["trust", "UTMA", "custodian"]
            ):
                issues.append("minor_no_trust")
                break

        if not issues:
            fully_covered += 1
            severity = "ok"
        elif "missing_primary" in issues:
            severity = "critical"
        else:
            severity = "warning"

        audit_accounts.append({
            "account_id": str(acct.id),
            "account_name": acct.name,
            "account_type": acct_type,
            "current_balance": float(acct.current_balance or 0),
            "issues": list(dict.fromkeys(issues)),  # deduplicate, preserve order
            "severity": severity,
            "beneficiaries": [
                {
                    "name": b.name,
                    "designation_type": b.designation_type,
                    "percentage": float(b.percentage),
                }
                for b in account_bens
            ],
        })

    overall_score = round((fully_covered / total_audited * 100) if total_audited > 0 else 100)

    return {
        "summary": {
            "total_accounts_audited": total_audited,
            "fully_covered": fully_covered,
            "missing_primary": missing_primary,
            "missing_contingent": missing_contingent,
            "percentage_issues": pct_issues,
            "overall_score": overall_score,
        },
        "accounts": audit_accounts,
    }


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


# ── Beneficiary Audit ─────────────────────────────────────────────────────────

# Account type strings that should have beneficiary designations
_AUDITABLE_TYPE_STRINGS = {
    "retirement_401k", "retirement_403b", "retirement_457b",
    "retirement_ira", "retirement_roth", "retirement_sep_ira",
    "retirement_simple_ira", "brokerage", "life_insurance_cash_value", "annuity",
}


class AuditBeneficiary(BaseModel):
    name: str
    designation_type: str  # primary / contingent
    percentage: float
    relationship: str


class AuditAccountResult(BaseModel):
    account_id: str
    account_name: str
    account_type: str
    current_balance: float
    issues: List[str]
    severity: str  # "ok" | "warning" | "critical"
    beneficiaries: List[AuditBeneficiary]


class BeneficiaryAuditSummary(BaseModel):
    total_accounts_audited: int
    fully_covered: int
    missing_primary: int
    missing_contingent: int
    percentage_issues: int
    overall_score: int  # 0–100


class BeneficiaryAuditResponse(BaseModel):
    summary: BeneficiaryAuditSummary
    accounts: List[AuditAccountResult]


@router.get(
    "/beneficiary-audit",
    response_model=BeneficiaryAuditResponse,
    summary="Beneficiary coverage audit",
)
async def get_beneficiary_audit(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Audit beneficiary designations across all retirement and investment accounts."""
    # Fetch auditable accounts
    acct_result = await db.execute(
        select(Account).where(
            Account.organization_id == current_user.organization_id,
            Account.is_active == True,
        )
    )
    all_accounts = acct_result.scalars().all()
    auditable = [a for a in all_accounts if str(a.account_type) in _AUDITABLE_TYPE_STRINGS]

    # Fetch all beneficiaries for this org
    ben_result = await db.execute(
        select(Beneficiary).where(
            Beneficiary.organization_id == current_user.organization_id,
        )
    )
    all_bens = ben_result.scalars().all()

    # Group by account_id
    bens_by_account: dict = {}
    for b in all_bens:
        key = str(b.account_id) if b.account_id else "_estate"
        bens_by_account.setdefault(key, []).append(b)

    account_results: List[AuditAccountResult] = []
    total = len(auditable)
    missing_primary = 0
    missing_contingent = 0
    pct_issues = 0
    fully_covered = 0

    for acct in auditable:
        acct_id = str(acct.id)
        bens = bens_by_account.get(acct_id, [])
        primaries = [b for b in bens if b.designation_type == "primary"]
        contingents = [b for b in bens if b.designation_type == "contingent"]

        issues: List[str] = []
        if not primaries:
            issues.append("missing_primary")
            missing_primary += 1
        if not contingents:
            issues.append("missing_contingent")
            missing_contingent += 1
        primary_pct = sum(float(b.percentage) for b in primaries)
        if primaries and abs(primary_pct - 100.0) > 0.5:
            issues.append("primary_pct_not_100")
            pct_issues += 1

        if not issues:
            fully_covered += 1

        severity = "ok"
        if "missing_primary" in issues:
            severity = "critical"
        elif issues:
            severity = "warning"

        account_results.append(AuditAccountResult(
            account_id=acct_id,
            account_name=acct.name or str(acct.account_type),
            account_type=str(acct.account_type),
            current_balance=float(acct.current_balance or 0),
            issues=issues,
            severity=severity,
            beneficiaries=[
                AuditBeneficiary(
                    name=b.name,
                    designation_type=b.designation_type,
                    percentage=float(b.percentage),
                    relationship=b.relationship or "",
                )
                for b in bens
            ],
        ))

    # Sort: critical first, then warning, then ok
    severity_order = {"critical": 0, "warning": 1, "ok": 2}
    account_results.sort(key=lambda a: severity_order[a.severity])

    overall_score = int((fully_covered / total * 100)) if total > 0 else 100

    return BeneficiaryAuditResponse(
        summary=BeneficiaryAuditSummary(
            total_accounts_audited=total,
            fully_covered=fully_covered,
            missing_primary=missing_primary,
            missing_contingent=missing_contingent,
            percentage_issues=pct_issues,
            overall_score=overall_score,
        ),
        accounts=account_results,
    )
