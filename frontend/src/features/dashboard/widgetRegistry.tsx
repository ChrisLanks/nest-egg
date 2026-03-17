/**
 * Widget catalog: all available dashboard widgets and the default layout.
 */

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
import type { LayoutItem, WidgetDefinition } from "./types";

export const WIDGET_REGISTRY: Record<string, WidgetDefinition> = {
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
      "Donut chart breakdown of your investment portfolio by asset type.",
    defaultSpan: 1,
    component: AssetAllocationWidget,
  },
  "net-worth-projection": {
    id: "net-worth-projection",
    title: "Net Worth Projection",
    description:
      "Monte Carlo projection of total net worth over 5–20 years, including monthly savings contributions.",
    defaultSpan: 2,
    component: NetWorthProjectionWidget,
  },
  "retirement-readiness": {
    id: "retirement-readiness",
    title: "Retirement Readiness",
    description:
      "Retirement readiness score and success rate from your default scenario.",
    defaultSpan: 1,
    component: RetirementReadinessWidget,
  },
  "fire-metrics": {
    id: "fire-metrics",
    title: "FIRE Progress",
    description: "FI ratio, savings rate, and years to financial independence.",
    defaultSpan: 1,
    component: FireMetricsWidget,
  },
  "financial-health": {
    id: "financial-health",
    title: "Financial Health",
    description:
      "Composite 0-100 score based on savings rate, emergency fund, debt-to-income, and retirement progress.",
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
      "Age-based tax action items: LTCG brackets, IRMAA, RMDs, Roth conversion windows.",
    defaultSpan: 1,
    component: TaxInsightsWidget,
  },
  "spending-velocity": {
    id: "spending-velocity",
    title: "Spending Velocity",
    description:
      "Month-over-month spending acceleration or deceleration trend.",
    defaultSpan: 1,
    component: SpendingVelocityWidget,
  },
  "fee-analysis": {
    id: "fee-analysis",
    title: "Fee Analysis",
    description:
      "Portfolio expense ratios, annual fee drag, and high-fee holdings.",
    defaultSpan: 1,
    component: FeeAnalysisWidget,
  },
  "fund-overlap": {
    id: "fund-overlap",
    title: "Fund Overlap",
    description:
      "Detects redundant holdings and concentration risk in your portfolio.",
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
      "Unrealized losses that could offset capital gains, with wash sale warnings.",
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
      "Estimated monthly Social Security benefits at ages 62, FRA, and 70.",
    defaultSpan: 1,
    component: SocialSecurityWidget,
  },
  "rmd-planner": {
    id: "rmd-planner",
    title: "RMD Planner",
    description:
      "Required Minimum Distribution tracking with deadlines and penalties.",
    defaultSpan: 1,
    component: RmdPlannerWidget,
  },
  "roth-conversion": {
    id: "roth-conversion",
    title: "Roth Conversion",
    description:
      "Traditional IRA/401k balances and Roth conversion opportunity analysis.",
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
      "Projected lifetime healthcare costs including Medicare, long-term care, and pre-65 insurance.",
    defaultSpan: 1,
    component: HealthcareCostWidget,
  },
};

/** Default layout shown to users who have never customized their dashboard. */
export const DEFAULT_LAYOUT: LayoutItem[] = [
  { id: "summary-stats", span: 2 },
  { id: "net-worth-chart", span: 2 },
  { id: "spending-insights", span: 2 },
  { id: "cash-flow-trend", span: 2 },
  { id: "cash-flow-forecast", span: 2 },
  { id: "top-expenses", span: 1 },
  { id: "recent-transactions", span: 1 },
  { id: "account-balances", span: 2 },
];
