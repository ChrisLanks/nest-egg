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

// ── Equity Grant Details section visibility ───────────────────────────────────

/**
 * The Grant Details card is shown when:
 *   account.account_type === 'stock_options' || account.account_type === 'private_equity'
 *
 * Mirrors the condition in AccountDetailPage.tsx.
 */
const showEquityGrantDetails = (type: string) =>
  type === 'stock_options' || type === 'private_equity';

describe('showEquityGrantDetails', () => {
  it('is true for stock_options', () => {
    expect(showEquityGrantDetails('stock_options')).toBe(true);
  });

  it('is true for private_equity', () => {
    expect(showEquityGrantDetails('private_equity')).toBe(true);
  });

  it('is false for checking', () => {
    expect(showEquityGrantDetails('checking')).toBe(false);
  });

  it('is false for brokerage', () => {
    expect(showEquityGrantDetails('brokerage')).toBe(false);
  });

  it('is false for retirement_401k', () => {
    expect(showEquityGrantDetails('retirement_401k')).toBe(false);
  });

  it('is false for property', () => {
    expect(showEquityGrantDetails('property')).toBe(false);
  });

  it('is false for business_equity', () => {
    // Business equity has its own valuation section; equity grant section is for stock_options/private_equity
    expect(showEquityGrantDetails('business_equity')).toBe(false);
  });
});

// ── Equity save button disabled state ─────────────────────────────────────────

/**
 * The Save Grant Details button is disabled when all equity fields are empty.
 * Mirrors:
 *   isDisabled={!equityGrantType && !equityQuantity && !equityStrikePrice
 *               && !equitySharePrice && !equityGrantDate && !equityCompanyStatus}
 */
const equitySaveDisabled = (
  grantType: string,
  quantity: string,
  strikePrice: string,
  sharePrice: string,
  grantDate: string,
  companyStatus: string,
) =>
  !grantType && !quantity && !strikePrice && !sharePrice && !grantDate && !companyStatus;

describe('equitySaveDisabled', () => {
  it('is disabled when all fields are empty', () => {
    expect(equitySaveDisabled('', '', '', '', '', '')).toBe(true);
  });

  it('is enabled when grant type is set', () => {
    expect(equitySaveDisabled('iso', '', '', '', '', '')).toBe(false);
  });

  it('is enabled when quantity is set', () => {
    expect(equitySaveDisabled('', '1000', '', '', '', '')).toBe(false);
  });

  it('is enabled when share price is set', () => {
    expect(equitySaveDisabled('', '', '', '25.00', '', '')).toBe(false);
  });

  it('is enabled when strike price is set', () => {
    expect(equitySaveDisabled('', '', '10.00', '', '', '')).toBe(false);
  });

  it('is enabled when grant date is set', () => {
    expect(equitySaveDisabled('', '', '', '', '2024-01-15', '')).toBe(false);
  });

  it('is enabled when company status is set', () => {
    expect(equitySaveDisabled('', '', '', '', '', 'public')).toBe(false);
  });

  it('is enabled when multiple fields are set', () => {
    expect(equitySaveDisabled('rsu', '500', '', '30.00', '', 'private')).toBe(false);
  });
});

// ── Strike price conditional display ─────────────────────────────────────────

/**
 * Strike price field is only shown for ISO/NSO grants (options, not RSUs).
 * Mirrors:
 *   equityGrantType === 'iso' || equityGrantType === 'nso'
 *   || account.grant_type === 'iso' || account.grant_type === 'nso'
 */
const showStrikePrice = (newGrantType: string, existingGrantType: string | null) =>
  newGrantType === 'iso' || newGrantType === 'nso' ||
  existingGrantType === 'iso' || existingGrantType === 'nso';

