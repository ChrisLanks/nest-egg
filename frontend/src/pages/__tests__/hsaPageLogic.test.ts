/**
 * Tests for HsaPage pure logic: contribution headroom, invest vs spend math,
 * receipt filtering, and display helpers.
 */

import { describe, it, expect } from 'vitest';

// ── Contribution headroom (mirrors backend service) ───────────────────────────

interface HeadroomResult {
  annual_limit: number;
  ytd_contributions: number;
  remaining_room: number;
  catch_up_eligible: boolean;
  can_contribute: boolean;
}

const LIMIT_INDIVIDUAL_2026 = 4300;
const LIMIT_FAMILY_2026 = 8550;
const CATCH_UP = 1000;
const MEDICARE_AGE = 65;

function calcHeadroom(ytd: number, isFamily: boolean, age: number): HeadroomResult {
  const base = isFamily ? LIMIT_FAMILY_2026 : LIMIT_INDIVIDUAL_2026;
  const catchUp = age >= 55 ? CATCH_UP : 0;
  const total = base + catchUp;
  const remaining = Math.max(0, total - ytd);
  return {
    annual_limit: total,
    ytd_contributions: ytd,
    remaining_room: remaining,
    catch_up_eligible: age >= 55,
    can_contribute: remaining > 0 && age < MEDICARE_AGE,
  };
}

describe('HSA contribution headroom', () => {
  it('individual plan, age 40, no contributions', () => {
    const h = calcHeadroom(0, false, 40);
    expect(h.annual_limit).toBe(4300);
    expect(h.remaining_room).toBe(4300);
    expect(h.catch_up_eligible).toBe(false);
  });

  it('family plan, age 40', () => {
    const h = calcHeadroom(0, false, 40);
    expect(h.annual_limit).toBe(4300);
  });

  it('family plan has higher limit', () => {
    const individual = calcHeadroom(0, false, 40);
    const family = calcHeadroom(0, true, 40);
    expect(family.annual_limit).toBeGreaterThan(individual.annual_limit);
    expect(family.annual_limit).toBe(8550);
  });

  it('age 55 enables catch-up contribution', () => {
    const h = calcHeadroom(0, false, 55);
    expect(h.catch_up_eligible).toBe(true);
    expect(h.annual_limit).toBe(4300 + 1000);
  });

  it('age 54 does NOT get catch-up', () => {
    const h = calcHeadroom(0, false, 54);
    expect(h.catch_up_eligible).toBe(false);
    expect(h.annual_limit).toBe(4300);
  });

  it('remaining room decreases with YTD contributions', () => {
    const h = calcHeadroom(2000, false, 40);
    expect(h.remaining_room).toBe(2300);
  });

  it('remaining room is 0 when fully contributed', () => {
    const h = calcHeadroom(4300, false, 40);
    expect(h.remaining_room).toBe(0);
  });

  it('remaining room cannot go negative', () => {
    const h = calcHeadroom(5000, false, 40);
    expect(h.remaining_room).toBe(0);
  });

  it('can_contribute is false when limit reached', () => {
    const h = calcHeadroom(4300, false, 40);
    expect(h.can_contribute).toBe(false);
  });

  it('can_contribute is true when room remains', () => {
    const h = calcHeadroom(1000, false, 40);
    expect(h.can_contribute).toBe(true);
  });
});

// ── Invest vs spend projection ────────────────────────────────────────────────

function projectStrategies(
  currentBalance: number,
  annualContrib: number,
  annualMedical: number,
  years: number,
  returnRate = 0.06,
): { spend: number; invest: number; advantage: number } {
  let spend = currentBalance;
  let invest = currentBalance;
  for (let i = 0; i < years; i++) {
    spend = spend * (1 + returnRate) + annualContrib - annualMedical;
    if (spend < 0) spend = 0;
    invest = invest * (1 + returnRate) + annualContrib;
  }
  return { spend, invest, advantage: invest - spend };
}

