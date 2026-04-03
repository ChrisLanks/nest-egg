"""HSA optimization API endpoints."""

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Body, Depends, File, HTTPException, Path, Query, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.account import Account, AccountType
from app.models.hsa_receipt import HsaReceipt
from app.models.transaction import Transaction
from app.models.user import User
from app.services.hsa_optimization_service import HsaOptimizationService
from app.services.input_sanitization_service import input_sanitization_service
from app.services.rate_limit_service import rate_limit_service
from app.services.storage_service import StorageService, get_storage_service

# Allowed MIME types for receipt attachments
_ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "application/pdf",
}

logger = logging.getLogger(__name__)


async def _rate_limit(http_request: Request, current_user: User = Depends(get_current_user)):
    """Shared rate-limit dependency for all HSA endpoints."""
    await rate_limit_service.check_rate_limit(
        request=http_request, max_requests=30, window_seconds=60, identifier=str(current_user.id)
    )


router = APIRouter(tags=["HSA Optimization"], dependencies=[Depends(_rate_limit)])


# ── Pydantic schemas ──────────────────────────────────────────────────────────


class HsaReceiptCreate(BaseModel):
    account_id: Optional[UUID] = None
    expense_date: date
    amount: Decimal
    description: str
    category: Optional[str] = None
    tax_year: int
    notes: Optional[str] = None


class HsaReceiptUpdate(BaseModel):
    is_reimbursed: Optional[bool] = None
    reimbursed_at: Optional[date] = None
    notes: Optional[str] = None


class HsaReceiptCreateResponse(BaseModel):
    id: str
    amount: float
    description: str
    tax_year: int
    is_reimbursed: bool
    created_at: str


class HsaReceiptUpdateResponse(BaseModel):
    id: str
    is_reimbursed: bool
    reimbursed_at: Optional[str] = None
    notes: Optional[str] = None


class HsaAttachmentResponse(BaseModel):
    id: str
    file_name: Optional[str] = None
    file_content_type: Optional[str] = None


# ── Calculation endpoints ─────────────────────────────────────────────────────


@router.get(
    "/contribution-headroom",
    summary="HSA contribution headroom",
    description="Returns remaining HSA contribution room for the year.",
)
async def get_contribution_headroom(
    is_family: bool = Query(False, description="True if enrolled in a family HDHP plan"),
    age: int = Query(..., ge=0, le=120, description="Account holder age"),
    year: Optional[int] = Query(None, ge=2000, le=2100, description="Tax year (defaults to current year)"),
    ytd_contributions: float = Query(0.0, ge=0, le=100_000, description="Year-to-date contributions (USD)"),
    current_user: User = Depends(get_current_user),
):
    """Returns remaining HSA contribution room for the year."""
    tax_year = year or date.today().year
    return HsaOptimizationService.calculate_contribution_headroom(
        ytd_contributions=Decimal(str(ytd_contributions)),
        is_family_plan=is_family,
        age=age,
        year=tax_year,
    )


@router.get(
    "/projection",
    summary="HSA invest vs spend projection",
    description=(
        "Projects HSA balance under two strategies: "
        "pay-as-you-go vs invest and pay medical expenses out-of-pocket."
    ),
)
async def get_hsa_projection(
    years: int = Query(20, ge=1, le=50, description="Projection horizon (years)"),
    annual_contribution: float = Query(..., ge=0, le=100_000, description="Annual HSA contribution (USD)"),
    annual_medical: float = Query(..., ge=0, le=1_000_000, description="Annual medical expenses (USD)"),
    current_balance: float = Query(0.0, ge=0, le=10_000_000, description="Current HSA balance (USD)"),
    investment_return: Optional[float] = Query(None, ge=0, le=1.0, description="Annual investment return (default 6%)"),
    current_user: User = Depends(get_current_user),
):
    """Projects HSA invest vs spend strategy over the given horizon."""
    return HsaOptimizationService.project_invest_strategy(
        current_balance=Decimal(str(current_balance)),
        annual_contribution=Decimal(str(annual_contribution)),
        annual_medical_expenses=Decimal(str(annual_medical)),
        years=years,
        investment_return=Decimal(str(investment_return)) if investment_return is not None else None,
    )


# ── Receipt CRUD ──────────────────────────────────────────────────────────────


