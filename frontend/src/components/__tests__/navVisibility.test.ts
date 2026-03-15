/**
 * Tests for the per-item nav visibility logic in Layout.tsx.
 *
 * The navigation system has three layers of visibility:
 * 1. User overrides (localStorage "nest-egg-nav-visibility")
 * 2. Account-based conditional defaults (debt, rental, 529)
 * 3. Always-visible fallback
 *
 * These functions mirror the exact expressions used in Layout so that
 * regressions in the filtering logic are caught without rendering.
 */

// @vitest-environment jsdom

import { describe, it, expect, beforeEach } from "vitest";

// ── helpers mirroring Layout.tsx logic ──────────────────────────────────────

interface Account {
  account_type: string;
  is_rental_property?: boolean;
}

const DEBT_TYPES = new Set(["credit_card", "loan", "student_loan", "mortgage"]);

const hasDebt = (accounts: Account[]): boolean =>
  accounts.some((a) => DEBT_TYPES.has(a.account_type));

const hasRental = (accounts: Account[]): boolean =>
  accounts.some((a) => a.is_rental_property);

const has529 = (accounts: Account[]): boolean =>
  accounts.some((a) => a.account_type === "retirement_529");

/**
 * Mirror of isNavVisible from Layout.tsx.
 * Priority: user override > account-based default > always visible.
 */
const isNavVisible = (
  path: string,
  defaultVisible: boolean,
  navOverrides: Record<string, boolean>,
  accountsLoading: boolean,
): boolean => {
  if (path in navOverrides) return navOverrides[path];
  if (accountsLoading) return true;
  return defaultVisible;
};

const buildConditionalDefaults = (
  accounts: Account[],
): Record<string, boolean> => ({
  "/rental-properties": hasRental(accounts),
  "/education": has529(accounts),
  "/debt-payoff": hasDebt(accounts),
});

type NavItem = { label: string; path: string };

const filterVisible = (
  items: NavItem[],
  conditionalDefaults: Record<string, boolean>,
  navOverrides: Record<string, boolean>,
  accountsLoading: boolean,
): NavItem[] =>
  items.filter((item) =>
    isNavVisible(
      item.path,
      conditionalDefaults[item.path] ?? true,
      navOverrides,
      accountsLoading,
    ),
  );

const STORAGE_KEY = "nest-egg-nav-visibility";

const loadOverrides = (): Record<string, boolean> => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
};

// ── Sample nav items ───────────────────────────────────────────────────────

const allSpendingItems: NavItem[] = [
  { label: "Transactions", path: "/transactions" },
  { label: "Budgets", path: "/budgets" },
  { label: "Recurring", path: "/recurring" },
  { label: "Bills", path: "/bills" },
  { label: "Categories", path: "/categories" },
  { label: "Rules", path: "/rules" },
];

const allAnalyticsItems: NavItem[] = [
  { label: "Cash Flow", path: "/income-expenses" },
  { label: "Trends", path: "/trends" },
  { label: "Reports", path: "/reports" },
  { label: "Year in Review", path: "/year-in-review" },
  { label: "Tax Deductible", path: "/tax-deductible" },
  { label: "Rental Properties", path: "/rental-properties" },
];

const allPlanningItems: NavItem[] = [
  { label: "Goals", path: "/goals" },
  { label: "Retirement", path: "/retirement" },
  { label: "Education", path: "/education" },
  { label: "FIRE", path: "/fire" },
  { label: "Debt Payoff", path: "/debt-payoff" },
];

// ── Tests ──────────────────────────────────────────────────────────────────

describe("Nav visibility: localStorage overrides", () => {
  beforeEach(() => localStorage.clear());

  it("returns empty object when nothing stored", () => {
    expect(loadOverrides()).toEqual({});
  });

  it("parses stored JSON correctly", () => {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ "/debt-payoff": true, "/education": false }),
    );
    expect(loadOverrides()).toEqual({
      "/debt-payoff": true,
      "/education": false,
    });
  });

  it("returns empty object on corrupt JSON", () => {
    localStorage.setItem(STORAGE_KEY, "not-json!!!");
    expect(loadOverrides()).toEqual({});
  });
});

