/**
 * Tests for the NavigationVisibilitySection logic in PreferencesPage
 * and the progressive sidebar advanced-features system in Layout.tsx.
 *
 * Mirrors the toggle/persist/reset/isItemOn/isNavVisible logic to catch
 * regressions without rendering Chakra components.
 */

// @vitest-environment jsdom

import { describe, it, expect, beforeEach } from "vitest";

// ── Constants mirroring PreferencesPage / Layout ────────────────────────────

const STORAGE_KEY = "nest-egg-nav-visibility";
const LEGACY_KEY = "nest-egg-show-all-nav";
const ADVANCED_KEY = "nest-egg-show-advanced-nav";

interface NavItem {
  label: string;
  path: string;
  alwaysOn?: boolean;
  conditional?: boolean;
  advanced?: boolean;
}

const NAV_SECTIONS: { group: string; items: NavItem[] }[] = [
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
      { label: "Recurring", path: "/recurring" },
      { label: "Bills", path: "/bills" },
      { label: "Categories", path: "/categories" },
      { label: "Rules", path: "/rules" },
    ],
  },
  {
    group: "Analytics",
    items: [
      { label: "Cash Flow", path: "/income-expenses" },
      { label: "Trends", path: "/trends" },
      { label: "Reports", path: "/reports" },
      { label: "Year in Review", path: "/year-in-review" },
      { label: "Tax Deductible", path: "/tax-deductible" },
      {
        label: "Rental Properties",
        path: "/rental-properties",
        conditional: true,
      },
    ],
  },
  {
    group: "Planning",
    items: [
      { label: "Goals", path: "/goals" },
      { label: "Retirement", path: "/retirement" },
      { label: "Education", path: "/education", conditional: true },
      { label: "FIRE", path: "/fire", advanced: true },
      { label: "Debt Payoff", path: "/debt-payoff", conditional: true },
      { label: "Tax Projection", path: "/tax-projection", advanced: true },
    ],
  },
];

// ── Helpers mirroring NavigationVisibilitySection ──────────────────────────

const loadOverrides = (): Record<string, boolean> => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
};

const loadShowAdvanced = (): boolean => {
  try {
    return localStorage.getItem(ADVANCED_KEY) === "true";
  } catch {
    return false;
  }
};

const persistAdvanced = (next: boolean) => {
  localStorage.setItem(ADVANCED_KEY, String(next));
};

const persist = (next: Record<string, boolean>) => {
  if (Object.keys(next).length === 0) {
    localStorage.removeItem(STORAGE_KEY);
  } else {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  }
};

const toggleItem = (
  overrides: Record<string, boolean>,
  path: string,
  checked: boolean,
): Record<string, boolean> => {
  const next = { ...overrides, [path]: checked };
  persist(next);
  return next;
};

const resetToDefaults = () => {
  persist({});
  try {
    localStorage.removeItem(LEGACY_KEY);
  } catch {
    /* ignore */
  }
};

const isItemOn = (
  item: NavItem,
  overrides: Record<string, boolean>,
): boolean => {
  if (item.alwaysOn) return true;
  if (item.path in overrides) return overrides[item.path];
  return !item.conditional;
};

// Mirrors Layout.tsx isNavVisible(path, defaultVisible, isAdvanced)
const isNavVisible = (
  path: string,
  defaultVisible: boolean,
  isAdvanced: boolean,
  overrides: Record<string, boolean>,
  showAdvanced: boolean,
): boolean => {
  if (path in overrides) return overrides[path];
  if (isAdvanced && !showAdvanced) return false;
  return defaultVisible;
};

// ── Tests: isItemOn ──────────────────────────────────────────────────────────

describe("NavigationVisibilitySection: isItemOn", () => {
  it("alwaysOn items are always on regardless of overrides", () => {
    const item: NavItem = {
      label: "Overview",
      path: "/overview",
      alwaysOn: true,
    };
    expect(isItemOn(item, {})).toBe(true);
    expect(isItemOn(item, { "/overview": false })).toBe(true);
  });

  it("non-conditional items default to on", () => {
    const item: NavItem = { label: "Transactions", path: "/transactions" };
    expect(isItemOn(item, {})).toBe(true);
  });

  it("conditional items default to off (auto-hide)", () => {
    const item: NavItem = {
      label: "Debt Payoff",
      path: "/debt-payoff",
      conditional: true,
    };
    expect(isItemOn(item, {})).toBe(false);
  });

  it("override true turns on a conditional item", () => {
    const item: NavItem = {
      label: "Education",
      path: "/education",
      conditional: true,
    };
    expect(isItemOn(item, { "/education": true })).toBe(true);
  });

  it("override false turns off a non-conditional item", () => {
    const item: NavItem = { label: "Budgets", path: "/budgets" };
    expect(isItemOn(item, { "/budgets": false })).toBe(false);
  });
});

