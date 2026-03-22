/**
 * Tests for AccountDataSummary exclusion toggle logic and bucket computation.
 *
 * Covers:
 * - localExcluded state initialized from scenario.excluded_account_ids
 * - handleToggleAccount adds/removes IDs from excluded set
 * - Bucket totals exclude excluded accounts
 * - Cash interest rate badge display logic
 * - "Excluded from simulation" section visibility
 */

import { describe, it, expect } from 'vitest';

// ── Types ─────────────────────────────────────────────────────────────────

type AccountBucket = 'pre_tax' | 'roth' | 'taxable' | 'hsa' | 'cash' | 'excluded';

interface AccountItem {
  id: string;
  name: string;
  balance: number;
  bucket: AccountBucket;
  account_type: string;
  interest_rate?: number;
  excluded: boolean;
}

interface AccountData {
  total_portfolio: number;
  accounts: AccountItem[];
  annual_income: number;
  annual_contributions: number;
  employer_match_annual: number;
  pension_monthly: number;
}

// ── Helpers mirroring AccountDataSummary logic ───────────────────────────

/** Initialize excluded set from scenario (mirrors useState initializer). */
function initExcluded(excludedAccountIds: string[] | null | undefined): Set<string> {
  return new Set(excludedAccountIds ?? []);
}

/** Toggle an account in/out of the excluded set. Returns new set. */
function toggleAccount(excluded: Set<string>, accountId: string, checked: boolean): Set<string> {
  const next = new Set(excluded);
  if (checked) {
    next.delete(accountId); // include
  } else {
    next.add(accountId); // exclude
  }
  return next;
}

/** Compute bucket totals (mirrors AccountDataSummary useMemo). */
function computeBuckets(
  accounts: AccountItem[],
  localExcluded: Set<string>
): Array<{ key: string; label: string; value: number; pct: number }> {
  const includedAccounts = accounts.filter((a) => !localExcluded.has(a.id));
  const total =
    includedAccounts.reduce(
      (s, a) => s + (a.bucket !== 'excluded' ? a.balance : 0),
      0
    ) || 1;

  const sum = (bucket: AccountBucket) =>
    includedAccounts.filter((a) => a.bucket === bucket).reduce((s, a) => s + a.balance, 0);

  const preTax = sum('pre_tax');
  const roth = sum('roth');
  const hsa = sum('hsa');
  const cashVal = sum('cash');
  const taxable = sum('taxable');
  const brokerage = taxable - cashVal;

  const items = [
    { key: 'pre_tax', label: 'Pre-Tax (401k, IRA)', value: preTax, pct: (preTax / total) * 100 },
    { key: 'roth', label: 'Roth', value: roth, pct: (roth / total) * 100 },
    { key: 'taxable', label: 'Taxable (Brokerage)', value: brokerage, pct: (brokerage / total) * 100 },
    { key: 'hsa', label: 'HSA', value: hsa, pct: (hsa / total) * 100 },
    { key: 'cash', label: 'Cash (Checking/Savings)', value: cashVal, pct: (cashVal / total) * 100 },
  ];

  return items.filter((b) => b.value > 0);
}

/** Compute the total portfolio value shown at top (mirrors the template). */
function computeDisplayTotal(accounts: AccountItem[], localExcluded: Set<string>): number {
  return accounts
    .filter((a) => !localExcluded.has(a.id) && a.bucket !== 'excluded')
    .reduce((s, a) => s + a.balance, 0);
}

/** Cash interest rate badge display logic. */
function cashBadgeText(interestRate: number): string {
  return interestRate > 0 ? `${interestRate.toFixed(2)}%` : '0%';
}

function cashBadgeColor(interestRate: number): string {
  return interestRate > 0 ? 'green' : 'gray';
}

// ── Fixtures ──────────────────────────────────────────────────────────────

const IRA_ID = 'acct-ira-1';
const ROTH_ID = 'acct-roth-1';
const SAVINGS_ID = 'acct-savings-1';
const CHECKING_ID = 'acct-checking-1';

const SAMPLE_ACCOUNTS: AccountItem[] = [
  { id: IRA_ID, name: 'Traditional IRA', balance: 50000, bucket: 'pre_tax', account_type: 'traditional_ira', excluded: false },
  { id: ROTH_ID, name: 'Roth IRA', balance: 30000, bucket: 'roth', account_type: 'roth_ira', excluded: false },
  { id: SAVINGS_ID, name: 'HYSA', balance: 10000, bucket: 'cash', account_type: 'savings', interest_rate: 4.5, excluded: false },
  { id: CHECKING_ID, name: 'Checking', balance: 2000, bucket: 'cash', account_type: 'checking', interest_rate: 0, excluded: false },
];

