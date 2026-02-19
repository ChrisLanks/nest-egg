/**
 * Zod validation schemas for manual account creation
 */

import { z } from 'zod';

// Account types
export const ACCOUNT_TYPES = {
  // Cash & Checking
  CHECKING: 'checking',
  SAVINGS: 'savings',
  MONEY_MARKET: 'money_market',
  CD: 'cd',

  // Credit & Debt
  CREDIT_CARD: 'credit_card',
  LOAN: 'loan',
  STUDENT_LOAN: 'student_loan',
  MORTGAGE: 'mortgage',

  // Investment accounts
  BROKERAGE: 'brokerage',
  RETIREMENT_401K: 'retirement_401k',
  RETIREMENT_IRA: 'retirement_ira',
  RETIREMENT_ROTH: 'retirement_roth',
  RETIREMENT_529: 'retirement_529',
  HSA: 'hsa',
  PENSION: 'pension',

  // Alternative Investments
  CRYPTO: 'crypto',
  PRIVATE_EQUITY: 'private_equity',
  PRIVATE_DEBT: 'private_debt',
  COLLECTIBLES: 'collectibles',
  PRECIOUS_METALS: 'precious_metals',

  // Insurance & Annuities
  LIFE_INSURANCE_CASH_VALUE: 'life_insurance_cash_value',
  ANNUITY: 'annuity',

  // Securities
  BOND: 'bond',
  STOCK_OPTIONS: 'stock_options',

  // Business
  BUSINESS_EQUITY: 'business_equity',

  // Real Estate & Vehicles
  PROPERTY: 'property',
  VEHICLE: 'vehicle',

  // Other
  MANUAL: 'manual',
  OTHER: 'other',
} as const;

export type AccountType = typeof ACCOUNT_TYPES[keyof typeof ACCOUNT_TYPES];

// Basic manual account schema (checking, savings, loans, etc.)
export const basicManualAccountSchema = z.object({
  name: z.string().min(1, 'Account name is required'),
  institution: z.string().optional(),
  account_type: z.enum([
    ACCOUNT_TYPES.CHECKING,
    ACCOUNT_TYPES.SAVINGS,
    ACCOUNT_TYPES.MONEY_MARKET,
    ACCOUNT_TYPES.CD,
    ACCOUNT_TYPES.CREDIT_CARD,
    ACCOUNT_TYPES.LOAN,
    ACCOUNT_TYPES.STUDENT_LOAN,
    ACCOUNT_TYPES.MORTGAGE,
    ACCOUNT_TYPES.MANUAL,
    ACCOUNT_TYPES.OTHER,
  ]),
  balance: z.number().or(z.string().transform((val) => parseFloat(val))),
  account_number_last4: z.string().max(4).optional(),
});

export type BasicManualAccountFormData = z.infer<typeof basicManualAccountSchema>;

// Investment holding schema
export const holdingSchema = z.object({
  ticker: z.string().min(1, 'Ticker symbol is required').toUpperCase(),
  shares: z.number().or(z.string().transform((val) => parseFloat(val))).refine((val) => val > 0, 'Shares must be greater than 0'),
  price_per_share: z.number().or(z.string().transform((val) => parseFloat(val))).refine((val) => val > 0, 'Price must be greater than 0'),
});

export type HoldingFormData = z.infer<typeof holdingSchema>;

// Investment account schema
export const investmentAccountSchema = z.object({
  name: z.string().min(1, 'Account name is required'),
  institution: z.string().optional(),
  account_type: z.enum([
    ACCOUNT_TYPES.BROKERAGE,
    ACCOUNT_TYPES.RETIREMENT_401K,
    ACCOUNT_TYPES.RETIREMENT_IRA,
    ACCOUNT_TYPES.RETIREMENT_ROTH,
    ACCOUNT_TYPES.RETIREMENT_529,
    ACCOUNT_TYPES.HSA,
    ACCOUNT_TYPES.PENSION,
    ACCOUNT_TYPES.CRYPTO,
    ACCOUNT_TYPES.PRIVATE_EQUITY,
    ACCOUNT_TYPES.COLLECTIBLES,
    ACCOUNT_TYPES.PRECIOUS_METALS,
    ACCOUNT_TYPES.LIFE_INSURANCE_CASH_VALUE,
    ACCOUNT_TYPES.ANNUITY,
    ACCOUNT_TYPES.BOND,
    ACCOUNT_TYPES.STOCK_OPTIONS,
    ACCOUNT_TYPES.BUSINESS_EQUITY,
  ]),
  holdings: z.array(holdingSchema).min(1, 'At least one holding is required'),
  account_number_last4: z.string().max(4).optional(),
});