@router.get(
    "/receipts",
    summary="List HSA receipts",
)
async def list_receipts(
    tax_year: Optional[int] = Query(None, description="Filter by tax year"),
    is_reimbursed: Optional[bool] = Query(None, description="Filter by reimbursement status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns all HSA receipts for the current user."""
    stmt = select(HsaReceipt).where(
        HsaReceipt.organization_id == current_user.organization_id,
        HsaReceipt.user_id == current_user.id,
    )
    if tax_year is not None:
        stmt = stmt.where(HsaReceipt.tax_year == tax_year)
    if is_reimbursed is not None:
        stmt = stmt.where(HsaReceipt.is_reimbursed == is_reimbursed)
    stmt = stmt.order_by(HsaReceipt.expense_date.desc())

    result = await db.execute(stmt)
    receipts = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "account_id": str(r.account_id) if r.account_id else None,
            "expense_date": r.expense_date.isoformat(),
            "amount": float(r.amount),
            "description": r.description,
            "category": r.category,
            "is_reimbursed": r.is_reimbursed,
            "reimbursed_at": r.reimbursed_at.isoformat() if r.reimbursed_at else None,
            "tax_year": r.tax_year,
            "notes": r.notes,
            "file_name": r.file_name,
            "file_content_type": r.file_content_type,
            "has_attachment": r.file_key is not None,
            "created_at": r.created_at.isoformat(),
        }
        for r in receipts
    ]


