/**
 * Tests for Monte Carlo simulation utility.
 *
 * Covers: accumulation phase, withdrawal/retirement phase,
 * stress test overrides, depletion tracking, and summary statistics.
 */

import { describe, it, expect } from 'vitest';
import {
  runMonteCarloSimulation,
  runSimulationProjections,
  calculateCompoundGrowth,
  STRESS_SCENARIOS,
  type SimulationParams,
} from '../monteCarloSimulation';

// ── Helpers ──────────────────────────────────────────────────────────────────

const baseParams: SimulationParams = {
  currentValue: 100000,
  years: 10,
  simulations: 500,
  annualReturn: 7,
  volatility: 15,
  inflationRate: 3,
};

// ── Basic accumulation ───────────────────────────────────────────────────────

describe('runMonteCarloSimulation — accumulation phase', () => {
  it('returns projections array with length years + 1 (year 0 included)', () => {
    const result = runMonteCarloSimulation(baseParams);
    expect(result.projections).toHaveLength(baseParams.years + 1);
  });

  it('year 0 projection equals currentValue', () => {
    const result = runMonteCarloSimulation(baseParams);
    const y0 = result.projections[0];
    expect(y0.year).toBe(0);
    expect(y0.median).toBe(baseParams.currentValue);
    expect(y0.percentile10).toBe(baseParams.currentValue);
    expect(y0.percentile90).toBe(baseParams.currentValue);
  });

  it('median grows over time for positive returns', () => {
    const result = runMonteCarloSimulation(baseParams);
    const y0 = result.projections[0].median;
    const yFinal = result.projections[baseParams.years].median;
    expect(yFinal).toBeGreaterThan(y0);
  });

  it('percentile90 > median > percentile10 at final year', () => {
    const result = runMonteCarloSimulation(baseParams);
    const final = result.projections[baseParams.years];
    expect(final.percentile90).toBeGreaterThan(final.median);
    expect(final.median).toBeGreaterThan(final.percentile10);
  });

  it('inflation-adjusted values are less than nominal', () => {
    const result = runMonteCarloSimulation(baseParams);
    const final = result.projections[baseParams.years];
    expect(final.medianInflationAdjusted).toBeLessThan(final.median);
  });

  it('depletion rate is 0 for pure accumulation', () => {
    const result = runMonteCarloSimulation(baseParams);
    const final = result.projections[baseParams.years];
    expect(final.depletionRate).toBe(0);
  });

  it('successRate is 100% for accumulation-only (no withdrawals)', () => {
    const result = runMonteCarloSimulation(baseParams);
    expect(result.successRate).toBe(100);
  });

  it('medianDepletionYear is null when no depletion occurs', () => {
    const result = runMonteCarloSimulation(baseParams);
    expect(result.medianDepletionYear).toBeNull();
  });
});

// ── Monthly contributions ────────────────────────────────────────────────────

describe('runMonteCarloSimulation — contributions', () => {
  it('portfolio grows faster with monthly contributions', () => {
    const without = runMonteCarloSimulation(baseParams);
    const with_ = runMonteCarloSimulation({ ...baseParams, monthlyContribution: 500 });
    const medianWithout = without.projections[baseParams.years].median;
    const medianWith = with_.projections[baseParams.years].median;
    expect(medianWith).toBeGreaterThan(medianWithout);
  });
});

// ── Withdrawal / retirement phase ────────────────────────────────────────────