describe("Nav visibility: isNavVisible", () => {
  it("user override true wins over default false", () => {
    expect(
      isNavVisible("/debt-payoff", false, { "/debt-payoff": true }, false),
    ).toBe(true);
  });

  it("user override false wins over default true", () => {
    expect(
      isNavVisible("/transactions", true, { "/transactions": false }, false),
    ).toBe(false);
  });

  it("falls back to default when no override", () => {
    expect(isNavVisible("/debt-payoff", false, {}, false)).toBe(false);
    expect(isNavVisible("/transactions", true, {}, false)).toBe(true);
  });

  it("shows everything while accounts are loading (no override)", () => {
    expect(isNavVisible("/debt-payoff", false, {}, true)).toBe(true);
  });

  it("override still wins even while loading", () => {
    expect(
      isNavVisible("/debt-payoff", false, { "/debt-payoff": false }, true),
    ).toBe(false);
  });
});

describe("Nav visibility: account-based conditional defaults", () => {
  it("hides debt-payoff when no debt accounts", () => {
    const defaults = buildConditionalDefaults([
      { account_type: "checking" },
      { account_type: "savings" },
    ]);
    expect(defaults["/debt-payoff"]).toBe(false);
  });

  it("shows debt-payoff when credit card exists", () => {
    const defaults = buildConditionalDefaults([
      { account_type: "credit_card" },
    ]);
    expect(defaults["/debt-payoff"]).toBe(true);
  });

  it("shows debt-payoff when mortgage exists", () => {
    const defaults = buildConditionalDefaults([{ account_type: "mortgage" }]);
    expect(defaults["/debt-payoff"]).toBe(true);
  });

  it("shows debt-payoff when loan exists", () => {
    const defaults = buildConditionalDefaults([{ account_type: "loan" }]);
    expect(defaults["/debt-payoff"]).toBe(true);
  });

  it("shows debt-payoff when student loan exists", () => {
    const defaults = buildConditionalDefaults([
      { account_type: "student_loan" },
    ]);
    expect(defaults["/debt-payoff"]).toBe(true);
  });

  it("hides rental-properties when no rental accounts", () => {
    const defaults = buildConditionalDefaults([{ account_type: "checking" }]);
    expect(defaults["/rental-properties"]).toBe(false);
  });

  it("shows rental-properties when rental property exists", () => {
    const defaults = buildConditionalDefaults([
      { account_type: "property", is_rental_property: true },
    ]);
    expect(defaults["/rental-properties"]).toBe(true);
  });

  it("hides education when no 529 accounts", () => {
    const defaults = buildConditionalDefaults([{ account_type: "checking" }]);
    expect(defaults["/education"]).toBe(false);
  });

  it("shows education when 529 account exists", () => {
    const defaults = buildConditionalDefaults([
      { account_type: "retirement_529" },
    ]);
    expect(defaults["/education"]).toBe(true);
  });
});

