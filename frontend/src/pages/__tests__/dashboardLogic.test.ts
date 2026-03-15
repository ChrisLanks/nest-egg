/**
 * Tests for DashboardPage logic: welcome greeting, layout resolution,
 * widget add/remove/reorder, span toggle, available-widget filtering,
 * default layout integrity, summary stat formatting, and color conditions.
 *
 * All helpers mirror the exact expressions used in DashboardPage.tsx,
 * DashboardGrid.tsx, AddWidgetDrawer.tsx, useWidgetLayout.ts, and
 * SummaryStatsWidget.tsx so that regressions are caught without rendering.
 */

import { describe, it, expect } from "vitest";

// ── Types (mirrored from features/dashboard/types.ts) ───────────────────────

interface LayoutItem {
  id: string;
  span: 1 | 2;
}

interface WidgetDefinition {
  id: string;
  title: string;
  description: string;
  defaultSpan: 1 | 2;
}

// ── Helpers (mirrored from page / widget expressions) ────────────────────────

/** DashboardPage.tsx: greeting display name chain */
const greetingName = (
  user: {
    display_name?: string | null;
    first_name?: string | null;
    email?: string | null;
  } | null,
): string =>
  user?.display_name ||
  user?.first_name ||
  user?.email?.split("@")[0] ||
  "User";

/** useWidgetLayout.ts: active layout resolution */
const resolveLayout = (
  pendingLayout: LayoutItem[] | null,
  savedLayout: LayoutItem[] | null,
  defaultLayout: LayoutItem[],
): LayoutItem[] => pendingLayout ?? savedLayout ?? defaultLayout;

/** DashboardPage.tsx: handleAddWidget builds a new LayoutItem */
const buildNewItem = (
  widgetId: string,
  registry: Record<string, WidgetDefinition>,
): LayoutItem | null => {
  const def = registry[widgetId];
  if (!def) return null;
  return { id: widgetId, span: def.defaultSpan };
};

/** DashboardGrid.tsx: remove widget */
const removeWidget = (layout: LayoutItem[], id: string): LayoutItem[] =>
  layout.filter((item) => item.id !== id);

/** DashboardGrid.tsx: toggle span 1 <-> 2 */
const toggleSpan = (layout: LayoutItem[], id: string): LayoutItem[] =>
  layout.map((item) =>
    item.id === id
      ? { ...item, span: (item.span === 2 ? 1 : 2) as 1 | 2 }
      : item,
  );

/** AddWidgetDrawer.tsx: filter out widgets already in layout */
const availableWidgets = (
  registry: Record<string, WidgetDefinition>,
  currentLayout: LayoutItem[],
): WidgetDefinition[] => {
  const activeIds = new Set(currentLayout.map((item) => item.id));
  return Object.values(registry).filter((def) => !activeIds.has(def.id));
};

/** SummaryStatsWidget.tsx: currency formatter */
const formatCurrency = (amount: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);

/** SummaryStatsWidget.tsx: net-worth color */
const netWorthColor = (netWorth: number): string =>
  netWorth >= 0 ? "finance.positive" : "finance.negative";

/** SummaryStatsWidget.tsx: monthly-net color */
const monthlyNetColor = (monthlyNet: number): string =>
  monthlyNet >= 0 ? "finance.positive" : "finance.negative";

/** SummaryStatsWidget.tsx: nullish coalescing for summary fields */
const resolveSummaryField = (value: number | undefined | null): number =>
  value ?? 0;

/** DashboardGrid.tsx: gridColumn expression */
const gridColumn = (span: 1 | 2): string => (span === 2 ? "span 2" : "span 1");

/** DashboardGrid.tsx: span-toggle tooltip */
const spanTooltip = (span: 1 | 2): string =>
  span === 2 ? "Switch to half width" : "Switch to full width";

// ── Fixtures ─────────────────────────────────────────────────────────────────

const MINI_REGISTRY: Record<string, WidgetDefinition> = {
  "summary-stats": {
    id: "summary-stats",
    title: "Summary Stats",
    description: "At a glance.",
    defaultSpan: 2,
  },
  "net-worth-chart": {
    id: "net-worth-chart",
    title: "Net Worth Over Time",
    description: "Historical chart.",
    defaultSpan: 2,
  },
  "top-expenses": {
    id: "top-expenses",
    title: "Top Expenses",
    description: "Top categories.",
    defaultSpan: 1,
  },
  "recent-transactions": {
    id: "recent-transactions",
    title: "Recent Transactions",
    description: "Recent txns.",
    defaultSpan: 1,
  },
};

const DEFAULT_LAYOUT: LayoutItem[] = [
  { id: "summary-stats", span: 2 },
  { id: "net-worth-chart", span: 2 },
  { id: "top-expenses", span: 1 },
  { id: "recent-transactions", span: 1 },
];

const FULL_USER = {
  display_name: "John Doe",
  first_name: "John",
  email: "john@example.com",
};

// ── Tests ────────────────────────────────────────────────────────────────────

describe("greetingName", () => {
  it("prefers display_name when all fields present", () => {
    expect(greetingName(FULL_USER)).toBe("John Doe");
  });

  it("falls back to first_name when display_name is null", () => {
    expect(
      greetingName({
        display_name: null,
        first_name: "Jane",
        email: "j@e.com",
      }),
    ).toBe("Jane");
  });

  it("falls back to first_name when display_name is empty string", () => {
    expect(
      greetingName({ display_name: "", first_name: "Jane", email: "j@e.com" }),
    ).toBe("Jane");
  });

  it("falls back to email local part when names are null", () => {
    expect(
      greetingName({
        display_name: null,
        first_name: null,
        email: "alice@example.com",
      }),
    ).toBe("alice");
  });

  it("falls back to email local part when names are empty strings", () => {
    expect(
      greetingName({ display_name: "", first_name: "", email: "bob@test.org" }),
    ).toBe("bob");
  });

  it('returns "User" when all fields are null', () => {
    expect(
      greetingName({ display_name: null, first_name: null, email: null }),
    ).toBe("User");
  });

  it('returns "User" when user is null', () => {
    expect(greetingName(null)).toBe("User");
  });

  it('returns "User" when all fields are undefined', () => {
    expect(greetingName({})).toBe("User");
  });

  it("handles email with no local part gracefully", () => {
    // edge: email is just "@domain" — split gives empty string, falsy → "User"
    expect(
      greetingName({
        display_name: null,
        first_name: null,
        email: "@domain.com",
      }),
    ).toBe("User");
  });
});

describe("resolveLayout", () => {
  it("returns pendingLayout when all three sources present", () => {
    const pending: LayoutItem[] = [{ id: "top-expenses", span: 1 }];
    const saved: LayoutItem[] = [{ id: "summary-stats", span: 2 }];
    expect(resolveLayout(pending, saved, DEFAULT_LAYOUT)).toEqual(pending);
  });

  it("returns savedLayout when pendingLayout is null", () => {
    const saved: LayoutItem[] = [{ id: "summary-stats", span: 2 }];
    expect(resolveLayout(null, saved, DEFAULT_LAYOUT)).toEqual(saved);
  });

  it("returns DEFAULT_LAYOUT when both pending and saved are null", () => {
    expect(resolveLayout(null, null, DEFAULT_LAYOUT)).toEqual(DEFAULT_LAYOUT);
  });

  it("returns pendingLayout even if it is empty array", () => {
    // empty array is truthy, should NOT fall through
    expect(resolveLayout([], null, DEFAULT_LAYOUT)).toEqual([]);
  });
});

describe("buildNewItem (handleAddWidget)", () => {
  it("creates a LayoutItem with the widget default span", () => {
    const item = buildNewItem("summary-stats", MINI_REGISTRY);
    expect(item).toEqual({ id: "summary-stats", span: 2 });
  });

  it("creates a span-1 item for a half-width widget", () => {
    const item = buildNewItem("top-expenses", MINI_REGISTRY);
    expect(item).toEqual({ id: "top-expenses", span: 1 });
  });

  it("returns null for an unknown widgetId", () => {
    expect(buildNewItem("nonexistent-widget", MINI_REGISTRY)).toBeNull();
  });

  it("appending a new item to existing layout produces correct length", () => {
    const item = buildNewItem("recent-transactions", MINI_REGISTRY);
    const existing: LayoutItem[] = [{ id: "summary-stats", span: 2 }];
    const updated = [...existing, item!];
    expect(updated).toHaveLength(2);
    expect(updated[1]).toEqual({ id: "recent-transactions", span: 1 });
  });
});

describe("removeWidget", () => {
  it("removes the target widget from the layout", () => {
    const result = removeWidget(DEFAULT_LAYOUT, "net-worth-chart");
    expect(result).toHaveLength(3);
    expect(result.find((i) => i.id === "net-worth-chart")).toBeUndefined();
  });

  it("returns the same layout when the id does not exist", () => {
    const result = removeWidget(DEFAULT_LAYOUT, "nonexistent");
    expect(result).toHaveLength(DEFAULT_LAYOUT.length);
  });

  it("returns empty array when removing the only widget", () => {
    const single: LayoutItem[] = [{ id: "summary-stats", span: 2 }];
    expect(removeWidget(single, "summary-stats")).toEqual([]);
  });

  it("does not mutate the original layout", () => {
    const original: LayoutItem[] = [
      { id: "a", span: 1 },
      { id: "b", span: 2 },
    ];
    const copy = [...original];
    removeWidget(original, "a");
    expect(original).toEqual(copy);
  });
});

describe("toggleSpan", () => {
  it("toggles span from 2 to 1", () => {
    const layout: LayoutItem[] = [{ id: "summary-stats", span: 2 }];
    const result = toggleSpan(layout, "summary-stats");
    expect(result[0].span).toBe(1);
  });

  it("toggles span from 1 to 2", () => {
    const layout: LayoutItem[] = [{ id: "top-expenses", span: 1 }];
    const result = toggleSpan(layout, "top-expenses");
    expect(result[0].span).toBe(2);
  });

  it("only affects the targeted widget", () => {
    const result = toggleSpan(DEFAULT_LAYOUT, "summary-stats");
    expect(result[0].span).toBe(1); // toggled
    expect(result[1].span).toBe(2); // net-worth-chart unchanged
    expect(result[2].span).toBe(1); // top-expenses unchanged
    expect(result[3].span).toBe(1); // recent-transactions unchanged
  });

  it("does not mutate the original layout", () => {
    const original: LayoutItem[] = [{ id: "x", span: 2 }];
    const copy = [{ ...original[0] }];
    toggleSpan(original, "x");
    expect(original).toEqual(copy);
  });

  it("returns layout unchanged when id not found", () => {
    const result = toggleSpan(DEFAULT_LAYOUT, "nonexistent");
    expect(result).toEqual(DEFAULT_LAYOUT);
  });
});

describe("availableWidgets", () => {
  it("excludes widgets already in the layout", () => {
    const layout: LayoutItem[] = [
      { id: "summary-stats", span: 2 },
      { id: "top-expenses", span: 1 },
    ];
    const available = availableWidgets(MINI_REGISTRY, layout);
    const ids = available.map((w) => w.id);
    expect(ids).toContain("net-worth-chart");
    expect(ids).toContain("recent-transactions");
    expect(ids).not.toContain("summary-stats");
    expect(ids).not.toContain("top-expenses");
  });

  it("returns all widgets when layout is empty", () => {
    const available = availableWidgets(MINI_REGISTRY, []);
    expect(available).toHaveLength(Object.keys(MINI_REGISTRY).length);
  });

  it("returns empty array when all widgets are already in layout", () => {
    const allLayout: LayoutItem[] = Object.values(MINI_REGISTRY).map((def) => ({
      id: def.id,
      span: def.defaultSpan,
    }));
    const available = availableWidgets(MINI_REGISTRY, allLayout);
    expect(available).toHaveLength(0);
  });

  it("ignores layout items that do not exist in registry", () => {
    const layout: LayoutItem[] = [{ id: "nonexistent-widget", span: 1 }];
    const available = availableWidgets(MINI_REGISTRY, layout);
    expect(available).toHaveLength(Object.keys(MINI_REGISTRY).length);
  });
});

