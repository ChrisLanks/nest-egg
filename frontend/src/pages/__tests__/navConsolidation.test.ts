/**
 * Tests for nav consolidation: verifies the consolidated planning hub items
 * are correct and the old individual items were removed.
 */

import { describe, it, expect } from "vitest";
import { NAV_SECTIONS, buildConditionalDefaults } from "../../hooks/useNavDefaults";

// ── Nav sections structure ────────────────────────────────────────────────────

describe("nav consolidation — planning items", () => {
  const planningSection = NAV_SECTIONS.find((s) => s.group === "Planning");
  const planningPaths = planningSection?.items.map((i) => i.path) ?? [];

  it("planning section exists", () => {
    expect(planningSection).toBeDefined();
  });

  it("has the three consolidated hub items", () => {
    expect(planningPaths).toContain("/tax-center");
    expect(planningPaths).toContain("/life-planning");
    expect(planningPaths).toContain("/investment-tools");
  });

  it("does NOT have old individual items that were merged into hubs", () => {
    // These were merged into /tax-center
    expect(planningPaths).not.toContain("/tax-projection");
    expect(planningPaths).not.toContain("/tax-buckets");
    expect(planningPaths).not.toContain("/charitable-giving");
    // These were merged into /life-planning
    expect(planningPaths).not.toContain("/ss-claiming");
    expect(planningPaths).not.toContain("/variable-income");
    expect(planningPaths).not.toContain("/estate");
    // These were merged into /investment-tools
    expect(planningPaths).not.toContain("/fire");
    expect(planningPaths).not.toContain("/equity");
    expect(planningPaths).not.toContain("/loan-modeler");
  });

  it("still has standalone items", () => {
    expect(planningPaths).toContain("/goals");
    expect(planningPaths).toContain("/retirement");
    expect(planningPaths).toContain("/debt-payoff");
    expect(planningPaths).toContain("/mortgage");
  });

  it("does NOT have /smart-insights (moved to Analytics group)", () => {
    expect(planningPaths).not.toContain("/smart-insights");
  });

  it("does NOT have /financial-health (moved to Analytics group)", () => {
    expect(planningPaths).not.toContain("/financial-health");
  });

  it("does NOT have /hsa (moved into Investment Tools hub)", () => {
    expect(planningPaths).not.toContain("/hsa");
  });

  it("only /investment-tools is marked advanced", () => {
    const advancedItems = planningSection?.items.filter((i) => i.advanced) ?? [];
    expect(advancedItems).toHaveLength(1);
    expect(advancedItems[0].path).toBe("/investment-tools");
  });

  it("total planning items is 9 or fewer (was 15)", () => {
    expect(planningSection!.items.length).toBeLessThanOrEqual(10);
  });
});

// ── Analytics section ─────────────────────────────────────────────────────────

describe("nav consolidation — analytics items", () => {
  const analyticsSection = NAV_SECTIONS.find((s) => s.group === "Analytics");
  const analyticsPaths = analyticsSection?.items.map((i) => i.path) ?? [];

  it("Smart Insights is in Analytics group", () => {
    expect(analyticsPaths).toContain("/smart-insights");
  });

  it("Financial Health is in Analytics group", () => {
    expect(analyticsPaths).toContain("/financial-health");
  });
});

// ── Spending section ──────────────────────────────────────────────────────────

describe("nav consolidation — spending items", () => {
  const spendingSection = NAV_SECTIONS.find((s) => s.group === "Spending");
  const spendingPaths = spendingSection?.items.map((i) => i.path) ?? [];

  it("has recurring-bills hub", () => {
    expect(spendingPaths).toContain("/recurring-bills");
  });

  it("does NOT have old separate recurring and bills paths", () => {
    expect(spendingPaths).not.toContain("/recurring");
    expect(spendingPaths).not.toContain("/bills");
  });

  it("spending items reduced to 5 (was 6)", () => {
    expect(spendingSection!.items.length).toBe(5);
  });
});

// ── buildConditionalDefaults ──────────────────────────────────────────────────

