"""Service for portfolio rebalancing analysis and target allocations."""

from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.target_allocation import TargetAllocation
from app.schemas.target_allocation import (
    AllocationSlice,
    DriftItem,
    TradeRecommendation,
)

# Preset portfolio allocations
PRESET_PORTFOLIOS: Dict[str, Dict] = {
    "bogleheads_3fund": {
        "name": "Bogleheads Three-Fund Portfolio",
        "allocations": [
            {"asset_class": "domestic", "target_percent": 60, "label": "US Stocks"},
            {"asset_class": "international", "target_percent": 30, "label": "International Stocks"},
            {"asset_class": "bond", "target_percent": 10, "label": "Bonds"},
        ],
    },
    "balanced_60_40": {
        "name": "Balanced 60/40 Portfolio",
        "allocations": [
            {"asset_class": "domestic", "target_percent": 42, "label": "US Stocks"},
            {"asset_class": "international", "target_percent": 18, "label": "International Stocks"},
            {"asset_class": "bond", "target_percent": 40, "label": "Bonds"},
        ],
    },
    "target_date_2050": {
        "name": "Target Date 2050",
        "allocations": [
            {"asset_class": "domestic", "target_percent": 54, "label": "US Stocks"},
            {"asset_class": "international", "target_percent": 36, "label": "International Stocks"},
            {"asset_class": "bond", "target_percent": 10, "label": "Bonds"},
        ],
    },
    "conservative_30_70": {
        "name": "Conservative 30/70 Portfolio",
        "allocations": [
            {"asset_class": "domestic", "target_percent": 21, "label": "US Stocks"},
            {"asset_class": "international", "target_percent": 9, "label": "International Stocks"},
            {"asset_class": "bond", "target_percent": 60, "label": "Bonds"},
            {"asset_class": "cash", "target_percent": 10, "label": "Cash"},
        ],
    },
    "all_weather": {
        "name": "All Weather Portfolio",
        "allocations": [
            {"asset_class": "domestic", "target_percent": 30, "label": "US Stocks"},
            {"asset_class": "bond", "target_percent": 55, "label": "Bonds"},
            {"asset_class": "other", "target_percent": 15, "label": "Alternatives"},
        ],
    },
}


class RebalancingService:
    """Service for portfolio rebalancing calculations."""

    @staticmethod
    def get_presets() -> Dict[str, Dict]:
        """Return preset portfolio allocations."""
        return PRESET_PORTFOLIOS

    @staticmethod
    async def get_active_allocation(
        db: AsyncSession, org_id: UUID, user_id: Optional[UUID] = None
    ) -> Optional[TargetAllocation]:
        """
        Get the active target allocation for an org/user.

        Queries TargetAllocation where is_active=True, ordered by updated_at desc, limit 1.

        Args:
            db: Database session
            org_id: Organization ID
            user_id: Optional user ID for filtering

        Returns:
            Active TargetAllocation or None
        """
        conditions = [
            TargetAllocation.organization_id == org_id,
            TargetAllocation.is_active.is_(True),
        ]

        if user_id is not None:
            conditions.append(TargetAllocation.user_id == user_id)

        result = await db.execute(
            select(TargetAllocation)
            .where(and_(*conditions))
            .order_by(TargetAllocation.updated_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def deactivate_other_allocations(
        db: AsyncSession, org_id: UUID, user_id: UUID, exclude_id: Optional[UUID] = None
    ) -> None:
        """
        Deactivate all active allocations for this org/user except the excluded one.

        Args:
            db: Database session
            org_id: Organization ID
            user_id: User ID
            exclude_id: Optional allocation ID to exclude from deactivation
        """
        conditions = [
            TargetAllocation.organization_id == org_id,
            TargetAllocation.user_id == user_id,
            TargetAllocation.is_active.is_(True),
        ]
        if exclude_id is not None:
            conditions.append(TargetAllocation.id != exclude_id)

        # Lock matching rows first to prevent race condition where two
        # concurrent creates both deactivate and both insert active rows
        await db.execute(
            select(TargetAllocation.id)
            .where(and_(*conditions))
            .with_for_update()
        )

        await db.execute(
            update(TargetAllocation)
            .where(and_(*conditions))
            .values(is_active=False)
        )

    @staticmethod
    def calculate_drift(
        target_slices: List[AllocationSlice],
        current_by_class: Dict[str, Decimal],
        portfolio_total: Decimal,
        threshold: Decimal,
    ) -> Tuple[List[DriftItem], List[TradeRecommendation], bool, Decimal]:
        """
        Calculate portfolio drift from target allocation.

        Args:
            target_slices: List of target allocation slices
            current_by_class: Dict mapping asset_class to current dollar value
            portfolio_total: Total portfolio value
            threshold: Drift threshold percentage for triggering rebalancing

        Returns:
            Tuple of (drift_items, trade_recommendations, needs_rebalancing, max_drift)
        """
        drift_items: List[DriftItem] = []
        trade_recs: List[TradeRecommendation] = []
        max_drift = Decimal("0")
        needs_rebalancing = False

        for slice_ in target_slices:
            current_value = current_by_class.get(slice_.asset_class, Decimal("0"))

            if portfolio_total > 0:
                current_percent = (current_value / portfolio_total * Decimal("100")).quantize(
                    Decimal("0.01")
                )
            else:
                current_percent = Decimal("0")

            target_percent = slice_.target_percent
            drift_percent = (current_percent - target_percent).quantize(Decimal("0.01"))

            target_value = (portfolio_total * target_percent / Decimal("100")).quantize(
                Decimal("0.01")
            )
            drift_value = (current_value - target_value).quantize(Decimal("0.01"))

            # Determine status
            if drift_percent > Decimal("1"):
                status = "overweight"
            elif drift_percent < Decimal("-1"):
                status = "underweight"
            else:
                status = "on_target"

            drift_items.append(
                DriftItem(
                    asset_class=slice_.asset_class,
                    label=slice_.label,
                    target_percent=target_percent,
                    current_percent=current_percent,
                    current_value=current_value,
                    drift_percent=drift_percent,
                    drift_value=drift_value,
                    status=status,
                )
            )

            abs_drift = abs(drift_percent)
            if abs_drift > max_drift:
                max_drift = abs_drift

            # Generate trade recommendation if drift exceeds threshold
            if abs_drift > threshold:
                needs_rebalancing = True
                trade_recs.append(
                    TradeRecommendation(
                        asset_class=slice_.asset_class,
                        label=slice_.label,
                        action="SELL" if drift_percent > 0 else "BUY",
                        amount=abs(drift_value),
                        current_value=current_value,
                        target_value=target_value,
                        current_percent=current_percent,
                        target_percent=target_percent,
                    )
                )

        return drift_items, trade_recs, needs_rebalancing, max_drift
