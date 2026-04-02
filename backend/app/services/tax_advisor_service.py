"""Age-based tax advisor service.

Provides personalized tax guidance that changes as a person ages:
- Social Security benefit taxation (combined income thresholds)
- Long-term capital gains 0% bracket opportunity
- Medicare IRMAA surcharge awareness
- Net Investment Income (NII) 3.8% surtax
- RMD planning and impact on tax brackets
- Age-based deduction increases (65+ standard deduction bump)
- Retirement contribution limit changes (50+/55+ catch-ups)
"""

import logging
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.financial import (
    CRYPTO_TAX,
    MEDICARE,
    RENTAL,
    RETIREMENT,
    SS,
    TAX,
)
from app.constants.financial import (
    RMD as RMD_CONSTANTS,
)
from app.models.account import Account, AccountType, RentalType, TaxTreatment
from app.models.user import User

logger = logging.getLogger(__name__)


def get_ltcg_rate(taxable_income: float, filing_status: str = "single") -> float:
    """Get the long-term capital gains tax rate for a given income level."""
    brackets = TAX.LTCG_BRACKETS_SINGLE if filing_status == "single" else TAX.LTCG_BRACKETS_MARRIED
    for threshold, rate in brackets:
        if taxable_income <= threshold:
            return rate
    return brackets[-1][1]


def get_ss_taxable_pct(combined_income: float, filing_status: str = "single") -> float:
    """Get the percentage of Social Security benefits that are taxable."""
    thresholds = (
        TAX.SS_TAXATION_THRESHOLDS_SINGLE
        if filing_status == "single"
        else TAX.SS_TAXATION_THRESHOLDS_MARRIED
    )
    for threshold, pct in thresholds:
        if combined_income <= threshold:
            return pct
    return thresholds[-1][1]


def compute_nii_surtax(
    magi: float,
    net_investment_income: float,
    filing_status: str = "single",
) -> float:
    """Compute Net Investment Income Tax (3.8% surtax)."""
    threshold = TAX.NII_THRESHOLD_SINGLE if filing_status == "single" else TAX.NII_THRESHOLD_MARRIED
    if magi <= threshold:
        return 0.0
    excess = magi - threshold
    taxable_nii = min(excess, net_investment_income)
    return round(taxable_nii * TAX.NII_SURTAX_RATE, 2)


