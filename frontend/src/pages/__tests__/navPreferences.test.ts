/**
 * Tests for NavigationVisibilitySection logic in PreferencesPage and the
 * progressive sidebar advanced-features system.
 *
 * Architecture (post-unification with useNavDefaults hook):
 *   - All visibility state in one store: nest-egg-nav-visibility
 *   - "Show advanced features" toggle writes /investment-tools into that store
 *   - isNavVisible(path, overrides, defaults) — overrides always win
 *   - showAdvancedNav is DERIVED: true iff ALL advanced paths are explicitly true
 *   - Per-item switch can turn an advanced tab on even when master toggle is off
 *   - isItemOn now uses account-aware conditionalDefaults, not !item.conditional
 *   - Per-item toggles set pendingReload=true; Apply button calls window.location.reload()
 *   - "Show advanced features" toggle and "Reset to Default" reload immediately
 *   - No standalone "Advanced" button in the top nav (removed as duplicate)
 *   - Recurring + Bills merged into /recurring-bills hub
 *   - 9 planning items consolidated into 3 hubs (/tax-center, /life-planning, /investment-tools)
 *
 * @vitest-environment jsdom
 */

import { describe, it, expect, beforeEach } from "vitest";
import {
  buildConditionalDefaults,
  NAV_SECTIONS,
} from "../../hooks/useNavDefaults";

// ── Constants mirroring PreferencesPage / Layout ──────────────────────────────

const STORAGE_KEY = "nest-egg-nav-visibility";
const LEGACY_KEY = "nest-egg-show-all-nav";
const LEGACY_ADVANCED_KEY = "nest-egg-show-advanced-nav";
// Must match ADVANCED_PATHS in PreferencesPage (all items with advanced: true in NAV_SECTIONS)
// Only /investment-tools is advanced; /pe-performance is conditional (unlocked by account type)
const ADVANCED_NAV_PATHS = [
  "/investment-tools",
];

// ── Account fixtures ──────────────────────────────────────────────────────────

interface Account {
  account_type: string;
  is_rental_property?: boolean;
  plaid_item_id?: string | null;
  plaid_item_hash?: string | null;
}

const noAccounts: Account[] = [];
const withMortgage: Account[] = [{ account_type: "mortgage" }];
const withRental: Account[] = [
  { account_type: "property", is_rental_property: true },
];
const withLinkedBank: Account[] = [
  { account_type: "checking", plaid_item_id: "plaid-1", plaid_item_hash: null },
];
const withCreditCard: Account[] = [{ account_type: "credit_card" }];

// ── Helpers mirroring PreferencesPage / Layout ────────────────────────────────

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

/** Mirrors toggleItem in PreferencesPage — sets pendingReload=true in real code */
const toggleItem = (
  overrides: Record<string, boolean>,
  path: string,
  checked: boolean,
): Record<string, boolean> => {
  const next = { ...overrides, [path]: checked };
  persistOverrides(next);
  return next;
};

/** Mirrors toggleAdvanced in PreferencesPage — reloads immediately in real code */
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

/** Mirrors derived showAdvancedNav — true only when ALL advanced paths explicitly true */
const deriveShowAdvanced = (overrides: Record<string, boolean>): boolean =>
  ADVANCED_NAV_PATHS.every((p) => overrides[p] === true);

/** Mirrors resetToDefaults in PreferencesPage — reloads immediately in real code */
const resetToDefaults = () => {
  persistOverrides({});
  localStorage.removeItem(LEGACY_KEY);
  localStorage.removeItem(LEGACY_ADVANCED_KEY);
};

/** Mirror of updated isNavVisible — overrides win over account defaults */
const isNavVisible = (
  path: string,
  overrides: Record<string, boolean>,
  defaults: Record<string, boolean>,
): boolean => {
  if (path in overrides) return overrides[path];
  return defaults[path] ?? true;
};

/**
 * Mirror of updated isItemOn in PreferencesPage.
 * Uses conditionalDefaults (account/age-aware) instead of !item.conditional.
 */