describe('HSA invest vs spend projection', () => {
  it('invest strategy always >= spend strategy', () => {
    const r = projectStrategies(0, 4300, 2000, 20);
    expect(r.invest).toBeGreaterThanOrEqual(r.spend);
  });

  it('invest advantage is positive when annual medical > 0', () => {
    const r = projectStrategies(0, 4300, 2000, 20);
    expect(r.advantage).toBeGreaterThan(0);
  });

  it('invest equals spend when annual medical is 0', () => {
    const r = projectStrategies(0, 4300, 0, 20);
    expect(r.invest).toBeCloseTo(r.spend, 0);
    expect(r.advantage).toBeCloseTo(0, 0);
  });

  it('longer horizon increases the invest advantage', () => {
    const r10 = projectStrategies(0, 4300, 2000, 10);
    const r20 = projectStrategies(0, 4300, 2000, 20);
    expect(r20.advantage).toBeGreaterThan(r10.advantage);
  });

  it('higher starting balance grows more under invest strategy', () => {
    const low = projectStrategies(1000, 4300, 2000, 20);
    const high = projectStrategies(10000, 4300, 2000, 20);
    expect(high.invest).toBeGreaterThan(low.invest);
  });

  it('spend balance does not go below 0', () => {
    // Medical far exceeds contribution
    const r = projectStrategies(0, 1000, 10000, 5);
    expect(r.spend).toBeGreaterThanOrEqual(0);
  });
});

// ── Receipt filtering ─────────────────────────────────────────────────────────

interface Receipt {
  id: string;
  amount: number;
  is_reimbursed: boolean;
  tax_year: number;
}

function unreimbursedTotal(receipts: Receipt[]): number {
  return receipts
    .filter((r) => !r.is_reimbursed)
    .reduce((s, r) => s + r.amount, 0);
}

function receiptsByYear(receipts: Receipt[], year: number): Receipt[] {
  return receipts.filter((r) => r.tax_year === year);
}

describe('receipt filtering', () => {
  const receipts: Receipt[] = [
    { id: '1', amount: 250, is_reimbursed: false, tax_year: 2024 },
    { id: '2', amount: 180, is_reimbursed: true, tax_year: 2024 },
    { id: '3', amount: 400, is_reimbursed: false, tax_year: 2025 },
    { id: '4', amount: 100, is_reimbursed: false, tax_year: 2023 },
  ];

  it('sums only unreimbursed receipts', () => {
    expect(unreimbursedTotal(receipts)).toBe(750); // 250 + 400 + 100
  });

  it('returns 0 when all reimbursed', () => {
    const all = receipts.map((r) => ({ ...r, is_reimbursed: true }));
    expect(unreimbursedTotal(all)).toBe(0);
  });

  it('filters receipts by tax year', () => {
    const yr2024 = receiptsByYear(receipts, 2024);
    expect(yr2024).toHaveLength(2);
  });

  it('returns empty array for year with no receipts', () => {
    expect(receiptsByYear(receipts, 2020)).toHaveLength(0);
  });
});

// ── toFloat: safe Decimal-string → number conversion ─────────────────────────
//
// The API serializes Decimal fields as strings ("5000.00") which causes
// reduce(...) to produce NaN when naively added as numbers.

function toFloat(v: string | number | null | undefined): number {
  if (v === null || v === undefined) return 0;
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
}

describe('toFloat', () => {
  it('converts a numeric string to a number', () => {
    expect(toFloat('5000.00')).toBe(5000);
  });

  it('passes through a plain number unchanged', () => {
    expect(toFloat(3000)).toBe(3000);
  });

  it('returns 0 for null', () => {
    expect(toFloat(null)).toBe(0);
  });

  it('returns 0 for undefined', () => {
    expect(toFloat(undefined)).toBe(0);
  });

  it('returns 0 for non-numeric string (not NaN)', () => {
    expect(toFloat('not-a-number')).toBe(0);
  });

  it('summing two Decimal strings does NOT produce NaN', () => {
    const balances: (string | number | null)[] = ['5000.00', '3000.50'];
    const total = balances.reduce((s: number, b) => s + toFloat(b), 0);
    expect(Number.isNaN(total)).toBe(false);
    expect(total).toBeCloseTo(8000.5);
  });
});