// ── Tests ──────────────────────────────────────────────────────────────────

describe('AccountDataSummary — excluded state initialization', () => {
  it('should initialize empty set when scenario has no excluded accounts', () => {
    const set = initExcluded(null);
    expect(set.size).toBe(0);
  });

  it('should initialize set from scenario.excluded_account_ids', () => {
    const set = initExcluded([IRA_ID, ROTH_ID]);
    expect(set.has(IRA_ID)).toBe(true);
    expect(set.has(ROTH_ID)).toBe(true);
    expect(set.size).toBe(2);
  });

  it('should handle empty array as no exclusions', () => {
    const set = initExcluded([]);
    expect(set.size).toBe(0);
  });

  it('should handle undefined the same as null', () => {
    const set = initExcluded(undefined);
    expect(set.size).toBe(0);
  });
});

describe('AccountDataSummary — toggleAccount', () => {
  it('should exclude an account when unchecked', () => {
    const excluded = new Set<string>();
    const next = toggleAccount(excluded, IRA_ID, false);
    expect(next.has(IRA_ID)).toBe(true);
  });

  it('should include (un-exclude) an account when checked', () => {
    const excluded = new Set<string>([IRA_ID]);
    const next = toggleAccount(excluded, IRA_ID, true);
    expect(next.has(IRA_ID)).toBe(false);
  });

  it('should not mutate the original set', () => {
    const excluded = new Set<string>([ROTH_ID]);
    const next = toggleAccount(excluded, IRA_ID, false);
    expect(excluded.has(IRA_ID)).toBe(false); // original unchanged
    expect(next.has(IRA_ID)).toBe(true);       // new set has exclusion
  });

  it('should toggle multiple accounts independently', () => {
    let excluded = new Set<string>();
    excluded = toggleAccount(excluded, IRA_ID, false);
    excluded = toggleAccount(excluded, ROTH_ID, false);
    expect(excluded.size).toBe(2);

    excluded = toggleAccount(excluded, IRA_ID, true);
    expect(excluded.size).toBe(1);
    expect(excluded.has(ROTH_ID)).toBe(true);
  });

  it('including an already-included account is a no-op', () => {
    const excluded = new Set<string>();
    const next = toggleAccount(excluded, IRA_ID, true);
    expect(next.size).toBe(0);
  });

  it('excluding an already-excluded account keeps it excluded', () => {
    const excluded = new Set<string>([IRA_ID]);
    const next = toggleAccount(excluded, IRA_ID, false);
    expect(next.has(IRA_ID)).toBe(true);
  });
});

describe('AccountDataSummary — bucket totals with exclusions', () => {
  it('should include all accounts when nothing is excluded', () => {
    const excluded = new Set<string>();
    const buckets = computeBuckets(SAMPLE_ACCOUNTS, excluded);

    const preTax = buckets.find((b) => b.key === 'pre_tax');
    const roth = buckets.find((b) => b.key === 'roth');
    const cash = buckets.find((b) => b.key === 'cash');

    expect(preTax?.value).toBe(50000);
    expect(roth?.value).toBe(30000);
    expect(cash?.value).toBe(12000); // 10000 + 2000
  });

  it('should exclude an account from bucket totals when it is in localExcluded', () => {
    const excluded = new Set<string>([IRA_ID]);
    const buckets = computeBuckets(SAMPLE_ACCOUNTS, excluded);

    const preTax = buckets.find((b) => b.key === 'pre_tax');
    // IRA excluded → pre_tax bucket should have 0 (filtered out entirely)
    expect(preTax).toBeUndefined(); // filtered because value is 0
  });

  it('should recalculate percentages after exclusion', () => {
    const excluded = new Set<string>([IRA_ID]);
    const buckets = computeBuckets(SAMPLE_ACCOUNTS, excluded);

    const total = buckets.reduce((s, b) => s + b.value, 0);
    const pctSum = buckets.reduce((s, b) => s + b.pct, 0);

    // All percentages should sum to ~100% of the new (smaller) total
    expect(pctSum).toBeCloseTo(100, 0);

    // Roth should now be a larger share
    const roth = buckets.find((b) => b.key === 'roth');
    expect(roth).toBeDefined();
    expect(roth!.pct).toBeGreaterThan(50); // 30000 / 42000 ≈ 71%
  });

  it('should return empty array when all accounts are excluded', () => {
    const allIds = SAMPLE_ACCOUNTS.map((a) => a.id);
    const excluded = new Set<string>(allIds);
    const buckets = computeBuckets(SAMPLE_ACCOUNTS, excluded);
    expect(buckets.length).toBe(0);
  });
});