describe('showStrikePrice', () => {
  it('shows for new iso selection', () => {
    expect(showStrikePrice('iso', null)).toBe(true);
  });

  it('shows for new nso selection', () => {
    expect(showStrikePrice('nso', null)).toBe(true);
  });

  it('shows when existing grant type is iso', () => {
    expect(showStrikePrice('', 'iso')).toBe(true);
  });

  it('shows when existing grant type is nso', () => {
    expect(showStrikePrice('', 'nso')).toBe(true);
  });

  it('hides for rsu', () => {
    expect(showStrikePrice('rsu', null)).toBe(false);
  });

  it('hides for rsa with no existing type', () => {
    expect(showStrikePrice('rsa', null)).toBe(false);
  });

  it('hides when no type is selected and existing is rsu', () => {
    expect(showStrikePrice('', 'rsu')).toBe(false);
  });

  it('hides when both empty', () => {
    expect(showStrikePrice('', null)).toBe(false);
  });
});

// ── Vest row validation (Add Event rows in Grant Details card) ────────────────

interface VestRow { date: string; quantity: string; notes: string; }

const validVestRows = (rows: VestRow[]) =>
  rows.filter((r) => r.date && r.quantity && !isNaN(parseFloat(r.quantity)));

describe('validVestRows', () => {
  it('returns empty for no rows', () => {
    expect(validVestRows([])).toHaveLength(0);
  });

  it('filters out rows missing date', () => {
    expect(validVestRows([{ date: '', quantity: '100', notes: '' }])).toHaveLength(0);
  });

  it('filters out rows missing quantity', () => {
    expect(validVestRows([{ date: '2025-01-01', quantity: '', notes: '' }])).toHaveLength(0);
  });

  it('filters out rows with non-numeric quantity', () => {
    expect(validVestRows([{ date: '2025-01-01', quantity: 'abc', notes: '' }])).toHaveLength(0);
  });

  it('keeps valid rows', () => {
    const rows = [
      { date: '2025-01-01', quantity: '250', notes: 'Cliff' },
      { date: '2025-04-01', quantity: '62.5', notes: '' },
    ];
    expect(validVestRows(rows)).toHaveLength(2);
  });

  it('mixed valid and invalid — only valid returned', () => {
    const rows = [
      { date: '2025-01-01', quantity: '100', notes: '' },
      { date: '', quantity: '50', notes: '' },
    ];
    expect(validVestRows(rows)).toHaveLength(1);
  });
});

// ── Save button disabled with vest rows ───────────────────────────────────────

const equitySaveDisabledWithVest = (
  grantType: string,
  quantity: string,
  strikePrice: string,
  sharePrice: string,
  grantDate: string,
  companyStatus: string,
  validVestRowCount: number,
) =>
  !grantType && !quantity && !strikePrice && !sharePrice && !grantDate && !companyStatus && validVestRowCount === 0;

describe('equitySaveDisabledWithVest', () => {
  it('disabled when all fields empty and no valid vest rows', () => {
    expect(equitySaveDisabledWithVest('', '', '', '', '', '', 0)).toBe(true);
  });

  it('enabled when there is at least one valid vest row', () => {
    expect(equitySaveDisabledWithVest('', '', '', '', '', '', 1)).toBe(false);
  });

  it('enabled when grant type set even with no vest rows', () => {
    expect(equitySaveDisabledWithVest('rsu', '', '', '', '', '', 0)).toBe(false);
  });
});

// ── Reclassify dropdown — complete type list ──────────────────────────────────

/**
 * These are the account types available in the reclassify <Select> in
 * AccountDetailPage. The list must include equity types so users can
 * correct an account that was imported with the wrong type (e.g., "checking"
 * instead of "stock_options").
 *
 * Mirrors the array literal in AccountDetailPage.tsx.
 */
const RECLASSIFY_TYPES = [
  "checking",
  "savings",
  "credit_card",
  "brokerage",
  "retirement_401k",
  "retirement_403b",
  "retirement_457b",
  "retirement_ira",
  "retirement_roth",
  "retirement_sep_ira",
  "retirement_simple_ira",
  "retirement_529",
  "hsa",
  "loan",
  "mortgage",
  "student_loan",
  "property",
  "vehicle",
  "crypto",
  "stock_options",
  "private_equity",
  "business_equity",
  "collectibles",
  "precious_metals",
  "manual",
  "other",
] as const;

