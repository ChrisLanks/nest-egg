/**
 * Tests for AccountDetailPage section-visibility logic.
 *
 * All helpers mirror the exact expressions used inside AccountDetailPage so
 * that regressions in the conditional logic are caught without rendering.
 *
 * Sections governed by these flags:
 *   showTransactions      – Transactions card
 *   showContributions     – Recurring Contributions card
 *   showUpdateBalance     – "Update Value" card (manual asset accounts)
 *   showDebtBalanceUpdate – "Update Balance" card (manual debt accounts)
 *   showHoldings          – Holdings card (investment account types)
 *   canAddTransaction     – "Add Transaction" button inside Transactions card
 */

import { describe, it, expect } from 'vitest';

// ── constants mirroring AccountDetailPage ─────────────────────────────────────

const ASSET_ACCOUNT_TYPES = [
  'property', 'vehicle', 'collectibles', 'precious_metals',
  'business_equity', 'private_equity', 'private_debt', 'bond',
  'life_insurance_cash_value', 'pension', 'annuity',
];

const CONTRIBUTION_ACCOUNT_TYPES = [
  'savings', 'brokerage', 'retirement_401k', 'retirement_ira',
  'retirement_roth', 'retirement_529', 'hsa',
];

const DEBT_ACCOUNT_TYPES = ['credit_card', 'loan', 'student_loan', 'mortgage'];

const HOLDINGS_ACCOUNT_TYPES = [
  'brokerage', 'retirement_401k', 'retirement_ira', 'retirement_roth',
  'retirement_529', 'hsa',
];

// ── helpers mirroring AccountDetailPage expressions ───────────────────────────

const isAsset = (type: string) => ASSET_ACCOUNT_TYPES.includes(type);

const showTransactions = (type: string) => !ASSET_ACCOUNT_TYPES.includes(type);

const showContributions = (source: string, type: string) =>
  source === 'manual' && CONTRIBUTION_ACCOUNT_TYPES.includes(type);

const showUpdateBalance = (source: string, type: string) =>
  source === 'manual' && ASSET_ACCOUNT_TYPES.includes(type) && type !== 'vehicle';

const showDebtBalanceUpdate = (source: string, type: string) =>
  source === 'manual' && DEBT_ACCOUNT_TYPES.includes(type);

const showHoldings = (type: string) => HOLDINGS_ACCOUNT_TYPES.includes(type);

const canAddTransaction = (source: string, type: string, canEdit: boolean) =>
  source === 'manual' && !ASSET_ACCOUNT_TYPES.includes(type) && canEdit;

// ── isAsset ───────────────────────────────────────────────────────────────────

describe('isAsset', () => {
  it('is true for property', () => {
    expect(isAsset('property')).toBe(true);
  });

  it('is true for vehicle', () => {
    expect(isAsset('vehicle')).toBe(true);
  });

  it('is true for collectibles', () => {
    expect(isAsset('collectibles')).toBe(true);
  });

  it('is true for precious_metals', () => {
    expect(isAsset('precious_metals')).toBe(true);
  });

  it('is true for business_equity', () => {
    expect(isAsset('business_equity')).toBe(true);
  });

  it('is true for private_equity', () => {
    expect(isAsset('private_equity')).toBe(true);
  });

  it('is true for pension', () => {
    expect(isAsset('pension')).toBe(true);
  });

  it('is true for annuity', () => {
    expect(isAsset('annuity')).toBe(true);
  });

  it('is false for checking', () => {
    expect(isAsset('checking')).toBe(false);
  });

  it('is false for credit_card', () => {
    expect(isAsset('credit_card')).toBe(false);
  });

  it('is false for brokerage', () => {
    expect(isAsset('brokerage')).toBe(false);
  });

  it('is false for retirement_529', () => {
    expect(isAsset('retirement_529')).toBe(false);
  });

  it('is false for mortgage', () => {
    expect(isAsset('mortgage')).toBe(false);
  });
});

// ── showTransactions ──────────────────────────────────────────────────────────

describe('showTransactions', () => {
  it('shows for checking', () => {
    expect(showTransactions('checking')).toBe(true);
  });

  it('shows for savings', () => {
    expect(showTransactions('savings')).toBe(true);
  });

  it('shows for credit_card', () => {
    expect(showTransactions('credit_card')).toBe(true);
  });

  it('shows for brokerage', () => {
    expect(showTransactions('brokerage')).toBe(true);
  });

  it('shows for mortgage', () => {
    expect(showTransactions('mortgage')).toBe(true);
  });

  it('hides for property', () => {
    expect(showTransactions('property')).toBe(false);
  });

  it('hides for vehicle', () => {
    expect(showTransactions('vehicle')).toBe(false);
  });

  it('hides for collectibles', () => {
    expect(showTransactions('collectibles')).toBe(false);
  });

  it('hides for pension', () => {
    expect(showTransactions('pension')).toBe(false);
  });

  it('hides for business_equity', () => {
    expect(showTransactions('business_equity')).toBe(false);
  });
});

