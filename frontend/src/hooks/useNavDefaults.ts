/**
 * Centralizes nav visibility defaults so Layout and PreferencesPage
 * derive the same "should this path be visible?" answer from the same
 * account/age data, preventing the Preferences UI from showing a tab
 * as "off" when the nav actually shows it (e.g. mortgage when the user
 * has a mortgage account).
 */

import { useQuery } from "@tanstack/react-query";
import api from "../services/api";

interface Account {
  account_type: string;
  is_rental_property?: boolean;
  plaid_item_id?: string | null;
  plaid_item_hash?: string | null;
}

const DEBT_TYPES = new Set(["credit_card", "loan", "student_loan", "mortgage"]);

const INVESTMENT_TYPES = new Set([
  "brokerage",
  "retirement_401k",
  "retirement_ira",
  "retirement_roth_ira",
  "retirement_403b",
  "retirement_457",
  "retirement_pension",
  "crypto",
]);

/** Nav item definition — matches NAV_SECTIONS shape in PreferencesPage */
export interface NavItem {
  label: string;
  path: string;
  alwaysOn?: boolean;
  conditional?: boolean;
  advanced?: boolean;
  reason?: string;
}

export interface NavSection {
  group: string;
  items: NavItem[];
}

/** Canonical nav section definitions shared across Layout and Preferences */
export const NAV_SECTIONS: NavSection[] = [
  {
    group: "Top Level",
    items: [
      { label: "Overview", path: "/overview", alwaysOn: true },
      { label: "Calendar", path: "/calendar", alwaysOn: true },
      { label: "Investments", path: "/investments", alwaysOn: true },
      { label: "Accounts", path: "/accounts", alwaysOn: true },
    ],
  },
  {
    group: "Spending",
    items: [
      { label: "Transactions", path: "/transactions" },
      { label: "Budgets", path: "/budgets" },
      { label: "Categories & Labels", path: "/categories" },
      {
        label: "Recurring & Bills",
        path: "/recurring-bills",
        conditional: true,
        reason: "Shown once a bank account is connected",
      },
      {
        label: "Rules",
        path: "/rules",
        conditional: true,
        reason: "Shown once any account is added",
      },
    ],
  },
  {
    group: "Analytics",
    items: [
      { label: "Cash Flow", path: "/income-expenses" },
      { label: "Net Worth Timeline", path: "/net-worth-timeline" },
      { label: "Trends", path: "/trends" },
      { label: "Reports", path: "/reports" },
      { label: "Year in Review", path: "/year-in-review" },
      {
        label: "Tax Deductible",
        path: "/tax-deductible",
        conditional: true,
        reason: "Shown with investment or rental accounts",
      },
      {
        label: "Rental Properties",
        path: "/rental-properties",
        conditional: true,
        reason: "Shown when you have a rental property account",
      },
      { label: "Smart Insights", path: "/smart-insights" },
      {
        label: "Financial Health",
        path: "/financial-health",
        reason: "Financial ratios, debt-to-income analysis, and emergency fund coverage",
      },
    ],
  },
  {
    group: "Planning",
    items: [
      { label: "Goals", path: "/goals" },
      { label: "Retirement", path: "/retirement" },
      {
        label: "Education",
        path: "/education",
        conditional: true,
        reason: "Shown when you have a 529 account",
      },
      {
        label: "Debt Payoff",
        path: "/debt-payoff",
        conditional: true,
        reason: "Shown when you have loans or credit card debt",
      },
      {
        label: "Mortgage",
        path: "/mortgage",
        conditional: true,
        reason: "Shown when you have a mortgage account",
      },
      {
        label: "Tax Center",
        path: "/tax-center",
        reason: "Tax projection, tax buckets, and charitable giving",
      },
      {
        label: "Life Planning",
        path: "/life-planning",
        reason: "Social Security, variable income, and estate planning",
      },
      {
        label: "Planning Tools",
        path: "/investment-tools",
        advanced: true,
        reason: "Advanced — FIRE, equity compensation, and loan modeling",
      },
    ],
  },
];

/**
 * Computes per-path default visibility based on accounts and user age.
 * Paths not in this map default to `true` (always visible).
 */
export function buildConditionalDefaults(
  accounts: Account[],
  userAge: number | null,
): Record<string, boolean> {
  const hasDebt = accounts.some((a) => DEBT_TYPES.has(a.account_type));
  const hasRental = accounts.some((a) => a.is_rental_property);
  const hasMortgage = accounts.some((a) => a.account_type === "mortgage");
  const has529 = accounts.some((a) => a.account_type === "retirement_529");
  const hasInvestments = accounts.some((a) =>
    INVESTMENT_TYPES.has(a.account_type),
  );
  const hasLinkedAccounts = accounts.some(
    (a) => a.plaid_item_id !== null || a.plaid_item_hash !== null,
  );
  const hasAnyAccounts = accounts.length > 0;

  // SS Optimizer is only relevant for users approaching retirement age
  const isSsAge = userAge !== null && userAge >= 50;

  return {
    "/rental-properties": hasRental,
    "/education": has529,
    "/debt-payoff": hasDebt,
    "/mortgage": hasMortgage,
    "/recurring-bills": hasLinkedAccounts,
    "/rules": hasAnyAccounts,
    "/tax-deductible": hasInvestments || hasRental,
    "/ss-claiming": isSsAge,
    // Consolidated hubs — always visible (contain their own conditional logic)
    "/tax-center": true,
    "/life-planning": true,
    "/investment-tools": true,
    "/financial-health": true,
  };
}

/**
 * Hook — fetches accounts and user profile, returns computed nav defaults.
 * Both Layout and PreferencesPage call this so they always agree on what
 * "default visible" means for each path.
 */
export function useNavDefaults(selectedUserId?: string | null) {
  const { data: accounts = [], isLoading: accountsLoading } = useQuery<
    Account[]
  >({
    queryKey: ["accounts", selectedUserId ?? null],
    queryFn: async () => {
      const params = selectedUserId ? { user_id: selectedUserId } : {};
      const res = await api.get("/accounts", { params });
      return res.data;
    },
  });

  const { data: userProfile } = useQuery({
    queryKey: ["user-profile-nav"],
    queryFn: async () => {
      const res = await api.get("/settings/profile");
      return res.data as { birth_year?: number | null };
    },
    staleTime: 30 * 60 * 1000,
  });

  const currentYear = new Date().getFullYear();
  const userAge = userProfile?.birth_year
    ? currentYear - userProfile.birth_year
    : null;

  const conditionalDefaults = buildConditionalDefaults(accounts, userAge);

  return {
    accounts,
    accountsLoading,
    userAge,
    conditionalDefaults,
    /** True if path should be visible by default (no overrides applied) */
    getDefault: (path: string): boolean => conditionalDefaults[path] ?? true,
  };
}