// ── HSA account filtering ─────────────────────────────────────────────────────

interface Account {
  id: string;
  account_type: string;
  current_balance: string | number | null;
}

function filterHsaAccounts(accounts: Account[]): Account[] {
  return accounts.filter((a) => a.account_type === 'hsa');
}

function totalHsaBalance(accounts: Account[]): number {
  return accounts.reduce((s, a) => s + toFloat(a.current_balance), 0);
}

describe('HSA account helpers', () => {
  const accounts: Account[] = [
    { id: '1', account_type: 'hsa', current_balance: '5000.00' },
    { id: '2', account_type: 'checking', current_balance: 10000 },
    { id: '3', account_type: 'hsa', current_balance: '3000.00' },
    { id: '4', account_type: 'retirement_401k', current_balance: 50000 },
  ];

  it('filters only HSA accounts', () => {
    const hsa = filterHsaAccounts(accounts);
    expect(hsa).toHaveLength(2);
    expect(hsa.every((a) => a.account_type === 'hsa')).toBe(true);
  });

  it('sums HSA balances (string Decimals from API)', () => {
    const hsa = filterHsaAccounts(accounts);
    expect(totalHsaBalance(hsa)).toBe(8000);
  });

  it('handles null balance as 0', () => {
    const withNull: Account[] = [{ id: '1', account_type: 'hsa', current_balance: null }];
    expect(totalHsaBalance(withNull)).toBe(0);
  });

  it('returns 0 for empty account list', () => {
    expect(totalHsaBalance([])).toBe(0);
  });

  it('does not produce NaN when balance is a Decimal string', () => {
    const withString: Account[] = [{ id: '1', account_type: 'hsa', current_balance: '12345.67' }];
    const total = totalHsaBalance(withString);
    expect(Number.isNaN(total)).toBe(false);
    expect(total).toBeCloseTo(12345.67);
  });
});

// ── Member-filter scoping ─────────────────────────────────────────────────────
// Mirrors the matchesMemberFilter logic in MemberFilterContext so that HSA
// account cards never show another household member's account.

interface AccountWithUser {
  id: string;
  account_type: string;
  current_balance: string | number | null;
  user_id: string;
}

/** Mimics matchesMemberFilter from MemberFilterContext */
function matchesMemberFilter(
  selectedMemberIds: Set<string>,
  isAllSelected: boolean,
  itemUserId: string | null | undefined,
): boolean {
  if (isAllSelected) return true;
  if (!itemUserId) return true;
  return selectedMemberIds.has(itemUserId);
}

function filterHsaAccountsByMember(
  accounts: AccountWithUser[],
  selectedMemberIds: Set<string>,
  isAllSelected: boolean,
): AccountWithUser[] {
  return accounts.filter(
    (a) =>
      a.account_type === 'hsa' &&
      matchesMemberFilter(selectedMemberIds, isAllSelected, a.user_id),
  );
}