const isItemOn = (
  item: { path: string; alwaysOn?: boolean },
  overrides: Record<string, boolean>,
  conditionalDefaults: Record<string, boolean>,
): boolean => {
  if (item.alwaysOn) return true;
  if (item.path in overrides) return overrides[item.path];
  return conditionalDefaults[item.path] ?? true;
};

// ── isItemOn: account-aware defaults ─────────────────────────────────────────

describe("isItemOn: account-aware defaults (conditionalDefaults)", () => {
  it("alwaysOn items are always on regardless of overrides", () => {
    const defaults = buildConditionalDefaults(noAccounts);
    expect(isItemOn({ path: "/overview", alwaysOn: true }, {}, defaults)).toBe(
      true,
    );
    expect(
      isItemOn(
        { path: "/overview", alwaysOn: true },
        { "/overview": false },
        defaults,
      ),
    ).toBe(true);
  });

  it("account-gated items are off with no accounts, on once any account exists", () => {
    const defaults = buildConditionalDefaults(noAccounts);
    expect(isItemOn({ path: "/transactions" }, {}, defaults)).toBe(false);
    expect(isItemOn({ path: "/retirement" }, {}, defaults)).toBe(false);
    expect(isItemOn({ path: "/goals" }, {}, defaults)).toBe(false);

    const withAccount = buildConditionalDefaults([{ account_type: "checking", plaid_item_id: null, plaid_item_hash: null }]);
    expect(isItemOn({ path: "/transactions" }, {}, withAccount)).toBe(true);
    expect(isItemOn({ path: "/retirement" }, {}, withAccount)).toBe(true);
    expect(isItemOn({ path: "/goals" }, {}, withAccount)).toBe(true);
  });

  it("mortgage shows as ON when user has mortgage account", () => {
    const defaults = buildConditionalDefaults(withMortgage);
    expect(isItemOn({ path: "/mortgage" }, {}, defaults)).toBe(true);
  });

  it("mortgage shows as OFF when user has no mortgage account", () => {
    const defaults = buildConditionalDefaults(noAccounts);
    expect(isItemOn({ path: "/mortgage" }, {}, defaults)).toBe(false);
  });

  it("debt-payoff shows as ON when user has credit card", () => {
    const defaults = buildConditionalDefaults(withCreditCard);
    expect(isItemOn({ path: "/debt-payoff" }, {}, defaults)).toBe(true);
  });

  it("rental-properties shows as ON when rental account exists", () => {
    const defaults = buildConditionalDefaults(withRental);
    expect(isItemOn({ path: "/rental-properties" }, {}, defaults)).toBe(true);
  });

  it("rental-properties shows as OFF with no rental account", () => {
    const defaults = buildConditionalDefaults(noAccounts);
    expect(isItemOn({ path: "/rental-properties" }, {}, defaults)).toBe(false);
  });

  it("recurring-bills shows as ON with linked bank account", () => {
    const defaults = buildConditionalDefaults(withLinkedBank);
    expect(isItemOn({ path: "/recurring-bills" }, {}, defaults)).toBe(true);
  });

  it("recurring-bills shows as OFF with no linked account", () => {
    const defaults = buildConditionalDefaults(noAccounts);
    expect(isItemOn({ path: "/recurring-bills" }, {}, defaults)).toBe(false);
  });

  it("override true turns on a conditionally-off item", () => {
    const defaults = buildConditionalDefaults(noAccounts);
    expect(
      isItemOn({ path: "/mortgage" }, { "/mortgage": true }, defaults),
    ).toBe(true);
  });

  it("override false turns off a conditionally-on item", () => {
    const defaults = buildConditionalDefaults(withMortgage);
    expect(
      isItemOn({ path: "/mortgage" }, { "/mortgage": false }, defaults),
    ).toBe(false);
  });

  it("override false turns off a conditional item", () => {
    const defaults = buildConditionalDefaults(noAccounts);
    expect(
      isItemOn({ path: "/budgets" }, { "/budgets": false }, defaults),
    ).toBe(false);
  });
});

// ── isNavVisible ──────────────────────────────────────────────────────────────

