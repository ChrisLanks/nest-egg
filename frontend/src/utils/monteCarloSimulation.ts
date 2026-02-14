/**
 * Monte Carlo simulation utilities for portfolio growth projections.
 *
 * Uses Box-Muller transform to generate normally distributed returns
 * and runs multiple simulation paths to calculate percentiles.
 */

export interface SimulationParams {
  currentValue: number;
  years: number;
  simulations: number; // Number of simulation runs (typically 1000)
  annualReturn: number; // Expected annual return (e.g., 7 for 7%)
  volatility: number; // Annual volatility/std deviation (e.g., 15 for 15%)
  inflationRate: number; // Annual inflation rate (e.g., 3 for 3%)
}

export interface ProjectionResult {
  year: number;
  median: number;
  percentile10: number; // Pessimistic case (10th percentile)
  percentile25: number;
  percentile75: number;
  percentile90: number; // Optimistic case (90th percentile)
  medianInflationAdjusted: number;
}

/**
 * Generate normally distributed random return using Box-Muller transform.
 * This creates more realistic return patterns than uniform distribution.
 *
 * @param mean - Expected return (as decimal, e.g., 0.07 for 7%)
 * @param stdDev - Standard deviation (as decimal, e.g., 0.15 for 15%)
 * @returns Random return rate from normal distribution
 */
function generateNormalReturn(mean: number, stdDev: number): number {
  // Box-Muller transform to convert uniform random to normal distribution
  const u1 = Math.random();
  const u2 = Math.random();

  // Standard normal random variable (mean=0, stdDev=1)
  const z = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);

  // Scale to desired mean and standard deviation
  return mean + z * stdDev;
}

/**
 * Run Monte Carlo simulation for portfolio growth.
 *
 * Simulates multiple possible future paths based on expected returns and volatility.
 * Returns percentiles at each year to show range of potential outcomes.
 *
 * @param params - Simulation parameters
 * @returns Array of projection results for each year
 */
export function runMonteCarloSimulation(params: SimulationParams): ProjectionResult[] {
  const { currentValue, years, simulations, annualReturn, volatility, inflationRate } = params;

  // Convert percentages to decimals
  const returnDecimal = annualReturn / 100;
  const volDecimal = volatility / 100;
  const inflationDecimal = inflationRate / 100;

  // Run all simulation paths
  const allPaths: number[][] = [];

  for (let sim = 0; sim < simulations; sim++) {
    const path = [currentValue];

    // Simulate year by year
    for (let year = 1; year <= years; year++) {
      const returnRate = generateNormalReturn(returnDecimal, volDecimal);
      const newValue = path[year - 1] * (1 + returnRate);
      path.push(newValue);
    }

    allPaths.push(path);
  }

  // Calculate percentiles for each year
  const results: ProjectionResult[] = [];

  for (let year = 0; year <= years; year++) {
    // Extract all values for this year across all simulations
    const yearValues = allPaths.map(path => path[year]).sort((a, b) => a - b);

    // Calculate inflation adjustment factor
    const inflationAdjustment = Math.pow(1 + inflationDecimal, year);

    // Calculate percentile indices
    const p10Index = Math.floor(simulations * 0.10);
    const p25Index = Math.floor(simulations * 0.25);
    const p50Index = Math.floor(simulations * 0.50);
    const p75Index = Math.floor(simulations * 0.75);
    const p90Index = Math.floor(simulations * 0.90);

    results.push({
      year,
      median: yearValues[p50Index],
      percentile10: yearValues[p10Index],
      percentile25: yearValues[p25Index],
      percentile75: yearValues[p75Index],
      percentile90: yearValues[p90Index],
      medianInflationAdjusted: yearValues[p50Index] / inflationAdjustment,
    });
  }

  return results;
}

/**
 * Calculate expected value at a specific year using compound growth formula.
 * This is a deterministic alternative to Monte Carlo for quick estimates.
 *
 * @param currentValue - Current portfolio value
 * @param years - Number of years to project
 * @param annualReturn - Annual return rate (as percentage, e.g., 7)
 * @returns Expected value after compound growth
 */
export function calculateCompoundGrowth(
  currentValue: number,
  years: number,
  annualReturn: number
): number {
  return currentValue * Math.pow(1 + annualReturn / 100, years);
}