class TaxAdvisorService:
    """Generates age-aware tax insights and recommendations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_tax_insights(
        self,
        organization_id: UUID,
        user_id: UUID,
    ) -> Dict[str, Any]:
        """Generate tax insights based on user age and finances."""
        # Get user info
        user_result = await self.db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if not user or not user.birthdate:
            return {
                "error": "Birthdate required for tax insights",
                "insights": [],
            }

        today = date.today()
        age = (
            today.year
            - user.birthdate.year
            - ((today.month, today.day) < (user.birthdate.month, user.birthdate.day))
        )

        # Get account balances by tax treatment
        acct_result = await self.db.execute(
            select(Account).where(
                Account.organization_id == organization_id,
                Account.is_active.is_(True),
            )
        )
        accounts = list(acct_result.scalars().all())

        pre_tax_total = Decimal("0")
        roth_total = Decimal("0")
        taxable_total = Decimal("0")
        hsa_total = Decimal("0")

        for acct in accounts:
            bal = acct.current_balance or Decimal("0")
            if acct.tax_treatment == TaxTreatment.PRE_TAX:
                pre_tax_total += bal
            elif acct.tax_treatment == TaxTreatment.ROTH:
                roth_total += bal
            elif acct.tax_treatment == TaxTreatment.TAX_FREE:
                hsa_total += bal
            elif acct.account_type in (
                AccountType.BROKERAGE,
                AccountType.CRYPTO,
            ):
                taxable_total += bal

        # Detect STR and crypto accounts for targeted insights
        str_accounts = [
            a for a in accounts
            if a.is_rental_property and a.rental_type == RentalType.SHORT_TERM_RENTAL
        ]
        crypto_accounts = [a for a in accounts if a.account_type == AccountType.CRYPTO]

        insights: List[Dict[str, Any]] = []
        contribution_limits: List[Dict[str, Any]] = []

        # --- Contribution limit guidance ---
        _add_contribution_limits(age, contribution_limits)

        # --- Age-based standard deduction ---
        if age >= MEDICARE.ELIGIBILITY_AGE:
            extra_s = TAX.STANDARD_DEDUCTION_OVER_65_EXTRA_SINGLE
            extra_m = TAX.STANDARD_DEDUCTION_OVER_65_EXTRA_MARRIED
            total_s = TAX.STANDARD_DEDUCTION_SINGLE + extra_s
            insights.append(
                {
                    "category": "deduction",
                    "title": "Age 65+ Standard Deduction Increase",
                    "description": (
                        f"You qualify for an additional "
                        f"${extra_s:,} standard deduction "
                        f"(single) or ${extra_m:,} per spouse "
                        f"(married). Total for single 65+: "
                        f"${total_s:,}."
                    ),
                    "priority": "info",
                    "age_relevant": True,
                }
            )

        # --- 0% LTCG bracket opportunity ---
        zero_pct = TAX.LTCG_BRACKETS_SINGLE[0][0]
        if taxable_total > 0:
            insights.append(
                {
                    "category": "capital_gains",
                    "title": "0% Long-Term Capital Gains Bracket",
                    "description": (
                        f"Single filers with taxable income "
                        f"up to ${zero_pct:,.0f} pay 0% on "
                        f"long-term capital gains. Consider "
                        f"harvesting gains tax-free. You have "
                        f"${float(taxable_total):,.0f} in "
                        f"taxable accounts."
                    ),
                    "priority": "action" if age >= SS.PLANNING_START_AGE else "info",
                    "age_relevant": age >= RETIREMENT.CATCH_UP_AGE_HSA,
                }
            )

        # --- Social Security taxation ---
        if age >= SS.PLANNING_START_AGE:
            ss_thresh = TAX.SS_TAXATION_THRESHOLDS_SINGLE[0][0]
            insights.append(
                {
                    "category": "social_security",
                    "title": "Social Security Taxation Planning",
                    "description": (
                        "Up to 85% of SS benefits can be taxed. "
                        f"For single filers, taxation starts at "
                        f"combined income above "
                        f"${ss_thresh:,.0f}. Consider Roth "
                        "conversions before claiming to reduce "
                        "taxable income later. Combined income "
                        "= AGI + nontaxable interest + 50% of "
                        "SS benefits."
                    ),
                    "priority": "action" if age >= SS.MIN_CLAIMING_AGE else "info",
                    "age_relevant": True,
                }
            )

        # --- Medicare IRMAA ---
        if age >= MEDICARE.IRMAA_PLANNING_AGE:
            irmaa_thresh = MEDICARE.IRMAA_BRACKETS_SINGLE[0][0]
            tier1_b = MEDICARE.IRMAA_BRACKETS_SINGLE[1][1]
            tier1_d = MEDICARE.IRMAA_BRACKETS_SINGLE[1][2]
            insights.append(
                {
                    "category": "medicare",
                    "title": "Medicare IRMAA Surcharge Planning",
                    "description": (
                        f"Medicare premiums increase above "
                        f"${irmaa_thresh:,.0f} MAGI (single). "
                        f"IRMAA uses income from 2 years prior. "
                        f"Tier 1 adds ${tier1_b:.2f}/mo Part B "
                        f"+ ${tier1_d:.2f}/mo Part D. Plan "
                        f"income carefully before enrollment."
                    ),
                    "priority": "action" if age >= MEDICARE.IRMAA_PLANNING_AGE else "info",
                    "age_relevant": True,
                }
            )

        # --- RMD planning ---
        if age >= MEDICARE.ELIGIBILITY_AGE:
            rmd_age = RMD_CONSTANTS.TRIGGER_AGE
            years_to_rmd = max(rmd_age - age, 0)
            pre_tax_f = float(pre_tax_total)
            rmd_status = (
                "RMDs are required now."
                if age >= rmd_age
                else f"{years_to_rmd} years until RMDs begin."
            )
            insights.append(
                {
                    "category": "rmd",
                    "title": (f"Required Minimum Distributions " f"(Age {rmd_age})"),
                    "description": (
                        f"RMDs begin at age {rmd_age}. You have "
                        f"${pre_tax_f:,.0f} in pre-tax accounts."
                        f" {rmd_status} Consider Roth conversions"
                        " before RMDs to reduce future taxable "
                        "distributions. RMD penalty is 25% of "
                        "any shortfall (10% if corrected within "
                        "2 years)."
                    ),
                    "priority": ("action" if years_to_rmd <= 5 else "info"),
                    "age_relevant": True,
                }
            )

        # --- Roth conversion opportunity ---
        if pre_tax_total > 50000 and age >= RETIREMENT.CATCH_UP_AGE_HSA:
            pre_tax_f = float(pre_tax_total)
            insights.append(
                {
                    "category": "roth_conversion",
                    "title": "Roth Conversion Opportunity Window",
                    "description": (
                        f"With ${pre_tax_f:,.0f} in pre-tax "
                        "accounts, consider strategic Roth "
                        "conversions during lower-income years "
                        "(e.g., between retirement and SS/RMDs)."
                        " This reduces future RMDs and creates "
                        "tax-free income in retirement. Fill up "
                        "to the top of your current tax bracket."
                    ),
                    "priority": "action",
                    "age_relevant": True,
                }
            )

        # --- NII surtax ---
        nii_s = TAX.NII_THRESHOLD_SINGLE
        nii_m = TAX.NII_THRESHOLD_MARRIED
        insights.append(
            {
                "category": "nii_surtax",
                "title": "Net Investment Income Tax (3.8%)",
                "description": (
                    f"A 3.8% surtax applies to investment "
                    f"income when MAGI exceeds ${nii_s:,} "
                    f"(single) or ${nii_m:,} (married). "
                    "This affects capital gains, dividends, "
                    "interest, and rental income. Consider "
                    "timing gains to manage MAGI."
                ),
                "priority": "info",
                "age_relevant": False,
            }
        )

        # --- HSA triple tax advantage ---
        if age < 65 and hsa_total > 0:
            hsa_f = float(hsa_total)
            hsa_ind = RETIREMENT.LIMIT_HSA_INDIVIDUAL
            hsa_fam = RETIREMENT.LIMIT_HSA_FAMILY
            catch_up_note = ""
            if age >= 55:
                cu = RETIREMENT.LIMIT_HSA_CATCH_UP
                catch_up_note = f", +${cu:,} catch-up (55+)"
            insights.append(
                {
                    "category": "hsa",
                    "title": "HSA Triple Tax Advantage",
                    "description": (
                        f"Your HSA has ${hsa_f:,.0f}. After 65, "
                        "HSA withdrawals for any purpose are "
                        "taxed like a traditional IRA (no 20% "
                        "penalty). For medical expenses, "
                        "withdrawals remain tax-free at any age."
                        f" Max: ${hsa_ind:,} (individual) / "
                        f"${hsa_fam:,} (family)"
                        f"{catch_up_note}."
                    ),
                    "priority": "info",
                    "age_relevant": True,
                }
            )

        # --- Short-Term Rental (STR) tax loophole ---
        if str_accounts and RENTAL.STR_LOOPHOLE_ACTIVE:
            str_names = ", ".join(a.name for a in str_accounts[:3])
            insights.append(
                {
                    "category": "rental",
                    "title": "Short-Term Rental (STR) Tax Opportunity",
                    "description": (
                        f"You have {len(str_accounts)} short-term rental propert"
                        f"{'y' if len(str_accounts) == 1 else 'ies'} ({str_names}). "
                        f"STRs with average stays ≤{RENTAL.STR_AVG_RENTAL_DAYS_THRESHOLD} days "
                        f"may qualify for the IRC §469 material participation exception — "
                        f"rental losses can offset ordinary income (bypassing the "
                        f"${RENTAL.PASSIVE_LOSS_ALLOWANCE_MAX:,}/yr passive loss limit that "
                        f"applies to long-term rentals). You must materially participate "
                        f"(≥750 hrs/yr or meet one of the 7 IRS tests). Consult a CPA."
                    ),
                    "priority": "action",
                    "age_relevant": False,
                }
            )

        # --- Crypto: no wash-sale rule ---
        if crypto_accounts and CRYPTO_TAX.IS_PROPERTY:
            crypto_bal = sum(float(a.current_balance or 0) for a in crypto_accounts)
            insights.append(
                {
                    "category": "capital_gains",
                    "title": "Crypto Has No Wash-Sale Rule",
                    "description": (
                        f"You have ${crypto_bal:,.0f} in crypto holdings. "
                        f"Unlike stocks, crypto is classified as property (IRC §1221) — "
                        f"the wash-sale rule (IRC §1091) does not apply. "
                        f"You can sell crypto at a loss to harvest a tax deduction and "
                        f"immediately repurchase it. This flexibility makes crypto a "
                        f"powerful tax-loss harvesting tool if you have unrealized losses."
                    ),
                    "priority": "info",
                    "age_relevant": False,
                }
            )

        return {
            "age": age,
            "pre_tax_total": float(pre_tax_total),
            "roth_total": float(roth_total),
            "taxable_total": float(taxable_total),
            "hsa_total": float(hsa_total),
            "insights": insights,
            "contribution_limits": contribution_limits,
            "tax_constants": {
                "standard_deduction_single": TAX.STANDARD_DEDUCTION_SINGLE,
                "standard_deduction_married": TAX.STANDARD_DEDUCTION_MARRIED,
                "ltcg_0pct_threshold_single": TAX.LTCG_BRACKETS_SINGLE[0][0],
                "ltcg_0pct_threshold_married": TAX.LTCG_BRACKETS_MARRIED[0][0],
                "nii_surtax_rate": TAX.NII_SURTAX_RATE,
                "rmd_trigger_age": RMD_CONSTANTS.TRIGGER_AGE,
                "medicare_eligibility_age": MEDICARE.ELIGIBILITY_AGE,
            },
        }


def _add_contribution_limits(age: int, limits: List[Dict[str, Any]]) -> None:
    """Add age-appropriate contribution limit guidance."""
    catch_up = age >= 50

    limits.append(
        {
            "account_type": "401k/403b/457b",
            "base_limit": RETIREMENT.LIMIT_401K,
            "catch_up_limit": (RETIREMENT.LIMIT_401K_CATCH_UP if catch_up else 0),
            "total_limit": RETIREMENT.LIMIT_401K
            + (RETIREMENT.LIMIT_401K_CATCH_UP if catch_up else 0),
            "catch_up_eligible": catch_up,
            "total_with_employer": RETIREMENT.LIMIT_401K_TOTAL,
        }
    )

    limits.append(
        {
            "account_type": "IRA (Traditional/Roth)",
            "base_limit": RETIREMENT.LIMIT_IRA,
            "catch_up_limit": (RETIREMENT.LIMIT_IRA_CATCH_UP if catch_up else 0),
            "total_limit": RETIREMENT.LIMIT_IRA
            + (RETIREMENT.LIMIT_IRA_CATCH_UP if catch_up else 0),
            "catch_up_eligible": catch_up,
        }
    )

    if age < MEDICARE.ELIGIBILITY_AGE:
        hsa_catch_up = age >= 55
        limits.append(
            {
                "account_type": "HSA (requires HDHP)",
                "base_limit_individual": RETIREMENT.LIMIT_HSA_INDIVIDUAL,
                "base_limit_family": RETIREMENT.LIMIT_HSA_FAMILY,
                "catch_up_limit": (RETIREMENT.LIMIT_HSA_CATCH_UP if hsa_catch_up else 0),
                "catch_up_eligible": hsa_catch_up,
            }
        )

    limits.append(
        {
            "account_type": "529 Plan",
            "annual_gift_exclusion": (RETIREMENT.LIMIT_529_ANNUAL_GIFT_EXCLUSION),
            "superfunding": RETIREMENT.LIMIT_529_SUPERFUND,
            "note": (
                "Per beneficiary, per donor. " "Superfunding allows 5-year gift tax averaging."
            ),
        }
    )
