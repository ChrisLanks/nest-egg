/**
 * Monte Carlo simulation utilities for portfolio growth projections.
 *
 * Uses Box-Muller transform to generate normally distributed returns
 * and runs multiple simulation paths to calculate percentiles.
 * Supports accumulation phase, withdrawal/retirement phase, scenario
 * comparison, and stress-test overlays.
 */

export interface SimulationParams {
  currentValue: number;
  years: number;
  simulations: number; // Number of simulation runs (typically 1000)
  annualReturn: number; // Expected annual return (e.g., 7 for 7%)
  volatility: number; // Annual volatility/std deviation (e.g., 15 for 15%)
  inflationRate: number; // Annual inflation rate (e.g., 3 for 3%)
  monthlyContribution?: number; // Optional: additional monthly savings added each year
  // Retirement / withdrawal phase
  retirementYear?: number; // Year offset when contributions stop and withdrawals begin
  annualWithdrawal?: number; // Fixed annual withdrawal in today's dollars
  withdrawalRate?: number; // Alternative: % of portfolio at retirement (e.g., 4 for 4%)
  inflationAdjustWithdrawals?: boolean; // Increase withdrawals with inflation each year
  // Stress-test overrides (deterministic for specific years)
  stressOverrides?: StressScenario;
}

export interface ProjectionResult {
  year: number;
  median: number;
  percentile10: number; // Pessimistic case (10th percentile)
  percentile25: number;
  percentile75: number;
  percentile90: number; // Optimistic case (90th percentile)
  medianInflationAdjusted: number;
  percentile10InflationAdjusted: number;
  percentile90InflationAdjusted: number;
  depletionRate: number; // % of simulations depleted by this year (0-100)
}

export interface SimulationSummary {
  projections: ProjectionResult[];
  successRate: number; // % of sims with money remaining at end (0-100)
  medianDepletionYear: number | null; // Median year of depletion, null if >50% survive
}

// ── Stress scenario presets ─────────────────────────────────────────────────

export interface StressScenario {
  name: string;
  description: string;
  returnOverrides: { yearOffset: number; returnOverride: number }[];
  inflationOverrides?: { yearOffset: number; inflationOverride: number }[];
}

export const STRESS_SCENARIOS: Record<string, StressScenario> = {
  financial_crisis: {
    name: '2008 Financial Crisis',
    description: '40% drop in year 1, slow recovery over 3 years',
    returnOverrides: [
      { yearOffset: 1, returnOverride: -40 },
      { yearOffset: 2, returnOverride: 5 },
      { yearOffset: 3, returnOverride: 15 },
    ],
  },
  high_inflation: {
    name: 'Prolonged High Inflation',
    description: '6% inflation for 5 years with reduced real returns',
    returnOverrides: [],
    inflationOverrides: [
      { yearOffset: 1, inflationOverride: 6 },
      { yearOffset: 2, inflationOverride: 6 },
      { yearOffset: 3, inflationOverride: 6 },
      { yearOffset: 4, inflationOverride: 6 },
      { yearOffset: 5, inflationOverride: 6 },
    ],
  },
  lost_decade: {
    name: 'Lost Decade',
    description: 'Near-zero returns (0.5%) for 10 years',
    returnOverrides: Array.from({ length: 10 }, (_, i) => ({
      yearOffset: i + 1,
      returnOverride: 0.5,
    })),
  },
};

// ── Core simulation ─────────────────────────────────────────────────────────

/**
 * Generate normally distributed random return using Box-Muller transform.
 * This creates more realistic return patterns than uniform distribution.
 */
function generateNormalReturn(mean: number, stdDev: number): number {
  // Clamp u1 away from 0 to prevent log(0) = -Infinity in Box-Muller
  const u1 = Math.random() || 1e-10;
  const u2 = Math.random();
  const z = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
  return mean + z * stdDev;
}

/**
 * Run Monte Carlo simulation for portfolio growth with optional retirement phase.
 *
 * Simulates multiple possible future paths based on expected returns and volatility.
 * Returns percentiles at each year to show range of potential outcomes.
 * When retirementYear is set, switches from contributions to withdrawals at that point.
 */
