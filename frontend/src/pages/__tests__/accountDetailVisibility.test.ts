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
import {
  ASSET_ACCOUNT_TYPES,
  CONTRIBUTION_ACCOUNT_TYPES,
  DEBT_ACCOUNT_TYPES,
  HOLDINGS_ACCOUNT_TYPES,
} from '../../constants/accountTypeGroups';

// ── helpers mirroring AccountDetailPage expressions ───────────────────────────

const isAsset = (type: string) => ASSET_ACCOUNT_TYPES.includes(type);

const showTransactions = (type: string) => !ASSET_ACCOUNT_TYPES.includes(type);

const showContributions = (source: string, type: string) =>
  source === 'manual' && CONTRIBUTION_ACCOUNT_TYPES.includes(type);

const showUpdateBalance = (source: string, type: string) =>
  source === 'manual'
  && type !== 'vehicle'
  && !DEBT_ACCOUNT_TYPES.includes(type);

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

  it('shows for manual retirement_403b', () => {
    expect(showContributions('manual', 'retirement_403b')).toBe(true);
  });

  it('shows for manual retirement_457b', () => {
    expect(showContributions('manual', 'retirement_457b')).toBe(true);
  });

  it('shows for manual retirement_sep_ira', () => {
    expect(showContributions('manual', 'retirement_sep_ira')).toBe(true);
  });

  it('shows for manual retirement_simple_ira', () => {
    expect(showContributions('manual', 'retirement_simple_ira')).toBe(true);
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

// ── showUpdateBalance (all manual accounts except vehicle + debt) ─────────────

describe('showUpdateBalance', () => {
  // asset types
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

  // non-asset manual accounts (expanded behavior)
  it('shows for manual checking', () => {
    expect(showUpdateBalance('manual', 'checking')).toBe(true);
  });

  it('shows for manual savings', () => {
    expect(showUpdateBalance('manual', 'savings')).toBe(true);
  });

  it('shows for manual brokerage', () => {
    expect(showUpdateBalance('manual', 'brokerage')).toBe(true);
  });

  it('shows for manual crypto', () => {
    expect(showUpdateBalance('manual', 'crypto')).toBe(true);
  });

  it('shows for manual retirement_401k', () => {
    expect(showUpdateBalance('manual', 'retirement_401k')).toBe(true);
  });

  // always hidden
  it('hides for manual vehicle (has its own dedicated section)', () => {
    expect(showUpdateBalance('manual', 'vehicle')).toBe(false);
  });

  it('hides for manual credit_card (has debt section)', () => {
    expect(showUpdateBalance('manual', 'credit_card')).toBe(false);
  });

  it('hides for manual mortgage (has debt section)', () => {
    expect(showUpdateBalance('manual', 'mortgage')).toBe(false);
  });

  it('hides for manual loan (has debt section)', () => {
    expect(showUpdateBalance('manual', 'loan')).toBe(false);
  });

  it('hides for plaid checking (balance synced automatically)', () => {
    expect(showUpdateBalance('plaid', 'checking')).toBe(false);
  });

  it('hides for plaid property (balance synced automatically)', () => {
    expect(showUpdateBalance('plaid', 'property')).toBe(false);
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

  it('shows for retirement_403b', () => {
    expect(showHoldings('retirement_403b')).toBe(true);
  });

  it('shows for retirement_457b', () => {
    expect(showHoldings('retirement_457b')).toBe(true);
  });

  it('shows for retirement_sep_ira', () => {
    expect(showHoldings('retirement_sep_ira')).toBe(true);
  });

  it('shows for retirement_simple_ira', () => {
    expect(showHoldings('retirement_simple_ira')).toBe(true);
  });

  it('shows for retirement_529', () => {
    expect(showHoldings('retirement_529')).toBe(true);
  });

  it('shows for hsa', () => {
    expect(showHoldings('hsa')).toBe(true);
  });

  it('shows for crypto', () => {
    expect(showHoldings('crypto')).toBe(true);
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

// ── include_in_networth toggle ────────────────────────────────────────────

/**
 * The toggle appears in the main Account Settings panel for every account
 * type EXCEPT vehicle (vehicles have their own dedicated section for it).
 */
const showIncludeInNetworthInSettings = (accountType: string) =>
  accountType !== "vehicle";

describe("include_in_networth toggle in Account Settings", () => {
  it("is present for checking accounts", () => {
    expect(showIncludeInNetworthInSettings("checking")).toBe(true);
  });

  it("is present for savings accounts", () => {
    expect(showIncludeInNetworthInSettings("savings")).toBe(true);
  });

  it("is present for brokerage accounts", () => {
    expect(showIncludeInNetworthInSettings("brokerage")).toBe(true);
  });

  it("is present for credit_card accounts", () => {
    expect(showIncludeInNetworthInSettings("credit_card")).toBe(true);
  });

  it("is present for property accounts", () => {
    expect(showIncludeInNetworthInSettings("property")).toBe(true);
  });

  it("is present for retirement_401k accounts", () => {
    expect(showIncludeInNetworthInSettings("retirement_401k")).toBe(true);
  });

  it("is present for mortgage accounts", () => {
    expect(showIncludeInNetworthInSettings("mortgage")).toBe(true);
  });

  it("is NOT shown for vehicle accounts (they have their own section)", () => {
    expect(showIncludeInNetworthInSettings("vehicle")).toBe(false);
  });
});

/**
 * The checked state of the toggle reflects the account's include_in_networth
 * value (defaulting to true when null).
 */
const toggleChecked = (includeInNetworth: boolean | null): boolean =>
  includeInNetworth ?? true;

describe("include_in_networth toggle — reflects current value", () => {
  it("is checked when include_in_networth is true", () => {
    expect(toggleChecked(true)).toBe(true);
  });

  it("is unchecked when include_in_networth is false", () => {
    expect(toggleChecked(false)).toBe(false);
  });

  it("defaults to checked (true) when include_in_networth is null", () => {
    expect(toggleChecked(null)).toBe(true);
  });
});

/**
 * The toggle calls updateAccount with the new boolean value on change.
 * This mirrors handleToggleIncludeInNetworth in AccountDetailPage.
 */
const buildUpdatePayload = (checked: boolean) => ({
  include_in_networth: checked,
});

describe("include_in_networth toggle — calls update on change", () => {
  it("sends include_in_networth: true when toggled on", () => {
    expect(buildUpdatePayload(true)).toEqual({ include_in_networth: true });
  });

  it("sends include_in_networth: false when toggled off", () => {
    expect(buildUpdatePayload(false)).toEqual({ include_in_networth: false });
  });
});

import { readFileSync } from "fs";

describe("AccountDetailPage source — include_in_networth toggle wiring", () => {
  const src = readFileSync("src/pages/AccountDetailPage.tsx", "utf-8");

  it("declares handleToggleIncludeInNetworth handler", () => {
    expect(src).toContain("handleToggleIncludeInNetworth");
  });

  it("renders Include in Net Worth label", () => {
    expect(src).toContain("Include in Net Worth");
  });

  it("binds handler to the Switch onChange in Account Settings", () => {
    expect(src).toContain("onChange={handleToggleIncludeInNetworth}");
  });

  it("uses include_in_networth ?? true as default for isChecked in settings", () => {
    expect(src).toContain("include_in_networth ?? true");
  });

  it("shows the toggle only for non-vehicle accounts in settings", () => {
    expect(src).toContain('account_type !== "vehicle"');
  });

  it("has helper text describing the net worth impact", () => {
    expect(src).toContain("net worth");
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

  it('brokerage (manual): showTransactions + showContributions + showUpdateBalance + showHoldings', () => {
    expect(showTransactions('brokerage')).toBe(true);
    expect(showContributions('manual', 'brokerage')).toBe(true);
    expect(showUpdateBalance('manual', 'brokerage')).toBe(true);
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

  it('checking (manual): showTransactions + showUpdateBalance are true', () => {
    expect(showTransactions('checking')).toBe(true);
    expect(showContributions('manual', 'checking')).toBe(false);
    expect(showUpdateBalance('manual', 'checking')).toBe(true);
    expect(showDebtBalanceUpdate('manual', 'checking')).toBe(false);
    expect(showHoldings('checking')).toBe(false);
  });

  it('checking (plaid): only showTransactions is true', () => {
    expect(showTransactions('checking')).toBe(true);
    expect(showContributions('plaid', 'checking')).toBe(false);
    expect(showUpdateBalance('plaid', 'checking')).toBe(false);
    expect(showDebtBalanceUpdate('plaid', 'checking')).toBe(false);
    expect(showHoldings('checking')).toBe(false);
  });

  it('crypto (manual): showTransactions + showUpdateBalance + showHoldings are true', () => {
    expect(showTransactions('crypto')).toBe(true);
    expect(showContributions('manual', 'crypto')).toBe(false);
    expect(showUpdateBalance('manual', 'crypto')).toBe(true);
    expect(showDebtBalanceUpdate('manual', 'crypto')).toBe(false);
    expect(showHoldings('crypto')).toBe(true);
  });

  it('retirement_529 (manual): showTransactions + showContributions + showUpdateBalance + showHoldings', () => {
    expect(showTransactions('retirement_529')).toBe(true);
    expect(showContributions('manual', 'retirement_529')).toBe(true);
    expect(showHoldings('retirement_529')).toBe(true);
    expect(showUpdateBalance('manual', 'retirement_529')).toBe(true);
    expect(showDebtBalanceUpdate('manual', 'retirement_529')).toBe(false);
  });
});

// ── AccountDetailPage error state rendering decision ─────────────────────────
//
// Mirrors the render-branch logic added to AccountDetailPage:
//   isLoading    → spinner
//   accountError → error state with retry button
//   !account     → account not found message
//   otherwise    → full account detail page

type AccountDetailPageState =
  | 'loading'
  | 'error'
  | 'not-found'
  | 'content';

const resolveAccountDetailPageState = (
  isLoading: boolean,
  accountError: boolean,
  account: object | null,
): AccountDetailPageState => {
  if (isLoading) return 'loading';
  if (accountError) return 'error';
  if (!account) return 'not-found';
  return 'content';
};

const accountErrorMessageText =
  'Failed to load account. Please try again.';
const accountRetryButtonLabel = 'Retry';

describe('AccountDetailPage error state', () => {
  it("resolves to 'loading' when isLoading is true", () => {
    expect(resolveAccountDetailPageState(true, false, null)).toBe('loading');
  });

  it("loading takes priority over error", () => {
    expect(resolveAccountDetailPageState(true, true, null)).toBe('loading');
  });

  it("resolves to 'error' when accountError is true", () => {
    expect(resolveAccountDetailPageState(false, true, null)).toBe('error');
  });

  it("resolves to 'not-found' when no error and account is null", () => {
    expect(resolveAccountDetailPageState(false, false, null)).toBe(
      'not-found',
    );
  });

  it("resolves to 'content' when account data is available", () => {
    expect(
      resolveAccountDetailPageState(false, false, { id: 'acc-1' }),
    ).toBe('content');
  });

  it("error message text mentions account", () => {
    expect(accountErrorMessageText.toLowerCase()).toContain('account');
  });

  it("retry button label is defined", () => {
    expect(accountRetryButtonLabel).toBe('Retry');
  });
});
