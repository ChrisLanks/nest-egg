/**
 * Centralizes nav visibility defaults so Layout and PreferencesPage
 * derive the same "should this path be visible?" answer from the same
 * account/age data, preventing the Preferences UI from showing a tab
 * as "off" when the nav actually shows it (e.g. mortgage when the user
 * has a mortgage account).
 */

import { useQuery } from "@tanstack/react-query";
import api from "../services/api";
import { useLocalStorage } from "./useLocalStorage";

interface Account {
  account_type: string;
  user_id?: string;
  is_rental_property?: boolean;
  property_type?: string | null;
  plaid_item_id?: string | null;
  plaid_item_hash?: string | null;
}

const DEBT_TYPES = new Set(["credit_card", "loan", "student_loan", "mortgage"]);


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

/**
 * Canonical nav section definitions shared across Layout and Preferences.
 *
 * Progressive disclosure philosophy:
 *  - alwaysOn: visible from day one, even with no accounts
 *  - conditional: unlocked by specific account type (mortgage, 529, etc.)
 *  - no flag (default): shown once ANY account exists (gated in buildConditionalDefaults)
 *  - advanced: hidden behind the "Show advanced features" toggle in Preferences
 *
 * Day-one view (zero accounts): Overview, Calendar, Investments, Accounts only.
 * After first account: Goals, Retirement + spending/analytics unlock.
 */
export const NAV_SECTIONS: NavSection[] = [
  {
    group: "Top Level",
    items: [
      { label: "Overview", path: "/overview", alwaysOn: true, reason: "Always visible — your financial snapshot at a glance" },
      { label: "Calendar", path: "/calendar", alwaysOn: true, reason: "Always visible — upcoming bills, dividends, and financial events" },
      { label: "Investments", path: "/investments", alwaysOn: true, reason: "Always visible — portfolio holdings, performance, and allocation" },
      { label: "Accounts", path: "/accounts", alwaysOn: true, reason: "Always visible — manage all your linked and manual accounts" },
    ],
  },
  {
    group: "Spending",
    items: [
      {
        label: "Transactions",
        path: "/transactions",
        conditional: true,
        reason: "Unlocks with first account — search, filter, and categorize all transactions",
      },
      {
        label: "Budgets",
        path: "/budgets",
        conditional: true,
        reason: "Unlocks with first account — set monthly spending limits by category",
      },
      {
        label: "Spending Categories",
        path: "/categories",
        conditional: true,
        reason: "Unlocks with first account — customize categories and manage auto-categorization rules",
      },
      {
        label: "Recurring & Bills",
        path: "/recurring-bills",
        conditional: true,
        reason: "Unlocks when a bank account is connected — track subscriptions and recurring charges",
      },
      {
        label: "Rules",
        path: "/rules",
        conditional: true,
        reason: "Unlocks with first account — auto-categorize and rename transactions by pattern",
      },
    ],
  },
  {
    group: "Analytics",
    items: [
      {
        label: "Cash Flow",
        path: "/cash-flow",
        conditional: true,
        reason: "Unlocks with first account — monthly income vs. spending trends and cash flow analysis",
      },
      {
        label: "Net Worth Timeline",
        path: "/net-worth-timeline",
        conditional: true,
        reason: "Unlocks with first account — historical net worth chart with asset and liability breakdown",
      },
      {
        label: "Reports & Trends",
        path: "/reports",
        conditional: true,
        reason: "Unlocks with first account — spending trends, category breakdowns, and custom reports",
      },
      {
        label: "Financial Checkup",
        path: "/financial-health",
        conditional: true,
        reason: "Unlocks with first account — savings rate, debt ratios, liquidity score, and credit score tracking",
      },
      {
        label: "PE Performance",
        path: "/pe-performance",
        conditional: true,
        reason: "Unlocks when you add a private equity account — IRR, MOIC, and fund-level attribution",
      },
      {
        label: "Rental Properties",
        path: "/rental-properties",
        conditional: true,
        reason: "Unlocks when you add an investment property — Schedule E P&L, cap rate, and STR analysis",
      },
    ],
  },
  {
    group: "Planning",
    items: [
      {
        label: "Goals",
        path: "/goals",
        conditional: true,
        reason: "Unlocks with first account — track savings targets like emergency fund, down payment, and vacation",
      },
      {
        label: "Retirement & Income",
        path: "/retirement",
        conditional: true,
        reason: "Unlocks with first account — retirement planner, Social Security optimizer, RMD projections, and variable income",
      },
      {
        label: "Debt Payoff",
        path: "/debt-payoff",
        conditional: true,
        reason: "Unlocks when you have loans or credit cards — avalanche vs. snowball payoff strategies",
      },
      {
        label: "Mortgage",
        path: "/mortgage",
        conditional: true,
        reason: "Unlocks when you add a mortgage — amortization schedule and refinance break-even analysis",
      },
      {
        label: "Education",
        path: "/education",
        conditional: true,
        reason: "Unlocks when you add a 529 — college savings projection and contribution strategy",
      },
      {
        label: "Estate & Insurance",
        path: "/estate-insurance",
        conditional: true,
        reason: "Unlocks with first account — beneficiary tracking, estate planning, and insurance coverage gap analysis",
      },
      // ── Advanced ──
      {
        label: "Tax Center",
        path: "/tax-center",
        advanced: true,
        reason: "Advanced — tax projection, Roth conversion, backdoor Roth, IRMAA, withholding check, and charitable giving",
      },
      {
        label: "Planning Tools",
        path: "/investment-tools",
        advanced: true,
        reason: "Advanced — FIRE calculator, loan modeler, HSA optimizer, bond ladder, employer match, and what-if scenarios",
      },
    ],
  },
];

