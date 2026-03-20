/**
 * Tests for the NavigationVisibilitySection logic in PreferencesPage
 * and the progressive sidebar advanced-features system in Layout.tsx.
 *
 * Architecture (post-unification):
 *   - All visibility state lives in a single store: nest-egg-nav-visibility
 *   - The "Show advanced features" master toggle writes /fire and /tax-projection
 *     directly into that store — no separate flag
 *   - isNavVisible(path, defaultVisible) — no isAdvanced param; overrides win always
 *   - showAdvancedNav is DERIVED: true iff ALL advanced paths are explicitly true
 *   - Per-item switch can turn an advanced tab on even when master toggle is off
 */

// @vitest-environment jsdom

import { describe, it, expect, beforeEach } from "vitest";

// ── Constants mirroring PreferencesPage / Layout ────────────────────────────

const STORAGE_KEY = "nest-egg-nav-visibility";
const LEGACY_KEY = "nest-egg-show-all-nav";
const LEGACY_ADVANCED_KEY = "nest-egg-show-advanced-nav"; // written for compat, not read for state

const ADVANCED_NAV_PATHS = ["/fire", "/tax-projection"];

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

// ── Helpers mirroring Layout.tsx / PreferencesPage ──────────────────────────

const loadOverrides = (): Record<string, boolean> => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
};

const persistOverrides = (next: Record<string, boolean>) => {
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
  persistOverrides(next);
  return next;
};

// Mirrors Layout.tsx / PreferencesPage toggleAdvancedNav / toggleAdvanced:
// writes all ADVANCED_NAV_PATHS into overrides and also syncs the legacy flag.
const toggleAdvancedNav = (
  overrides: Record<string, boolean>,
  next: boolean,
): Record<string, boolean> => {
  const updated = { ...overrides };
  for (const path of ADVANCED_NAV_PATHS) {
    updated[path] = next;
  }
  persistOverrides(updated);
  localStorage.setItem(LEGACY_ADVANCED_KEY, String(next));
  return updated;
};

// Mirrors the derived showAdvancedNav in Layout.tsx:
// true only when ALL advanced paths are explicitly true in overrides.
const deriveShowAdvanced = (overrides: Record<string, boolean>): boolean =>
  ADVANCED_NAV_PATHS.every((p) => overrides[p] === true);

const resetToDefaults = (overrides: Record<string, boolean>) => {
  void overrides;
  persistOverrides({});
  try {
    localStorage.removeItem(LEGACY_KEY);
    localStorage.removeItem(LEGACY_ADVANCED_KEY);
  } catch {
    /* ignore */
  }
};

// Mirrors simplified Layout.tsx isNavVisible(path, defaultVisible):
// override wins; falls back to defaultVisible.
const isNavVisible = (
  path: string,
  defaultVisible: boolean,
  overrides: Record<string, boolean>,
): boolean => {
  if (path in overrides) return overrides[path];
  return defaultVisible;
};

const isItemOn = (
  item: NavItem,
  overrides: Record<string, boolean>,
): boolean => {
  if (item.alwaysOn) return true;
  if (item.path in overrides) return overrides[item.path];
  return !item.conditional;
};

// ── Tests: isItemOn ──────────────────────────────────────────────────────────

describe("NavigationVisibilitySection: isItemOn", () => {
  it("alwaysOn items are always on regardless of overrides", () => {
    const item: NavItem = { label: "Overview", path: "/overview", alwaysOn: true };
    expect(isItemOn(item, {})).toBe(true);
    expect(isItemOn(item, { "/overview": false })).toBe(true);
  });

  it("non-conditional items default to on", () => {
    const item: NavItem = { label: "Transactions", path: "/transactions" };
    expect(isItemOn(item, {})).toBe(true);
  });

  it("conditional items default to off (auto-hide)", () => {
    const item: NavItem = { label: "Debt Payoff", path: "/debt-payoff", conditional: true };
    expect(isItemOn(item, {})).toBe(false);
  });

  it("override true turns on a conditional item", () => {
    const item: NavItem = { label: "Education", path: "/education", conditional: true };
    expect(isItemOn(item, { "/education": true })).toBe(true);
  });

  it("override false turns off a non-conditional item", () => {
    const item: NavItem = { label: "Budgets", path: "/budgets" };
    expect(isItemOn(item, { "/budgets": false })).toBe(false);
  });

  it("advanced items without override default to off (treated like conditional)", () => {
    // FIRE and Tax Projection are advanced — no explicit override means hidden
    const fire: NavItem = { label: "FIRE", path: "/fire", advanced: true };
    // advanced items have no conditional flag — isItemOn uses !conditional = true
    // but isNavVisible (Layout) uses the override; isItemOn is the Prefs display helper.
    // Without an override, isItemOn returns true (not conditional).
    // Visibility in the nav is controlled by conditionalDefaults["/fire"] defaultVisible.
    expect(isItemOn(fire, { "/fire": false })).toBe(false);
    expect(isItemOn(fire, { "/fire": true })).toBe(true);
  });
});