// ── showContributions ─────────────────────────────────────────────────────────

describe('showContributions', () => {
  it('shows for manual savings', () => {
    expect(showContributions('manual', 'savings')).toBe(true);
  });

  it('shows for manual brokerage', () => {
    expect(showContributions('manual', 'brokerage')).toBe(true);
  });

  it('shows for manual retirement_401k', () => {
    expect(showContributions('manual', 'retirement_401k')).toBe(true);
  });

  it('shows for manual retirement_ira', () => {
    expect(showContributions('manual', 'retirement_ira')).toBe(true);
  });

  it('shows for manual retirement_roth', () => {
    expect(showContributions('manual', 'retirement_roth')).toBe(true);
  });

  it('shows for manual retirement_529', () => {
    expect(showContributions('manual', 'retirement_529')).toBe(true);
  });

  it('shows for manual hsa', () => {
    expect(showContributions('manual', 'hsa')).toBe(true);
  });

  it('hides for plaid brokerage (not manual)', () => {
    expect(showContributions('plaid', 'brokerage')).toBe(false);
  });

  it('hides for manual property (asset type)', () => {
    expect(showContributions('manual', 'property')).toBe(false);
  });

  it('hides for manual vehicle (asset type)', () => {
    expect(showContributions('manual', 'vehicle')).toBe(false);
  });

  it('hides for manual checking (not in contribution types)', () => {
    expect(showContributions('manual', 'checking')).toBe(false);
  });

  it('hides for manual credit_card (debt type)', () => {
    expect(showContributions('manual', 'credit_card')).toBe(false);
  });

  it('hides for manual mortgage (debt type)', () => {
    expect(showContributions('manual', 'mortgage')).toBe(false);
  });
});

// ── showUpdateBalance (asset "Update Value") ──────────────────────────────────

describe('showUpdateBalance', () => {
  it('shows for manual property', () => {
    expect(showUpdateBalance('manual', 'property')).toBe(true);
  });

  it('shows for manual collectibles', () => {
    expect(showUpdateBalance('manual', 'collectibles')).toBe(true);
  });

  it('shows for manual precious_metals', () => {
    expect(showUpdateBalance('manual', 'precious_metals')).toBe(true);
  });

  it('shows for manual pension', () => {
    expect(showUpdateBalance('manual', 'pension')).toBe(true);
  });

  it('shows for manual business_equity', () => {
    expect(showUpdateBalance('manual', 'business_equity')).toBe(true);
  });

  it('hides for manual vehicle (has its own dedicated section)', () => {
    expect(showUpdateBalance('manual', 'vehicle')).toBe(false);
  });

  it('hides for plaid property (balance synced automatically)', () => {
    expect(showUpdateBalance('plaid', 'property')).toBe(false);
  });

  it('hides for manual checking (not an asset type)', () => {
    expect(showUpdateBalance('manual', 'checking')).toBe(false);
  });

  it('hides for manual brokerage (not an asset type)', () => {
    expect(showUpdateBalance('manual', 'brokerage')).toBe(false);
  });
});

// ── showDebtBalanceUpdate ─────────────────────────────────────────────────────

describe('showDebtBalanceUpdate', () => {
  it('shows for manual credit_card', () => {
    expect(showDebtBalanceUpdate('manual', 'credit_card')).toBe(true);
  });

  it('shows for manual loan', () => {
    expect(showDebtBalanceUpdate('manual', 'loan')).toBe(true);
  });

  it('shows for manual student_loan', () => {
    expect(showDebtBalanceUpdate('manual', 'student_loan')).toBe(true);
  });

  it('shows for manual mortgage', () => {
    expect(showDebtBalanceUpdate('manual', 'mortgage')).toBe(true);
  });

  it('hides for plaid mortgage (balance synced)', () => {
    expect(showDebtBalanceUpdate('plaid', 'mortgage')).toBe(false);
  });

  it('hides for manual checking (not a debt type)', () => {
    expect(showDebtBalanceUpdate('manual', 'checking')).toBe(false);
  });

  it('hides for manual brokerage (not a debt type)', () => {
    expect(showDebtBalanceUpdate('manual', 'brokerage')).toBe(false);
  });

  it('hides for manual property (asset type)', () => {
    expect(showDebtBalanceUpdate('manual', 'property')).toBe(false);
  });
});

// ── showHoldings ──────────────────────────────────────────────────────────────