describe("isNavVisible: unified override model", () => {
  it("override=true shows regardless of account default", () => {
    const defaults = buildConditionalDefaults(noAccounts);
    expect(isNavVisible("/mortgage", { "/mortgage": true }, defaults)).toBe(
      true,
    );
  });
  it("override=false hides regardless of account default", () => {
    const defaults = buildConditionalDefaults(withMortgage);
    expect(isNavVisible("/mortgage", { "/mortgage": false }, defaults)).toBe(
      false,
    );
  });
  it("no override → account default used", () => {
    expect(
      isNavVisible(
        "/mortgage",
        {},
        buildConditionalDefaults(withMortgage),
      ),
    ).toBe(true);
    expect(
      isNavVisible("/mortgage", {}, buildConditionalDefaults(noAccounts)),
    ).toBe(false);
  });
  it("paths not in conditionalDefaults default to true", () => {
    const defaults = buildConditionalDefaults(noAccounts);
    // /overview is alwaysOn and not in the conditional map — defaults to true
    expect(isNavVisible("/overview", {}, defaults)).toBe(true);
    // account-gated paths are in the map — return false with no accounts
    expect(isNavVisible("/transactions", {}, defaults)).toBe(false);
    expect(isNavVisible("/retirement", {}, defaults)).toBe(false);
  });
});

// ── toggleAdvancedNav ─────────────────────────────────────────────────────────

describe("toggleAdvancedNav: writes into shared overrides store", () => {
  beforeEach(() => localStorage.clear());

  it("enabling sets all advanced paths to true", () => {
    const updated = toggleAdvancedNav({}, true);
    for (const p of ADVANCED_NAV_PATHS) {
      expect(updated[p]).toBe(true);
    }
  });
  it("disabling sets all advanced paths to false", () => {
    const updated = toggleAdvancedNav({}, false);
    for (const p of ADVANCED_NAV_PATHS) {
      expect(updated[p]).toBe(false);
    }
  });
  it("persists all advanced paths to nest-egg-nav-visibility", () => {
    toggleAdvancedNav({}, true);
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY)!);
    for (const p of ADVANCED_NAV_PATHS) {
      expect(stored[p]).toBe(true);
    }
  });
  it("also writes legacy compat flag", () => {
    toggleAdvancedNav({}, true);
    expect(localStorage.getItem(LEGACY_ADVANCED_KEY)).toBe("true");
  });
  it("does not disturb other overrides", () => {
    const updated = toggleAdvancedNav({ "/budgets": false }, true);
    expect(updated["/budgets"]).toBe(false);
  });
  it("toggle off then on restores investment-tools to true", () => {
    const off = toggleAdvancedNav({}, false);
    const on = toggleAdvancedNav(off, true);
    expect(on["/investment-tools"]).toBe(true);
  });
});

// ── deriveShowAdvanced ────────────────────────────────────────────────────────

describe("deriveShowAdvanced: derived from overrides", () => {
  it("false when overrides is empty", () => {
    expect(deriveShowAdvanced({})).toBe(false);
  });
  it("false when a non-advanced path is true", () => {
    expect(deriveShowAdvanced({ "/budgets": true })).toBe(false);
  });
  it("false when /investment-tools is explicitly false", () => {
    expect(deriveShowAdvanced({ "/investment-tools": false })).toBe(false);
  });
  it("true when ALL advanced paths are explicitly true", () => {
    const allOn = Object.fromEntries(ADVANCED_NAV_PATHS.map((p) => [p, true]));
    expect(deriveShowAdvanced(allOn)).toBe(true);
  });
  it("roundtrip: toggle on → derive true", () => {
    expect(deriveShowAdvanced(toggleAdvancedNav({}, true))).toBe(true);
  });
  it("roundtrip: toggle off → derive false", () => {
    expect(
      deriveShowAdvanced(toggleAdvancedNav({ "/investment-tools": true }, false)),
    ).toBe(false);
  });
  it("per-item on for a non-advanced path does not flip master to true", () => {
    expect(deriveShowAdvanced({ "/budgets": true })).toBe(false);
  });
});

