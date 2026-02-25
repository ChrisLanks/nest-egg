"""Utility functions for determining account tax treatment.

Prefer using the `Account.tax_treatment` field directly when you have an
Account instance.  These helpers are for cases where you only have an
AccountType and an optional TaxTreatment value.
"""

from typing import Optional

from app.models.account import AccountType, TaxTreatment
from app.utils.account_type_groups import TAX_TREATMENT_DEFAULTS


# Mapping from TaxTreatment enum → display category string
_TREATMENT_TO_CATEGORY = {
    TaxTreatment.PRE_TAX: "tax-deferred",
    TaxTreatment.ROTH: "tax-free",
    TaxTreatment.TAX_FREE: "tax-free",
    TaxTreatment.TAXABLE: "taxable",
}

# Fallback when tax_treatment is NULL — infer from account_type.
# Built from TAX_TREATMENT_DEFAULTS + additional display-only entries.
_TYPE_FALLBACK: dict[AccountType, str] = {
    at: _TREATMENT_TO_CATEGORY[tt]
    for at, tt in TAX_TREATMENT_DEFAULTS.items()
}
_TYPE_FALLBACK.update({
    AccountType.PENSION: "tax-deferred",
    AccountType.BROKERAGE: "taxable",
    AccountType.CHECKING: "taxable",
    AccountType.SAVINGS: "taxable",
    AccountType.MONEY_MARKET: "taxable",
    AccountType.CD: "taxable",
})


def get_tax_treatment(
    account_type: AccountType,
    tax_treatment: Optional[TaxTreatment] = None,
) -> str:
    """Get the tax treatment category for an account.

    Args:
        account_type: The account's AccountType.
        tax_treatment: The account's TaxTreatment field (preferred). If None,
                       falls back to inferring from account_type.

    Returns:
        "tax-deferred": Traditional IRA, 401k, pension (taxed on withdrawal)
        "tax-free": Roth IRA, Roth 401k, HSA, 529 (qualified withdrawals tax-free)
        "taxable": Brokerage, checking, savings (capital gains / interest taxes)
        "other": Other account types
    """
    if tax_treatment is not None:
        return _TREATMENT_TO_CATEGORY.get(tax_treatment, "other")
    return _TYPE_FALLBACK.get(account_type, "other")


def get_tax_treatment_label(
    account_type: AccountType,
    tax_treatment: Optional[TaxTreatment] = None,
) -> str:
    """Get a human-readable tax treatment label."""
    labels = {
        "tax-deferred": "Tax-Deferred",
        "tax-free": "Tax-Free",
        "taxable": "Taxable",
        "other": "Other",
    }
    return labels.get(get_tax_treatment(account_type, tax_treatment), "Other")


def get_tax_treatment_description(
    account_type: AccountType,
    tax_treatment: Optional[TaxTreatment] = None,
) -> str:
    """Get a detailed description of the tax treatment."""
    descriptions = {
        "tax-deferred": "Contributions may be tax-deductible. Growth is tax-deferred. Withdrawals are taxed as ordinary income.",
        "tax-free": "Contributions made with after-tax dollars. Growth and qualified withdrawals are tax-free.",
        "taxable": "No special tax treatment. Investment gains are subject to capital gains tax.",
        "other": "Tax treatment varies by account type.",
    }
    return descriptions.get(get_tax_treatment(account_type, tax_treatment), "Tax treatment varies.")