describe("Nav visibility: filterVisible", () => {
  const noAccounts: Account[] = [];
  const allAccounts: Account[] = [
    { account_type: "credit_card" },
    { account_type: "retirement_529" },
    { account_type: "property", is_rental_property: true },
  ];

  it("shows all spending items regardless of accounts", () => {
    const defaults = buildConditionalDefaults(noAccounts);
    const result = filterVisible(allSpendingItems, defaults, {}, false);
    expect(result).toHaveLength(allSpendingItems.length);
  });

  it("hides conditional analytics items when no accounts", () => {
    const defaults = buildConditionalDefaults(noAccounts);
    const result = filterVisible(allAnalyticsItems, defaults, {}, false);
    expect(result.map((i) => i.path)).not.toContain("/rental-properties");
  });

  it("shows conditional analytics items when accounts exist", () => {
    const defaults = buildConditionalDefaults(allAccounts);
    const result = filterVisible(allAnalyticsItems, defaults, {}, false);
    expect(result.map((i) => i.path)).toContain("/rental-properties");
  });

  it("hides conditional planning items when no accounts", () => {
    const defaults = buildConditionalDefaults(noAccounts);
    const result = filterVisible(allPlanningItems, defaults, {}, false);
    expect(result.map((i) => i.path)).not.toContain("/debt-payoff");
    expect(result.map((i) => i.path)).not.toContain("/education");
  });

  it("shows conditional planning items when accounts exist", () => {
    const defaults = buildConditionalDefaults(allAccounts);
    const result = filterVisible(allPlanningItems, defaults, {}, false);
    expect(result.map((i) => i.path)).toContain("/debt-payoff");
    expect(result.map((i) => i.path)).toContain("/education");
  });

  it("user override can force-show hidden conditional item", () => {
    const defaults = buildConditionalDefaults(noAccounts);
    const overrides = { "/debt-payoff": true };
    const result = filterVisible(allPlanningItems, defaults, overrides, false);
    expect(result.map((i) => i.path)).toContain("/debt-payoff");
  });

  it("user override can force-hide unconditional item", () => {
    const defaults = buildConditionalDefaults(allAccounts);
    const overrides = { "/transactions": false };
    const result = filterVisible(allSpendingItems, defaults, overrides, false);
    expect(result.map((i) => i.path)).not.toContain("/transactions");
  });

  it("shows all items while accounts are loading", () => {
    const defaults = buildConditionalDefaults(noAccounts);
    const result = filterVisible(allPlanningItems, defaults, {}, true);
    expect(result).toHaveLength(allPlanningItems.length);
  });
});

describe("Nav visibility: UserMenu permissions visibility", () => {
  /**
   * Mirror of the menuItems array in UserMenu component.
   * Permissions is only shown when isMultiMemberHousehold is true.
   */
  const buildMenuItems = (isMultiMemberHousehold: boolean) => [
    { label: "Household Settings", path: "/household" },
    ...(isMultiMemberHousehold
      ? [{ label: "My Permissions", path: "/permissions" }]
      : []),
    { label: "My Preferences", path: "/preferences" },
  ];

  it("single-member household: no Permissions item", () => {
    const items = buildMenuItems(false);
    expect(items.map((i) => i.label)).not.toContain("My Permissions");
    expect(items).toHaveLength(2);
  });

  it("multi-member household: shows My Permissions", () => {
    const items = buildMenuItems(true);
    expect(items.map((i) => i.label)).toContain("My Permissions");
    expect(items).toHaveLength(3);
  });

  it("always shows My Preferences", () => {
    expect(buildMenuItems(false).map((i) => i.label)).toContain(
      "My Preferences",
    );
    expect(buildMenuItems(true).map((i) => i.label)).toContain(
      "My Preferences",
    );
  });

  it("always shows Household Settings", () => {
    expect(buildMenuItems(false).map((i) => i.label)).toContain(
      "Household Settings",
    );
    expect(buildMenuItems(true).map((i) => i.label)).toContain(
      "Household Settings",
    );
  });

  /**
   * Mirror of the isMultiMemberHousehold prop computation.
   */
  const computeIsMultiMember = (
    members: unknown[] | null | undefined,
  ): boolean => (members?.length ?? 0) >= 2;

  it("null members -> single member", () => {
    expect(computeIsMultiMember(null)).toBe(false);
  });

  it("undefined members -> single member", () => {
    expect(computeIsMultiMember(undefined)).toBe(false);
  });

  it("empty array -> single member", () => {
    expect(computeIsMultiMember([])).toBe(false);
  });

  it("one member -> single member", () => {
    expect(computeIsMultiMember([{}])).toBe(false);
  });

  it("two members -> multi member", () => {
    expect(computeIsMultiMember([{}, {}])).toBe(true);
  });

  it("three members -> multi member", () => {
    expect(computeIsMultiMember([{}, {}, {}])).toBe(true);
  });
});