// ── Tests: isNavVisible (advanced-feature gating) ───────────────────────────

describe("isNavVisible: advanced feature gating", () => {
  it("FIRE is hidden by default when advanced toggle is off", () => {
    expect(isNavVisible("/fire", true, true, {}, false)).toBe(false);
  });

  it("Tax Projection is hidden by default when advanced toggle is off", () => {
    expect(isNavVisible("/tax-projection", true, true, {}, false)).toBe(false);
  });

  it("FIRE is shown when advanced toggle is on", () => {
    expect(isNavVisible("/fire", true, true, {}, true)).toBe(true);
  });

  it("Tax Projection is shown when advanced toggle is on", () => {
    expect(isNavVisible("/tax-projection", true, true, {}, true)).toBe(true);
  });

  it("per-item override=true shows an advanced item even when toggle is off", () => {
    expect(isNavVisible("/fire", true, true, { "/fire": true }, false)).toBe(
      true,
    );
  });

  it("per-item override=false hides a non-advanced item", () => {
    expect(
      isNavVisible("/budgets", true, false, { "/budgets": false }, false),
    ).toBe(false);
  });

  it("non-advanced items are unaffected by the advanced toggle", () => {
    expect(isNavVisible("/retirement", true, false, {}, false)).toBe(true);
    expect(isNavVisible("/retirement", true, false, {}, true)).toBe(true);
  });

  it("conditional default=false item stays hidden even with advanced toggle on", () => {
    // e.g. /debt-payoff when user has no debt — defaultVisible=false, isAdvanced=false
    expect(isNavVisible("/debt-payoff", false, false, {}, true)).toBe(false);
  });
});

// ── Tests: smart auto-show rules ─────────────────────────────────────────────

describe("smart auto-show rules for advanced items", () => {
  type Account = { account_type: string };

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

  const hasInvestments = (accounts: Account[]) =>
    accounts.some((a) => INVESTMENT_TYPES.has(a.account_type));

  const showFireSmart = (accounts: Account[], userAge: number | null) =>
    hasInvestments(accounts) && userAge !== null && userAge < 50;

  const showTaxProjectionSmart = (accounts: Account[]) =>
    hasInvestments(accounts);

  it("FIRE auto-shows for user under 50 with investment account", () => {
    const accounts: Account[] = [{ account_type: "retirement_401k" }];
    expect(showFireSmart(accounts, 35)).toBe(true);
  });

  it("FIRE does NOT auto-show for user 50 or older", () => {
    const accounts: Account[] = [{ account_type: "brokerage" }];
    expect(showFireSmart(accounts, 50)).toBe(false);
    expect(showFireSmart(accounts, 65)).toBe(false);
  });

  it("FIRE does NOT auto-show when user has no investment accounts", () => {
    const accounts: Account[] = [{ account_type: "checking" }];
    expect(showFireSmart(accounts, 30)).toBe(false);
  });

  it("FIRE does NOT auto-show when userAge is null (no birthdate)", () => {
    const accounts: Account[] = [{ account_type: "brokerage" }];
    expect(showFireSmart(accounts, null)).toBe(false);
  });

  it("Tax Projection auto-shows for any user with investment account", () => {
    expect(showTaxProjectionSmart([{ account_type: "brokerage" }])).toBe(true);
    expect(showTaxProjectionSmart([{ account_type: "retirement_ira" }])).toBe(
      true,
    );
  });

  it("Tax Projection does NOT auto-show with no investment accounts", () => {
    expect(showTaxProjectionSmart([{ account_type: "savings" }])).toBe(false);
    expect(showTaxProjectionSmart([])).toBe(false);
  });

  it("crypto account triggers investment detection", () => {
    expect(showTaxProjectionSmart([{ account_type: "crypto" }])).toBe(true);
  });
});

// ── Tests: advanced toggle persist/read ─────────────────────────────────────

