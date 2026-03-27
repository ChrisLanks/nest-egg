"""ESPP (Employee Stock Purchase Plan) tax calculation service.

Handles Section 423 qualified ESPP taxation for:
- Qualifying dispositions (held >2 yr from offering, >1 yr from purchase)
- Disqualifying dispositions (sold before qualifying period ends)
"""

from __future__ import annotations

from decimal import Decimal

from app.constants.financial import ESPP


class ESPPService:
    """Calculate ESPP disposition tax implications."""

    MAX_DISCOUNT_RATE = ESPP.MAX_DISCOUNT_RATE
    ANNUAL_PURCHASE_LIMIT = ESPP.ANNUAL_PURCHASE_LIMIT

    @staticmethod
    def calculate_ordinary_income(
        purchase_price: Decimal,
        fmv_at_purchase: Decimal,
        shares: Decimal,
    ) -> Decimal:
        """Ordinary income for disqualifying disposition = (FMV at purchase - purchase price) * shares."""
        return (fmv_at_purchase - purchase_price) * shares

    @staticmethod
    def calculate_qualifying_gain(
        purchase_price: Decimal,
        fmv_at_sale: Decimal,
        shares: Decimal,
    ) -> Decimal:
        """Total gain on a qualifying disposition (before splitting ordinary vs capital)."""
        return (fmv_at_sale - purchase_price) * shares

    @staticmethod
    def calculate_disqualifying_gain(
        fmv_at_purchase: Decimal,
        fmv_at_sale: Decimal,
        shares: Decimal,
    ) -> Decimal:
        """Capital gain portion on a disqualifying disposition (FMV at sale - FMV at purchase)."""
        return (fmv_at_sale - fmv_at_purchase) * shares


espp_service = ESPPService()