/**
 * Computes per-path default visibility based on accounts.
 * Paths not in this map default to `true` (always visible).
 *
 * Progressive disclosure: most items are hidden until the user has at least
 * one account, reducing day-one overwhelm. Only Overview/Calendar/Investments/
 * Accounts are shown before any account is added (those are alwaysOn in
 * NAV_SECTIONS and not gated here).
 */
export function buildConditionalDefaults(
  accounts: Account[],
): Record<string, boolean> {
  const hasDebt = accounts.some((a) => DEBT_TYPES.has(a.account_type));
  const hasRental = accounts.some((a) => a.is_rental_property || a.property_type === "investment");
  const hasMortgage = accounts.some((a) => a.account_type === "mortgage");
  const has529 = accounts.some((a) => a.account_type === "retirement_529");
  const hasLinkedAccounts = accounts.some(
    (a) => a.plaid_item_id !== null || a.plaid_item_hash !== null,
  );
  const hasAnyAccounts = accounts.length > 0;

  return {
    // ── Spending — unlock with any account ──────────────────────────────
    "/transactions": hasAnyAccounts,
    "/budgets": hasAnyAccounts,
    "/categories": hasAnyAccounts,
    "/recurring-bills": hasLinkedAccounts,
    "/rules": hasAnyAccounts,
    // ── Analytics — unlock with any account ─────────────────────────────
    "/cash-flow": hasAnyAccounts,
    "/net-worth-timeline": hasAnyAccounts,
    "/reports": hasAnyAccounts,
    "/financial-health": hasAnyAccounts,
    "/pe-performance": accounts.some((a) => a.account_type === "private_equity"),
    "/rental-properties": hasRental,
    // ── Planning — goals/retirement/dashboard unlock with any account ────
    "/goals": hasAnyAccounts,
    "/retirement": hasAnyAccounts,
    "/debt-payoff": hasDebt,
    "/mortgage": hasMortgage,
    "/education": has529,
    "/estate-insurance": hasAnyAccounts,
    // investment-tools and pe-performance are advanced — gated separately
  };
}

