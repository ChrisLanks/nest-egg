"""
Central registry of AccountType group memberships.

All other modules should import from here instead of defining their own
inline lists.  Groups are frozensets of AccountType enum members so they
can be used in ``in`` tests, SQLAlchemy ``.in_()``, and set operations.

DESIGN: Sets are composed from named atomic building blocks so that a
new type added to, say, EMPLOYER_PLAN_TYPES automatically propagates
to every set built on it.
"""

from app.models.account import AccountType, TaxTreatment

# ---------------------------------------------------------------------------
# Atomic building blocks
# ---------------------------------------------------------------------------

#: Pre-tax employer-sponsored plans (401k family)
EMPLOYER_PLAN_TYPES: frozenset[AccountType] = frozenset({
    AccountType.RETIREMENT_401K,
    AccountType.RETIREMENT_403B,
    AccountType.RETIREMENT_457B,
})

#: IRA family (Traditional, SEP, SIMPLE — all pre-tax by default)
TRADITIONAL_IRA_TYPES: frozenset[AccountType] = frozenset({
    AccountType.RETIREMENT_IRA,
    AccountType.RETIREMENT_SEP_IRA,
    AccountType.RETIREMENT_SIMPLE_IRA,
})

#: Roth family (after-tax, no RMD during owner's lifetime)
ROTH_TYPES: frozenset[AccountType] = frozenset({
    AccountType.RETIREMENT_ROTH,
})

#: Tax-free savings vehicles (not employer plans, not Roth)
TAX_FREE_SAVINGS_TYPES: frozenset[AccountType] = frozenset({
    AccountType.HSA,
    AccountType.RETIREMENT_529,
})

# ---------------------------------------------------------------------------
# Composed retirement groups
# ---------------------------------------------------------------------------

#: All retirement account types that hold investment assets
CORE_RETIREMENT_TYPES: frozenset[AccountType] = (
    EMPLOYER_PLAN_TYPES | TRADITIONAL_IRA_TYPES | ROTH_TYPES
)

#: All retirement types + tax-free savings
ALL_RETIREMENT_TYPES: frozenset[AccountType] = (
    CORE_RETIREMENT_TYPES | TAX_FREE_SAVINGS_TYPES
)

#: RMD-applicable accounts: pre-tax plans + PENSION (no ROTH, HSA, 529)
#: Per IRS rules: Roth IRAs do NOT require RMDs during owner's lifetime
RMD_ACCOUNT_TYPES: frozenset[AccountType] = (
    EMPLOYER_PLAN_TYPES | TRADITIONAL_IRA_TYPES | frozenset({AccountType.PENSION})
)

#: Types that show employer match UI
EMPLOYER_MATCH_TYPES: frozenset[AccountType] = EMPLOYER_PLAN_TYPES

#: Types eligible for Roth conversion analysis
#: Note: actual filter also checks tax_treatment != ROTH at query time
ROTH_CONVERSION_ELIGIBLE_TYPES: frozenset[AccountType] = CORE_RETIREMENT_TYPES

# ---------------------------------------------------------------------------
# Investment / holdings groups
# ---------------------------------------------------------------------------

#: Accounts that can hold securities/crypto.
#: MANUAL and OTHER included for user-tracked private investments.
INVESTMENT_ACCOUNT_TYPES: frozenset[AccountType] = (
    frozenset({
        AccountType.BROKERAGE,
        AccountType.CRYPTO,
        AccountType.MANUAL,
        AccountType.OTHER,
    })
    | ALL_RETIREMENT_TYPES
)

#: Cash account types (used in style-box Cash breakdown)
CASH_ACCOUNT_TYPES: frozenset[AccountType] = frozenset({
    AccountType.CHECKING,
    AccountType.SAVINGS,
    AccountType.MONEY_MARKET,
})

# ---------------------------------------------------------------------------
# Debt / liability groups
# ---------------------------------------------------------------------------

#: True liability types (balance is a debt, not an asset)
DEBT_ACCOUNT_TYPES: frozenset[AccountType] = frozenset({
    AccountType.CREDIT_CARD,
    AccountType.LOAN,
    AccountType.STUDENT_LOAN,
    AccountType.MORTGAGE,
})

#: Amortizing loan types (interest rate + scheduled payments).
#: Credit cards excluded — they use revolving logic, not amortization.
AMORTIZING_LOAN_TYPES: frozenset[AccountType] = frozenset({
    AccountType.MORTGAGE,
    AccountType.LOAN,
    AccountType.STUDENT_LOAN,
})

# ---------------------------------------------------------------------------
# Cash-flow exclusion groups
# ---------------------------------------------------------------------------

#: Manual accounts excluded from cash flow by default.
MANUAL_EXCLUDE_CASH_FLOW_TYPES: frozenset[AccountType] = (
    AMORTIZING_LOAN_TYPES | frozenset({AccountType.CREDIT_CARD})
)

#: Plaid-linked accounts excluded from cash flow by default.
#: Credit cards intentionally NOT excluded — purchases show in cash flow.
PLAID_EXCLUDE_CASH_FLOW_TYPES: frozenset[AccountType] = AMORTIZING_LOAN_TYPES

# ---------------------------------------------------------------------------
# Net worth exclusion
# ---------------------------------------------------------------------------

#: Types that default to EXCLUDED from net worth when include_in_networth is NULL.
#: Note: PRIVATE_EQUITY has a secondary rule (excluded unless public) handled in code.
NET_WORTH_EXCLUDED_BY_DEFAULT: frozenset[AccountType] = frozenset({
    AccountType.VEHICLE,
    AccountType.COLLECTIBLES,
    AccountType.OTHER,
    AccountType.MANUAL,
    AccountType.PENSION,
})

# ---------------------------------------------------------------------------
# Tax treatment defaults
# ---------------------------------------------------------------------------

#: Default TaxTreatment to assign when creating a new account with no explicit value.
TAX_TREATMENT_DEFAULTS: dict[AccountType, TaxTreatment] = {
    AccountType.RETIREMENT_401K:       TaxTreatment.PRE_TAX,
    AccountType.RETIREMENT_403B:       TaxTreatment.PRE_TAX,
    AccountType.RETIREMENT_457B:       TaxTreatment.PRE_TAX,
    AccountType.RETIREMENT_IRA:        TaxTreatment.PRE_TAX,
    AccountType.RETIREMENT_SEP_IRA:    TaxTreatment.PRE_TAX,
    AccountType.RETIREMENT_SIMPLE_IRA: TaxTreatment.PRE_TAX,
    AccountType.RETIREMENT_ROTH:       TaxTreatment.ROTH,
    AccountType.HSA:                   TaxTreatment.TAX_FREE,
    AccountType.RETIREMENT_529:        TaxTreatment.TAX_FREE,
}
