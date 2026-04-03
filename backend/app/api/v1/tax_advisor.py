"""Tax advisor API endpoints — age-aware tax insights and planning."""

import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services.rate_limit_service import rate_limit_service
from app.services.tax_advisor_service import TaxAdvisorService
from typing import Any, Dict

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/insights", response_model=Dict[str, Any])
async def get_tax_insights(
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get age-based tax insights: SS taxation, LTCG 0%, IRMAA, NII surtax, RMDs."""
    # Rate-limit: tax insight computation (30/min per user)
    await rate_limit_service.check_rate_limit(
        request=http_request,
        max_requests=30,
        window_seconds=60,
        identifier=str(current_user.id),
    )

    service = TaxAdvisorService(db)
    return await service.get_tax_insights(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )