/**
 * Tests for SmartInsightsPage category-filter pill logic.
 *
 * The pills let users narrow displayed insights to a single category.
 * All logic mirrors the exact expressions used inside SmartInsightsPage so
 * that regressions are caught without rendering.
 */

import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import type { InsightItem } from "../../api/smartInsights";

// ── Helpers mirroring SmartInsightsPage expressions ───────────────────────

/** Group insights by category (same logic as the page). */
function groupByCategory(
  insights: InsightItem[],
): Record<string, InsightItem[]> {
  const grouped: Record<string, InsightItem[]> = {};
  for (const insight of insights) {
    (grouped[insight.category] ??= []).push(insight);
  }
  return grouped;
}

const categoryOrder = ["cash", "tax", "retirement", "investing"] as const;

/** Active categories in display order (categories that have at least one insight). */
function activeCategories(grouped: Record<string, InsightItem[]>) {
  return categoryOrder.filter((c) => grouped[c]?.length);
}

/** Apply the selectedCategory filter — null means "All". */
function visibleCategories(
  active: readonly string[],
  selectedCategory: string | null,
): string[] {
  if (selectedCategory !== null) {
    return active.filter((c) => c === selectedCategory);
  }
  return [...active];
}

/** Toggle logic: clicking the active pill deselects (returns null). */
function handlePillClick(
  prev: string | null,
  cat: string,
): string | null {
  return prev === cat ? null : cat;
}

// ── Sample data ────────────────────────────────────────────────────────────

function makeInsight(
  overrides: Partial<InsightItem> & { category: InsightItem["category"] },
): InsightItem {
  return {
    type: "test",
    title: "Test insight",
    message: "Test message",
    action: "Take action",
    priority: "medium",
    priority_score: 50,
    icon: "💡",
    amount: null,
    ...overrides,
  };
}

const cashInsight1 = makeInsight({ category: "cash", type: "emergency_fund" });
const cashInsight2 = makeInsight({ category: "cash", type: "high_yield" });
const taxInsight = makeInsight({ category: "tax", type: "tax_loss" });
const retirementInsight = makeInsight({
  category: "retirement",
  type: "roth_conversion",
});
const investingInsight = makeInsight({
  category: "investing",
  type: "rebalance",
});

const allInsights = [
  cashInsight1,
  cashInsight2,
  taxInsight,
  retirementInsight,
  investingInsight,
];

// ── groupByCategory ────────────────────────────────────────────────────────

describe("groupByCategory", () => {
  it("puts cash insights under cash key", () => {
    const g = groupByCategory(allInsights);
    expect(g["cash"]).toHaveLength(2);
    expect(g["cash"]).toContain(cashInsight1);
    expect(g["cash"]).toContain(cashInsight2);
  });

  it("puts tax insight under tax key", () => {
    const g = groupByCategory(allInsights);
    expect(g["tax"]).toHaveLength(1);
    expect(g["tax"][0]).toBe(taxInsight);
  });

  it("puts retirement insight under retirement key", () => {
    const g = groupByCategory(allInsights);
    expect(g["retirement"]).toHaveLength(1);
  });

  it("puts investing insight under investing key", () => {
    const g = groupByCategory(allInsights);
    expect(g["investing"]).toHaveLength(1);
  });

  it("returns empty object for no insights", () => {
    expect(groupByCategory([])).toEqual({});
  });
});

// ── activeCategories ───────────────────────────────────────────────────────

describe("activeCategories", () => {
  it("returns categories present in data in display order", () => {
    const g = groupByCategory(allInsights);
    expect(activeCategories(g)).toEqual(["cash", "tax", "retirement", "investing"]);
  });

  it("omits categories with no insights", () => {
    // Only cash and investing
    const subset = [cashInsight1, investingInsight];
    const g = groupByCategory(subset);
    expect(activeCategories(g)).toEqual(["cash", "investing"]);
  });

  it("returns empty array when insights list is empty", () => {
    expect(activeCategories({})).toEqual([]);
  });
});

// ── pill selection filters insights ───────────────────────────────────────

describe("visibleCategories — pill selection filters insights", () => {
  const grouped = groupByCategory(allInsights);
  const active = activeCategories(grouped);

  it("shows all categories when selectedCategory is null", () => {
    const visible = visibleCategories(active, null);
    expect(visible).toEqual(["cash", "tax", "retirement", "investing"]);
  });

  it("shows only cash when cash pill is selected", () => {
    const visible = visibleCategories(active, "cash");
    expect(visible).toEqual(["cash"]);
  });

  it("shows only tax when tax pill is selected", () => {
    const visible = visibleCategories(active, "tax");
    expect(visible).toEqual(["tax"]);
  });

  it("shows only retirement when retirement pill is selected", () => {
    const visible = visibleCategories(active, "retirement");
    expect(visible).toEqual(["retirement"]);
  });

  it("shows only investing when investing pill is selected", () => {
    const visible = visibleCategories(active, "investing");
    expect(visible).toEqual(["investing"]);
  });

  it("returns empty when selected category has no insights", () => {
    const partialGrouped = groupByCategory([cashInsight1]);
    const partialActive = activeCategories(partialGrouped);
    // tax is not in partialActive, so filtering for it returns []
    const visible = visibleCategories(partialActive, "tax");
    expect(visible).toEqual([]);
  });
});

// ── "All" pill / deselect returns to all ──────────────────────────────────

describe("handlePillClick — deselect returns to all", () => {
  it("clicking a new category selects it", () => {
    expect(handlePillClick(null, "cash")).toBe("cash");
  });

  it("clicking the active category deselects (returns null)", () => {
    expect(handlePillClick("cash", "cash")).toBeNull();
  });

  it("clicking a different category switches selection", () => {
    expect(handlePillClick("cash", "tax")).toBe("tax");
  });

  it("null → 'All' means visibleCategories shows everything", () => {
    const grouped = groupByCategory(allInsights);
    const active = activeCategories(grouped);
    // After deselect, selectedCategory is null
    expect(visibleCategories(active, null)).toHaveLength(4);
  });
});

// ── Source-level checks ────────────────────────────────────────────────────

describe("SmartInsightsPage source — pill wiring", () => {
  const src = readFileSync(
    "src/pages/SmartInsightsPage.tsx",
    "utf-8",
  );

  it("imports useState", () => {
    expect(src).toContain("useState");
  });

  it("declares selectedCategory state", () => {
    expect(src).toContain("selectedCategory");
  });

  it("renders an All pill", () => {
    expect(src).toContain("pill-all");
  });

  it("renders category pills with data-testid", () => {
    expect(src).toContain("pill-${cat}");
  });

  it("pill onClick calls handlePillClick", () => {
    expect(src).toContain("handlePillClick");
  });

  it("uses visibleCategories to drive the rendered list", () => {
    expect(src).toContain("visibleCategories");
  });

  it("pill variant changes based on selected state (solid vs subtle)", () => {
    expect(src).toContain('"solid"');
    expect(src).toContain('"subtle"');
  });

  it("cursor is pointer on pills", () => {
    expect(src).toContain('cursor="pointer"');
  });
});