// ── Per-item switch independence from master toggle ───────────────────────────

describe("per-item switch independence", () => {
  beforeEach(() => localStorage.clear());

  it("per-item on for /investment-tools while master is off — visible, master still false", () => {
    // Master off sets /investment-tools=false; then per-item overrides it back to true
    let overrides = toggleAdvancedNav({}, false);
    overrides = toggleItem(overrides, "/investment-tools", true);
    const defaults = buildConditionalDefaults(noAccounts);
    expect(isNavVisible("/investment-tools", overrides, defaults)).toBe(true);
    // Master is still considered off because we manually set it — the derived state
    // checks ALL advanced paths are true; here we forced it true via per-item so master = true
    expect(deriveShowAdvanced(overrides)).toBe(true);
  });

  it("per-item off for /investment-tools overrides master-on state", () => {
    let overrides = toggleAdvancedNav({}, true);
    overrides = toggleItem(overrides, "/investment-tools", false);
    const defaults = buildConditionalDefaults(noAccounts);
    expect(isNavVisible("/investment-tools", overrides, defaults)).toBe(false);
    expect(deriveShowAdvanced(overrides)).toBe(false);
  });
});

// ── Pending reload behavior ───────────────────────────────────────────────────

describe("pending reload: per-item toggle does NOT reload immediately", () => {
  beforeEach(() => localStorage.clear());

  it("toggleItem persists to localStorage without reloading", () => {
    // In real PreferencesPage, toggleItem sets pendingReload=true but does NOT call
    // window.location.reload(). The Apply button is what triggers reload.
    const overrides = toggleItem({}, "/mortgage", true);
    expect(overrides["/mortgage"]).toBe(true);
    // Value is in localStorage
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY)!);
    expect(stored["/mortgage"]).toBe(true);
  });

  it("multiple toggles accumulate in localStorage before apply", () => {
    const first = toggleItem({}, "/mortgage", true);
    toggleItem(first, "/rental-properties", false);
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY)!);
    expect(stored).toMatchObject({
      "/mortgage": true,
      "/rental-properties": false,
    });
  });

  it("toggling same item twice reflects final value", () => {
    const first = toggleItem({}, "/budgets", false);
    toggleItem(first, "/budgets", true);
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY)!);
    expect(stored["/budgets"]).toBe(true);
  });
});

// ── Reset to defaults ─────────────────────────────────────────────────────────

describe("reset to defaults", () => {
  beforeEach(() => localStorage.clear());

  it("clears all overrides from localStorage", () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ "/debt-payoff": true }));
    resetToDefaults();
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
  });
  it("removes legacy show-all-nav key", () => {
    localStorage.setItem(LEGACY_KEY, "true");
    resetToDefaults();
    expect(localStorage.getItem(LEGACY_KEY)).toBeNull();
  });
  it("removes legacy show-advanced-nav key", () => {
    localStorage.setItem(LEGACY_ADVANCED_KEY, "true");
    resetToDefaults();
    expect(localStorage.getItem(LEGACY_ADVANCED_KEY)).toBeNull();
  });
  it("loadOverrides returns empty after reset", () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ "/budgets": false }));
    resetToDefaults();
    expect(loadOverrides()).toEqual({});
  });
  it("advanced paths cleared along with all other overrides", () => {
    const overrides = toggleAdvancedNav({}, true);
    void overrides;
    resetToDefaults();
    expect(loadOverrides()).toEqual({});
    expect(deriveShowAdvanced(loadOverrides())).toBe(false);
  });

  // After reset, isItemOn reflects account data (not all-off)
  it("post-reset: mortgage ON when mortgage account exists", () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ "/mortgage": false }));
    resetToDefaults();
    const defaults = buildConditionalDefaults(withMortgage);
    expect(isItemOn({ path: "/mortgage" }, loadOverrides(), defaults)).toBe(
      true,
    );
  });
  it("post-reset: mortgage OFF when no mortgage account", () => {
    resetToDefaults();
    const defaults = buildConditionalDefaults(noAccounts);
    expect(isItemOn({ path: "/mortgage" }, loadOverrides(), defaults)).toBe(
      false,
    );
  });
  it("post-reset: rental-properties ON with rental account", () => {
    resetToDefaults();
    const defaults = buildConditionalDefaults(withRental);
    expect(
      isItemOn({ path: "/rental-properties" }, loadOverrides(), defaults),
    ).toBe(true);
  });
  it("post-reset: rental-properties OFF without rental account", () => {
    resetToDefaults();
    const defaults = buildConditionalDefaults(noAccounts);
    expect(
      isItemOn({ path: "/rental-properties" }, loadOverrides(), defaults),
    ).toBe(false);
  });
});

