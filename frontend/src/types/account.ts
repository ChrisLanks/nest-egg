/**
 * Account types
 */

export enum PropertyType {
  PERSONAL_RESIDENCE = 'personal_residence',
  INVESTMENT = 'investment',
  VACATION_HOME = 'vacation_home',
}

export enum AccountType {
  // Cash & Checking
  CHECKING = 'checking',
  SAVINGS = 'savings',
  MONEY_MARKET = 'money_market',
  CD = 'cd',

  // Credit & Debt
  CREDIT_CARD = 'credit_card',
  LOAN = 'loan',
  STUDENT_LOAN = 'student_loan',
  MORTGAGE = 'mortgage',

  // Investment Accounts
  BROKERAGE = 'brokerage',
  RETIREMENT_401K = 'retirement_401k',
  RETIREMENT_403B = 'retirement_403b',
  RETIREMENT_457B = 'retirement_457b',
  RETIREMENT_IRA = 'retirement_ira',
  RETIREMENT_ROTH = 'retirement_roth',
  RETIREMENT_SEP_IRA = 'retirement_sep_ira',
  RETIREMENT_SIMPLE_IRA = 'retirement_simple_ira',
  RETIREMENT_529 = 'retirement_529',
  HSA = 'hsa',
  PENSION = 'pension',

  // Alternative Investments
  CRYPTO = 'crypto',
  PRIVATE_EQUITY = 'private_equity',
  PRIVATE_DEBT = 'private_debt',
  COLLECTIBLES = 'collectibles',
  PRECIOUS_METALS = 'precious_metals',

  // Real Estate & Vehicles
  PROPERTY = 'property',
  VEHICLE = 'vehicle',

  // Insurance & Annuities
  LIFE_INSURANCE_CASH_VALUE = 'life_insurance_cash_value',
  ANNUITY = 'annuity',

  // Securities
  BOND = 'bond',
  STOCK_OPTIONS = 'stock_options',

  // Business
  BUSINESS_EQUITY = 'business_equity',

  // Other
  MANUAL = 'manual',
  OTHER = 'other',
}

export enum AccountSource {
  PLAID = 'plaid',
  TELLER = 'teller',
  MX = 'mx',
  MANUAL = 'manual',
}

export interface Account {
  id: string;
  user_id: string;
  name: string;
  account_type: AccountType;
  account_source: AccountSource;
  property_type?: PropertyType | null;
  institution_name: string | null;
  mask: string | null;
  current_balance: number | null;
  available_balance?: number | null;
  limit?: number | null;
  balance_as_of?: string | null;
  is_active: boolean;
  exclude_from_cash_flow: boolean;
  plaid_item_hash?: string | null;

  // Auto-valuation metadata
  last_auto_valued_at?: string | null;
  valuation_adjustment_pct?: number | null;

  // Provider-agnostic sync status
  provider_item_id?: string | null;
  last_synced_at?: string | null;
  last_error_code?: string | null;
  last_error_message?: string | null;
  needs_reauth?: boolean | null;
}
