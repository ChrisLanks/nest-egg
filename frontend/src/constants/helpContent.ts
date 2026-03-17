/**
 * Centralized help text for contextual hints across the app.
 * Organized by page/feature, then by specific metric or concept.
 *
 * Guidelines:
 * - Keep each hint to 1-2 sentences (fits in a tooltip).
 * - Write for someone who is NOT a finance professional.
 * - Avoid jargon; if you must use a term, define it inline.
 */

export const helpContent = {
  // ── FIRE Metrics ──────────────────────────────────────────────────────
  fire: {
    fiRatio:
      "Your FI Ratio is your investable assets divided by your FI Number (annual expenses ÷ withdrawal rate). A ratio of 1.0 means you could retire today.",
    coastFi:
      "Coast FI is the point where your current investments will grow to cover retirement on their own — even if you never save another dollar. It assumes compound growth at your expected return rate.",
    savingsRate:
      "The percentage of your gross income that you're saving or investing. A 20%+ savings rate is a strong foundation; FIRE enthusiasts often aim for 50%+.",
    withdrawalRate:
      "The percentage of your portfolio you plan to withdraw each year in retirement. The '4% rule' is a common starting point based on historical stock/bond returns over 30-year periods.",
    yearsToFi:
      "Estimated years until your investment portfolio can fully cover your annual expenses at your chosen withdrawal rate. Lower spending or higher savings shortens this.",
  },

  // ── Retirement Planning ───────────────────────────────────────────────
  retirement: {
    monteCarlo:
      "Monte Carlo simulation runs thousands of randomized market scenarios to estimate how likely your plan is to succeed. A 80%+ success rate is generally considered solid.",
    withdrawalStrategy:
      "How you pull money from accounts in retirement. 'Tax-optimized' withdraws from taxable accounts first to let tax-advantaged accounts grow longer. 'Simple rate' uses a fixed percentage each year.",
    readinessScore:
      "A 0-100 score based on your Monte Carlo success rate, savings trajectory, and healthcare coverage. Think of it as a retirement health checkup.",
    socialSecurityAge:
      "You can claim Social Security between ages 62 and 70. Claiming earlier means smaller monthly checks; waiting until 70 maximizes your benefit — roughly 8% more per year you delay past full retirement age.",
    lifeEvents:
      "Major expenses or income changes you expect in retirement — like a home downsize, caring for a parent, or a career sabbatical. Adding these makes your projection more realistic.",
  },

  // ── Investments ───────────────────────────────────────────────────────
  investments: {
    taxLossHarvesting:
      "Selling investments at a loss to offset capital gains taxes. The 'harvested' loss reduces your tax bill, and you can reinvest in a similar (but not identical) fund to maintain your allocation.",
    rothConversion:
      "Moving money from a traditional IRA/401(k) to a Roth IRA. You pay taxes now, but future withdrawals are tax-free. Often beneficial if you expect a higher tax bracket in retirement.",
    fundOverlap:
      "When multiple funds in your portfolio hold the same underlying stocks, you may be less diversified than you think. High overlap means you're doubling down on the same bets.",
    rmd: "Required Minimum Distributions — after age 73 you must withdraw a minimum amount from traditional IRAs and 401(k)s each year, or face a 25% penalty on the shortfall.",
    feeAnalysis:
      "Even small differences in expense ratios compound dramatically over decades. A 0.5% fee difference on $500K costs roughly $90K over 30 years.",
    assetAllocation:
      "How your portfolio is split across stocks, bonds, cash, and other assets. A common rule of thumb: subtract your age from 110 to get your stock percentage, though your risk tolerance matters too.",
  },

  // ── Debt Payoff ───────────────────────────────────────────────────────
  debtPayoff: {
    snowball:
      "Pay off your smallest balance first, then roll that payment into the next smallest. You pay more interest overall, but the quick wins build momentum and motivation.",
    avalanche:
      "Pay off the highest interest rate debt first to minimize total interest paid. Mathematically optimal, but the first payoff may take longer.",
  },

  // ── Budgets ───────────────────────────────────────────────────────────
  budgets: {
    rollover:
      "When enabled, any unspent budget from one period carries over to the next. Useful for categories with variable spending, like car maintenance.",
    alertThreshold:
      "You'll get a notification when your spending reaches this percentage of the budget. Default is 80% — early enough to adjust, not so early it's noisy.",
    period:
      "Monthly works for regular expenses like groceries. Quarterly or yearly is better for irregular costs like insurance premiums or annual subscriptions.",
  },

  // ── Income & Expenses ─────────────────────────────────────────────────
  incomeExpenses: {
    sankey:
      "The Sankey diagram shows how money flows from your income sources through spending categories. Wider bands mean more money — it's a visual budget at a glance.",
    cashFlow:
      "Cash flow is simply income minus expenses for a given period. Positive means you're saving; negative means you're spending more than you earn.",
  },

  // ── Net Worth ─────────────────────────────────────────────────────────
  netWorth: {
    primaryProperty:
      "Your primary residence is tracked separately because it's not a liquid asset — you can't easily spend your home equity. This gives you a clearer picture of investable wealth.",
    inflationAdjusted:
      "Shows values in today's dollars by removing the effect of inflation. Helpful for comparing your purchasing power over time rather than just the raw number.",
  },

  // ── Savings Goals ─────────────────────────────────────────────────────
  savingsGoals: {
    emergencyFund:
      "Financial experts recommend saving 3-6 months of essential expenses. This cushion covers job loss, medical bills, or unexpected repairs without touching investments.",
    autoSync:
      "Links a goal to a bank account so the balance updates automatically. Great for dedicated savings accounts where the balance = your progress.",
    fundingAllocation:
      "Waterfall fills goals by priority — the top goal gets funded first. Proportional splits your balance across all goals based on their target amounts.",
  },
} as const;

/** Type helper for accessing help content keys. */
export type HelpContentPage = keyof typeof helpContent;