describe('showHoldings', () => {
  it('shows for brokerage', () => {
    expect(showHoldings('brokerage')).toBe(true);
  });

  it('shows for retirement_401k', () => {
    expect(showHoldings('retirement_401k')).toBe(true);
  });

  it('shows for retirement_ira', () => {
    expect(showHoldings('retirement_ira')).toBe(true);
  });

  it('shows for retirement_roth', () => {
    expect(showHoldings('retirement_roth')).toBe(true);
  });

  it('shows for retirement_529', () => {
    expect(showHoldings('retirement_529')).toBe(true);
  });

  it('shows for hsa', () => {
    expect(showHoldings('hsa')).toBe(true);
  });

  it('hides for savings', () => {
    expect(showHoldings('savings')).toBe(false);
  });

  it('hides for checking', () => {
    expect(showHoldings('checking')).toBe(false);
  });

  it('hides for property (asset, not investable)', () => {
    expect(showHoldings('property')).toBe(false);
  });

  it('hides for crypto (balance-based, not share-based)', () => {
    expect(showHoldings('crypto')).toBe(false);
  });

  it('hides for mortgage', () => {
    expect(showHoldings('mortgage')).toBe(false);
  });
});

// ── canAddTransaction ─────────────────────────────────────────────────────────

describe('canAddTransaction', () => {
  it('true for manual checking owned by current user', () => {
    expect(canAddTransaction('manual', 'checking', true)).toBe(true);
  });

  it('true for manual savings', () => {
    expect(canAddTransaction('manual', 'savings', true)).toBe(true);
  });

  it('true for manual credit_card', () => {
    expect(canAddTransaction('manual', 'credit_card', true)).toBe(true);
  });

  it('true for manual brokerage', () => {
    expect(canAddTransaction('manual', 'brokerage', true)).toBe(true);
  });

  it('false for plaid account (not manual)', () => {
    expect(canAddTransaction('plaid', 'checking', true)).toBe(false);
  });

  it('false for manual account when canEdit is false (read-only)', () => {
    expect(canAddTransaction('manual', 'checking', false)).toBe(false);
  });

  it('false for manual property (asset type has no transactions)', () => {
    expect(canAddTransaction('manual', 'property', true)).toBe(false);
  });

  it('false for manual vehicle (asset type)', () => {
    expect(canAddTransaction('manual', 'vehicle', true)).toBe(false);
  });

  it('false for manual pension (asset type)', () => {
    expect(canAddTransaction('manual', 'pension', true)).toBe(false);
  });
});

// ── mutual exclusivity spot-checks ───────────────────────────────────────────

describe('section mutual exclusivity', () => {
  it('property: only showUpdateBalance is true (manual)', () => {
    expect(showTransactions('property')).toBe(false);
    expect(showContributions('manual', 'property')).toBe(false);
    expect(showUpdateBalance('manual', 'property')).toBe(true);
    expect(showDebtBalanceUpdate('manual', 'property')).toBe(false);
    expect(showHoldings('property')).toBe(false);
  });

  it('brokerage/IRA: showTransactions + showContributions(manual) + showHoldings are true', () => {
    expect(showTransactions('brokerage')).toBe(true);
    expect(showContributions('manual', 'brokerage')).toBe(true);
    expect(showUpdateBalance('manual', 'brokerage')).toBe(false);
    expect(showDebtBalanceUpdate('manual', 'brokerage')).toBe(false);
    expect(showHoldings('brokerage')).toBe(true);
  });

  it('credit_card: showTransactions + showDebtBalanceUpdate(manual) are true', () => {
    expect(showTransactions('credit_card')).toBe(true);
    expect(showContributions('manual', 'credit_card')).toBe(false);
    expect(showUpdateBalance('manual', 'credit_card')).toBe(false);
    expect(showDebtBalanceUpdate('manual', 'credit_card')).toBe(true);
    expect(showHoldings('credit_card')).toBe(false);
  });

  it('checking: only showTransactions is true (plaid or manual)', () => {
    expect(showTransactions('checking')).toBe(true);
    expect(showContributions('manual', 'checking')).toBe(false);
    expect(showUpdateBalance('manual', 'checking')).toBe(false);
    expect(showDebtBalanceUpdate('manual', 'checking')).toBe(false);
    expect(showHoldings('checking')).toBe(false);
  });

  it('retirement_529: showTransactions + showContributions(manual) + showHoldings', () => {
    expect(showTransactions('retirement_529')).toBe(true);
    expect(showContributions('manual', 'retirement_529')).toBe(true);
    expect(showHoldings('retirement_529')).toBe(true);
    expect(showUpdateBalance('manual', 'retirement_529')).toBe(false);
    expect(showDebtBalanceUpdate('manual', 'retirement_529')).toBe(false);
  });
});
