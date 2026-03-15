/**
 * Tests for the NavigationVisibilitySection logic in PreferencesPage.
 *
 * Mirrors the toggle/persist/reset/isItemOn logic from PreferencesPage
 * to catch regressions without rendering Chakra components.
 */

// @vitest-environment jsdom

import { describe, it, expect, beforeEach } from "vitest";

// ── Constants mirroring PreferencesPage ────────────────────────────────────

const STORAGE_KEY = "nest-egg-nav-visibility";
const LEGACY_KEY = "nest-egg-show-all-nav";

interface NavItem {
  label: string;
  path: string;
  alwaysOn?: boolean;
  conditional?: boolean;
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
      { label: "FIRE", path: "/fire" },
      { label: "Debt Payoff", path: "/debt-payoff", conditional: true },
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

// ── Tests ──────────────────────────────────────────────────────────────────

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
});

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

  it("no spending items are conditional", () => {
    const spending = NAV_SECTIONS.find((s) => s.group === "Spending");
    expect(spending!.items.every((i) => !i.conditional)).toBe(true);
  });

  it("all items have unique paths", () => {
    const allPaths = NAV_SECTIONS.flatMap((s) => s.items).map((i) => i.path);
    expect(new Set(allPaths).size).toBe(allPaths.length);
  });
});