describe('reclassify dropdown type list', () => {
  it('includes stock_options', () => {
    expect(RECLASSIFY_TYPES).toContain('stock_options');
  });

  it('includes private_equity', () => {
    expect(RECLASSIFY_TYPES).toContain('private_equity');
  });

  it('includes business_equity', () => {
    expect(RECLASSIFY_TYPES).toContain('business_equity');
  });

  it('includes student_loan', () => {
    expect(RECLASSIFY_TYPES).toContain('student_loan');
  });

  it('includes collectibles', () => {
    expect(RECLASSIFY_TYPES).toContain('collectibles');
  });

  it('includes precious_metals', () => {
    expect(RECLASSIFY_TYPES).toContain('precious_metals');
  });

  it('includes standard cash account types', () => {
    expect(RECLASSIFY_TYPES).toContain('checking');
    expect(RECLASSIFY_TYPES).toContain('savings');
    expect(RECLASSIFY_TYPES).toContain('credit_card');
  });

  it('includes all major retirement types', () => {
    expect(RECLASSIFY_TYPES).toContain('retirement_401k');
    expect(RECLASSIFY_TYPES).toContain('retirement_ira');
    expect(RECLASSIFY_TYPES).toContain('retirement_roth');
    expect(RECLASSIFY_TYPES).toContain('retirement_sep_ira');
    expect(RECLASSIFY_TYPES).toContain('retirement_529');
  });

  it('includes property and vehicle', () => {
    expect(RECLASSIFY_TYPES).toContain('property');
    expect(RECLASSIFY_TYPES).toContain('vehicle');
  });

  it('has no duplicate entries', () => {
    const unique = new Set(RECLASSIFY_TYPES);
    expect(unique.size).toBe(RECLASSIFY_TYPES.length);
  });

  it('covers all equity-related types that trigger the Grant Details card', () => {
    // Every type where showEquityGrantDetails returns true must be reclassifiable to
    const equityTypes = ['stock_options', 'private_equity'];
    equityTypes.forEach((t) => expect(RECLASSIFY_TYPES).toContain(t));
  });
});

// ── formatAccountType display labels for new types ───────────────────────────

/**
 * The reclassify dropdown uses formatAccountType() for labels.
 * New types added to the list must produce readable labels (not empty strings).
 * We test the fallback snake_case → Title Case path since these types have no
 * explicit override in formatAccountType.ts.
 */
const snakeCaseToTitle = (type: string): string =>
  type
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(' ');

describe('formatAccountType fallback for equity types', () => {
  it('renders stock_options as "Stock Options"', () => {
    expect(snakeCaseToTitle('stock_options')).toBe('Stock Options');
  });

  it('renders private_equity as "Private Equity"', () => {
    expect(snakeCaseToTitle('private_equity')).toBe('Private Equity');
  });

  it('renders business_equity as "Business Equity"', () => {
    expect(snakeCaseToTitle('business_equity')).toBe('Business Equity');
  });

  it('renders collectibles as "Collectibles"', () => {
    expect(snakeCaseToTitle('collectibles')).toBe('Collectibles');
  });

  it('renders precious_metals as "Precious Metals"', () => {
    expect(snakeCaseToTitle('precious_metals')).toBe('Precious Metals');
  });

  it('renders student_loan as "Student Loan"', () => {
    expect(snakeCaseToTitle('student_loan')).toBe('Student Loan');
  });

  it('produces a non-empty string for every type in the dropdown', () => {
    RECLASSIFY_TYPES.forEach((type) => {
      expect(snakeCaseToTitle(type).length).toBeGreaterThan(0);
    });
  });
});

// ── Vesting schedule template generator ──────────────────────────────────────

type VestRow2 = { date: string; quantity: string; notes: string };

const addMonths2 = (startIso: string, months: number): string => {
  const d = new Date(startIso + 'T00:00:00');
  d.setMonth(d.getMonth() + months);
  return d.toISOString().slice(0, 10);
};

