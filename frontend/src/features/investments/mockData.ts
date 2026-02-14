/**
 * Mock historical data generator for Phase 3 development.
 *
 * Generates realistic-looking portfolio snapshots before the actual
 * historical tracking infrastructure is in place. Useful for developing
 * and testing Performance Trends and Risk Analysis tabs.
 */

export interface HistoricalSnapshot {
  date: string; // ISO date string (YYYY-MM-DD)
  total_value: number;
  total_gain_loss: number | null;
  stocks_value: number;
  bonds_value: number;
  cash_value: number;
}

/**
 * Generate mock historical portfolio snapshots.
 *
 * Simulates portfolio growth with:
 * - Base annual growth rate (default 7%)
 * - Random volatility (±5%)
 * - Proportional asset allocation maintained
 *
 * @param currentValue - Current total portfolio value
 * @param months - Number of months of history to generate (default 12)
 * @param stocksPercent - Percentage of portfolio in stocks (default 70%)
 * @param bondsPercent - Percentage in bonds (default 20%)
 * @param cashPercent - Percentage in cash (default 10%)
 * @returns Array of historical snapshots in chronological order
 */
export function generateMockSnapshots(
  currentValue: number,
  months: number = 12,
  stocksPercent: number = 70,
  bondsPercent: number = 20,
  cashPercent: number = 10
): HistoricalSnapshot[] {
  const snapshots: HistoricalSnapshot[] = [];
  const today = new Date();

  // Assumed annual growth rate (7%)
  const annualGrowthRate = 0.07;

  // Generate backwards from today
  for (let i = months; i >= 0; i--) {
    const date = new Date(today);
    date.setMonth(date.getMonth() - i);
    date.setHours(0, 0, 0, 0);

    // Calculate value at this point in time
    // Work backwards: if current value grew at 7%/year, what was it months ago?
    const monthsFromNow = i;
    const yearsFromNow = monthsFromNow / 12;

    // Reverse compound growth: value / (1 + rate)^years
    const baseValue = currentValue / Math.pow(1 + annualGrowthRate, yearsFromNow);

    // Add random volatility (±5% swing)
    const volatility = (Math.random() - 0.5) * 0.1; // Random between -0.05 and +0.05
    const value = baseValue * (1 + volatility);

    // Calculate asset allocation (maintain rough percentages)
    const stocksValue = value * (stocksPercent / 100);
    const bondsValue = value * (bondsPercent / 100);
    const cashValue = value * (cashPercent / 100);

    // Calculate gain/loss (10% assumed total return)
    const totalGainLoss = value * 0.10;

    snapshots.push({
      date: date.toISOString().split('T')[0],
      total_value: Math.round(value * 100) / 100,
      total_gain_loss: Math.round(totalGainLoss * 100) / 100,
      stocks_value: Math.round(stocksValue * 100) / 100,
      bonds_value: Math.round(bondsValue * 100) / 100,
      cash_value: Math.round(cashValue * 100) / 100,
    });
  }

  return snapshots;
}

/**
 * Generate daily snapshots for more granular historical data.
 * Useful for volatility calculations in Risk Analysis.
 *
 * @param currentValue - Current portfolio value
 * @param days - Number of days of history (default 365)
 * @returns Array of daily snapshots
 */
export function generateDailySnapshots(
  currentValue: number,
  days: number = 365
): HistoricalSnapshot[] {
  const snapshots: HistoricalSnapshot[] = [];
  const today = new Date();

  const annualGrowthRate = 0.07;
  const dailyGrowthRate = Math.pow(1 + annualGrowthRate, 1 / 365) - 1;

  // Daily volatility (15% annual volatility = ~0.95% daily)
  const dailyVolatility = 0.15 / Math.sqrt(252); // 252 trading days per year

  for (let i = days; i >= 0; i--) {
    const date = new Date(today);
    date.setDate(date.getDate() - i);
    date.setHours(0, 0, 0, 0);

    // Reverse compound daily growth
    const baseValue = currentValue / Math.pow(1 + dailyGrowthRate, i);

    // Add daily volatility using normal distribution approximation
    const randomReturn = (Math.random() - 0.5) * 2 * dailyVolatility;
    const value = baseValue * (1 + randomReturn);

    snapshots.push({
      date: date.toISOString().split('T')[0],
      total_value: Math.round(value * 100) / 100,
      total_gain_loss: Math.round((value - baseValue * 0.9) * 100) / 100,
      stocks_value: Math.round(value * 0.70 * 100) / 100,
      bonds_value: Math.round(value * 0.20 * 100) / 100,
      cash_value: Math.round(value * 0.10 * 100) / 100,
    });
  }

  return snapshots;
}