describe("advanced toggle: persist and read", () => {
  beforeEach(() => localStorage.clear());

  it("defaults to false when key is absent", () => {
    expect(loadShowAdvanced()).toBe(false);
  });

  it("persisting true stores 'true' string", () => {
    persistAdvanced(true);
    expect(localStorage.getItem(ADVANCED_KEY)).toBe("true");
  });

  it("persisting false stores 'false' string", () => {
    persistAdvanced(false);
    expect(localStorage.getItem(ADVANCED_KEY)).toBe("false");
  });

  it("loadShowAdvanced reads back true correctly", () => {
    persistAdvanced(true);
    expect(loadShowAdvanced()).toBe(true);
  });

  it("loadShowAdvanced reads back false correctly", () => {
    persistAdvanced(false);
    expect(loadShowAdvanced()).toBe(false);
  });

  it("only 'true' string is truthy — other values return false", () => {
    localStorage.setItem(ADVANCED_KEY, "1");
    expect(loadShowAdvanced()).toBe(false);
    localStorage.setItem(ADVANCED_KEY, "yes");
    expect(loadShowAdvanced()).toBe(false);
  });
});

// ── Tests: toggle and persist (per-item overrides) ───────────────────────────

describe("NavigationVisibilitySection: toggle and persist", () => {
  beforeEach(() => localStorage.clear());

  it("toggling stores value in localStorage", () => {
    toggleItem({}, "/debt-payoff", true);
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY)!);
    expect(stored["/debt-payoff"]).toBe(true);
  });

  it("multiple toggles accumulate", () => {
    const first = toggleItem({}, "/debt-payoff", true);
    toggleItem(first, "/education", false);
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY)!);
    expect(stored).toEqual({ "/debt-payoff": true, "/education": false });
  });

  it("toggling same item updates the value", () => {
    const first = toggleItem({}, "/budgets", false);
    toggleItem(first, "/budgets", true);
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY)!);
    expect(stored["/budgets"]).toBe(true);
  });
});

// ── Tests: reset to defaults ─────────────────────────────────────────────────

describe("NavigationVisibilitySection: reset to defaults", () => {
  beforeEach(() => localStorage.clear());

  it("clears all overrides from localStorage", () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ "/debt-payoff": true }));
    resetToDefaults();
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
  });

  it("also removes legacy key", () => {
    localStorage.setItem(LEGACY_KEY, "true");
    resetToDefaults();
    expect(localStorage.getItem(LEGACY_KEY)).toBeNull();
  });

  it("loadOverrides returns empty after reset", () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ "/budgets": false }));
    resetToDefaults();
    expect(loadOverrides()).toEqual({});
  });

  it("does NOT clear the advanced toggle — that's a separate preference", () => {
    persistAdvanced(true);
    resetToDefaults();
    expect(loadShowAdvanced()).toBe(true);
  });
});

// ── Tests: NAV_SECTIONS structure ────────────────────────────────────────────

describe("NavigationVisibilitySection: NAV_SECTIONS structure", () => {
  it("has 4 groups", () => {
    expect(NAV_SECTIONS).toHaveLength(4);
  });

  it("all top-level items are alwaysOn", () => {
    const topLevel = NAV_SECTIONS.find((s) => s.group === "Top Level");
    expect(topLevel).toBeDefined();
    for (const item of topLevel!.items) {
      expect(item.alwaysOn).toBe(true);
    }
  });

  it("conditional items are exactly: rental-properties, education, debt-payoff", () => {
    const conditionalPaths = NAV_SECTIONS.flatMap((s) => s.items)
      .filter((i) => i.conditional)
      .map((i) => i.path)
      .sort();
    expect(conditionalPaths).toEqual([
      "/debt-payoff",
      "/education",
      "/rental-properties",
    ]);
  });

  it("advanced items are exactly: /fire and /tax-projection", () => {
    const advancedPaths = NAV_SECTIONS.flatMap((s) => s.items)
      .filter((i) => i.advanced)
      .map((i) => i.path)
      .sort();
    expect(advancedPaths).toEqual(["/fire", "/tax-projection"]);
  });

  it("no spending items are conditional or advanced", () => {
    const spending = NAV_SECTIONS.find((s) => s.group === "Spending");
    expect(spending!.items.every((i) => !i.conditional && !i.advanced)).toBe(
      true,
    );
  });

  it("all items have unique paths", () => {
    const allPaths = NAV_SECTIONS.flatMap((s) => s.items).map((i) => i.path);
    expect(new Set(allPaths).size).toBe(allPaths.length);
  });

  it("FIRE and Tax Projection are in Planning group", () => {
    const planning = NAV_SECTIONS.find((s) => s.group === "Planning");
    const paths = planning!.items.map((i) => i.path);
    expect(paths).toContain("/fire");
    expect(paths).toContain("/tax-projection");
  });
});