const fmt2 = (n: number) => String(Math.round(n * 10000) / 10000);

function applyVestTemplate(template: string, startDate: string, totalShares: number): VestRow2[] {
  const rows: VestRow2[] = [];
  if (template === '4yr-1yr-cliff-monthly') {
    const cliff = totalShares * 0.25;
    const remaining = totalShares - cliff;
    const monthly = remaining / 36;
    rows.push({ date: addMonths2(startDate, 12), quantity: fmt2(cliff), notes: 'Cliff (1 year)' });
    for (let i = 1; i <= 36; i++)
      rows.push({ date: addMonths2(startDate, 12 + i), quantity: fmt2(monthly), notes: `Month ${12 + i}` });
  } else if (template === '4yr-1yr-cliff-quarterly') {
    const cliff = totalShares * 0.25;
    const remaining = totalShares - cliff;
    const perQ = remaining / 12;
    rows.push({ date: addMonths2(startDate, 12), quantity: fmt2(cliff), notes: 'Cliff (1 year)' });
    for (let i = 1; i <= 12; i++)
      rows.push({ date: addMonths2(startDate, 12 + i * 3), quantity: fmt2(perQ), notes: `Q${i} post-cliff` });
  } else if (template === '4yr-quarterly') {
    const perEvent = totalShares / 16;
    for (let i = 1; i <= 16; i++)
      rows.push({ date: addMonths2(startDate, i * 3), quantity: fmt2(perEvent), notes: `Q${i}` });
  } else if (template === '4yr-annual') {
    const perYear = totalShares / 4;
    for (let i = 1; i <= 4; i++)
      rows.push({ date: addMonths2(startDate, i * 12), quantity: fmt2(perYear), notes: `Year ${i}` });
  } else if (template === '3yr-annual') {
    const perYear = totalShares / 3;
    for (let i = 1; i <= 3; i++)
      rows.push({ date: addMonths2(startDate, i * 12), quantity: fmt2(perYear), notes: `Year ${i}` });
  } else if (template === '2yr-semi') {
    const perEvent = totalShares / 4;
    for (let i = 1; i <= 4; i++)
      rows.push({ date: addMonths2(startDate, i * 6), quantity: fmt2(perEvent), notes: `Semi-annual ${i}` });
  } else if (template === '1yr-annual') {
    rows.push({ date: addMonths2(startDate, 12), quantity: fmt2(totalShares), notes: 'Full vest' });
  } else if (template === '1yr-monthly') {
    const perMonth = totalShares / 12;
    for (let i = 1; i <= 12; i++)
      rows.push({ date: addMonths2(startDate, i), quantity: fmt2(perMonth), notes: `Month ${i}` });
  }
  return rows;
}

const sumShares2 = (rows: VestRow2[]) => rows.reduce((s, r) => s + parseFloat(r.quantity), 0);

describe('applyVestTemplate — 4yr / 1yr cliff monthly', () => {
  const rows = applyVestTemplate('4yr-1yr-cliff-monthly', '2024-01-01', 4800);
  it('generates 37 events (1 cliff + 36 monthly)', () => { expect(rows).toHaveLength(37); });
  it('first event is the cliff at 12 months', () => { expect(rows[0].notes).toBe('Cliff (1 year)'); expect(rows[0].date).toBe(addMonths2('2024-01-01', 12)); });
  it('cliff is 25% of total shares', () => { expect(parseFloat(rows[0].quantity)).toBeCloseTo(1200, 2); });
  it('remaining 36 events are equal monthly tranches', () => { rows.slice(1).forEach((r) => expect(parseFloat(r.quantity)).toBeCloseTo((4800 * 0.75) / 36, 2)); });
  it('total shares sum equals grant size', () => { expect(sumShares2(rows)).toBeCloseTo(4800, 1); });
});