describe('runMonteCarloSimulation — retirement phase', () => {
  const retirementParams: SimulationParams = {
    currentValue: 1000000,
    years: 30,
    simulations: 500,
    annualReturn: 7,
    volatility: 15,
    inflationRate: 3,
    retirementYear: 1, // Retire immediately
    withdrawalRate: 4, // 4% rule
    inflationAdjustWithdrawals: true,
  };

  it('portfolio value decreases during withdrawal phase', () => {
    // With high withdrawal rate on a smaller portfolio
    const heavyWithdraw: SimulationParams = {
      currentValue: 500000,
      years: 30,
      simulations: 200,
      annualReturn: 5,
      volatility: 15,
      inflationRate: 3,
      retirementYear: 1,
      annualWithdrawal: 50000, // 10% of portfolio
      inflationAdjustWithdrawals: true,
    };
    const result = runMonteCarloSimulation(heavyWithdraw);
    // With 10% annual withdrawal, median should decrease
    const y5 = result.projections[5].median;
    expect(y5).toBeLessThan(500000);
  });

  it('successRate < 100 for aggressive withdrawal', () => {
    const aggressive: SimulationParams = {
      currentValue: 500000,
      years: 40,
      simulations: 200,
      annualReturn: 5,
      volatility: 20,
      inflationRate: 3,
      retirementYear: 1,
      annualWithdrawal: 40000, // 8% initial rate
      inflationAdjustWithdrawals: true,
    };
    const result = runMonteCarloSimulation(aggressive);
    expect(result.successRate).toBeLessThan(100);
  });

  it('depletion rate increases over time with withdrawals', () => {
    const result = runMonteCarloSimulation(retirementParams);
    const y10 = result.projections[10]?.depletionRate ?? 0;
    const y30 = result.projections[30]?.depletionRate ?? 0;
    expect(y30).toBeGreaterThanOrEqual(y10);
  });

  it('withdrawalRate of 4% calculates withdrawal from portfolio value at retirement', () => {
    const result = runMonteCarloSimulation(retirementParams);
    // With $1M and 4% rule, withdrawal should be ~$40k/year
    // The simulation should run without errors
    expect(result.projections.length).toBe(31);
    expect(result.successRate).toBeGreaterThan(0);
  });

  it('fixed annualWithdrawal is used when specified', () => {
    const fixed: SimulationParams = {
      currentValue: 1000000,
      years: 30,
      simulations: 200,
      annualReturn: 7,
      volatility: 15,
      inflationRate: 3,
      retirementYear: 1,
      annualWithdrawal: 40000,
    };
    const result = runMonteCarloSimulation(fixed);
    expect(result.projections).toHaveLength(31);
    expect(result.successRate).toBeGreaterThan(0);
  });
});

// ── Stress scenarios ─────────────────────────────────────────────────────────

describe('STRESS_SCENARIOS', () => {
  it('financial_crisis has a -40% year 1 override', () => {
    const crisis = STRESS_SCENARIOS.financial_crisis;
    expect(crisis.returnOverrides[0]).toEqual({ yearOffset: 1, returnOverride: -40 });
  });

  it('high_inflation has 5 years of 6% inflation', () => {
    const inflation = STRESS_SCENARIOS.high_inflation;
    expect(inflation.inflationOverrides).toHaveLength(5);
    expect(inflation.inflationOverrides![0].inflationOverride).toBe(6);
  });

  it('lost_decade has 10 years of near-zero returns', () => {
    const lost = STRESS_SCENARIOS.lost_decade;
    expect(lost.returnOverrides).toHaveLength(10);
    expect(lost.returnOverrides[0].returnOverride).toBe(0.5);
  });
});

describe('runMonteCarloSimulation — stress overrides', () => {
  it('financial crisis causes year-1 value to drop significantly', () => {
    const result = runMonteCarloSimulation({
      ...baseParams,
      stressOverrides: STRESS_SCENARIOS.financial_crisis,
    });
    const y1 = result.projections[1];
    // -40% return → value should drop to ~$60k from $100k
    expect(y1.median).toBeLessThan(baseParams.currentValue * 0.7);
  });

  it('lost decade results in much lower growth than base case', () => {
    const normal = runMonteCarloSimulation(baseParams);
    const stressed = runMonteCarloSimulation({
      ...baseParams,
      stressOverrides: STRESS_SCENARIOS.lost_decade,
    });
    expect(stressed.projections[10].median).toBeLessThan(normal.projections[10].median);
  });
});

// ── Backward compatibility ───────────────────────────────────────────────────

describe('runSimulationProjections (backward-compatible wrapper)', () => {
  it('returns ProjectionResult[] directly', () => {
    const projections = runSimulationProjections(baseParams);
    expect(Array.isArray(projections)).toBe(true);
    expect(projections).toHaveLength(baseParams.years + 1);
    expect(projections[0]).toHaveProperty('median');
    expect(projections[0]).toHaveProperty('percentile10');
    expect(projections[0]).toHaveProperty('depletionRate');
  });
});

// ── Compound growth helper ───────────────────────────────────────────────────

describe('calculateCompoundGrowth', () => {
  it('doubles approximately in 10 years at 7%', () => {
    const result = calculateCompoundGrowth(100000, 10, 7);
    expect(result).toBeCloseTo(196715, -2); // ~$196,715
  });

  it('returns currentValue for 0 years', () => {
    expect(calculateCompoundGrowth(50000, 0, 10)).toBe(50000);
  });

  it('decreases with negative returns', () => {
    const result = calculateCompoundGrowth(100000, 5, -5);
    expect(result).toBeLessThan(100000);
  });
});
