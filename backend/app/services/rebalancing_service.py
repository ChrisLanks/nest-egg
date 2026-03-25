"""Service for portfolio rebalancing analysis and target allocations."""

from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.financial import PORTFOLIO
from app.models.target_allocation import TargetAllocation
from app.schemas.target_allocation import (
    AllocationSlice,
    DriftItem,
    TradeRecommendation,
)

# Re-export from centralized constants for backward compatibility
PRESET_PORTFOLIOS = PORTFOLIO.PRESETS


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
        await db.execute(select(TargetAllocation.id).where(and_(*conditions)).with_for_update())

        await db.execute(update(TargetAllocation).where(and_(*conditions)).values(is_active=False))

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

    @staticmethod
    def calculate_drift_simple(
        current_allocations: dict[str, float],
        target_allocations: dict[str, float],
    ) -> list[dict]:
        """
        Calculates drift of each asset class from target.

        Returns list of {asset_class, current_pct, target_pct, drift_pct, severity, needs_action}

        Severity thresholds:
        - "ok"       : |drift| < warning_threshold
        - "warning"  : warning_threshold <= |drift| < critical_threshold
        - "critical" : |drift| >= critical_threshold
        """
        try:
            from app.constants.financial import PORTFOLIO

            warning_threshold = float(getattr(PORTFOLIO, "DRIFT_THRESHOLD_WARNING_PCT", 5.0))
            critical_threshold = float(getattr(PORTFOLIO, "DRIFT_THRESHOLD_CRITICAL_PCT", 10.0))
        except (ImportError, AttributeError):
            warning_threshold = 5.0
            critical_threshold = 10.0

        results = []
        all_classes = set(current_allocations) | set(target_allocations)
        for asset_class in sorted(all_classes):
            current = current_allocations.get(asset_class, 0.0)
            target = target_allocations.get(asset_class, 0.0)
            drift = current - target
            abs_drift = abs(drift)
            severity = "ok"
            if abs_drift >= critical_threshold:
                severity = "critical"
            elif abs_drift >= warning_threshold:
                severity = "warning"
            results.append(
                {
                    "asset_class": asset_class,
                    "current_pct": round(current, 2),
                    "target_pct": round(target, 2),
                    "drift_pct": round(drift, 2),
                    "severity": severity,
                    "needs_action": abs_drift >= warning_threshold,
                }
            )
        return results

    @staticmethod
    def generate_tax_aware_trades(
        current_allocations: dict[str, float],
        target_allocations: dict[str, float],
        account_tax_treatments: list[dict],
        total_portfolio_value: float,
    ) -> list[dict]:
        """
        Generates rebalancing trades preferring tax-advantaged accounts.

        Tax preference order: tax_free > pre_tax > taxable (avoid taxable events).
        Returns list of {action, asset_class, amount, preferred_account_treatment, reason}

        Trades smaller than $100 are skipped as not worth the friction.
        """
        trades = []

        for asset_class in sorted(set(current_allocations) | set(target_allocations)):
            current_val = current_allocations.get(asset_class, 0.0) / 100 * total_portfolio_value
            target_val = target_allocations.get(asset_class, 0.0) / 100 * total_portfolio_value
            delta = target_val - current_val

            if abs(delta) < 100:  # Skip tiny trades
                continue

            action = "buy" if delta > 0 else "sell"
            # Prefer tax-advantaged for sells (avoids capital gains)
            preferred_treatment = "pre_tax" if action == "sell" else "tax_free"
            trades.append(
                {
                    "action": action,
                    "asset_class": asset_class,
                    "amount": round(abs(delta), 2),
                    "preferred_account_treatment": preferred_treatment,
                    "reason": (
                        f"{'Increase' if action == 'buy' else 'Reduce'} {asset_class} "
                        f"by ${abs(delta):,.0f}. "
                        f"Prefer {preferred_treatment} accounts to minimize tax impact."
                    ),
                }
            )
        return trades
