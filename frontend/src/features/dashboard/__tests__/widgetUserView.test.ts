/**
 * Tests for dashboard widget user-view filtering logic.
 *
 * All dashboard widgets should include selectedUserId in their React Query
 * queryKey and pass user_id to the API when a user is selected. These tests
 * verify the query key construction and API params logic without rendering.
 */

import { describe, it, expect } from "vitest";

// ── Helpers mirroring widget patterns ──────────────────────────────────────

/**
 * Builds query key for a widget that depends on selectedUserId.
 * Mirrors: queryKey: ["widget-name", ...otherKeys, selectedUserId]
 */
const buildQueryKey = (
  baseName: string,
  otherKeys: unknown[],
  selectedUserId: string | null,
): unknown[] => [baseName, ...otherKeys, selectedUserId];

/**
 * Builds API params for widgets that pass user_id to the backend.
 * Mirrors the pattern used across InsightsCard, ForecastChart, etc.
 */
const buildApiParams = (
  baseParams: Record<string, unknown>,
  selectedUserId: string | null,
): Record<string, unknown> => {
  const params = { ...baseParams };
  if (selectedUserId) {
    params.user_id = selectedUserId;
  }
  return params;
};

// ── Tests ──────────────────────────────────────────────────────────────────

describe("Widget queryKey includes selectedUserId", () => {
  it("spending-insights key with null user", () => {
    const key = buildQueryKey("spending-insights", [], null);
    expect(key).toEqual(["spending-insights", null]);
  });

  it("spending-insights key with selected user", () => {
    const uid = "user-123";
    const key = buildQueryKey("spending-insights", [], uid);
    expect(key).toEqual(["spending-insights", "user-123"]);
  });

  it("cash-flow-forecast key includes timeRange and userId", () => {
    const key = buildQueryKey("cash-flow-forecast", [30], "user-456");
    expect(key).toEqual(["cash-flow-forecast", 30, "user-456"]);
  });

  it("historical-net-worth key includes all params", () => {
    const key = buildQueryKey(
      "historical-net-worth",
      ["1Y", null, null],
      "user-789",
    );
    expect(key).toEqual(["historical-net-worth", "1Y", null, null, "user-789"]);
  });

  it("different userId produces different key (cache invalidation)", () => {
    const key1 = buildQueryKey("spending-insights", [], "user-a");
    const key2 = buildQueryKey("spending-insights", [], "user-b");
    expect(key1).not.toEqual(key2);
  });

  it("null vs string userId produces different key", () => {
    const key1 = buildQueryKey("spending-insights", [], null);
    const key2 = buildQueryKey("spending-insights", [], "user-a");
    expect(key1).not.toEqual(key2);
  });
});

describe("Widget API params pass user_id correctly", () => {
  it("no user_id when selectedUserId is null", () => {
    const params = buildApiParams({}, null);
    expect(params).toEqual({});
    expect("user_id" in params).toBe(false);
  });

  it("includes user_id when selectedUserId is set", () => {
    const params = buildApiParams({}, "user-123");
    expect(params).toEqual({ user_id: "user-123" });
  });

  it("preserves existing params alongside user_id", () => {
    const params = buildApiParams({ days_ahead: 30 }, "user-123");
    expect(params).toEqual({ days_ahead: 30, user_id: "user-123" });
  });

  it("preserves existing params when no user selected", () => {
    const params = buildApiParams({ days_ahead: 30 }, null);
    expect(params).toEqual({ days_ahead: 30 });
  });

  it("empty string userId is treated as no selection", () => {
    // Empty string is falsy, so no user_id should be added
    const params = buildApiParams({}, "" as unknown as null);
    expect("user_id" in params).toBe(false);
  });
});

describe("Widget user-view: affected widgets list", () => {
  /**
   * All widgets that should honor user selection.
   * This list serves as documentation and a regression check.
   */
  const WIDGETS_WITH_USER_VIEW = [
    "InsightsCard",
    "ForecastChart",
    "NetWorthChartWidget",
    "FinancialHealthWidget",
    "AssetAllocationWidget",
    "SubscriptionsWidget",
    "BudgetsWidget",
    "SavingsGoalsWidget",
    "UpcomingBillsWidget",
    "InvestmentPerformanceWidget",
    "RetirementReadinessWidget",
    "FireMetricsWidget",
  ];

  it("has 12 widgets that honor user view", () => {
    expect(WIDGETS_WITH_USER_VIEW).toHaveLength(12);
  });

  it("all names are unique", () => {
    const unique = new Set(WIDGETS_WITH_USER_VIEW);
    expect(unique.size).toBe(WIDGETS_WITH_USER_VIEW.length);
  });
});
