/**
 * Tests for StressTestPanel pure logic functions.
 */

import { describe, it, expect } from 'vitest';

// ── Severity classification ────────────────────────────────────────────────────

function severityLabel(pctChange: number): string {
  if (pctChange <= -0.40) return 'Severe';
  if (pctChange <= -0.20) return 'High';
  if (pctChange <= -0.10) return 'Moderate';
  return 'Low';
}

function severityColor(pctChange: number): string {
  if (pctChange <= -0.40) return 'red';
  if (pctChange <= -0.20) return 'orange';
  if (pctChange <= -0.10) return 'yellow';
  return 'green';
}

describe('severityLabel', () => {
  it('labels -57% as Severe (GFC 2008)', () => {
    expect(severityLabel(-0.57)).toBe('Severe');
  });

  it('labels -49% as Severe (dot-com)', () => {
    expect(severityLabel(-0.49)).toBe('Severe');
  });

  it('labels -40% exactly as Severe (boundary)', () => {
    expect(severityLabel(-0.40)).toBe('Severe');
  });

  it('labels -34% as High (COVID)', () => {
    expect(severityLabel(-0.34)).toBe('High');
  });

  it('labels -20% exactly as High (boundary)', () => {
    expect(severityLabel(-0.20)).toBe('High');
  });

  it('labels -15% as Moderate', () => {
    expect(severityLabel(-0.15)).toBe('Moderate');
  });

  it('labels -10% exactly as Moderate (boundary)', () => {
    expect(severityLabel(-0.10)).toBe('Moderate');
  });

  it('labels -5% as Low', () => {
    expect(severityLabel(-0.05)).toBe('Low');
  });

  it('labels 0% as Low', () => {
    expect(severityLabel(0)).toBe('Low');
  });
});

describe('severityColor', () => {
  it('severe scenarios are red', () => {
    expect(severityColor(-0.57)).toBe('red');
  });

  it('high scenarios are orange', () => {
    expect(severityColor(-0.30)).toBe('orange');
  });

  it('moderate scenarios are yellow', () => {
    expect(severityColor(-0.15)).toBe('yellow');
  });

  it('low scenarios are green', () => {
    expect(severityColor(-0.05)).toBe('green');
  });
});

// ── Portfolio allocation percentages ─────────────────────────────────────────

function allocPct(assetValue: number, total: number): number {
  if (total === 0) return 0;
  return assetValue / total;
}

describe('allocPct', () => {
  it('returns 0 for zero total (no division by zero)', () => {
    expect(allocPct(0, 0)).toBe(0);
  });

  it('100% equity portfolio', () => {
    expect(allocPct(100000, 100000)).toBe(1);
  });

  it('60/40 split', () => {
    expect(allocPct(60000, 100000)).toBeCloseTo(0.6);
    expect(allocPct(40000, 100000)).toBeCloseTo(0.4);
  });

  it('percentages sum to 1 for a full portfolio', () => {
    const total = 150000;
    const equity = 90000;
    const bonds = 45000;
    const other = 15000;
    expect(allocPct(equity, total) + allocPct(bonds, total) + allocPct(other, total)).toBeCloseTo(1);
  });
});

// ── Dollar change calculation ─────────────────────────────────────────────────

function portfolioAfter(before: number, equityDrop: number, bondChange: number, equityPct: number, bondPct: number): number {
  const otherPct = 1 - equityPct - bondPct;
  const equity = before * equityPct;
  const bonds = before * bondPct;
  const other = before * otherPct;
  return equity * (1 + equityDrop) + bonds * (1 + bondChange) + other;
}

describe('portfolioAfter', () => {
  it('100% equity portfolio loses -57% in GFC', () => {
    const result = portfolioAfter(100000, -0.57, 0, 1, 0);
    expect(result).toBeCloseTo(43000);
  });

  it('60/40 portfolio is cushioned by bonds in equity crash', () => {
    const pureBefore = portfolioAfter(100000, -0.57, 0, 1, 0);
    const mixedBefore = portfolioAfter(100000, -0.57, 0.08, 0.6, 0.4);
    expect(mixedBefore).toBeGreaterThan(pureBefore);
  });

  it('zero equity means portfolio unchanged in equity crash', () => {
    const result = portfolioAfter(100000, -0.57, 0, 0, 0);
    expect(result).toBeCloseTo(100000);
  });
});

// ── Scenarios sorted worst to best ────────────────────────────────────────────

interface ScenarioResult {
  scenario_key: string;
  pct_change: number;
}

function sortedWorstToBest(scenarios: ScenarioResult[]): ScenarioResult[] {
  return [...scenarios].sort((a, b) => a.pct_change - b.pct_change);
}

describe('sortedWorstToBest', () => {
  const scenarios: ScenarioResult[] = [
    { scenario_key: 'covid_2020', pct_change: -0.34 },
    { scenario_key: 'gfc_2008', pct_change: -0.57 },
    { scenario_key: 'rate_shock', pct_change: -0.10 },
    { scenario_key: 'dot_com', pct_change: -0.49 },
  ];

  it('places worst (most negative) scenario first', () => {
    expect(sortedWorstToBest(scenarios)[0].scenario_key).toBe('gfc_2008');
  });

  it('places least bad scenario last', () => {
    const sorted = sortedWorstToBest(scenarios);
    expect(sorted[sorted.length - 1].scenario_key).toBe('rate_shock');
  });

  it('does not mutate original array', () => {
    const copy = [...scenarios];
    sortedWorstToBest(scenarios);
    expect(scenarios).toEqual(copy);
  });
});