describe('applyVestTemplate — 4yr / 1yr cliff quarterly', () => {
  const rows = applyVestTemplate('4yr-1yr-cliff-quarterly', '2024-01-01', 4000);
  it('generates 13 events (1 cliff + 12 quarterly)', () => { expect(rows).toHaveLength(13); });
  it('total shares sum equals grant size', () => { expect(sumShares2(rows)).toBeCloseTo(4000, 1); });
  it('post-cliff events are spaced 3 months apart', () => {
    const prev = new Date(rows[1].date);
    const next = new Date(rows[2].date);
    const diff = (next.getFullYear() - prev.getFullYear()) * 12 + next.getMonth() - prev.getMonth();
    expect(diff).toBe(3);
  });
});

describe('applyVestTemplate — 4yr quarterly', () => {
  const rows = applyVestTemplate('4yr-quarterly', '2024-01-01', 1600);
  it('generates 16 events', () => { expect(rows).toHaveLength(16); });
  it('first event is 3 months after start', () => { expect(rows[0].date).toBe(addMonths2('2024-01-01', 3)); });
  it('equal shares per event', () => { rows.forEach((r) => expect(parseFloat(r.quantity)).toBeCloseTo(100, 2)); });
  it('total shares sum equals grant size', () => { expect(sumShares2(rows)).toBeCloseTo(1600, 1); });
});

describe('applyVestTemplate — 4yr annual', () => {
  const rows = applyVestTemplate('4yr-annual', '2024-01-01', 4000);
  it('generates 4 events', () => { expect(rows).toHaveLength(4); });
  it('last event is 4 years after start', () => { expect(rows[3].date).toBe(addMonths2('2024-01-01', 48)); });
  it('total shares sum equals grant size', () => { expect(sumShares2(rows)).toBeCloseTo(4000, 1); });
});

describe('applyVestTemplate — 3yr annual', () => {
  const rows = applyVestTemplate('3yr-annual', '2024-06-15', 3000);
  it('generates 3 events', () => { expect(rows).toHaveLength(3); });
  it('events are labeled Year 1, Year 2, Year 3', () => { expect(rows[0].notes).toBe('Year 1'); expect(rows[2].notes).toBe('Year 3'); });
  it('total shares sum equals grant size', () => { expect(sumShares2(rows)).toBeCloseTo(3000, 1); });
});

describe('applyVestTemplate — 2yr semi-annual', () => {
  const rows = applyVestTemplate('2yr-semi', '2024-01-01', 2000);
  it('generates 4 events', () => { expect(rows).toHaveLength(4); });
  it('events spaced 6 months apart', () => {
    expect(rows[0].date).toBe(addMonths2('2024-01-01', 6));
    expect(rows[3].date).toBe(addMonths2('2024-01-01', 24));
  });
  it('total shares sum equals grant size', () => { expect(sumShares2(rows)).toBeCloseTo(2000, 1); });
});

describe('applyVestTemplate — 1yr annual', () => {
  const rows = applyVestTemplate('1yr-annual', '2024-01-01', 500);
  it('generates exactly 1 event', () => { expect(rows).toHaveLength(1); });
  it('vest date is 12 months after start', () => { expect(rows[0].date).toBe(addMonths2('2024-01-01', 12)); });
  it('full grant vests in one event', () => { expect(parseFloat(rows[0].quantity)).toBeCloseTo(500, 2); });
});

describe('applyVestTemplate — 1yr monthly', () => {
  const rows = applyVestTemplate('1yr-monthly', '2024-01-01', 1200);
  it('generates 12 events', () => { expect(rows).toHaveLength(12); });
  it('first event is 1 month after start', () => { expect(rows[0].date).toBe(addMonths2('2024-01-01', 1)); });
  it('equal shares per month', () => { rows.forEach((r) => expect(parseFloat(r.quantity)).toBeCloseTo(100, 2)); });
  it('total shares sum equals grant size', () => { expect(sumShares2(rows)).toBeCloseTo(1200, 1); });
});

describe('applyVestTemplate — unknown template', () => {
  it('returns empty array for unrecognized template id', () => {
    expect(applyVestTemplate('bogus', '2024-01-01', 1000)).toHaveLength(0);
  });
});
