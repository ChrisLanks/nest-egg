/**
 * Tests for EquityPage pure logic: parseVesting, computed display values,
 * grant type label mapping, AMT/tax estimates.
 */

import { describe, it, expect } from 'vitest';

// ── parseVesting (mirrors EquityPage implementation) ─────────────────────────

interface VestEvent {
  date: string;
  quantity: number;
  notes?: string;
}

function parseVesting(raw: string | null | undefined): VestEvent[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

describe('parseVesting', () => {
  it('returns empty array for null', () => {
    expect(parseVesting(null)).toEqual([]);
  });

  it('returns empty array for undefined', () => {
    expect(parseVesting(undefined)).toEqual([]);
  });

  it('returns empty array for empty string', () => {
    expect(parseVesting('')).toEqual([]);
  });

  it('returns empty array for malformed JSON', () => {
    expect(parseVesting('not-json')).toEqual([]);
  });

  it('returns empty array when JSON is an object, not an array', () => {
    expect(parseVesting('{"date":"2024-01-01","quantity":100}')).toEqual([]);
  });

  it('parses a valid single-event schedule', () => {
    const raw = JSON.stringify([{ date: '2024-01-01', quantity: 250, notes: 'Cliff' }]);
    const result = parseVesting(raw);
    expect(result).toHaveLength(1);
    expect(result[0].quantity).toBe(250);
    expect(result[0].notes).toBe('Cliff');
  });

  it('parses a multi-event schedule', () => {
    const events = [
      { date: '2024-01-01', quantity: 100 },
      { date: '2024-07-01', quantity: 100 },
      { date: '2025-01-01', quantity: 100 },
    ];
    const result = parseVesting(JSON.stringify(events));
    expect(result).toHaveLength(3);
    expect(result.map((e) => e.quantity)).toEqual([100, 100, 100]);
  });
});

// ── Total shares calculation ──────────────────────────────────────────────────

const totalShares = (quantity: number | null | undefined): number =>
  quantity ?? 0;

describe('totalShares', () => {
  it('returns quantity when set', () => {
    expect(totalShares(10000)).toBe(10000);
  });

  it('returns 0 for null', () => {
    expect(totalShares(null)).toBe(0);
  });

  it('returns 0 for undefined', () => {
    expect(totalShares(undefined)).toBe(0);
  });
});

// ── Spread per share (current - strike) ──────────────────────────────────────

const spreadPerShare = (
  sharePrice: number | null,
  strikePrice: number | null,
): number | null => {
  if (sharePrice == null || strikePrice == null) return null;
  return sharePrice - strikePrice;
};

describe('spreadPerShare', () => {
  it('calculates spread', () => {
    expect(spreadPerShare(30, 10)).toBe(20);
  });

  it('returns null when share price is missing', () => {
    expect(spreadPerShare(null, 10)).toBeNull();
  });

  it('returns null when strike price is missing', () => {
    expect(spreadPerShare(30, null)).toBeNull();
  });

  it('returns negative spread when underwater', () => {
    expect(spreadPerShare(5, 10)).toBe(-5);
  });

  it('returns zero when at-the-money', () => {
    expect(spreadPerShare(10, 10)).toBe(0);
  });
});

// ── Estimated value (quantity * share_price) ─────────────────────────────────

const estimatedValue = (
  quantity: number | null,
  sharePrice: number | null,
): number => {
  if (quantity == null || sharePrice == null) return 0;
  return quantity * sharePrice;
};

describe('estimatedValue', () => {
  it('calculates value', () => {
    expect(estimatedValue(1000, 25)).toBe(25000);
  });

  it('returns 0 when quantity is null', () => {
    expect(estimatedValue(null, 25)).toBe(0);
  });

  it('returns 0 when share price is null', () => {
    expect(estimatedValue(1000, null)).toBe(0);
  });

  it('handles fractional prices', () => {
    expect(estimatedValue(500, 12.5)).toBe(6250);
  });
});

// ── Grant type label mapping ──────────────────────────────────────────────────

const GRANT_TYPE_LABELS: Record<string, string> = {
  iso: 'ISO',
  nso: 'NSO',
  rsu: 'RSU',
  rsa: 'RSA',
  profit_interest: 'Profits Interest',
};

const grantTypeLabel = (type: string | null | undefined): string =>
  type ? (GRANT_TYPE_LABELS[type] ?? type.toUpperCase()) : '—';

describe('grantTypeLabel', () => {
  it('returns ISO for iso', () => {
    expect(grantTypeLabel('iso')).toBe('ISO');
  });

  it('returns NSO for nso', () => {
    expect(grantTypeLabel('nso')).toBe('NSO');
  });

  it('returns RSU for rsu', () => {
    expect(grantTypeLabel('rsu')).toBe('RSU');
  });

  it('returns RSA for rsa', () => {
    expect(grantTypeLabel('rsa')).toBe('RSA');
  });

  it('returns Profits Interest for profit_interest', () => {
    expect(grantTypeLabel('profit_interest')).toBe('Profits Interest');
  });

  it('returns em-dash for null', () => {
    expect(grantTypeLabel(null)).toBe('—');
  });

  it('returns em-dash for undefined', () => {
    expect(grantTypeLabel(undefined)).toBe('—');
  });

  it('uppercases unknown types', () => {
    expect(grantTypeLabel('phantom')).toBe('PHANTOM');
  });
});

// ── Vesting split: upcoming vs past ──────────────────────────────────────────

const splitVesting = (
  events: VestEvent[],
  today: string,
): { upcoming: VestEvent[]; past: VestEvent[] } => {
  const upcoming = events.filter((e) => e.date >= today);
  const past = events.filter((e) => e.date < today);
  return { upcoming, past };
};

describe('splitVesting', () => {
  const today = '2025-01-01';
  const events: VestEvent[] = [
    { date: '2024-06-01', quantity: 100 },  // past
    { date: '2025-01-01', quantity: 200 },  // today = upcoming
    { date: '2025-06-01', quantity: 300 },  // future
  ];

  it('separates past from upcoming', () => {
    const { upcoming, past } = splitVesting(events, today);
    expect(past).toHaveLength(1);
    expect(past[0].date).toBe('2024-06-01');
    expect(upcoming).toHaveLength(2);
  });

  it('treats today as upcoming', () => {
    const { upcoming } = splitVesting(events, today);
    expect(upcoming.some((e) => e.date === '2025-01-01')).toBe(true);
  });

  it('returns empty arrays for empty schedule', () => {
    const { upcoming, past } = splitVesting([], today);
    expect(upcoming).toEqual([]);
    expect(past).toEqual([]);
  });
});

// ── ISO AMT exposure estimate ─────────────────────────────────────────────────

/**
 * AMT income = spread_per_share * quantity
 * AMT tax ≈ AMT income * 0.26 (below AMT bracket crossover, simplified)
 * after subtracting exemption (single: 88,100 for 2026).
 */
const estimateAMT = (
  spreadPerShare: number,
  quantity: number,
  amtExemption: number,
  amtRate: number,
): number => {
  const amtIncome = spreadPerShare * quantity;
  const taxableAmt = Math.max(0, amtIncome - amtExemption);
  return taxableAmt * amtRate;
};

describe('estimateAMT', () => {
  it('returns 0 when spread is below exemption', () => {
    expect(estimateAMT(5, 1000, 88100, 0.26)).toBe(0); // 5000 < 88100
  });

  it('calculates AMT above exemption', () => {
    // spread 100 * 10000 qty = 1_000_000. Above 88100 exemption.
    const result = estimateAMT(100, 10000, 88100, 0.26);
    expect(result).toBeCloseTo((1000000 - 88100) * 0.26);
  });

  it('clamps to 0 for underwater options', () => {
    expect(estimateAMT(-5, 1000, 88100, 0.26)).toBe(0);
  });
});