export function runMonteCarloSimulation(params: SimulationParams): SimulationSummary {
  const {
    currentValue,
    years,
    simulations,
    annualReturn,
    volatility,
    inflationRate,
    monthlyContribution = 0,
    retirementYear,
    annualWithdrawal,
    withdrawalRate,
    inflationAdjustWithdrawals = true,
    stressOverrides,
  } = params;
  const annualContribution = monthlyContribution * 12;

  const returnDecimal = annualReturn / 100;
  const volDecimal = volatility / 100;
  const inflationDecimal = inflationRate / 100;

  // Build lookup maps for stress overrides
  const returnOverrideMap = new Map<number, number>();
  const inflationOverrideMap = new Map<number, number>();
  if (stressOverrides) {
    for (const o of stressOverrides.returnOverrides) {
      returnOverrideMap.set(o.yearOffset, o.returnOverride / 100);
    }
    for (const o of stressOverrides.inflationOverrides ?? []) {
      inflationOverrideMap.set(o.yearOffset, o.inflationOverride / 100);
    }
  }

  // Track depletion (portfolio hit $0)
  const depletedAtYear: number[] = []; // Per-sim: year of depletion or Infinity
  const allPaths: number[][] = [];

  for (let sim = 0; sim < simulations; sim++) {
    const path = [currentValue];
    let depleted = false;
    let depletionYear = Infinity;
    // If using withdrawalRate, compute the fixed withdrawal at retirement
    let fixedWithdrawalFromRate = 0;
    // Track cumulative inflation for withdrawal adjustments year-over-year
    let cumulativeInflation = 1;

    for (let year = 1; year <= years; year++) {
      if (depleted) {
        path.push(0);
        continue;
      }

      // Determine return for this year
      let returnRate: number;
      if (returnOverrideMap.has(year)) {
        // Stress override: deterministic return
        returnRate = returnOverrideMap.get(year)!;
      } else {
        returnRate = generateNormalReturn(returnDecimal, volDecimal);
      }

      const isRetired = retirementYear != null && year >= retirementYear;

      let newValue: number;
      if (isRetired) {
        // Withdrawal phase
        const yearsInRetirement = year - retirementYear!;

        // Calculate the fixed withdrawal at retirement start (once)
        if (yearsInRetirement === 0 && withdrawalRate && !annualWithdrawal) {
          fixedWithdrawalFromRate = path[year - 1] * (withdrawalRate / 100);
        }

        const baseWithdrawal = annualWithdrawal || fixedWithdrawalFromRate;
        let withdrawal = baseWithdrawal;
        if (inflationAdjustWithdrawals && yearsInRetirement > 0) {
          // Compound cumulative inflation year-over-year (not single rate ^ years)
          const yearInflation = inflationOverrideMap.get(year) ?? inflationDecimal;
          cumulativeInflation *= 1 + yearInflation;
          withdrawal = baseWithdrawal * cumulativeInflation;
        }

        newValue = path[year - 1] * (1 + returnRate) - withdrawal;
      } else {
        // Accumulation phase
        newValue = path[year - 1] * (1 + returnRate) + annualContribution;
      }

      if (newValue <= 0) {
        newValue = 0;
        depleted = true;
        depletionYear = year;
      }

      path.push(newValue);
    }

    allPaths.push(path);
    depletedAtYear.push(depletionYear);
  }

  // Calculate percentiles and depletion rates for each year
  const projections: ProjectionResult[] = [];

  for (let year = 0; year <= years; year++) {
    const yearValues = allPaths.map(path => path[year]).sort((a, b) => a - b);

    const yearInflation = inflationOverrideMap.get(year) ?? inflationDecimal;
    // Use base inflation for adjustment factor (stress inflation only affects withdrawals)
    const inflationAdjustment = Math.pow(1 + inflationDecimal, year);

    const p10Index = Math.floor(simulations * 0.10);
    const p25Index = Math.floor(simulations * 0.25);
    const p50Index = Math.floor(simulations * 0.50);
    const p75Index = Math.floor(simulations * 0.75);
    const p90Index = Math.floor(simulations * 0.90);

    const depletedCount = depletedAtYear.filter(d => d <= year).length;
    const depletionRate = (depletedCount / simulations) * 100;

    projections.push({
      year,
      median: yearValues[p50Index],
      percentile10: yearValues[p10Index],
      percentile25: yearValues[p25Index],
      percentile75: yearValues[p75Index],
      percentile90: yearValues[p90Index],
      medianInflationAdjusted: yearValues[p50Index] / inflationAdjustment,
      percentile10InflationAdjusted: yearValues[p10Index] / inflationAdjustment,
      percentile90InflationAdjusted: yearValues[p90Index] / inflationAdjustment,
      depletionRate,
    });
  }

  // Summary stats
  const finalDepleted = depletedAtYear.filter(d => d <= years).length;
  const successRate = ((simulations - finalDepleted) / simulations) * 100;

  const sortedDepletion = depletedAtYear.filter(d => d <= years).sort((a, b) => a - b);
  const medianDepletionYear =
    sortedDepletion.length > simulations / 2
      ? sortedDepletion[Math.floor(sortedDepletion.length / 2)]
      : null;

  return { projections, successRate, medianDepletionYear };
}

/**
 * Backward-compatible wrapper that returns just ProjectionResult[] for existing callers.
 */
export function runSimulationProjections(params: SimulationParams): ProjectionResult[] {
  return runMonteCarloSimulation(params).projections;
}

/**
 * Calculate expected value at a specific year using compound growth formula.
 * This is a deterministic alternative to Monte Carlo for quick estimates.
 */
export function calculateCompoundGrowth(
  currentValue: number,
  years: number,
  annualReturn: number
): number {
  return currentValue * Math.pow(1 + annualReturn / 100, years);
}