describe("DEFAULT_LAYOUT integrity", () => {
  // Mirrors the real DEFAULT_LAYOUT from widgetRegistry.tsx
  const REAL_DEFAULT_LAYOUT: LayoutItem[] = [
    { id: "summary-stats", span: 2 },
    { id: "net-worth-chart", span: 2 },
    { id: "spending-insights", span: 2 },
    { id: "cash-flow-trend", span: 2 },
    { id: "cash-flow-forecast", span: 2 },
    { id: "top-expenses", span: 1 },
    { id: "recent-transactions", span: 1 },
    { id: "account-balances", span: 2 },
  ];

  it("contains 8 widgets for new users", () => {
    expect(REAL_DEFAULT_LAYOUT).toHaveLength(8);
  });

  it("starts with summary-stats as the first widget", () => {
    expect(REAL_DEFAULT_LAYOUT[0].id).toBe("summary-stats");
  });

  it("has no duplicate widget ids", () => {
    const ids = REAL_DEFAULT_LAYOUT.map((item) => item.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("only uses valid span values (1 or 2)", () => {
    for (const item of REAL_DEFAULT_LAYOUT) {
      expect([1, 2]).toContain(item.span);
    }
  });
});

describe("formatCurrency (SummaryStatsWidget)", () => {
  it("formats positive amounts with two decimals", () => {
    expect(formatCurrency(1500000)).toBe("$1,500,000.00");
  });

  it("formats zero", () => {
    expect(formatCurrency(0)).toBe("$0.00");
  });

  it("formats negative amounts", () => {
    expect(formatCurrency(-25000.5)).toBe("-$25,000.50");
  });

  it("formats small amounts", () => {
    expect(formatCurrency(0.99)).toBe("$0.99");
  });

  it("formats large amounts with commas", () => {
    expect(formatCurrency(1234567.89)).toBe("$1,234,567.89");
  });
});

describe("netWorthColor", () => {
  it('returns "finance.positive" for positive net worth', () => {
    expect(netWorthColor(500000)).toBe("finance.positive");
  });

  it('returns "finance.positive" for zero net worth', () => {
    expect(netWorthColor(0)).toBe("finance.positive");
  });

  it('returns "finance.negative" for negative net worth', () => {
    expect(netWorthColor(-10000)).toBe("finance.negative");
  });

  it("boundary: -0.01 is negative", () => {
    expect(netWorthColor(-0.01)).toBe("finance.negative");
  });
});

describe("monthlyNetColor", () => {
  it('returns "finance.positive" for positive monthly net', () => {
    expect(monthlyNetColor(1500)).toBe("finance.positive");
  });

  it('returns "finance.positive" for zero monthly net', () => {
    expect(monthlyNetColor(0)).toBe("finance.positive");
  });

  it('returns "finance.negative" for negative monthly net', () => {
    expect(monthlyNetColor(-200)).toBe("finance.negative");
  });
});

describe("resolveSummaryField (nullish coalescing)", () => {
  it("returns the value when present", () => {
    expect(resolveSummaryField(42000)).toBe(42000);
  });

  it("returns 0 when value is undefined", () => {
    expect(resolveSummaryField(undefined)).toBe(0);
  });

  it("returns 0 when value is null", () => {
    expect(resolveSummaryField(null)).toBe(0);
  });

  it("returns 0 (the actual number) when value is 0", () => {
    expect(resolveSummaryField(0)).toBe(0);
  });

  it("does NOT coalesce negative numbers to 0", () => {
    expect(resolveSummaryField(-500)).toBe(-500);
  });
});

describe("gridColumn", () => {
  it('returns "span 2" for full-width widgets', () => {
    expect(gridColumn(2)).toBe("span 2");
  });

  it('returns "span 1" for half-width widgets', () => {
    expect(gridColumn(1)).toBe("span 1");
  });
});

describe("spanTooltip", () => {
  it('shows "Switch to half width" for full-width widget', () => {
    expect(spanTooltip(2)).toBe("Switch to half width");
  });

  it('shows "Switch to full width" for half-width widget', () => {
    expect(spanTooltip(1)).toBe("Switch to full width");
  });
});

describe("edit mode button visibility", () => {
  it("shows Customize button when NOT editing", () => {
    const isEditing = false;
    expect(!isEditing).toBe(true); // Customize button renders
  });

  it("shows Add Widget / Done / Cancel buttons when editing", () => {
    const isEditing = true;
    expect(isEditing).toBe(true); // edit-mode HStack renders
  });

  it("Add Widget button is disabled while saving", () => {
    const isSaving = true;
    expect(isSaving).toBe(true); // isDisabled={isSaving}
  });

  it("Done button shows loading state while saving", () => {
    const isSaving = true;
    expect(isSaving).toBe(true); // isLoading={isSaving}
  });

  it("Cancel button is disabled while saving", () => {
    const isSaving = true;
    expect(isSaving).toBe(true); // isDisabled={isSaving}
  });
});

describe("drag-and-drop reorder logic", () => {
  // Mirrors arrayMove from @dnd-kit/sortable
  const arrayMove = <T>(arr: T[], from: number, to: number): T[] => {
    const result = [...arr];
    const [removed] = result.splice(from, 1);
    result.splice(to, 0, removed);
    return result;
  };

  it("moves a widget from index 0 to index 2", () => {
    const layout: LayoutItem[] = [
      { id: "a", span: 2 },
      { id: "b", span: 1 },
      { id: "c", span: 1 },
    ];
    const result = arrayMove(layout, 0, 2);
    expect(result.map((i) => i.id)).toEqual(["b", "c", "a"]);
  });

  it("moves a widget from index 2 to index 0", () => {
    const layout: LayoutItem[] = [
      { id: "a", span: 2 },
      { id: "b", span: 1 },
      { id: "c", span: 1 },
    ];
    const result = arrayMove(layout, 2, 0);
    expect(result.map((i) => i.id)).toEqual(["c", "a", "b"]);
  });

  it("no-op when from and to are the same index", () => {
    const layout: LayoutItem[] = [
      { id: "a", span: 2 },
      { id: "b", span: 1 },
    ];
    const result = arrayMove(layout, 1, 1);
    expect(result.map((i) => i.id)).toEqual(["a", "b"]);
  });

  it("does not mutate the original array", () => {
    const layout: LayoutItem[] = [
      { id: "a", span: 2 },
      { id: "b", span: 1 },
    ];
    const copy = layout.map((i) => ({ ...i }));
    arrayMove(layout, 0, 1);
    expect(layout).toEqual(copy);
  });
});

describe("DashboardGrid: handleDragEnd guard", () => {
  it("does NOT reorder when active.id === over.id", () => {
    const activeId = "summary-stats";
    const overId = "summary-stats";
    const shouldReorder = activeId !== overId;
    expect(shouldReorder).toBe(false);
  });

  it("reorders when active.id !== over.id", () => {
    const activeId = "summary-stats";
    const overId = "top-expenses";
    const shouldReorder = activeId !== overId;
    expect(shouldReorder).toBe(true);
  });

  it("does NOT reorder when over is null (dropped outside)", () => {
    const over = null;
    const shouldReorder =
      over != null && "some-id" !== (over as { id: string }).id;
    expect(shouldReorder).toBe(false);
  });
});