/**
 * For locked (conditional=false) nav items, returns a tooltip hint.
 */
export function getLockedNavTooltip(path: string): string | undefined {
  const hints: Record<string, string> = {
    // Unlocked by any account
    "/transactions": "Add an account to unlock",
    "/budgets": "Add an account to unlock",
    "/categories": "Add an account to unlock",
    "/cash-flow": "Add an account to unlock",
    "/net-worth-timeline": "Add an account to unlock",
    "/reports": "Add an account to unlock",
    "/financial-health": "Add an account to unlock",
    "/goals": "Add an account to unlock",
    "/retirement": "Add an account to unlock",
    "/estate-insurance": "Add an account to unlock",
    "/rules": "Add an account to unlock",
    // Unlocked by specific account types
    "/recurring-bills": "Connect a bank account to unlock",
    "/pe-performance": "Add a private equity account to unlock PE performance metrics",
    "/rental-properties": "Add a rental property account to unlock",
    "/education": "Add a 529 account to unlock",
    "/debt-payoff": "Add a loan or credit card account to unlock",
    "/mortgage": "Add a mortgage account to unlock",
  };
  return hints[path];
}

/**
 * Hook — fetches accounts and user profile, returns computed nav defaults.
 * Both Layout and PreferencesPage call this so they always agree on what
 * "default visible" means for each path.
 */
export function useNavDefaults(
  selectedUserId?: string | null,
  memberEffectiveUserId?: string | null,
  isPartialMemberSelection?: boolean,
  matchesMemberFilter?: (itemUserId: string | null | undefined) => boolean,
) {
  // In combined view with member filter, use memberEffectiveUserId for the query
  // (undefined = fetch all, then filter client-side for partial selections)
  const queryUserId = selectedUserId ?? memberEffectiveUserId ?? null;

  const { data: rawAccounts = [], isLoading: accountsLoading } = useQuery<
    Account[]
  >({
    queryKey: ["accounts", queryUserId, isPartialMemberSelection ?? false],
    queryFn: async () => {
      const params = queryUserId ? { user_id: queryUserId } : {};
      const res = await api.get("/accounts", { params });
      return res.data;
    },
  });

  // When 2+ members are selected (partial), filter client-side by selected members
  const accounts =
    isPartialMemberSelection && matchesMemberFilter
      ? rawAccounts.filter((a) => matchesMemberFilter(a.user_id))
      : rawAccounts;

  const { data: userProfile } = useQuery({
    queryKey: ["user-profile-nav"],
    queryFn: async () => {
      const res = await api.get("/settings/profile");
      return res.data as { birth_year?: number | null };
    },
    staleTime: 30 * 60 * 1000,
  });

  // show_locked_nav preference — stored in localStorage, default true
  const [showLockedNav] = useLocalStorage<boolean>("show_locked_nav", true);

  const currentYear = new Date().getFullYear();
  const userAge = userProfile?.birth_year
    ? currentYear - userProfile.birth_year
    : null;

  const conditionalDefaults = buildConditionalDefaults(accounts);

  return {
    accounts,
    accountsLoading,
    userAge,
    conditionalDefaults,
    showLockedNav,
    /** True if path should be visible by default (no overrides applied) */
    getDefault: (path: string): boolean => conditionalDefaults[path] ?? true,
    /**
     * Determines visibility state for a nav item:
     * - "visible": show normally
     * - "locked": show dimmed with tooltip (when showLockedNav=true)
     * - "hidden": hide entirely (when showLockedNav=false and condition not met)
     */
    getNavState: (path: string): "visible" | "locked" | "hidden" => {
      const isConditional = conditionalDefaults[path] !== undefined;
      const conditionMet = conditionalDefaults[path] ?? true;
      if (!isConditional || conditionMet) return "visible";
      return showLockedNav ? "locked" : "hidden";
    },
  };
}
