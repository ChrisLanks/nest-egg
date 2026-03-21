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
    accountExclusions:
      "Your primary home, vacation home, and personal vehicles are hidden by default — you need those to live, so they aren't liquid investments. Investment properties are included. Use the Filter button to change what's shown.",
    // Sub-tab descriptions
    sectorBreakdown:
      "Shows how your investments are spread across industries like tech, healthcare, and energy. If one sector crashes, heavy concentration there can drag your whole portfolio down. Aim for no single sector above 25-30%.",
    holdingsDetail:
      "A complete list of every investment you own — what you paid, what it's worth now, and what fees you're paying. Use this to spot investments that are losing money, charging high fees, or taking up too much of your portfolio.",
    dividendIncome:
      "Tracks cash payments your investments send you — dividends from stocks and interest from bonds. Dividend income can provide steady cash flow in retirement without selling shares.",
    futureGrowth:
      "Projects your portfolio's future value using Monte Carlo simulation — thousands of randomized market scenarios. Adjust return, volatility, and inflation to see optimistic, average, and pessimistic outcomes.",
    performanceTrends:
      "Shows how your portfolio value has changed over time. Compare the blue line (current value) against the green line (what you originally paid) to see how much you've actually earned.",
    riskAnalysis:
      "Measures how risky your portfolio is based on price volatility and how concentrated your holdings are. Lower risk scores mean more stability, but potentially lower returns too.",
    rebalancing:
      "Compares your current portfolio mix against your target allocation and shows where you've drifted. Rebalancing — selling what's overweight and buying what's underweight — keeps your risk level consistent.",
    // In-panel metrics
    costBasis:
      "The total amount of money you originally spent to buy this investment — your 'in for' amount. If your cost basis is $5,000 and it's now worth $7,000, you're up $2,000.",
    expenseRatio:
      "The annual fee a fund charges, expressed as a percentage of your investment. A 0.03% index fund costs $3/year per $10K invested; a 1% fund costs $100.",
    gainLoss:
      "How much money you've made or lost on this investment so far. Green means it's worth more than you paid; red means it's worth less. This is a 'paper' gain/loss — it only counts when you actually sell.",
    yieldOnCost:
      "Annual dividends divided by what you originally paid for the shares. A 5% yield on cost means you're earning 5% of your original investment back each year in dividends.",
    volatility:
      "How much your portfolio's value swings up and down. Measured as annualized standard deviation — the S&P 500 typically runs about 15%. Higher volatility means bigger ups AND bigger downs.",
    diversificationScore:
      "A 0-100 score measuring how evenly your money is spread across holdings. 100 means perfectly equal; a low score means a few positions dominate. More diversification reduces the impact of any single investment tanking.",
    riskScore:
      "A 0-100 composite score — 60% based on volatility, 40% on diversification. Lower is less risky. Under 40 is conservative, 40-70 is moderate, above 70 is aggressive.",
    cagr: "Compound Annual Growth Rate — your average yearly return accounting for compounding. Unlike simple average, CAGR shows the smooth annual rate needed to get from start to end value.",
    maxDrift:
      "The largest gap between any asset class's current allocation and its target. When drift exceeds your threshold, it's time to rebalance.",
    driftThreshold:
      "The maximum drift percentage you'll tolerate before rebalancing. Default is 5%. Lower thresholds keep you closer to target but mean more frequent trades.",
    suggestedTrades:
      "Buy/sell recommendations to bring your portfolio back to target. These are suggestions only — consider tax implications and transaction costs before executing.",
    percentiles:
      "Percentile bands show the range of possible outcomes. The 50th percentile (median) is the middle outcome; 90th is optimistic, 10th is pessimistic. Wider bands mean more uncertainty.",
    stressTests:
      "Simulates specific bad market periods — like the 2008 crisis or high inflation — to see how your portfolio would hold up. Helps you prepare for worst-case scenarios.",
    successRate:
      "The percentage of simulated scenarios where your portfolio lasted through retirement without running out. Aim for 80%+ for confidence.",
    inflationAdjusted:
      "When ON, values are shown in today's dollars — what your money will actually be able to buy. $1M in 30 years won't buy as much as $1M today. This gives you a more realistic picture of future purchasing power.",
  },

  // ── Debt Payoff ───────────────────────────────────────────────────────
  debtPayoff: {
    snowball:
      "Pay off your smallest balance first, then roll that payment into the next smallest. You pay more interest overall, but the quick wins build momentum and motivation.",
    avalanche:
      "Pay off the highest interest rate debt first to minimize total interest paid. Mathematically optimal, but the first payoff may take longer.",
    interestRate:
      "The yearly percentage your lender charges you for borrowing money. A 6% rate on a $10,000 loan means you pay roughly $600/year in interest on top of the loan itself.",
    minimumPayment:
      "The smallest amount you must pay each month to stay current on the debt. Paying only the minimum stretches out repayment and costs more in interest over time.",
    totalInterest:
      "The total amount of extra money you'll pay in interest charges over the life of the debt — on top of the original amount you borrowed.",
    extraPayment:
      "Any amount you pay above the minimum each month. Even small extra payments can save thousands in interest and shave years off your payoff timeline.",
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

  // ── Rules ────────────────────────────────────────────────────────────
  rules: {
    matchAll:
      "ALL conditions must be true for the rule to trigger. Use this for precise matching — e.g., merchant IS 'Starbucks' AND amount is under $20.",
    matchAny:
      "Only ONE condition needs to be true. Use this for broad matching — e.g., merchant CONTAINS 'starbucks' OR merchant CONTAINS 'dunkin'.",
    applyTo:
      "Controls which transactions the rule affects. 'New only' applies to future transactions. 'Existing' retroactively applies to past ones. 'Both' does both.",
    conditions:
      "The criteria that must be met for this rule to fire — like merchant name, amount range, or description keywords.",
    actions:
      "What happens when the conditions match — set a category, add a label, or override the merchant name.",
  },

  // ── Accounts ────────────────────────────────────────────────────────
  accounts: {
    excludeFromCashFlow:
      "When ON, this account's transactions won't show up in your Income & Expenses or budget tracking. Useful for investment accounts or transfers that aren't regular spending.",
    interestRate:
      "The annual percentage rate (APR) your lender charges. Lower is better — refinancing can sometimes get you a lower rate.",
    loanTerm:
      "How long you have to pay off the loan. Shorter terms mean higher monthly payments but less total interest paid.",
    originationDate:
      "The date the loan was opened. Used to calculate where you are in the repayment schedule and how much principal vs. interest you're paying.",
    minimumPayment:
      "The smallest monthly payment required by your lender. Paying only the minimum extends the loan and increases total interest.",
    employerMatch:
      "Free money from your employer — they contribute a percentage of what you put into your 401(k). For example, a 100% match on 3% means if you contribute 3% of your salary, they add another 3%.",
    employerMatchLimit:
      "The maximum percentage of your salary your employer will match. Contributing at least this much captures the full match — anything less leaves free money on the table.",
    trackHoldings:
      "When ON, you can enter individual stocks, funds, and ETFs in this account for detailed analysis (sector breakdown, fees, gains). When OFF, only the total balance is tracked.",
  },

  // ── Recurring Transactions ──────────────────────────────────────────
  recurring: {
    isBill:
      "Bills are required payments like rent, utilities, or insurance. Marking something as a bill helps you track must-pay expenses separately from optional subscriptions.",
    frequency:
      "How often this transaction repeats — weekly, monthly, quarterly, or yearly. Used to calculate your total recurring costs.",
    reminderDays:
      "Get a heads-up this many days before the payment is due, so you can make sure you have enough in your account.",
  },

  // ── Categories ──────────────────────────────────────────────────────
  categories: {
    providerCategories:
      "These categories come from your bank or card provider (via Plaid/Teller). They're auto-assigned but can be overridden. Click 'Make Custom' to rename or reorganize them.",
  },

  // ── Tax ─────────────────────────────────────────────────────────────
  tax: {
    taxDeductible:
      "Expenses that can reduce your taxable income when you file taxes. Tracking them here makes tax season easier — just export the totals for your accountant or tax software.",
  },

  // ── Settings/Preferences ────────────────────────────────────────────
  preferences: {
    birthYear:
      "Used to calculate retirement milestones: age 59½ (penalty-free retirement withdrawals), age 65 (Medicare eligibility), and age 73 (required minimum distributions from retirement accounts).",
    claimingAge:
      "The age you plan to start receiving Social Security. You can claim as early as 62, but waiting until 70 gives you about 77% more per month. Full retirement age is typically 67.",
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