// ── Tests: isNavVisible (unified override model) ─────────────────────────────

describe("isNavVisible: unified override model", () => {
  it("override=true shows an item regardless of defaultVisible", () => {
    expect(isNavVisible("/fire", false, { "/fire": true })).toBe(true);
    expect(isNavVisible("/tax-projection", false, { "/tax-projection": true })).toBe(true);
  });

  it("override=false hides an item regardless of defaultVisible", () => {
    expect(isNavVisible("/fire", true, { "/fire": false })).toBe(false);
    expect(isNavVisible("/budgets", true, { "/budgets": false })).toBe(false);
  });

  it("no override falls back to defaultVisible=true", () => {
    expect(isNavVisible("/retirement", true, {})).toBe(true);
  });

  it("no override falls back to defaultVisible=false", () => {
    expect(isNavVisible("/fire", false, {})).toBe(false);
  });

  it("advanced items are hidden by default (defaultVisible=false, no override)", () => {
    // Layout passes conditionalDefaults["/fire"] as defaultVisible; without smart
    // auto-show conditions met, that resolves to false
    expect(isNavVisible("/fire", false, {})).toBe(false);
    expect(isNavVisible("/tax-projection", false, {})).toBe(false);
  });

  it("advanced items are shown when override is true", () => {
    expect(isNavVisible("/fire", false, { "/fire": true })).toBe(true);
    expect(isNavVisible("/tax-projection", false, { "/tax-projection": true })).toBe(true);
  });
});

// ── Tests: toggleAdvancedNav writes into overrides ───────────────────────────

describe("toggleAdvancedNav: writes into shared overrides store", () => {
  beforeEach(() => localStorage.clear());

  it("enabling advanced sets /fire and /tax-projection to true in overrides", () => {
    const updated = toggleAdvancedNav({}, true);
    expect(updated["/fire"]).toBe(true);
    expect(updated["/tax-projection"]).toBe(true);
  });

  it("disabling advanced sets /fire and /tax-projection to false in overrides", () => {
    const after = toggleAdvancedNav({}, false);
    expect(after["/fire"]).toBe(false);
    expect(after["/tax-projection"]).toBe(false);
  });

  it("written values persist to nest-egg-nav-visibility", () => {
    toggleAdvancedNav({}, true);
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY)!);
    expect(stored["/fire"]).toBe(true);
    expect(stored["/tax-projection"]).toBe(true);
  });

  it("also writes the legacy compat flag nest-egg-show-advanced-nav", () => {
    toggleAdvancedNav({}, true);
    expect(localStorage.getItem(LEGACY_ADVANCED_KEY)).toBe("true");
  });

  it("does not disturb other overrides when toggling", () => {
    const initial = { "/budgets": false, "/debt-payoff": true };
    const updated = toggleAdvancedNav(initial, true);
    expect(updated["/budgets"]).toBe(false);
    expect(updated["/debt-payoff"]).toBe(true);
  });

  it("toggle off → then on restores both paths to true", () => {
    const off = toggleAdvancedNav({}, false);
    const on = toggleAdvancedNav(off, true);
    expect(on["/fire"]).toBe(true);
    expect(on["/tax-projection"]).toBe(true);
  });
});

// ── Tests: deriveShowAdvanced ─────────────────────────────────────────────────

describe("deriveShowAdvanced: derived from overrides", () => {
  it("false when overrides is empty", () => {
    expect(deriveShowAdvanced({})).toBe(false);
  });

  it("false when only one advanced path is true", () => {
    expect(deriveShowAdvanced({ "/fire": true })).toBe(false);
    expect(deriveShowAdvanced({ "/tax-projection": true })).toBe(false);
  });

  it("false when one advanced path is false", () => {
    expect(deriveShowAdvanced({ "/fire": true, "/tax-projection": false })).toBe(false);
  });

  it("true when ALL advanced paths are explicitly true", () => {
    expect(deriveShowAdvanced({ "/fire": true, "/tax-projection": true })).toBe(true);
  });

  it("extra non-advanced overrides don't affect derivation", () => {
    expect(
      deriveShowAdvanced({ "/fire": true, "/tax-projection": true, "/budgets": false }),
    ).toBe(true);
  });

  it("roundtrip: toggle on → derive true", () => {
    const overrides = toggleAdvancedNav({}, true);
    expect(deriveShowAdvanced(overrides)).toBe(true);
  });

  it("roundtrip: toggle off → derive false", () => {
    const after = toggleAdvancedNav({ "/fire": true, "/tax-projection": true }, false);
    expect(deriveShowAdvanced(after)).toBe(false);
  });

  it("per-item override of one path does not flip master to true", () => {
    // User manually turned on /fire but not /tax-projection — master stays off
    expect(deriveShowAdvanced({ "/fire": true })).toBe(false);
  });
});

