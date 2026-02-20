/**
 * Unit tests for pure business logic used by dashboard widgets.
 *
 * All tests operate on plain data — no React rendering or API calls.
 */

import { describe, it, expect } from 'vitest';

// ── Debt filtering (DebtSummaryWidget) ───────────────────────────────────────

const DEBT_TYPES = new Set([
  'credit_card',
  'loan',
  'student_loan',
  'mortgage',
  'heloc',
  'personal_loan',
  'auto_loan',
  'line_of_credit',
  'private_debt',
]);

type AccountBalance = { id: string; name: string; type: string; balance: number };

const filterDebtAccounts = (accounts: AccountBalance[]) =>
  accounts.filter((a) => DEBT_TYPES.has(a.type) && a.balance < 0);

const sumDebt = (accounts: AccountBalance[]) =>
  accounts.reduce((sum, a) => sum + Math.abs(a.balance), 0);

describe('DebtSummaryWidget — debt account filtering', () => {
  const sampleAccounts: AccountBalance[] = [
    { id: '1', name: 'Chase Visa', type: 'credit_card', balance: -2500 },
    { id: '2', name: 'Student Loan', type: 'student_loan', balance: -15000 },
    { id: '3', name: 'Savings', type: 'savings', balance: 10000 },
    { id: '4', name: 'Checking', type: 'checking', balance: 3000 },
    { id: '5', name: 'Mortgage', type: 'mortgage', balance: -250000 },
    { id: '6', name: 'Auto Loan', type: 'auto_loan', balance: -8000 },
    { id: '7', name: 'Investment', type: 'investment', balance: 50000 },
    { id: '8', name: 'HELOC', type: 'heloc', balance: -12000 },
    { id: '9', name: 'Paid-off card', type: 'credit_card', balance: 0 },
  ];

  it('includes all debt-type accounts with negative balances', () => {
    const result = filterDebtAccounts(sampleAccounts);
    expect(result.map((a) => a.id).sort()).toEqual(['1', '2', '5', '6', '8'].sort());
    const ids = new Set(result.map((a) => a.id));
    expect(ids.has('1')).toBe(true); // credit card
    expect(ids.has('2')).toBe(true); // student loan
    expect(ids.has('5')).toBe(true); // mortgage
    expect(ids.has('6')).toBe(true); // auto loan
    expect(ids.has('8')).toBe(true); // heloc
  });

  it('excludes asset accounts (savings, checking, investment)', () => {
    const result = filterDebtAccounts(sampleAccounts);
    const ids = new Set(result.map((a) => a.id));
    expect(ids.has('3')).toBe(false); // savings
    expect(ids.has('4')).toBe(false); // checking
    expect(ids.has('7')).toBe(false); // investment
  });

  it('excludes zero-balance credit card accounts', () => {
    const result = filterDebtAccounts(sampleAccounts);
    const ids = new Set(result.map((a) => a.id));
    expect(ids.has('9')).toBe(false);
  });

  it('returns empty array when no debt accounts exist', () => {
    const assets: AccountBalance[] = [
      { id: '1', name: 'Checking', type: 'checking', balance: 5000 },
    ];
    expect(filterDebtAccounts(assets)).toHaveLength(0);
  });

  it('calculates total debt as sum of absolute balances', () => {
    const debts = filterDebtAccounts(sampleAccounts);
    const total = sumDebt(debts);
    expect(total).toBe(2500 + 15000 + 250000 + 8000 + 12000);
  });

  it('recognizes all DEBT_TYPES', () => {
    const expectedTypes = [
      'credit_card', 'loan', 'student_loan', 'mortgage',
      'heloc', 'personal_loan', 'auto_loan', 'line_of_credit', 'private_debt',
    ];
    for (const type of expectedTypes) {
      expect(DEBT_TYPES.has(type), `"${type}" should be a debt type`).toBe(true);
    }
  });

  it('does not treat investment/brokerage as debt', () => {
    const nonDebtTypes = ['checking', 'savings', 'investment', 'brokerage', 'hsa', 'retirement'];
    for (const type of nonDebtTypes) {
      expect(DEBT_TYPES.has(type), `"${type}" should not be a debt type`).toBe(false);
    }
  });
});

// ── Budget progress computation (BudgetsWidget) ───────────────────────────────

type BudgetSpending = { spent: number; percentage: number };

const computeBudgetPct = (spending: BudgetSpending | undefined) =>
  spending ? Math.min(100, spending.percentage * 100) : 0;

const getBudgetColorScheme = (pct: number) =>
  pct >= 100 ? 'red' : pct >= 80 ? 'orange' : 'green';

describe('BudgetsWidget — progress percentage', () => {
  it('returns 0 when spending is undefined (still loading)', () => {
    expect(computeBudgetPct(undefined)).toBe(0);
  });

  it('converts fractional percentage correctly', () => {
    expect(computeBudgetPct({ spent: 50, percentage: 0.5 })).toBe(50);
  });

  it('clamps at 100 when over budget', () => {
    expect(computeBudgetPct({ spent: 600, percentage: 1.2 })).toBe(100);
  });

  it('handles exactly 100%', () => {
    expect(computeBudgetPct({ spent: 500, percentage: 1.0 })).toBe(100);
  });

  it('handles 0% spent', () => {
    expect(computeBudgetPct({ spent: 0, percentage: 0 })).toBe(0);
  });
});

