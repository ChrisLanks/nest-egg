/**
 * Widget catalog: all available dashboard widgets and the default layout.
 */
/* eslint-disable react-refresh/only-export-components */

import { InsightsCard } from "../../components/InsightsCard";
import { ForecastChart } from "../../components/ForecastChart";
import { SummaryStatsWidget } from "./widgets/SummaryStatsWidget";
import { NetWorthChartWidget } from "./widgets/NetWorthChartWidget";
import { CashFlowTrendWidget } from "./widgets/CashFlowTrendWidget";
import { TopExpensesWidget } from "./widgets/TopExpensesWidget";
import { RecentTransactionsWidget } from "./widgets/RecentTransactionsWidget";
import { AccountBalancesWidget } from "./widgets/AccountBalancesWidget";
import { SavingsGoalsWidget } from "./widgets/SavingsGoalsWidget";
import { BudgetsWidget } from "./widgets/BudgetsWidget";
import { DebtSummaryWidget } from "./widgets/DebtSummaryWidget";
import { UpcomingBillsWidget } from "./widgets/UpcomingBillsWidget";
import { SubscriptionsWidget } from "./widgets/SubscriptionsWidget";
import { InvestmentPerformanceWidget } from "./widgets/InvestmentPerformanceWidget";
import { AssetAllocationWidget } from "./widgets/AssetAllocationWidget";
import { NetWorthProjectionWidget } from "./widgets/NetWorthProjectionWidget";
import { NetWorthBenchmarkWidget } from "./widgets/NetWorthBenchmarkWidget";
import { RetirementReadinessWidget } from "./widgets/RetirementReadinessWidget";
import { FireMetricsWidget } from "./widgets/FireMetricsWidget";
import { FinancialHealthWidget } from "./widgets/FinancialHealthWidget";
import { DividendIncomeWidget } from "./widgets/DividendIncomeWidget";
import { TaxInsightsWidget } from "./widgets/TaxInsightsWidget";
import { SpendingVelocityWidget } from "./widgets/SpendingVelocityWidget";
import { FeeAnalysisWidget } from "./widgets/FeeAnalysisWidget";
import { FundOverlapWidget } from "./widgets/FundOverlapWidget";
import { YearOverYearWidget } from "./widgets/YearOverYearWidget";
import { TaxLossHarvestingWidget } from "./widgets/TaxLossHarvestingWidget";
import { TopMerchantsWidget } from "./widgets/TopMerchantsWidget";
import { SocialSecurityWidget } from "./widgets/SocialSecurityWidget";
import { RmdPlannerWidget } from "./widgets/RmdPlannerWidget";
import { RothConversionWidget } from "./widgets/RothConversionWidget";
import { QuarterlyPerformanceWidget } from "./widgets/QuarterlyPerformanceWidget";
import { LabelInsightsWidget } from "./widgets/LabelInsightsWidget";
import { HealthcareCostWidget } from "./widgets/HealthcareCostWidget";
import { MoneyFlowWidget } from "./widgets/MoneyFlowWidget";
import { SavingsRateWidget } from "./widgets/SavingsRateWidget";
import { DebtCostWidget } from "./widgets/DebtCostWidget";
import { BillPriceAlertsWidget } from "./widgets/BillPriceAlertsWidget";
import { MortgageRateWidget } from "./widgets/MortgageRateWidget";
import { GettingStartedWidget } from "./widgets/GettingStartedWidget";
import { SmartInsightsWidget } from "./widgets/SmartInsightsWidget";
import type { LayoutItem, WidgetDefinition } from "./types";