@router.post(
    "/receipts",
    summary="Create HSA receipt",
    status_code=201,
    response_model=HsaReceiptCreateResponse,
)
async def create_receipt(
    body: HsaReceiptCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Creates a new HSA receipt record."""
    description = input_sanitization_service.sanitize_html(body.description)
    notes = input_sanitization_service.sanitize_html(body.notes) if body.notes else body.notes
    receipt = HsaReceipt(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        account_id=body.account_id,
        expense_date=body.expense_date,
        amount=body.amount,
        description=description,
        category=body.category,
        tax_year=body.tax_year,
        notes=notes,
        is_reimbursed=False,
    )
    db.add(receipt)
    await db.commit()
    await db.refresh(receipt)
    return HsaReceiptCreateResponse(
        id=str(receipt.id),
        amount=float(receipt.amount),
        description=receipt.description,
        tax_year=receipt.tax_year,
        is_reimbursed=receipt.is_reimbursed,
        created_at=receipt.created_at.isoformat(),
    )


@router.patch(
    "/receipts/{receipt_id}",
    summary="Update HSA receipt reimbursement status",
    response_model=HsaReceiptUpdateResponse,
)
async def update_receipt(
    receipt_id: UUID = Path(...),
    body: HsaReceiptUpdate = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Updates the reimbursement status or notes on an HSA receipt."""
    result = await db.execute(
        select(HsaReceipt).where(
            HsaReceipt.id == receipt_id,
            HsaReceipt.organization_id == current_user.organization_id,
            HsaReceipt.user_id == current_user.id,
        )
    )
    receipt = result.scalar_one_or_none()
    if not receipt:
        raise HTTPException(status_code=404, detail="HSA receipt not found")

    if body.is_reimbursed is not None:
        receipt.is_reimbursed = body.is_reimbursed
    if body.reimbursed_at is not None:
        receipt.reimbursed_at = body.reimbursed_at
    if body.notes is not None:
        receipt.notes = input_sanitization_service.sanitize_html(body.notes)

    await db.commit()
    await db.refresh(receipt)
    return HsaReceiptUpdateResponse(
        id=str(receipt.id),
        is_reimbursed=receipt.is_reimbursed,
        reimbursed_at=receipt.reimbursed_at.isoformat() if receipt.reimbursed_at else None,
        notes=receipt.notes,
    )


# ── YTD summary ───────────────────────────────────────────────────────────────


@router.get(
    "/ytd-summary",
    summary="HSA year-to-date contribution and expense summary",
    description=(
        "Aggregates transactions from HSA accounts for the current year. "
        "Returns ytd_contributions (positive amounts) and ytd_medical_expenses (absolute value of negatives)."
    ),
)
async def get_ytd_summary(
    year: Optional[int] = Query(None, description="Tax year (defaults to current year)"),
    user_id: Optional[UUID] = Query(None, description="Filter to a specific household member"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns YTD contribution and medical expense totals from linked HSA accounts."""
    tax_year = year or datetime.utcnow().year
    start = date(tax_year, 1, 1)
    end = date(tax_year, 12, 31)

    # Find HSA accounts scoped to org (and optionally a specific user)
    acct_stmt = select(Account.id).where(
        Account.organization_id == current_user.organization_id,
        Account.account_type == AccountType.HSA,
    )
    if user_id:
        acct_stmt = acct_stmt.where(Account.user_id == user_id)
    acct_result = await db.execute(acct_stmt)
    hsa_account_ids = [row[0] for row in acct_result.fetchall()]

    if not hsa_account_ids:
        return {
            "year": tax_year,
            "ytd_contributions": 0.0,
            "ytd_medical_expenses": 0.0,
            "hsa_accounts_found": 0,
        }

    # Positive transactions = contributions; negative = withdrawals/medical
    txn_result = await db.execute(
        select(Transaction.amount).where(
            and_(
                Transaction.organization_id == current_user.organization_id,
                Transaction.account_id.in_(hsa_account_ids),
                Transaction.date >= start,
                Transaction.date <= end,
                Transaction.is_pending.is_(False),
            )
        )
    )
    amounts = [row[0] for row in txn_result.fetchall()]

    ytd_contributions = float(sum(a for a in amounts if a > 0))
    ytd_medical_expenses = float(abs(sum(a for a in amounts if a < 0)))

    return {
        "year": tax_year,
        "ytd_contributions": ytd_contributions,
        "ytd_medical_expenses": ytd_medical_expenses,
        "hsa_accounts_found": len(hsa_account_ids),
    }


# ── Receipt file attachment ───────────────────────────────────────────────────


@router.post(
    "/receipts/{receipt_id}/attachment",
    summary="Upload a file attachment for an HSA receipt",
    status_code=200,
    response_model=HsaAttachmentResponse,
)
async def upload_receipt_attachment(
    receipt_id: UUID = Path(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
):
    """Uploads a receipt image or PDF and stores the file key on the receipt record."""
    content_type = file.content_type or ""
    if content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{content_type}'. Allowed: image/jpeg, image/png, image/gif, image/webp, application/pdf.",
        )

    result = await db.execute(
        select(HsaReceipt).where(
            HsaReceipt.id == receipt_id,
            HsaReceipt.organization_id == current_user.organization_id,
            HsaReceipt.user_id == current_user.id,
        )
    )
    receipt = result.scalar_one_or_none()
    if not receipt:
        raise HTTPException(status_code=404, detail="HSA receipt not found")

    data = await file.read()
    if len(data) > 20 * 1024 * 1024:  # 20 MB cap
        raise HTTPException(status_code=413, detail="File too large (max 20 MB)")

    ext = (file.filename or "receipt").rsplit(".", 1)[-1] if "." in (file.filename or "") else "bin"
    key = f"hsa-receipts/{current_user.organization_id}/{receipt_id}/{uuid4()}.{ext}"
    await storage.save(key, data, content_type=content_type)

    receipt.file_key = key
    receipt.file_name = file.filename
    receipt.file_content_type = content_type
    await db.commit()

    return HsaAttachmentResponse(
        id=str(receipt.id),
        file_name=receipt.file_name,
        file_content_type=receipt.file_content_type,
    )


@router.get(
    "/receipts/{receipt_id}/attachment",
    summary="Download the file attachment for an HSA receipt",
)
async def download_receipt_attachment(
    receipt_id: UUID = Path(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
):
    """Returns the raw bytes of the stored receipt file."""
    result = await db.execute(
        select(HsaReceipt).where(
            HsaReceipt.id == receipt_id,
            HsaReceipt.organization_id == current_user.organization_id,
            HsaReceipt.user_id == current_user.id,
        )
    )
    receipt = result.scalar_one_or_none()
    if not receipt:
        raise HTTPException(status_code=404, detail="HSA receipt not found")
    if not receipt.file_key:
        raise HTTPException(status_code=404, detail="No attachment found for this receipt")

    try:
        data = await storage.load(receipt.file_key)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Attachment file not found in storage")

    return StreamingResponse(
        iter([data]),
        media_type=receipt.file_content_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{receipt.file_name or "receipt"}"',
            "Content-Length": str(len(data)),
        },
    )