describe('BudgetsWidget — color scheme', () => {
  it('green when under 80%', () => {
    expect(getBudgetColorScheme(0)).toBe('green');
    expect(getBudgetColorScheme(50)).toBe('green');
    expect(getBudgetColorScheme(79)).toBe('green');
  });

  it('orange between 80% and 99%', () => {
    expect(getBudgetColorScheme(80)).toBe('orange');
    expect(getBudgetColorScheme(95)).toBe('orange');
    expect(getBudgetColorScheme(99)).toBe('orange');
  });

  it('red at 100% (over budget)', () => {
    expect(getBudgetColorScheme(100)).toBe('red');
  });
});

// ── Savings goal progress (SavingsGoalsWidget) ────────────────────────────────

type Goal = { current_amount: number; target_amount: number; is_funded: boolean; is_completed: boolean };

const computeGoalPct = (goal: Goal) =>
  goal.target_amount > 0
    ? Math.min(100, (goal.current_amount / goal.target_amount) * 100)
    : 0;

const filterActiveGoals = (goals: Goal[]) =>
  goals.filter((g) => !g.is_funded && !g.is_completed);

describe('SavingsGoalsWidget — progress percentage', () => {
  it('calculates percentage correctly', () => {
    expect(computeGoalPct({ current_amount: 500, target_amount: 1000, is_funded: false, is_completed: false })).toBe(50);
  });

  it('clamps at 100 when current exceeds target', () => {
    expect(computeGoalPct({ current_amount: 1200, target_amount: 1000, is_funded: false, is_completed: false })).toBe(100);
  });

  it('returns 0 when target_amount is 0 (avoids divide-by-zero)', () => {
    expect(computeGoalPct({ current_amount: 0, target_amount: 0, is_funded: false, is_completed: false })).toBe(0);
  });

  it('returns 0 when nothing saved yet', () => {
    expect(computeGoalPct({ current_amount: 0, target_amount: 2000, is_funded: false, is_completed: false })).toBe(0);
  });
});

describe('SavingsGoalsWidget — active goal filtering', () => {
  const goals: Goal[] = [
    { current_amount: 0, target_amount: 1000, is_funded: false, is_completed: false },
    { current_amount: 1000, target_amount: 1000, is_funded: false, is_completed: true },
    { current_amount: 500, target_amount: 2000, is_funded: true, is_completed: false },
    { current_amount: 200, target_amount: 500, is_funded: false, is_completed: false },
  ];

  it('only includes non-funded, non-completed goals', () => {
    const active = filterActiveGoals(goals);
    expect(active).toHaveLength(2);
    expect(active[0].target_amount).toBe(1000);
    expect(active[1].target_amount).toBe(500);
  });

  it('excludes completed goals', () => {
    const active = filterActiveGoals(goals);
    expect(active.every((g) => !g.is_completed)).toBe(true);
  });

  it('excludes funded goals', () => {
    const active = filterActiveGoals(goals);
    expect(active.every((g) => !g.is_funded)).toBe(true);
  });

  it('returns empty array when all goals are done', () => {
    const done = goals.map((g) => ({ ...g, is_completed: true }));
    expect(filterActiveGoals(done)).toHaveLength(0);
  });
});

// ── NetWorthChartWidget — chartData fallback logic ────────────────────────────

type Snapshot = { snapshot_date: string; total_value: number };

const buildChartData = (
  rawHistory: Snapshot[],
  currentNetWorth: number | undefined
) => {
  if (rawHistory.length > 0) {
    return rawHistory.map((s) => ({
      date: new Date(s.snapshot_date).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
      }),
      value: Number(s.total_value),
    }));
  }
  if (currentNetWorth !== undefined) {
    return [
      {
        date: new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        value: currentNetWorth,
      },
    ];
  }
  return [];
};

describe('NetWorthChartWidget — chartData fallback', () => {
  const snapshots: Snapshot[] = [
    { snapshot_date: '2024-01-01', total_value: 100000 },
    { snapshot_date: '2024-02-01', total_value: 105000 },
  ];

  it('maps historical snapshots to {date, value} when available', () => {
    const data = buildChartData(snapshots, 110000);
    expect(data).toHaveLength(2);
    expect(data[0].value).toBe(100000);
    expect(data[1].value).toBe(105000);
  });

  it('uses historical data over current net worth (history takes priority)', () => {
    const data = buildChartData(snapshots, 999999);
    expect(data).toHaveLength(2);
    expect(data.every((d) => d.value !== 999999)).toBe(true);
  });

  it('falls back to single today point when history is empty but net worth is known', () => {
    const data = buildChartData([], 87500);
    expect(data).toHaveLength(1);
    expect(data[0].value).toBe(87500);
  });

  it('returns empty array when both history is empty and net worth is undefined', () => {
    expect(buildChartData([], undefined)).toHaveLength(0);
  });

  it('coerces total_value strings to numbers', () => {
    const stringSnapshot = [{ snapshot_date: '2024-01-01', total_value: '42000' as unknown as number }];
    const data = buildChartData(stringSnapshot, undefined);
    expect(typeof data[0].value).toBe('number');
    expect(data[0].value).toBe(42000);
  });
});
