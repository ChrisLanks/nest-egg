/**
 * Central registry of account type group memberships.
 *
 * All UI logic that tests which "bucket" an account_type falls into should
 * import from here. Changing a group here is sufficient — no need to update
 * every component that references the group.
 *
 * DESIGN: Arrays are composed from smaller named arrays (via spread) so
 * groups stay in sync. The `as const` suffix preserves literal types.
 */

import { AccountType } from '../types/account';

// ---------------------------------------------------------------------------
// Atomic building blocks (mirror the Python layer)
// ---------------------------------------------------------------------------

/** Pre-tax employer-sponsored plans (401k family) */
export const EMPLOYER_PLAN_TYPES = [
  AccountType.RETIREMENT_401K,
  AccountType.RETIREMENT_403B,
  AccountType.RETIREMENT_457B,
] as const;

/** IRA family (Traditional, SEP, SIMPLE — all pre-tax by default) */
export const TRADITIONAL_IRA_TYPES = [
  AccountType.RETIREMENT_IRA,
  AccountType.RETIREMENT_SEP_IRA,
  AccountType.RETIREMENT_SIMPLE_IRA,
] as const;

/** Roth family */
export const ROTH_TYPES = [
  AccountType.RETIREMENT_ROTH,
] as const;

/** Tax-free savings vehicles */
export const TAX_FREE_SAVINGS_TYPES = [
  AccountType.HSA,
  AccountType.RETIREMENT_529,
] as const;

// ---------------------------------------------------------------------------
// Composed groups
// ---------------------------------------------------------------------------

/** All retirement types + tax-free savings */
export const ALL_RETIREMENT_TYPES = [
  ...EMPLOYER_PLAN_TYPES,
  ...TRADITIONAL_IRA_TYPES,
  ...ROTH_TYPES,
  ...TAX_FREE_SAVINGS_TYPES,
] as const;

/** Manual accounts that make sense to schedule recurring contributions for. */
export const CONTRIBUTION_ACCOUNT_TYPES = [
  AccountType.SAVINGS,
  AccountType.BROKERAGE,
  ...EMPLOYER_PLAN_TYPES,
  ...TRADITIONAL_IRA_TYPES,
  ...ROTH_TYPES,
  ...TAX_FREE_SAVINGS_TYPES,
] as const;

/** Investment accounts that can have individual holdings tracked. */
export const HOLDINGS_ACCOUNT_TYPES = [
  AccountType.BROKERAGE,
  ...EMPLOYER_PLAN_TYPES,
  ...TRADITIONAL_IRA_TYPES,
  ...ROTH_TYPES,
  ...TAX_FREE_SAVINGS_TYPES,
  AccountType.CRYPTO,
] as const;

/** Asset accounts track a value, not a transaction flow. */
export const ASSET_ACCOUNT_TYPES = [
  AccountType.PROPERTY,
  AccountType.VEHICLE,
  AccountType.COLLECTIBLES,
  AccountType.PRECIOUS_METALS,
  AccountType.BUSINESS_EQUITY,
  AccountType.PRIVATE_EQUITY,
  AccountType.PRIVATE_DEBT,
  AccountType.BOND,
  AccountType.LIFE_INSURANCE_CASH_VALUE,
  AccountType.PENSION,
  AccountType.ANNUITY,
] as const;

/** Debt account types — balance is negative, shown with debt UI. */
export const DEBT_ACCOUNT_TYPES = [
  AccountType.CREDIT_CARD,
  AccountType.LOAN,
  AccountType.STUDENT_LOAN,
  AccountType.MORTGAGE,
] as const;

/** Types that show the tax treatment selector in account settings. */
export const TAX_TREATMENT_ACCOUNT_TYPES = [
  ...ALL_RETIREMENT_TYPES,
  AccountType.BROKERAGE,
] as const;

/** Types that show employer match UI. */
export const EMPLOYER_MATCH_TYPES = EMPLOYER_PLAN_TYPES;

// ---------------------------------------------------------------------------
// Sidebar grouping config
// ---------------------------------------------------------------------------

/** Maps every AccountType to a sidebar section label and sort order. */
export const ACCOUNT_TYPE_SIDEBAR_CONFIG: Record<string, { label: string; order: number }> = {
  [AccountType.CHECKING]:              { label: 'Cash', order: 1 },
  [AccountType.SAVINGS]:               { label: 'Cash', order: 1 },
  [AccountType.MONEY_MARKET]:          { label: 'Cash', order: 1 },
  [AccountType.CD]:                    { label: 'Cash', order: 1 },
  [AccountType.CREDIT_CARD]:           { label: 'Credit Cards', order: 2 },
  [AccountType.BROKERAGE]:             { label: 'Investments', order: 3 },
  [AccountType.PRIVATE_EQUITY]:        { label: 'Investments', order: 3 },
  [AccountType.CRYPTO]:                { label: 'Investments', order: 3 },
  [AccountType.RETIREMENT_401K]:       { label: 'Retirement', order: 4 },
  [AccountType.RETIREMENT_403B]:       { label: 'Retirement', order: 4 },
  [AccountType.RETIREMENT_457B]:       { label: 'Retirement', order: 4 },
  [AccountType.RETIREMENT_IRA]:        { label: 'Retirement', order: 4 },
  [AccountType.RETIREMENT_ROTH]:       { label: 'Retirement', order: 4 },
  [AccountType.RETIREMENT_SEP_IRA]:    { label: 'Retirement', order: 4 },
  [AccountType.RETIREMENT_SIMPLE_IRA]: { label: 'Retirement', order: 4 },
  [AccountType.RETIREMENT_529]:        { label: 'Retirement', order: 4 },
  [AccountType.HSA]:                   { label: 'Retirement', order: 4 },
  [AccountType.PENSION]:               { label: 'Retirement', order: 4 },
  [AccountType.LOAN]:                  { label: 'Loans', order: 5 },
  [AccountType.STUDENT_LOAN]:          { label: 'Loans', order: 5 },
  [AccountType.MORTGAGE]:              { label: 'Loans', order: 5 },
  [AccountType.PROPERTY]:              { label: 'Property', order: 6 },
  [AccountType.VEHICLE]:               { label: 'Property', order: 6 },
  [AccountType.BOND]:                  { label: 'Bonds & Securities', order: 7 },
  [AccountType.STOCK_OPTIONS]:         { label: 'Bonds & Securities', order: 7 },
  [AccountType.PRIVATE_DEBT]:          { label: 'Alternative', order: 8 },
  [AccountType.COLLECTIBLES]:          { label: 'Alternative', order: 8 },
  [AccountType.PRECIOUS_METALS]:       { label: 'Alternative', order: 8 },
  [AccountType.LIFE_INSURANCE_CASH_VALUE]: { label: 'Insurance', order: 9 },
  [AccountType.ANNUITY]:               { label: 'Insurance', order: 9 },
  [AccountType.BUSINESS_EQUITY]:       { label: 'Business', order: 10 },
  [AccountType.MANUAL]:                { label: 'Other', order: 11 },
  [AccountType.OTHER]:                 { label: 'Other', order: 11 },
};
