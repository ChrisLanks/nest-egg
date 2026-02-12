/**
 * Account types
 */

export enum AccountType {
  CHECKING = 'checking',
  SAVINGS = 'savings',
  CREDIT_CARD = 'credit_card',
  BROKERAGE = 'brokerage',
  RETIREMENT_401K = 'retirement_401k',
  RETIREMENT_IRA = 'retirement_ira',
  RETIREMENT_ROTH = 'retirement_roth',
  HSA = 'hsa',
  MANUAL = 'manual',
  OTHER = 'other',
}

export interface Account {
  id: string;
  name: string;
  account_type: AccountType;
  institution_name: string | null;
  mask: string | null;
  current_balance: number | null;
  available_balance: number | null;
  limit: number | null;
  is_active: boolean;
}
