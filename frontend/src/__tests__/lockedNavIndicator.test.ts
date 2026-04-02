/**
 * Tests for locked nav indicator (UX improvement A).
 *
 * When a user has no accounts, conditional nav items (Transactions, Goals,
 * Tax Center, etc.) show dimmed with a lock icon and "Add an account to unlock"
 * tooltip — so beginners know these features exist and how to get to them.
 *
 * Key rule: locked items appear when showLockedNav=true (default); they are
 * hidden entirely when showLockedNav=false (user preference "Hide locked items").
 */

import { describe, it, expect } from "vitest";
import { getLockedNavTooltip } from "../hooks/useNavDefaults";

// ── getLockedNavTooltip ───────────────────────────────────────────────────────

describe("getLockedNavTooltip", () => {
  it("returns a hint for paths locked by any account", () => {
    const paths = [
      "/transactions",
      "/budgets",
      "/categories",
      "/cash-flow",
      "/net-worth-timeline",
      "/reports",
      "/financial-health",
      "/goals",
      "/retirement",
      "/tax-center",
      "/estate-insurance",
      "/rules",
    ];
    for (const path of paths) {
      const tooltip = getLockedNavTooltip(path);
      expect(tooltip, `Missing tooltip for ${path}`).toBeTruthy();
      expect(tooltip).toContain("account");
    }
  });

  it("returns a hint for paths locked by specific account types", () => {
    expect(getLockedNavTooltip("/pe-performance")).toContain("private equity");
    expect(getLockedNavTooltip("/rental-properties")).toContain("rental");
    expect(getLockedNavTooltip("/education")).toContain("529");
    expect(getLockedNavTooltip("/debt-payoff")).toContain("loan");
    expect(getLockedNavTooltip("/mortgage")).toContain("mortgage");
  });

  it("returns undefined for always-on paths (Overview, Investments, etc.)", () => {
    expect(getLockedNavTooltip("/overview")).toBeUndefined();
    expect(getLockedNavTooltip("/investments")).toBeUndefined();
    expect(getLockedNavTooltip("/accounts")).toBeUndefined();
    expect(getLockedNavTooltip("/calendar")).toBeUndefined();
  });

  it("returns undefined for unknown paths", () => {
    expect(getLockedNavTooltip("/nonexistent")).toBeUndefined();
  });
});

// ── filterVisible (locked state logic) ───────────────────────────────────────

type NavState = "visible" | "locked" | "hidden";

interface NavItem {
  label: string;
  path: string;
  tooltip?: string;
  advanced?: boolean;
}

interface FilteredItem {
  label: string;
  path: string;
  tooltip?: string;
  locked?: boolean;
  lockedTooltip?: string;
}

/**
 * Mirrors the filterVisible function in Layout.tsx.
 * Pure function version for testing — no React hooks needed.
 */
function filterVisible(
  items: NavItem[],
  opts: {
    getNavState: (path: string) => NavState;
    showLockedNav: boolean;
    showAdvancedNav: boolean;
    navOverrides: Record<string, boolean>;
  },
): FilteredItem[] {
  const result: FilteredItem[] = [];
  for (const item of items) {
    if (item.advanced && !opts.showAdvancedNav && !(item.path in opts.navOverrides && opts.navOverrides[item.path])) {
      continue;
    }
    const navState = opts.getNavState(item.path);
    if (item.path in opts.navOverrides) {
      if (opts.navOverrides[item.path]) result.push(item);
      continue;
    }
    if (navState === "visible") {
      result.push(item);
    } else if (navState === "locked" && opts.showLockedNav) {
      result.push({ ...item, locked: true, lockedTooltip: getLockedNavTooltip(item.path) });
    }
  }
  return result;
}

const SPENDING_ITEMS: NavItem[] = [
  { label: "Transactions", path: "/transactions" },
  { label: "Budgets", path: "/budgets" },
  { label: "Cash Flow", path: "/cash-flow" },
];

const makeOpts = (overrides?: Partial<{
  getNavState: (path: string) => NavState;
  showLockedNav: boolean;
  showAdvancedNav: boolean;
  navOverrides: Record<string, boolean>;
}>) => ({
  getNavState: (_path: string): NavState => "visible",
  showLockedNav: true,
  showAdvancedNav: false,
  navOverrides: {},
  ...overrides,
});

describe("filterVisible with locked nav (UX improvement A)", () => {
  describe("no accounts — all conditional items locked", () => {
    const allLocked = makeOpts({ getNavState: () => "locked" });

    it("shows all items as locked when showLockedNav=true", () => {
      const result = filterVisible(SPENDING_ITEMS, allLocked);
      expect(result.length).toBe(3);
      result.forEach((item) => expect(item.locked).toBe(true));
    });

    it("each locked item has a lockedTooltip", () => {
      const result = filterVisible(SPENDING_ITEMS, allLocked);
      result.forEach((item) => expect(item.lockedTooltip).toBeTruthy());
    });

    it("hides all items when showLockedNav=false", () => {
      const opts = makeOpts({ getNavState: () => "locked", showLockedNav: false });
      const result = filterVisible(SPENDING_ITEMS, opts);
      expect(result.length).toBe(0);
    });
  });

  describe("with accounts — conditional items become visible", () => {
    const allVisible = makeOpts({ getNavState: () => "visible" });

    it("shows all items as normal (not locked)", () => {
      const result = filterVisible(SPENDING_ITEMS, allVisible);
      expect(result.length).toBe(3);
      result.forEach((item) => expect(item.locked).toBeUndefined());
    });
  });

  describe("mixed state — some locked, some visible", () => {
    it("passes through visible items and locks conditional ones", () => {
      const opts = makeOpts({
        getNavState: (path) => path === "/transactions" ? "visible" : "locked",
      });
      const result = filterVisible(SPENDING_ITEMS, opts);
      expect(result.length).toBe(3);
      expect(result[0].locked).toBeUndefined(); // transactions = visible
      expect(result[1].locked).toBe(true); // budgets = locked
      expect(result[2].locked).toBe(true); // cash-flow = locked
    });
  });

  describe("advanced items", () => {
    const advancedItem: NavItem[] = [
      { label: "PE Performance", path: "/pe-performance", advanced: true },
    ];

    it("hides advanced item when showAdvancedNav=false", () => {
      const opts = makeOpts({ getNavState: () => "visible" });
      const result = filterVisible(advancedItem, opts);
      expect(result.length).toBe(0);
    });

    it("shows advanced item when showAdvancedNav=true", () => {
      const opts = makeOpts({ showAdvancedNav: true, getNavState: () => "visible" });
      const result = filterVisible(advancedItem, opts);
      expect(result.length).toBe(1);
    });
  });

  describe("user override takes precedence", () => {
    it("explicitly enabled item shows even if getNavState would say locked", () => {
      const opts = makeOpts({
        getNavState: () => "locked",
        navOverrides: { "/transactions": true },
      });
      const result = filterVisible([SPENDING_ITEMS[0]], opts);
      expect(result.length).toBe(1);
      expect(result[0].locked).toBeUndefined();
    });

    it("explicitly disabled item is hidden even if getNavState says visible", () => {
      const opts = makeOpts({
        getNavState: () => "visible",
        navOverrides: { "/transactions": false },
      });
      const result = filterVisible([SPENDING_ITEMS[0]], opts);
      expect(result.length).toBe(0);
    });
  });
});