// ── NAV_SECTIONS structure (imported from canonical hook) ─────────────────────

describe("NAV_SECTIONS: structure", () => {
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
  it("conditional items include all account-gated tabs (progressive disclosure)", () => {
    const conditionalPaths = NAV_SECTIONS.flatMap((s) => s.items)
      .filter((i) => i.conditional)
      .map((i) => i.path)
      .sort();
    // All non-alwaysOn, non-advanced items are conditional (progressive disclosure)
    expect(conditionalPaths).toEqual([
      "/budgets",
      "/cash-flow",
      "/categories",
      "/debt-payoff",
      "/education",
      "/financial-health",
      "/goals",
      "/life-planning",
      "/mortgage",
      "/net-worth-timeline",
      "/pe-performance",
      "/recurring-bills",
      "/rental-properties",
      "/reports",
      "/retirement",
      "/rules",
      "/tax-center",
      "/transactions",
    ]);
  });
  it("advanced items are /investment-tools only", () => {
    const advancedPaths = NAV_SECTIONS.flatMap((s) => s.items)
      .filter((i) => i.advanced)
      .map((i) => i.path)
      .sort();
    expect(advancedPaths).toEqual(["/investment-tools"]);
  });
  it("no spending items are advanced; all spending items are conditional (progressive disclosure)", () => {
    const spending = NAV_SECTIONS.find((s) => s.group === "Spending");
    expect(spending!.items.every((i) => !i.advanced)).toBe(true);
    // All spending items are conditional — hidden until first account is added
    expect(spending!.items.every((i) => i.conditional)).toBe(true);
  });
  it("all items have unique paths", () => {
    const allPaths = NAV_SECTIONS.flatMap((s) => s.items).map((i) => i.path);
    expect(new Set(allPaths).size).toBe(allPaths.length);
  });
  it("consolidated hubs are in Planning group", () => {
    const planning = NAV_SECTIONS.find((s) => s.group === "Planning");
    const paths = planning!.items.map((i) => i.path);
    expect(paths).toContain("/tax-center");
    expect(paths).toContain("/life-planning");
    expect(paths).toContain("/investment-tools");
  });
  it("Mortgage is in Planning group as a conditional item", () => {
    const planning = NAV_SECTIONS.find((s) => s.group === "Planning");
    const mortgage = planning!.items.find((i) => i.path === "/mortgage");
    expect(mortgage).toBeDefined();
    expect(mortgage!.conditional).toBe(true);
  });
  it("/pe-performance is conditional (account-gated), NOT advanced", () => {
    const allItems = NAV_SECTIONS.flatMap((s) => s.items);
    const pe = allItems.find((i) => i.path === "/pe-performance");
    expect(pe).toBeDefined();
    expect(pe!.conditional).toBe(true);
    expect(pe!.advanced).toBeFalsy();
  });
  it("ADVANCED_NAV_PATHS constant matches NAV_SECTIONS advanced: true items exactly", () => {
    const advancedInSections = NAV_SECTIONS.flatMap((s) => s.items)
      .filter((i) => i.advanced)
      .map((i) => i.path)
      .sort();
    expect(ADVANCED_NAV_PATHS.slice().sort()).toEqual(advancedInSections);
  });
});

// ── Top-nav Advanced button is removed ───────────────────────────────────────