describe("buildConditionalDefaults — hub paths", () => {
  const noAccounts = buildConditionalDefaults([], null);

  it("tax-center always visible", () => {
    expect(noAccounts["/tax-center"]).toBe(true);
  });

  it("life-planning always visible", () => {
    expect(noAccounts["/life-planning"]).toBe(true);
  });

  it("investment-tools always visible by default", () => {
    expect(noAccounts["/investment-tools"]).toBe(true);
  });

  it("old individual paths are NOT in conditionalDefaults", () => {
    expect("/fire" in noAccounts).toBe(false);
    expect("/tax-projection" in noAccounts).toBe(false);
    expect("/ss-claiming" in noAccounts).toBe(false);
    expect("/estate" in noAccounts).toBe(false);
    expect("/equity" in noAccounts).toBe(false);
    expect("/variable-income" in noAccounts).toBe(false);
    expect("/loan-modeler" in noAccounts).toBe(false);
    expect("/charitable-giving" in noAccounts).toBe(false);
    expect("/recurring" in noAccounts).toBe(false);
    expect("/bills" in noAccounts).toBe(false);
  });

  it("recurring-bills shown only with linked accounts", () => {
    expect(noAccounts["/recurring-bills"]).toBe(false);
    const withLinked = buildConditionalDefaults(
      [{ account_type: "checking", plaid_item_id: "plaid-123", plaid_item_hash: null }],
      null,
    );
    expect(withLinked["/recurring-bills"]).toBe(true);
  });

  it("conditional items still work correctly", () => {
    const withMortgage = buildConditionalDefaults(
      [{ account_type: "mortgage", plaid_item_id: null, plaid_item_hash: null }],
      null,
    );
    expect(withMortgage["/mortgage"]).toBe(true);

    const withoutMortgage = buildConditionalDefaults([], null);
    expect(withoutMortgage["/mortgage"]).toBe(false);
  });

  it("/hsa is NOT in conditionalDefaults (moved into Investment Tools hub)", () => {
    const defaults = buildConditionalDefaults(
      [{ account_type: "hsa", plaid_item_id: null, plaid_item_hash: null }],
      null,
    );
    expect("/hsa" in defaults).toBe(false);
  });
});

// ── filterVisible logic (mirrors Layout) ─────────────────────────────────────

describe("filterVisible with consolidated nav", () => {
  const planningItems = NAV_SECTIONS.find((s) => s.group === "Planning")!.items;

  function filterVisible(
    showAdvancedNav: boolean,
    navOverridesState: Record<string, boolean>,
    conditionalDefaults: Record<string, boolean>,
  ) {
    const isNavVisible = (path: string): boolean => {
      if (path in navOverridesState) return navOverridesState[path];
      return conditionalDefaults[path] ?? true;
    };

    return planningItems.filter((item) => {
      if (!isNavVisible(item.path)) return false;
      if (
        item.advanced &&
        !showAdvancedNav &&
        !(item.path in navOverridesState && navOverridesState[item.path])
      ) {
        return false;
      }
      return true;
    });
  }

  const defaults = buildConditionalDefaults([], null);

  it("investment-tools hidden by default (advanced, no override)", () => {
    const visible = filterVisible(false, {}, defaults);
    const paths = visible.map((i) => i.path);
    expect(paths).not.toContain("/investment-tools");
  });

  it("investment-tools visible when showAdvancedNav=true", () => {
    const visible = filterVisible(true, {}, defaults);
    const paths = visible.map((i) => i.path);
    expect(paths).toContain("/investment-tools");
  });

  it("investment-tools visible via explicit override even without master toggle", () => {
    const visible = filterVisible(false, { "/investment-tools": true }, defaults);
    const paths = visible.map((i) => i.path);
    expect(paths).toContain("/investment-tools");
  });

  it("tax-center and life-planning always visible (not advanced)", () => {
    const visible = filterVisible(false, {}, defaults);
    const paths = visible.map((i) => i.path);
    expect(paths).toContain("/tax-center");
    expect(paths).toContain("/life-planning");
  });
});
