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
 * After first account: Goals, Retirement Planner, My Dashboard + spending/analytics unlock.
 */
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
      {
        label: "Transactions",
        path: "/transactions",
        conditional: true,
        reason: "Shown once any account is added",
      },
      {
        label: "Budgets",
        path: "/budgets",
        conditional: true,
        reason: "Shown once any account is added",
      },
      {
        label: "Spending Categories",
        path: "/categories",
        conditional: true,
        reason: "Shown once any account is added",
      },
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
      {
        label: "Cash Flow",
        path: "/cash-flow",
        conditional: true,
        reason: "Shown once any account is added",
      },
      {
        label: "Net Worth Timeline",
        path: "/net-worth-timeline",
        conditional: true,
        reason: "Shown once any account is added",
      },
      {
        label: "Reports & Trends",
        path: "/reports",
        conditional: true,
        reason: "Shown once any account is added",
      },

      {
        label: "Financial Checkup",
        path: "/financial-health",
        conditional: true,
        reason: "Shown once any account is added",
      },
      {
        label: "PE Performance",
        path: "/pe-performance",
        conditional: true,
        reason: "Shown when you have private equity accounts",
      },
      {
        label: "Rental Properties",
        path: "/rental-properties",
        conditional: true,
        reason: "Shown when you have a rental property account",
      },
    ],
  },
  {
    group: "Planning",
    items: [
      // ── Beginner-first order: most universal items first ──
      {
        label: "Goals",
        path: "/goals",
        conditional: true,
        reason: "Shown once any account is added",
      },
      {
        label: "Retirement",
        path: "/retirement",
        conditional: true,
        reason: "Shown once any account is added",
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
        label: "Education",
        path: "/education",
        conditional: true,
        reason: "Shown when you have a 529 account",
      },
      // ── Consolidated hubs (always visible once accounts exist) ──
      {
        label: "Tax Center",
        path: "/tax-center",
        conditional: true,
        reason: "Shown once any account is added",
      },
      {
        label: "Life Planning",
        path: "/life-planning",
        conditional: true,
        reason: "Shown once any account is added",
      },
      // ── Advanced ──
      {
        label: "Calculators",
        path: "/investment-tools",
        advanced: true,
        reason: "Advanced — FIRE, loan modeler, HSA, bond ladder, what-if scenarios, and more",
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
  const hasRental = accounts.some((a) => a.is_rental_property);
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
    "/tax-center": hasAnyAccounts,
    "/life-planning": hasAnyAccounts,
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
    "/tax-center": "Add an account to unlock",
    "/life-planning": "Add an account to unlock",
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