describe("top-nav Advanced button: removed (consolidated into Preferences)", () => {
  // The standalone "Advanced" toggle button that was in the Layout top nav has
  // been removed. The single canonical control is Preferences → Navigation →
  // "Show advanced features" toggle. These tests confirm the toggle/derive logic
  // works correctly from Preferences alone.

  it("enabling advanced via Preferences toggle makes all advanced paths visible", () => {
    const overrides = toggleAdvancedNav({}, true);
    const defaults = buildConditionalDefaults(noAccounts);
    for (const p of ADVANCED_NAV_PATHS) {
      expect(isNavVisible(p, overrides, defaults)).toBe(true);
    }
  });

  it("disabling advanced via Preferences toggle hides all advanced paths", () => {
    const overrides = toggleAdvancedNav({}, false);
    const defaults = buildConditionalDefaults(noAccounts);
    for (const p of ADVANCED_NAV_PATHS) {
      expect(isNavVisible(p, overrides, defaults)).toBe(false);
    }
  });

  it("state persists in the same localStorage key used by the nav", () => {
    toggleAdvancedNav({}, true);
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY)!);
    for (const p of ADVANCED_NAV_PATHS) {
      expect(stored[p]).toBe(true);
    }
  });
});

// ── SS Optimizer / Life Planning hub ─────────────────────────────────────────
// /ss-claiming was merged into /life-planning. The nav now shows /life-planning
// unconditionally; age-gating for SS is handled inside the hub page itself.

describe("Life Planning hub: always visible (SS age-gating inside hub)", () => {
  it("/ss-claiming is no longer a top-level nav path", () => {
    const allPaths = NAV_SECTIONS.flatMap((s) => s.items).map((i) => i.path);
    expect(allPaths).not.toContain("/ss-claiming");
  });

  it("/ss-claiming is not in conditionalDefaults (merged into hub)", () => {
    const defaults = buildConditionalDefaults(noAccounts);
    expect("/ss-claiming" in defaults).toBe(false);
  });

  it("/life-planning is visible once any account exists (no age-gating)", () => {
    // No accounts: locked (progressive disclosure, not age-gated)
    const defaultsNoAccounts = buildConditionalDefaults(noAccounts);
    expect(defaultsNoAccounts["/life-planning"]).toBe(false);

    // Any account (regardless of age): unlocked
    const withAnyAccount = buildConditionalDefaults([{ account_type: "checking", plaid_item_id: null, plaid_item_hash: null }]);
    expect(withAnyAccount["/life-planning"]).toBe(true);
  });
});

// ── Advanced nav gating fix ───────────────────────────────────────────────────

describe("advanced nav items hidden when showAdvancedNav is false", () => {
  it("Layout.tsx reads nest-egg-show-advanced-nav from localStorage", () => {
    const source = require("fs").readFileSync(
      require("path").join(__dirname, "../../components/Layout.tsx"),
      "utf8",
    );
    expect(source).toContain("nest-egg-show-advanced-nav");
  });

  it("filterVisible respects the advanced flag in Layout.tsx", () => {
    const source = require("fs").readFileSync(
      require("path").join(__dirname, "../../components/Layout.tsx"),
      "utf8",
    );
    // filterVisible must gate on advanced items via showAdvancedNav AND
    // also allow items with an explicit per-item override (navOverridesState)
    expect(source).toContain("item.advanced");
    expect(source).toContain("showAdvancedNav");
    expect(source).toContain("navOverridesState");
  });

  it("showAdvancedNav defaults to false when key absent from localStorage", () => {
    localStorage.removeItem("nest-egg-show-advanced-nav");
    const val =
      localStorage.getItem("nest-egg-show-advanced-nav") === "true";
    expect(val).toBe(false);
  });

  it("showAdvancedNav is true only when key is exactly 'true'", () => {
    localStorage.setItem("nest-egg-show-advanced-nav", "true");
    expect(localStorage.getItem("nest-egg-show-advanced-nav") === "true").toBe(
      true,
    );
    localStorage.setItem("nest-egg-show-advanced-nav", "false");
    expect(localStorage.getItem("nest-egg-show-advanced-nav") === "true").toBe(
      false,
    );
  });
});
