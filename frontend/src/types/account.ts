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
  RETIREMENT_IRA = 'retirement_ira',
  RETIREMENT_ROTH = 'retirement_roth',
  RETIREMENT_529 = 'retirement_529',
  HSA = 'hsa',
  PENSION = 'pension',

  // Alternative Investments
  CRYPTO = 'crypto',
  PRIVATE_EQUITY = 'private_equity',
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

export interface Account {
  id: string;
  name: string;
  account_type: AccountType;
  property_type?: PropertyType | null;
  institution_name: string | null;
  mask: string | null;
  current_balance: number | null;
  available_balance: number | null;
  limit: number | null;
  is_active: boolean;
}
