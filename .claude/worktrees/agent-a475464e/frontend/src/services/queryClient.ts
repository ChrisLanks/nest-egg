/**
 * React Query configuration and centralized query key registry
 */

import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      gcTime: 1000 * 60 * 30, // 30 minutes (formerly cacheTime)
      refetchOnWindowFocus: false, // opt-in per query; globally too noisy for a financial app
      refetchOnReconnect: true,
      retry: 1,
    },
    mutations: {
      retry: 1,
    },
  },
});

/**
 * Centralized query key registry.
 *
 * Using factory functions ensures consistent key structure across the app
 * and enables reliable invalidation via prefix matching.
 */
export const queryKeys = {
  // Auth & user
  currentUser: ["currentUser"] as const,
  userProfile: ["userProfile"] as const,

  // Accounts
  accounts: {
    all: ["accounts"] as const,
    admin: (userId?: string) => ["accounts-admin", userId] as const,
    allHousehold: ["accounts-all"] as const,
    detail: (id: string) => ["account", id] as const,
    checkShared: (hash: string) => ["accounts-check-shared", hash] as const,
  },

  // Transactions
  transactions: {
    all: ["transactions"] as const,
    infinite: (filters: Record<string, unknown>) =>
      ["infinite-transactions", ...Object.values(filters)] as const,
    allInfinite: (filters: Record<string, unknown>) =>
      ["all-transactions-infinite", ...Object.values(filters)] as const,
    detail: (id: string) => ["transaction", id] as const,
    merchants: ["transaction-merchants"] as const,
  },

  // Dashboard
  dashboard: {
    all: ["dashboard"] as const,
    summary: (userId?: string) => ["dashboard-summary", userId] as const,
  },

  // Investments & portfolio
  portfolio: {
    all: ["portfolio"] as const,
    summary: ["portfolio-summary"] as const,
    widget: ["portfolio-widget"] as const,
    snapshots: (range?: string) => ["portfolio-snapshots", range] as const,
    snapshotsRisk: ["portfolio-snapshots-risk"] as const,
  },
  holdings: (accountId: string) => ["holdings", accountId] as const,
  feeAnalysis: (accountId?: string) => ["fee-analysis", accountId] as const,
  fundOverlap: ["fund-overlap"] as const,
  targetAllocations: ["target-allocations"] as const,
  rebalancing: {
    analysis: ["rebalancing-analysis"] as const,
    presets: ["rebalancing-presets"] as const,
  },
  taxLots: (accountId: string) => ["tax-lots", accountId] as const,
  realizedGains: ["realized-gains"] as const,
  unrealizedGains: ["unrealized-gains"] as const,

  // Budgets
  budgets: {
    all: ["budgets"] as const,
    widget: ["budgets-widget"] as const,
    spending: (id: string) => ["budget-spending", id] as const,
  },

  // Goals
  goals: {
    all: ["goals"] as const,
    widget: ["goals-widget"] as const,
  },

  // Categories & labels
  categories: ["categories"] as const,
  labels: ["labels"] as const,

  // Household
  household: {
    members: ["household-members"] as const,
    users: ["household-users"] as const,
    invitations: ["household-invitations"] as const,
  },

  // Guest access
  guestAccess: {
    guests: ["guest-access-guests"] as const,
    invitations: ["guest-access-invitations"] as const,
    invitationDetails: (code: string) => ["invitation-details", code] as const,
  },

  // Permissions
  permissions: {
    all: ["permissions"] as const,
    given: ["permissions", "given"] as const,
    received: ["permissions", "received"] as const,
  },

  // Notifications
  notifications: ["notifications"] as const,

  // Rules
  rules: ["rules"] as const,

  // Financial features
  incomeExpenses: (filters: Record<string, unknown>) =>
    ["income-expenses", ...Object.values(filters)] as const,
  financialHealth: ["financial-health"] as const,
  cashFlowForecast: ["cash-flow-forecast"] as const,
  recurringTransactions: ["recurring-transactions"] as const,
  subscriptionsWidget: ["subscriptions-widget"] as const,
  spendingInsights: ["spending-insights"] as const,

  // Bills & calendar
  billCalendar: ["bill-calendar"] as const,
  upcomingBills: ["upcoming-bills"] as const,
  financialCalendar: ["financial-calendar"] as const,

  // Retirement
  retirement: {
    scenarios: ["retirement-scenarios"] as const,
    widget: ["retirement-scenarios-widget"] as const,
  },

  // FIRE
  fireMetrics: {
    widget: ["fire-metrics-widget"] as const,
  },

  // Education
  educationPlans: ["education-plans"] as const,

  // Reports & analytics
  annualSummaries: ["annual-summaries"] as const,
  yearInReview: ["year-in-review"] as const,
  yearOverYear: ["year-over-year"] as const,

  // Org preferences
  orgPreferences: ["orgPreferences"] as const,

  // Email config
  emailConfigured: ["emailConfigured"] as const,
  emailNotificationsPref: ["emailNotificationsPref"] as const,

  // Bank linking
  bankLinkToken: ["bank-link-token"] as const,
  providerAvailability: ["provider-availability"] as const,

  // Rental properties
  rentalPropertyPnl: (id: string) => ["rental-property-pnl", id] as const,

  // Reconciliation
  reconciliation: (accountId: string) => ["reconciliation", accountId] as const,

  // Migration
  migrationHistory: (accountId: string) =>
    ["migration-history", accountId] as const,

  // Attachments
  attachments: (transactionId: string) =>
    ["attachments", transactionId] as const,
};
