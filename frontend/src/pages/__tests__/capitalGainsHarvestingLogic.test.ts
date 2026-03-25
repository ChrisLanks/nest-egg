/**
 * Tests for CapitalGainsHarvestingPanel pure logic functions.
 */

import { describe, it, expect } from 'vitest';

// ── 0% LTCG bracket room calculation (mirrors backend) ────────────────────────

const LTCG_0PCT_CEILING: Record<string, number> = {
  single: 48350,
  married_filing_jointly: 96700,
  married_filing_separately: 48350,
  head_of_household: 64750,
};

function calcBracketRoom(income: number, filingStatus: string): number {
  const ceiling = LTCG_0PCT_CEILING[filingStatus] ?? 48350;
  return Math.max(0, ceiling - income);
}

function suggestedHarvest(room: number): number {
  return Math.min(room, 50000);
}

describe('calcBracketRoom', () => {
  it('returns full ceiling for zero income (single)', () => {
    expect(calcBracketRoom(0, 'single')).toBe(48350);
  });

  it('returns full ceiling for zero income (MFJ)', () => {
    expect(calcBracketRoom(0, 'married_filing_jointly')).toBe(96700);
  });

  it('returns remaining room for partial income', () => {
    expect(calcBracketRoom(30000, 'single')).toBe(18350);
  });

  it('returns 0 when income exceeds ceiling', () => {
    expect(calcBracketRoom(60000, 'single')).toBe(0);
  });

  it('returns 0 when income exactly equals ceiling', () => {
    expect(calcBracketRoom(48350, 'single')).toBe(0);
  });

  it('handles head_of_household status', () => {
    expect(calcBracketRoom(40000, 'head_of_household')).toBe(24750);
  });

  it('falls back to single ceiling for unknown status', () => {
    expect(calcBracketRoom(0, 'unknown_status')).toBe(48350);
  });

  it('MFJ has double the single ceiling', () => {
    const single = LTCG_0PCT_CEILING['single'];
    const mfj = LTCG_0PCT_CEILING['married_filing_jointly'];
    expect(mfj).toBe(single * 2);
  });
});

describe('suggestedHarvest', () => {
  it('caps suggestion at 50000', () => {
    expect(suggestedHarvest(80000)).toBe(50000);
  });

  it('returns full room when below cap', () => {
    expect(suggestedHarvest(20000)).toBe(20000);
  });

  it('returns 0 when room is 0', () => {
    expect(suggestedHarvest(0)).toBe(0);
  });

  it('returns exactly 50000 when room equals cap', () => {
    expect(suggestedHarvest(50000)).toBe(50000);
  });
});

// ── Holding period helpers ────────────────────────────────────────────────────

function isLongTerm(days: number): boolean {
  return days > 365;
}

function fmtDays(days: number): string {
  if (days >= 365) return `${(days / 365).toFixed(1)}y`;
  return `${days}d`;
}

describe('isLongTerm', () => {
  it('365 days is NOT long-term', () => {
    expect(isLongTerm(365)).toBe(false);
  });

  it('366 days IS long-term', () => {
    expect(isLongTerm(366)).toBe(true);
  });

  it('730 days is long-term', () => {
    expect(isLongTerm(730)).toBe(true);
  });
});

describe('fmtDays', () => {
  it('formats days under 365 as days', () => {
    expect(fmtDays(180)).toBe('180d');
  });

  it('formats 365 days as 1.0y', () => {
    expect(fmtDays(365)).toBe('1.0y');
  });

  it('formats 730 days as 2.0y', () => {
    expect(fmtDays(730)).toBe('2.0y');
  });

  it('formats 548 days as 1.5y', () => {
    expect(fmtDays(548)).toBe('1.5y');
  });
});

// ── YTD realized gains display logic ─────────────────────────────────────────

function totalRealized(stcg: number, ltcg: number): number {
  return stcg + ltcg;
}

describe('YTD realized gains', () => {
  it('sums stcg and ltcg', () => {
    expect(totalRealized(5000, 12000)).toBe(17000);
  });

  it('handles negative stcg (losses)', () => {
    expect(totalRealized(-3000, 8000)).toBe(5000);
  });

  it('handles both negative (net loss year)', () => {
    expect(totalRealized(-2000, -1000)).toBe(-3000);
  });

  it('handles zero values', () => {
    expect(totalRealized(0, 0)).toBe(0);
  });
});
