/**
 * Widget catalog: all available dashboard widgets and the default layout.
 */

import { InsightsCard } from '../../components/InsightsCard';
import { ForecastChart } from '../../components/ForecastChart';
import { SummaryStatsWidget } from './widgets/SummaryStatsWidget';
import { NetWorthChartWidget } from './widgets/NetWorthChartWidget';
import { CashFlowTrendWidget } from './widgets/CashFlowTrendWidget';
import { TopExpensesWidget } from './widgets/TopExpensesWidget';
import { RecentTransactionsWidget } from './widgets/RecentTransactionsWidget';
import { AccountBalancesWidget } from './widgets/AccountBalancesWidget';
import { SavingsGoalsWidget } from './widgets/SavingsGoalsWidget';
import { BudgetsWidget } from './widgets/BudgetsWidget';
import { DebtSummaryWidget } from './widgets/DebtSummaryWidget';
import type { LayoutItem, WidgetDefinition } from './types';

export const WIDGET_REGISTRY: Record<string, WidgetDefinition> = {
  'summary-stats': {
    id: 'summary-stats',
    title: 'Summary Stats',
    description: 'Net worth, assets, debts, income, and monthly spending at a glance.',
    defaultSpan: 2,
    component: SummaryStatsWidget,
  },
  'net-worth-chart': {
    id: 'net-worth-chart',
    title: 'Net Worth Over Time',
    description: 'Historical net worth chart with adjustable time range.',
    defaultSpan: 2,
    component: NetWorthChartWidget,
  },
  'spending-insights': {
    id: 'spending-insights',
    title: 'Spending Insights',
    description: 'Smart insights about spending trends and anomalies.',
    defaultSpan: 2,
    component: InsightsCard,
  },
  'cash-flow-trend': {
    id: 'cash-flow-trend',
    title: 'Cash Flow Trend',
    description: 'Monthly income vs. expenses bar chart.',
    defaultSpan: 2,
    component: CashFlowTrendWidget,
  },
  'cash-flow-forecast': {
    id: 'cash-flow-forecast',
    title: 'Cash Flow Forecast',
    description: '30/60/90-day projected balance based on recurring transactions.',
    defaultSpan: 2,
    component: ForecastChart,
  },
  'top-expenses': {
    id: 'top-expenses',
    title: 'Top Expenses',
    description: 'Top spending categories this month.',
    defaultSpan: 1,
    component: TopExpensesWidget,
  },
  'recent-transactions': {
    id: 'recent-transactions',
    title: 'Recent Transactions',
    description: 'Your most recent transactions.',
    defaultSpan: 1,
    component: RecentTransactionsWidget,
  },
  'account-balances': {
    id: 'account-balances',
    title: 'Account Balances',
    description: 'All account balances sorted by size.',
    defaultSpan: 2,
    component: AccountBalancesWidget,
  },
  'savings-goals': {
    id: 'savings-goals',
    title: 'Savings Goals',
    description: 'Progress toward your active savings goals.',
    defaultSpan: 1,
    component: SavingsGoalsWidget,
  },
  budgets: {
    id: 'budgets',
    title: 'Budgets',
    description: 'Current period spending vs. budget for each active budget.',
    defaultSpan: 1,
    component: BudgetsWidget,
  },
  'debt-summary': {
    id: 'debt-summary',
    title: 'Debt Summary',
    description: 'Total debt and a breakdown of your debt accounts.',
    defaultSpan: 1,
    component: DebtSummaryWidget,
  },
};

/** Default layout shown to users who have never customized their dashboard. */
export const DEFAULT_LAYOUT: LayoutItem[] = [
  { id: 'summary-stats', span: 2 },
  { id: 'net-worth-chart', span: 2 },
  { id: 'spending-insights', span: 2 },
  { id: 'cash-flow-trend', span: 2 },
  { id: 'cash-flow-forecast', span: 2 },
  { id: 'top-expenses', span: 1 },
  { id: 'recent-transactions', span: 1 },
  { id: 'account-balances', span: 2 },
];