export const WIDGET_REGISTRY: Record<string, WidgetDefinition> = {
  "getting-started": {
    id: "getting-started",
    title: "Getting Started",
    description:
      "Track your setup progress: connect accounts, set a budget, add a savings goal, and review your net worth.",
    defaultSpan: 2,
    component: GettingStartedWidget,
  },
  "summary-stats": {
    id: "summary-stats",
    title: "Summary Stats",
    description:
      "Net worth, assets, debts, income, and monthly spending at a glance.",
    defaultSpan: 2,
    component: SummaryStatsWidget,
  },
  "net-worth-chart": {
    id: "net-worth-chart",
    title: "Net Worth Over Time",
    description: "Historical net worth chart with adjustable time range.",
    defaultSpan: 2,
    component: NetWorthChartWidget,
  },
  "spending-insights": {
    id: "spending-insights",
    title: "Spending Insights",
    description: "Smart insights about spending trends and anomalies.",
    defaultSpan: 2,
    component: InsightsCard,
  },
  "cash-flow-trend": {
    id: "cash-flow-trend",
    title: "Cash Flow Trend",
    description: "Monthly income vs. expenses bar chart.",
    defaultSpan: 2,
    component: CashFlowTrendWidget,
  },
  "cash-flow-forecast": {
    id: "cash-flow-forecast",
    title: "Cash Flow Forecast",
    description:
      "30/60/90-day projected balance based on recurring transactions.",
    defaultSpan: 2,
    component: ForecastChart,
  },
  "top-expenses": {
    id: "top-expenses",
    title: "Top Expenses",
    description: "Top spending categories this month.",
    defaultSpan: 1,
    component: TopExpensesWidget,
  },
  "recent-transactions": {
    id: "recent-transactions",
    title: "Recent Transactions",
    description: "Your most recent transactions.",
    defaultSpan: 1,
    component: RecentTransactionsWidget,
  },
  "account-balances": {
    id: "account-balances",
    title: "Account Balances",
    description: "All account balances sorted by size.",
    defaultSpan: 2,
    component: AccountBalancesWidget,
  },
  "savings-goals": {
    id: "savings-goals",
    title: "Savings Goals",
    description: "Progress toward your active savings goals.",
    defaultSpan: 1,
    component: SavingsGoalsWidget,
  },
  budgets: {
    id: "budgets",
    title: "Budgets",
    description: "Current period spending vs. budget for each active budget.",
    defaultSpan: 1,
    component: BudgetsWidget,
  },
  "debt-summary": {
    id: "debt-summary",
    title: "Debt Summary",
    description: "Total debt and a breakdown of your debt accounts.",
    defaultSpan: 1,
    component: DebtSummaryWidget,
  },
  "upcoming-bills": {
    id: "upcoming-bills",
    title: "Upcoming Bills",
    description: "Recurring bills due in the next 30 days, sorted by urgency.",
    defaultSpan: 1,
    component: UpcomingBillsWidget,
  },
  subscriptions: {
    id: "subscriptions",
    title: "Subscriptions",
    description: "Monthly recurring charges and total subscription cost.",
    defaultSpan: 1,
    component: SubscriptionsWidget,
  },
  "investment-performance": {
    id: "investment-performance",
    title: "Investment Performance",
    description: "Portfolio value, total return, and top holdings.",
    defaultSpan: 2,
    component: InvestmentPerformanceWidget,
  },
  "asset-allocation": {
    id: "asset-allocation",
    title: "Asset Allocation",
    description:
      "Shows how your portfolio is split between stocks (growth), bonds (stability), and cash. A good mix depends on your age and risk tolerance.",
    defaultSpan: 1,
    component: AssetAllocationWidget,
  },
  "net-worth-projection": {
    id: "net-worth-projection",
    title: "Net Worth Projection",
    description:
      "Simulates thousands of possible market scenarios to show how your wealth might grow over 5–20 years. Adjust savings rate and return assumptions to see best, median, and worst cases.",
    defaultSpan: 2,
    component: NetWorthProjectionWidget,
  },
  "net-worth-benchmark": {
    id: "net-worth-benchmark",
    title: "Net Worth vs. Peers",
    description:
      "See how your net worth ranks against peers in your age group using Federal Reserve survey data.",
    defaultSpan: 1,
    component: NetWorthBenchmarkWidget,
  },
  "retirement-readiness": {
    id: "retirement-readiness",
    title: "Retirement Readiness",
    description:
      "A quick score showing whether you're on track to retire when you want. Based on your savings, expected expenses, and how your investments are likely to grow.",
    defaultSpan: 1,
    component: RetirementReadinessWidget,
  },
  "fire-metrics": {
    id: "fire-metrics",
    title: "Financial Independence Progress",
    description:
      "Tracks your progress toward never needing to work again — based on your savings rate, portfolio size, and annual expenses. Shows how many years until you're financially independent.",
    defaultSpan: 1,
    component: FireMetricsWidget,
  },
  "financial-health": {
    id: "financial-health",
    title: "Financial Health",
    description:
      "A 0-100 score for your overall financial well-being — based on how much you save each month, whether you have an emergency fund, your debt load, and retirement progress.",
    defaultSpan: 1,
    component: FinancialHealthWidget,
  },
  "dividend-income": {
    id: "dividend-income",
    title: "Dividend Income",
    description:
      "YTD, trailing 12-month, and projected annual dividend income with top payers.",
    defaultSpan: 1,
    component: DividendIncomeWidget,
  },
  "tax-insights": {
    id: "tax-insights",
    title: "Tax Insights",
    description:
      "Personalized tax action items based on your age and situation — like when to convert retirement accounts, how to reduce your tax bill, and upcoming mandatory withdrawals.",
    defaultSpan: 1,
    component: TaxInsightsWidget,
  },
  "spending-velocity": {
    id: "spending-velocity",
    title: "Spending Velocity",
    description:
      "Shows whether your spending is trending up or down compared to last month. Useful for catching lifestyle creep before it becomes a habit.",
    defaultSpan: 1,
    component: SpendingVelocityWidget,
  },
  "fee-analysis": {
    id: "fee-analysis",
    title: "Fee Analysis",
    description:
      "Shows how much you're paying in hidden fund fees each year — and how much that costs you over decades. Even a 0.5% fee difference on $500K costs roughly $90K over 30 years.",
    defaultSpan: 1,
    component: FeeAnalysisWidget,
  },
  "fund-overlap": {
    id: "fund-overlap",
    title: "Fund Overlap",
    description:
      "Checks if multiple funds in your portfolio own the same underlying stocks. High overlap means you're less diversified than you think — you're doubling down on the same bets.",
    defaultSpan: 1,
    component: FundOverlapWidget,
  },
  "year-over-year": {
    id: "year-over-year",
    title: "Year over Year",
    description:
      "Compare monthly spending between the current year and last year.",
    defaultSpan: 2,
    component: YearOverYearWidget,
  },
  "tax-loss-harvesting": {
    id: "tax-loss-harvesting",
    title: "Tax Loss Harvesting",
    description:
      "Identifies investments currently worth less than you paid — selling them can reduce your tax bill this year. Shows which ones qualify and flags timing restrictions.",
    defaultSpan: 1,
    component: TaxLossHarvestingWidget,
  },
  "top-merchants": {
    id: "top-merchants",
    title: "Top Merchants",
    description: "Highest spending by merchant this month.",
    defaultSpan: 1,
    component: TopMerchantsWidget,
  },
  "social-security": {
    id: "social-security",
    title: "Social Security",
    description:
      "Shows your estimated monthly Social Security check at different claiming ages (62, 67, or 70). Waiting longer means a bigger monthly payment — roughly 8% more per year you delay.",
    defaultSpan: 1,
    component: SocialSecurityWidget,
  },
  "rmd-planner": {
    id: "rmd-planner",
    title: "Retirement Withdrawal Planner",
    description:
      "After age 73, the IRS requires you to withdraw a minimum amount from traditional 401(k)s and IRAs each year — or face a 25% penalty. This tracks what you owe and when.",
    defaultSpan: 1,
    component: RmdPlannerWidget,
  },
  "roth-conversion": {
    id: "roth-conversion",
    title: "Roth Conversion Analyzer",
    description:
      "Helps you decide whether to move money from a traditional 401(k) or IRA into a Roth account. You pay taxes now, but future withdrawals are tax-free. Shows the best windows to convert.",
    defaultSpan: 1,
    component: RothConversionWidget,
  },
  "quarterly-performance": {
    id: "quarterly-performance",
    title: "Quarterly Performance",
    description:
      "Quarterly net income comparison between the current and prior year.",
    defaultSpan: 2,
    component: QuarterlyPerformanceWidget,
  },
  "label-insights": {
    id: "label-insights",
    title: "Label Insights",
    description:
      "Spending and income breakdown by transaction labels this month.",
    defaultSpan: 1,
    component: LabelInsightsWidget,
  },
  "healthcare-costs": {
    id: "healthcare-costs",
    title: "Healthcare Costs",
    description:
      "Estimates your future healthcare expenses — including insurance before Medicare kicks in at 65, Medicare premiums, and potential long-term care costs. Often the biggest surprise in retirement planning.",
    defaultSpan: 1,
    component: HealthcareCostWidget,
  },
  "money-flow": {
    id: "money-flow",
    title: "Money Flow",
    description:
      "Sankey diagram showing how income flows through your household into expense categories and savings.",
    defaultSpan: 2,
    component: MoneyFlowWidget,
  },
  "savings-rate": {
    id: "savings-rate",
    title: "Savings Rate",
    description:
      "Monthly savings rate trend with trailing 3-month and 12-month weighted averages.",
    defaultSpan: 1,
    component: SavingsRateWidget,
  },
  "debt-cost": {
    id: "debt-cost",
    title: "Debt Interest Cost",
    description:
      "True monthly and annual interest cost across all debt accounts, plus weighted average rate.",
    defaultSpan: 1,
    component: DebtCostWidget,
  },
  "bill-price-alerts": {
    id: "bill-price-alerts",
    title: "Bill Price Alerts",
    description:
      "Subscriptions and recurring bills where the charge has increased more than 5% vs. a year ago.",
    defaultSpan: 1,
    component: BillPriceAlertsWidget,
  },
  "mortgage-rates": {
    id: "mortgage-rates",
    title: "Mortgage Rates",
    description:
      "Shows today's 30-year and 15-year mortgage rates versus your current rate. If rates have dropped significantly, it may be worth looking into refinancing.",
    defaultSpan: 1,
    component: MortgageRateWidget,
  },
  "smart-insights": {
    id: "smart-insights",
    title: "Smart Insights",
    description:
      "Proactive financial alerts derived from your live data: spending anomalies, budget overruns, emergency fund gaps, fee drag, IRMAA risk, and more.",
    defaultSpan: 2,
    component: SmartInsightsWidget,
  },
};