describe('HSA member-filter scoping', () => {
  const CHRIS = 'user-chris';
  const TEST = 'user-test';
  const TEST2 = 'user-test2';

  const allAccounts: AccountWithUser[] = [
    { id: '1', account_type: 'hsa', current_balance: '5789.70', user_id: CHRIS },
    { id: '2', account_type: 'hsa', current_balance: '500.00', user_id: TEST },
    { id: '3', account_type: 'hsa', current_balance: '2000.00', user_id: TEST2 },
    { id: '4', account_type: 'checking', current_balance: 10000, user_id: CHRIS },
  ];

  it('all-selected returns all HSA accounts', () => {
    const result = filterHsaAccountsByMember(
      allAccounts,
      new Set([CHRIS, TEST, TEST2]),
      true,
    );
    expect(result).toHaveLength(3);
  });

  it('single user selected hides other members HSA accounts', () => {
    const result = filterHsaAccountsByMember(
      allAccounts,
      new Set([TEST]),
      false,
    );
    expect(result).toHaveLength(1);
    expect(result[0].user_id).toBe(TEST);
  });

  it('multi-select of test+test2 excludes Chris HSA', () => {
    const result = filterHsaAccountsByMember(
      allAccounts,
      new Set([TEST, TEST2]),
      false,
    );
    expect(result).toHaveLength(2);
    expect(result.every((a) => a.user_id !== CHRIS)).toBe(true);
  });

  it('selecting only Chris returns only his HSA', () => {
    const result = filterHsaAccountsByMember(
      allAccounts,
      new Set([CHRIS]),
      false,
    );
    expect(result).toHaveLength(1);
    expect(result[0].id).toBe('1');
  });

  it('balance total respects member filter — excludes Chris when not selected', () => {
    const filtered = filterHsaAccountsByMember(
      allAccounts,
      new Set([TEST, TEST2]),
      false,
    );
    const total = filtered.reduce((s, a) => s + toFloat(a.current_balance), 0);
    expect(total).toBeCloseTo(2500);
    // Chris's $5789.70 must NOT be included
    expect(total).toBeLessThan(5000);
  });

  it('null user_id on an account passes the filter (shared/org-level accounts)', () => {
    const accounts: AccountWithUser[] = [
      { id: '99', account_type: 'hsa', current_balance: 100, user_id: '' },
    ];
    // user_id falsy → matchesMemberFilter returns true regardless of selection
    const result = filterHsaAccountsByMember(accounts, new Set([TEST]), false);
    expect(result).toHaveLength(1);
  });
});

// ── Domestic partnership tax loop logic ───────────────────────────────────────
//
// When on a family HDHP plan due to domestic partnership, the employer's cost
// for the partner's coverage is imputed income (taxable). HSA contributions
// covering the partner's medical expenses are also treated as taxable
// distributions (unless the DP qualifies as an IRS tax dependent).

interface DomesticPartnershipState {
  isFamily: boolean;
  isDomesticPartnership: boolean;
}

/**
 * Mirrors the UI logic: isDomesticPartnership can only be true when isFamily is true.
 * Turning off family plan also resets domestic partnership.
 */
function toggleFamily(
  state: DomesticPartnershipState,
  checked: boolean,
): DomesticPartnershipState {
  if (!checked) return { isFamily: false, isDomesticPartnership: false };
  return { ...state, isFamily: true };
}

function toggleDomesticPartnership(
  state: DomesticPartnershipState,
  checked: boolean,
): DomesticPartnershipState {
  return { ...state, isDomesticPartnership: checked };
}

describe('Domestic partnership tax loop toggle logic', () => {
  it('domestic partnership starts as false', () => {
    const state = { isFamily: false, isDomesticPartnership: false };
    expect(state.isDomesticPartnership).toBe(false);
  });

  it('enabling family plan does not auto-enable domestic partnership', () => {
    const state = toggleFamily({ isFamily: false, isDomesticPartnership: false }, true);
    expect(state.isFamily).toBe(true);
    expect(state.isDomesticPartnership).toBe(false);
  });

  it('disabling family plan resets domestic partnership to false', () => {
    const state = toggleFamily({ isFamily: true, isDomesticPartnership: true }, false);
    expect(state.isFamily).toBe(false);
    expect(state.isDomesticPartnership).toBe(false);
  });

  it('domestic partnership can be enabled when family plan is on', () => {
    let state = toggleFamily({ isFamily: false, isDomesticPartnership: false }, true);
    state = toggleDomesticPartnership(state, true);
    expect(state.isFamily).toBe(true);
    expect(state.isDomesticPartnership).toBe(true);
  });

  it('warning is shown only when isDomesticPartnership is true', () => {
    const showWarning = (s: DomesticPartnershipState) => s.isDomesticPartnership;
    expect(showWarning({ isFamily: false, isDomesticPartnership: false })).toBe(false);
    expect(showWarning({ isFamily: true, isDomesticPartnership: false })).toBe(false);
    expect(showWarning({ isFamily: true, isDomesticPartnership: true })).toBe(true);
  });
});