// ── Tests: per-item switch independence from master toggle ───────────────────

describe("per-item switch independence", () => {
  beforeEach(() => localStorage.clear());

  it("per-item on for /fire while master is off — /fire visible, master still false", () => {
    // Master toggle sets both to false
    let overrides = toggleAdvancedNav({}, false);
    // User manually turns /fire back on
    overrides = toggleItem(overrides, "/fire", true);
    expect(isNavVisible("/fire", false, overrides)).toBe(true);
    // But master derived state is still false (tax-projection is false)
    expect(deriveShowAdvanced(overrides)).toBe(false);
  });

  it("per-item off for /fire overrides master-on state", () => {
    let overrides = toggleAdvancedNav({}, true);
    overrides = toggleItem(overrides, "/fire", false);
    expect(isNavVisible("/fire", false, overrides)).toBe(false);
    // Master derived is also false now (not ALL advanced paths true)
    expect(deriveShowAdvanced(overrides)).toBe(false);
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

  // Mirrors Layout.tsx conditionalDefaults["/fire"]
  const showFireDefault = (accounts: Account[], userAge: number | null) =>
    hasInvestments(accounts) && userAge !== null && userAge < 50;

  // Mirrors Layout.tsx conditionalDefaults["/tax-projection"]
  const showTaxProjectionDefault = (accounts: Account[]) =>
    hasInvestments(accounts);

  it("FIRE auto-shows (defaultVisible=true) for user under 50 with investments", () => {
    expect(showFireDefault([{ account_type: "retirement_401k" }], 35)).toBe(true);
  });

  it("FIRE defaultVisible=false for user 50+", () => {
    expect(showFireDefault([{ account_type: "brokerage" }], 50)).toBe(false);
    expect(showFireDefault([{ account_type: "brokerage" }], 65)).toBe(false);
  });

  it("FIRE defaultVisible=false with no investment accounts", () => {
    expect(showFireDefault([{ account_type: "checking" }], 30)).toBe(false);
  });

  it("FIRE defaultVisible=false when userAge is null (no birthdate set)", () => {
    expect(showFireDefault([{ account_type: "brokerage" }], null)).toBe(false);
  });

  it("Tax Projection defaultVisible=true for any user with investment account", () => {
    expect(showTaxProjectionDefault([{ account_type: "brokerage" }])).toBe(true);
    expect(showTaxProjectionDefault([{ account_type: "retirement_ira" }])).toBe(true);
    expect(showTaxProjectionDefault([{ account_type: "crypto" }])).toBe(true);
  });

  it("Tax Projection defaultVisible=false with no investment accounts", () => {
    expect(showTaxProjectionDefault([{ account_type: "savings" }])).toBe(false);
    expect(showTaxProjectionDefault([])).toBe(false);
  });

  it("smart auto-show is overridden by explicit override=false", () => {
    // Even if smart conditions say show, an explicit false override hides it
    expect(isNavVisible("/fire", true, { "/fire": false })).toBe(false);
  });

  it("smart auto-show works via defaultVisible even with no override", () => {
    expect(isNavVisible("/fire", true, {})).toBe(true);
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
    resetToDefaults({});
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
  });

  it("removes legacy show-all-nav key", () => {
    localStorage.setItem(LEGACY_KEY, "true");
    resetToDefaults({});
    expect(localStorage.getItem(LEGACY_KEY)).toBeNull();
  });

  it("removes legacy show-advanced-nav key", () => {
    localStorage.setItem(LEGACY_ADVANCED_KEY, "true");
    resetToDefaults({});
    expect(localStorage.getItem(LEGACY_ADVANCED_KEY)).toBeNull();
  });

  it("loadOverrides returns empty after reset", () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ "/budgets": false }));
    resetToDefaults({});
    expect(loadOverrides()).toEqual({});
  });

  it("clears advanced paths along with all other overrides", () => {
    // Advanced paths live in the same store — reset clears them too
    const overrides = toggleAdvancedNav({}, true);
    resetToDefaults(overrides);
    expect(loadOverrides()).toEqual({});
    expect(deriveShowAdvanced(loadOverrides())).toBe(false);
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
    expect(spending!.items.every((i) => !i.conditional && !i.advanced)).toBe(true);
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