/**
 * Simple layout — for users who picked "Keep it simple" during onboarding.
 * Shows only the essentials: checklist, net worth at a glance, recent spending.
 */
export const SIMPLE_LAYOUT: LayoutItem[] = [
  { id: "getting-started", span: 2 },
  { id: "summary-stats", span: 2 },
  { id: "net-worth-chart", span: 2 },
  { id: "top-expenses", span: 1 },
  { id: "recent-transactions", span: 1 },
];

/**
 * Advanced layout — for users who picked "Show me everything" during onboarding.
 * Full view with cash flow, forecasting, budgets, accounts, and insights.
 */
export const ADVANCED_LAYOUT: LayoutItem[] = [
  { id: "getting-started", span: 2 },
  { id: "summary-stats", span: 2 },
  { id: "net-worth-chart", span: 2 },
  { id: "financial-health", span: 1 },
  { id: "retirement-readiness", span: 1 },
  { id: "smart-insights", span: 2 },
  { id: "spending-insights", span: 2 },
  { id: "cash-flow-trend", span: 2 },
  { id: "cash-flow-forecast", span: 2 },
  { id: "top-expenses", span: 1 },
  { id: "recent-transactions", span: 1 },
  { id: "account-balances", span: 2 },
  { id: "budgets", span: 1 },
  { id: "savings-goals", span: 1 },
];

/** Default layout for users who skipped onboarding or came from an older version. */
export const DEFAULT_LAYOUT: LayoutItem[] = SIMPLE_LAYOUT;
