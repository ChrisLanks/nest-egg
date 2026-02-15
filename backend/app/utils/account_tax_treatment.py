"""Utility functions for determining account tax treatment."""

from app.models.account import AccountType


def get_tax_treatment(account_type: AccountType) -> str:
    """Get the tax treatment category for an account type.

    Returns:
        "tax-deferred": Traditional IRA, 401k (taxed on withdrawal)
        "tax-free": Roth IRA, Roth 401k, HSA (contributions are taxed, growth tax-free)
        "taxable": Brokerage (capital gains taxes on appreciation)
        "other": Other account types
    """
    tax_deferred = [
        AccountType.RETIREMENT_401K,  # Traditional 401(k)
        AccountType.RETIREMENT_IRA,  # Traditional IRA
        AccountType.PENSION,
    ]

    tax_free = [
        AccountType.RETIREMENT_ROTH,  # Roth IRA/401(k)
        AccountType.HSA,  # Triple tax-advantaged if used for medical
    ]

    taxable = [
        AccountType.BROKERAGE,
        AccountType.CHECKING,
        AccountType.SAVINGS,
        AccountType.MONEY_MARKET,
        AccountType.CD,
    ]

    if account_type in tax_deferred:
        return "tax-deferred"
    elif account_type in tax_free:
        return "tax-free"
    elif account_type in taxable:
        return "taxable"
    else:
        return "other"


def get_tax_treatment_label(account_type: AccountType) -> str:
    """Get a human-readable tax treatment label."""
    treatment = get_tax_treatment(account_type)

    labels = {
        "tax-deferred": "Tax-Deferred",
        "tax-free": "Tax-Free",
        "taxable": "Taxable",
        "other": "Other",
    }

    return labels.get(treatment, "Other")


def get_tax_treatment_description(account_type: AccountType) -> str:
    """Get a detailed description of the tax treatment."""
    treatment = get_tax_treatment(account_type)

    descriptions = {
        "tax-deferred": "Contributions may be tax-deductible. Growth is tax-deferred. Withdrawals are taxed as ordinary income.",
        "tax-free": "Contributions made with after-tax dollars. Growth and qualified withdrawals are tax-free.",
        "taxable": "No special tax treatment. Investment gains are subject to capital gains tax.",
        "other": "Tax treatment varies by account type.",
    }

    return descriptions.get(treatment, "Tax treatment varies.")
