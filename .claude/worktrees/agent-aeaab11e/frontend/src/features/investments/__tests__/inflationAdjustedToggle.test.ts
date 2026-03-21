/**
 * Tests for the inflation-adjusted toggle behavior.
 *
 * Covers:
 * - Monte Carlo simulation outputs all inflation-adjusted percentile fields
 * - Inflation-adjusted values are strictly less than nominal for all percentiles
 * - Summary stats computation switches between nominal and inflation-adjusted
 * - Ordering invariants hold for inflation-adjusted percentiles
 */

import { describe, it, expect } from "vitest";
import {
  runMonteCarloSimulation,
  type SimulationParams,
  type ProjectionResult,
} from "../../../utils/monteCarloSimulation";

const baseParams: SimulationParams = {
  currentValue: 100_000,
  years: 20,
  simulations: 1000,
  annualReturn: 7,
  volatility: 15,
  inflationRate: 3,
  monthlyContribution: 500,
};

// ── Simulation output fields ────────────────────────────────────────────────

describe("inflation-adjusted simulation fields", () => {
  it("produces all inflation-adjusted percentile fields", () => {
    const result = runMonteCarloSimulation(baseParams);
    const final = result.projections[baseParams.years];

    expect(final).toHaveProperty("medianInflationAdjusted");
    expect(final).toHaveProperty("percentile10InflationAdjusted");
    expect(final).toHaveProperty("percentile25InflationAdjusted");
    expect(final).toHaveProperty("percentile75InflationAdjusted");
    expect(final).toHaveProperty("percentile90InflationAdjusted");
  });

  it("inflation-adjusted values are less than nominal for all percentiles at final year", () => {
    const result = runMonteCarloSimulation(baseParams);
    const final = result.projections[baseParams.years];

    expect(final.medianInflationAdjusted).toBeLessThan(final.median);
    expect(final.percentile10InflationAdjusted).toBeLessThan(
      final.percentile10,
    );
    expect(final.percentile25InflationAdjusted).toBeLessThan(
      final.percentile25,
    );
    expect(final.percentile75InflationAdjusted).toBeLessThan(
      final.percentile75,
    );
    expect(final.percentile90InflationAdjusted).toBeLessThan(
      final.percentile90,
    );
  });

  it("inflation-adjusted percentile ordering is preserved (p10 < p25 < median < p75 < p90)", () => {
    const result = runMonteCarloSimulation(baseParams);
    const final = result.projections[baseParams.years];

    expect(final.percentile10InflationAdjusted).toBeLessThan(
      final.percentile25InflationAdjusted,
    );
    expect(final.percentile25InflationAdjusted).toBeLessThan(
      final.medianInflationAdjusted,
    );
    expect(final.medianInflationAdjusted).toBeLessThan(
      final.percentile75InflationAdjusted,
    );
    expect(final.percentile75InflationAdjusted).toBeLessThan(
      final.percentile90InflationAdjusted,
    );
  });

  it("year 0 inflation-adjusted values equal nominal (no inflation yet)", () => {
    const result = runMonteCarloSimulation(baseParams);
    const yearZero = result.projections[0];

    expect(yearZero.medianInflationAdjusted).toBe(yearZero.median);
    expect(yearZero.percentile10InflationAdjusted).toBe(yearZero.percentile10);
    expect(yearZero.percentile90InflationAdjusted).toBe(yearZero.percentile90);
  });

  it("inflation adjustment grows over time (larger gap at later years)", () => {
    const result = runMonteCarloSimulation(baseParams);
    const year5 = result.projections[5];
    const year20 = result.projections[20];

    const ratio5 = year5.medianInflationAdjusted / year5.median;
    const ratio20 = year20.medianInflationAdjusted / year20.median;

    // At 3% inflation: year 5 ratio ≈ 0.86, year 20 ratio ≈ 0.55
    expect(ratio20).toBeLessThan(ratio5);
  });

  it("zero inflation rate produces identical nominal and adjusted values", () => {
    const noInflation: SimulationParams = { ...baseParams, inflationRate: 0 };
    const result = runMonteCarloSimulation(noInflation);
    const final = result.projections[noInflation.years];

    expect(final.medianInflationAdjusted).toBe(final.median);
    expect(final.percentile10InflationAdjusted).toBe(final.percentile10);
    expect(final.percentile25InflationAdjusted).toBe(final.percentile25);
    expect(final.percentile75InflationAdjusted).toBe(final.percentile75);
    expect(final.percentile90InflationAdjusted).toBe(final.percentile90);
  });
});

// ── Summary stats computation (mirrors GrowthProjectionsChart logic) ────────

/**
 * Mirrors the summaryStats useMemo from GrowthProjectionsChart.tsx
 */
function computeSummaryStats(
  projections: ProjectionResult[],
  currentValue: number,
  showInflationAdjusted: boolean,
) {
  const finalYear = projections[projections.length - 1];
  const median = showInflationAdjusted
    ? finalYear.medianInflationAdjusted
    : finalYear.median;
  const pessimistic = showInflationAdjusted
    ? finalYear.percentile10InflationAdjusted
    : finalYear.percentile10;
  const optimistic = showInflationAdjusted
    ? finalYear.percentile90InflationAdjusted
    : finalYear.percentile90;
  return {
    medianValue: median,
    medianGain: median - currentValue,
    medianGainPercent: ((median - currentValue) / currentValue) * 100,
    pessimistic,
    optimistic,
  };
}

describe("summary stats toggle", () => {
  it("inflation-adjusted stats are lower than nominal stats", () => {
    const result = runMonteCarloSimulation(baseParams);

    const nominal = computeSummaryStats(
      result.projections,
      baseParams.currentValue,
      false,
    );
    const adjusted = computeSummaryStats(
      result.projections,
      baseParams.currentValue,
      true,
    );

    expect(adjusted.medianValue).toBeLessThan(nominal.medianValue);
    expect(adjusted.pessimistic).toBeLessThan(nominal.pessimistic);
    expect(adjusted.optimistic).toBeLessThan(nominal.optimistic);
    expect(adjusted.medianGain).toBeLessThan(nominal.medianGain);
    expect(adjusted.medianGainPercent).toBeLessThan(nominal.medianGainPercent);
  });

  it("toggle produces different values (not no-op)", () => {
    const result = runMonteCarloSimulation(baseParams);

    const nominal = computeSummaryStats(
      result.projections,
      baseParams.currentValue,
      false,
    );
    const adjusted = computeSummaryStats(
      result.projections,
      baseParams.currentValue,
      true,
    );

    expect(adjusted.medianValue).not.toBe(nominal.medianValue);
    expect(adjusted.pessimistic).not.toBe(nominal.pessimistic);
    expect(adjusted.optimistic).not.toBe(nominal.optimistic);
  });

  it("zero inflation makes toggle a no-op", () => {
    const noInflation: SimulationParams = { ...baseParams, inflationRate: 0 };
    const result = runMonteCarloSimulation(noInflation);

    const nominal = computeSummaryStats(
      result.projections,
      noInflation.currentValue,
      false,
    );
    const adjusted = computeSummaryStats(
      result.projections,
      noInflation.currentValue,
      true,
    );

    expect(adjusted.medianValue).toBe(nominal.medianValue);
    expect(adjusted.pessimistic).toBe(nominal.pessimistic);
    expect(adjusted.optimistic).toBe(nominal.optimistic);
  });
});