export type InvestmentAccountFormData = z.infer<typeof investmentAccountSchema>;

// Property account schema (homes)
export const propertyAccountSchema = z.object({
  name: z.string().min(1, 'Property name is required'),
  address: z.string().min(1, 'Address is required'),
  property_classification: z.enum(['personal_residence', 'investment', 'vacation_home']).default('personal_residence'),
  property_type: z.enum(['single_family', 'condo', 'townhouse', 'multi_family', 'other']).default('single_family'),
  value: z.number().or(z.string().transform((val) => parseFloat(val))).refine((val) => val > 0, 'Value must be greater than 0'),
  mortgage_balance: z.number().or(z.string().transform((val) => parseFloat(val))).optional(),
});

export type PropertyAccountFormData = z.infer<typeof propertyAccountSchema>;

// Vehicle account schema
export const vehicleAccountSchema = z.object({
  name: z.string().min(1, 'Vehicle name is required'),
  make: z.string().min(1, 'Make is required'),
  model: z.string().min(1, 'Model is required'),
  year: z.number().or(z.string().transform((val) => parseInt(val, 10))).refine((val) => val >= 1900 && val <= new Date().getFullYear() + 1, 'Invalid year'),
  mileage: z.number().or(z.string().transform((val) => parseInt(val, 10))).optional(),
  value: z.number().or(z.string().transform((val) => parseFloat(val))).refine((val) => val > 0, 'Value must be greater than 0'),
  loan_balance: z.number().or(z.string().transform((val) => parseFloat(val))).optional(),
});

export type VehicleAccountFormData = z.infer<typeof vehicleAccountSchema>;

// Vesting milestone schema
export const vestingMilestoneSchema = z.object({
  date: z.string(), // ISO date string
  quantity: z.number().or(z.string().transform((val) => parseFloat(val))),
  notes: z.string().optional(),
});

export type VestingMilestone = z.infer<typeof vestingMilestoneSchema>;

// Private Equity account schema
export const privateEquityAccountSchema = z.object({
  name: z.string().min(1, 'Company name is required'),
  institution: z.string().optional(),
  account_type: z.literal(ACCOUNT_TYPES.PRIVATE_EQUITY),
  balance: z.number().or(z.string().transform((val) => parseFloat(val))),

  // Private Equity specific fields
  grant_type: z.enum(['iso', 'nso', 'rsu', 'rsa']).optional(),
  grant_date: z.string().optional(), // ISO date string
  quantity: z.number().or(z.string().transform((val) => parseFloat(val))).optional(),
  strike_price: z.number().or(z.string().transform((val) => parseFloat(val))).optional(),
  vesting_schedule: z.array(vestingMilestoneSchema).optional(), // Array of vesting milestones
  share_price: z.number().or(z.string().transform((val) => parseFloat(val))).optional(),
  company_status: z.enum(['private', 'public']).default('private'),
  valuation_method: z.enum(['409a', 'preferred', 'custom']).optional(),
  include_in_networth: z.boolean().optional(), // Defaults based on company_status
});

export type PrivateEquityAccountFormData = z.infer<typeof privateEquityAccountSchema>;

// Private Debt account schema
export const privateDebtAccountSchema = z.object({
  name: z.string().min(1, 'Investment name is required'),
  institution: z.string().optional(),
  account_type: z.literal(ACCOUNT_TYPES.PRIVATE_DEBT),
  balance: z.number().or(z.string().transform((val) => parseFloat(val))),

  // Private Debt specific fields
  principal_amount: z.number().or(z.string().transform((val) => parseFloat(val))).optional(),
  interest_rate: z.number().or(z.string().transform((val) => parseFloat(val))).optional(),
  maturity_date: z.string().optional(), // ISO date string
});

export type PrivateDebtAccountFormData = z.infer<typeof privateDebtAccountSchema>;