describe('AccountDataSummary — display total', () => {
  it('should show total of included non-excluded-bucket accounts', () => {
    const excluded = new Set<string>();
    const total = computeDisplayTotal(SAMPLE_ACCOUNTS, excluded);
    expect(total).toBe(92000); // 50000 + 30000 + 10000 + 2000
  });

  it('should reduce total when account is excluded', () => {
    const excluded = new Set<string>([IRA_ID]);
    const total = computeDisplayTotal(SAMPLE_ACCOUNTS, excluded);
    expect(total).toBe(42000); // without the $50k IRA
  });

  it('should show 0 when everything is excluded', () => {
    const allIds = SAMPLE_ACCOUNTS.map((a) => a.id);
    const excluded = new Set<string>(allIds);
    const total = computeDisplayTotal(SAMPLE_ACCOUNTS, excluded);
    expect(total).toBe(0);
  });
});

describe('AccountDataSummary — cash interest rate badge', () => {
  it('should show formatted percentage for positive rate', () => {
    expect(cashBadgeText(4.5)).toBe('4.50%');
    expect(cashBadgeColor(4.5)).toBe('green');
  });

  it('should show 0% for zero interest rate', () => {
    expect(cashBadgeText(0)).toBe('0%');
    expect(cashBadgeColor(0)).toBe('gray');
  });

  it('should use green color for any positive rate', () => {
    expect(cashBadgeColor(0.01)).toBe('green');
  });

  it('should use gray color for 0% (cash under a sofa)', () => {
    expect(cashBadgeColor(0)).toBe('gray');
  });

  it('should format interest rates with 2 decimal places', () => {
    expect(cashBadgeText(3.0)).toBe('3.00%');
    expect(cashBadgeText(1.25)).toBe('1.25%');
  });
});

describe('AccountDataSummary — excluded section visibility', () => {
  it('should show excluded section when any account is excluded', () => {
    const accounts = SAMPLE_ACCOUNTS;
    const excluded = new Set<string>([IRA_ID]);

    const hasExcluded = accounts.some((a) => excluded.has(a.id));
    expect(hasExcluded).toBe(true);
  });

  it('should hide excluded section when nothing is excluded', () => {
    const accounts = SAMPLE_ACCOUNTS;
    const excluded = new Set<string>();

    const hasExcluded = accounts.some((a) => excluded.has(a.id));
    expect(hasExcluded).toBe(false);
  });

  it('excluded section should list only excluded accounts', () => {
    const accounts = SAMPLE_ACCOUNTS;
    const excluded = new Set<string>([IRA_ID]);

    const excludedAccounts = accounts.filter((a) => excluded.has(a.id));
    expect(excludedAccounts.length).toBe(1);
    expect(excludedAccounts[0].id).toBe(IRA_ID);
  });

  it('bucket sections should not show excluded accounts in per-account list', () => {
    const accounts = SAMPLE_ACCOUNTS;
    const excluded = new Set<string>([IRA_ID]);

    // Per-bucket account list uses data.accounts?.filter(a => a.bucket === bucket.key)
    // (NOT filtered by localExcluded) — UI dims them with opacity
    const preTaxAccounts = accounts.filter((a) => a.bucket === 'pre_tax');
    // The IRA still shows up in the bucket list (greyed out by opacity)
    expect(preTaxAccounts.length).toBe(1);
    // But the bucket totals do NOT include it
    const excluded_set = new Set<string>([IRA_ID]);
    const buckets = computeBuckets(accounts, excluded_set);
    const preTaxBucket = buckets.find((b) => b.key === 'pre_tax');
    expect(preTaxBucket).toBeUndefined(); // excluded from total
  });
});

describe('AccountDataSummary — scenario excluded_account_ids round-trip', () => {
  it('should fire onExcludedAccountsChange with array of excluded IDs', () => {
    // Simulate the component calling onExcludedAccountsChange([...next])
    let capturedIds: string[] = [];
    const onExcludedAccountsChange = (ids: string[]) => { capturedIds = ids; };

    let excluded = new Set<string>();
    excluded = toggleAccount(excluded, IRA_ID, false);
    onExcludedAccountsChange([...excluded]);

    expect(capturedIds).toContain(IRA_ID);
    expect(capturedIds.length).toBe(1);
  });

  it('should fire onExcludedAccountsChange with empty array when all re-included', () => {
    let capturedIds: string[] = ['initial'];
    const onExcludedAccountsChange = (ids: string[]) => { capturedIds = ids; };

    let excluded = new Set<string>([IRA_ID]);
    excluded = toggleAccount(excluded, IRA_ID, true);
    onExcludedAccountsChange([...excluded]);

    expect(capturedIds.length).toBe(0);
  });
});
