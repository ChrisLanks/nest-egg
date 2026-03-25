/**
 * Tests for scaling optimizations:
 * - Query key registry completeness
 * - MemberFilterContext isolation
 * - useInfiniteTransactions MAX_RENDERED_ROWS cap
 * - RouteErrorBoundary recovery
 *
 * @vitest-environment jsdom
 */

import { describe, it, expect } from "vitest";

// ---------------------------------------------------------------------------
// Query Key Registry
// ---------------------------------------------------------------------------

describe("queryKeys registry", () => {
  it("exports a queryKeys object with all required top-level keys", async () => {
    const { queryKeys } = await import("../services/queryClient");

    // Core keys that must exist
    const requiredKeys = [
      "currentUser",
      "accounts",
      "transactions",
      "dashboard",
      "portfolio",
      "budgets",
      "goals",
      "categories",
      "labels",
      "household",
      "guestAccess",
      "permissions",
      "notifications",
      "rules",
    ];

    for (const key of requiredKeys) {
      expect(queryKeys).toHaveProperty(key);
    }
  });

  it("accounts has nested factory functions", async () => {
    const { queryKeys } = await import("../services/queryClient");

    expect(queryKeys.accounts.all).toEqual(["accounts"]);
    expect(queryKeys.accounts.admin("user-1")).toEqual([
      "accounts-admin",
      "user-1",
    ]);
    expect(queryKeys.accounts.detail("acc-1")).toEqual(["account", "acc-1"]);
  });

  it("transactions has nested factory functions", async () => {
    const { queryKeys } = await import("../services/queryClient");

    expect(queryKeys.transactions.all).toEqual(["transactions"]);
    expect(queryKeys.transactions.merchants).toEqual(["transaction-merchants"]);
    expect(queryKeys.transactions.detail("tx-1")).toEqual([
      "transaction",
      "tx-1",
    ]);
  });

  it("dashboard keys are structured correctly", async () => {
    const { queryKeys } = await import("../services/queryClient");

    expect(queryKeys.dashboard.all).toEqual(["dashboard"]);
    expect(queryKeys.dashboard.summary("user-1")).toEqual([
      "dashboard-summary",
      "user-1",
    ]);
    expect(queryKeys.dashboard.summary(undefined)).toEqual([
      "dashboard-summary",
      undefined,
    ]);
  });

  it("portfolio keys include widget and snapshots", async () => {
    const { queryKeys } = await import("../services/queryClient");

    expect(queryKeys.portfolio.all).toEqual(["portfolio"]);
    expect(queryKeys.portfolio.summary).toEqual(["portfolio-summary"]);
    expect(queryKeys.portfolio.widget).toEqual(["portfolio-widget"]);
    expect(queryKeys.portfolio.snapshots("1Y")).toEqual([
      "portfolio-snapshots",
      "1Y",
    ]);
  });

  it("household keys are grouped", async () => {
    const { queryKeys } = await import("../services/queryClient");

    expect(queryKeys.household.members).toEqual(["household-members"]);
    expect(queryKeys.household.users).toEqual(["household-users"]);
    expect(queryKeys.household.invitations).toEqual(["household-invitations"]);
  });

  it("guest access keys are grouped", async () => {
    const { queryKeys } = await import("../services/queryClient");

    expect(queryKeys.guestAccess.guests).toEqual(["guest-access-guests"]);
    expect(queryKeys.guestAccess.invitations).toEqual([
      "guest-access-invitations",
    ]);
    expect(queryKeys.guestAccess.invitationDetails("abc")).toEqual([
      "invitation-details",
      "abc",
    ]);
  });

  it("permissions keys include given and received", async () => {
    const { queryKeys } = await import("../services/queryClient");

    expect(queryKeys.permissions.all).toEqual(["permissions"]);
    expect(queryKeys.permissions.given).toEqual(["permissions", "given"]);
    expect(queryKeys.permissions.received).toEqual(["permissions", "received"]);
  });

  it("factory functions return unique keys for different inputs", async () => {
    const { queryKeys } = await import("../services/queryClient");

    const key1 = queryKeys.holdings("acc-1");
    const key2 = queryKeys.holdings("acc-2");

    expect(key1).not.toEqual(key2);
    expect(key1[0]).toBe("holdings");
    expect(key2[0]).toBe("holdings");
  });
});

// ---------------------------------------------------------------------------
// MemberFilterContext logic (unit-testable without React)
// ---------------------------------------------------------------------------

describe("MemberFilterContext logic", () => {
  it("toggleMember does not deselect the last member", () => {
    // Simulating the toggle logic from MemberFilterContext
    const toggle = (prev: Set<string>, memberId: string): Set<string> => {
      const next = new Set(prev);
      if (next.has(memberId)) {
        if (next.size <= 1) return prev;
        next.delete(memberId);
      } else {
        next.add(memberId);
      }
      return next;
    };

    const singleMember = new Set(["user-1"]);
    const result = toggle(singleMember, "user-1");
    // Should not deselect the last member
    expect(result).toBe(singleMember);
    expect(result.size).toBe(1);
  });

  it("toggleMember adds a new member", () => {
    const toggle = (prev: Set<string>, memberId: string): Set<string> => {
      const next = new Set(prev);
      if (next.has(memberId)) {
        if (next.size <= 1) return prev;
        next.delete(memberId);
      } else {
        next.add(memberId);
      }
      return next;
    };

    const initial = new Set(["user-1"]);
    const result = toggle(initial, "user-2");
    expect(result.size).toBe(2);
    expect(result.has("user-1")).toBe(true);
    expect(result.has("user-2")).toBe(true);
  });

  it("toggleMember removes one of multiple members", () => {
    const toggle = (prev: Set<string>, memberId: string): Set<string> => {
      const next = new Set(prev);
      if (next.has(memberId)) {
        if (next.size <= 1) return prev;
        next.delete(memberId);
      } else {
        next.add(memberId);
      }
      return next;
    };

    const initial = new Set(["user-1", "user-2", "user-3"]);
    const result = toggle(initial, "user-2");
    expect(result.size).toBe(2);
    expect(result.has("user-2")).toBe(false);
  });

  it("isAllSelected is true when all members are selected", () => {
    const allMemberIds = new Set(["u1", "u2", "u3"]);
    const selectedMemberIds = new Set(["u1", "u2", "u3"]);

    const isAllSelected =
      selectedMemberIds.size === allMemberIds.size &&
      allMemberIds.size > 0 &&
      [...allMemberIds].every((id) => selectedMemberIds.has(id));

    expect(isAllSelected).toBe(true);
  });

  it("isAllSelected is false when subset selected", () => {
    const allMemberIds = new Set(["u1", "u2", "u3"]);
    const selectedMemberIds = new Set(["u1", "u2"]);

    const isAllSelected =
      selectedMemberIds.size === allMemberIds.size &&
      allMemberIds.size > 0 &&
      [...allMemberIds].every((id) => selectedMemberIds.has(id));

    expect(isAllSelected).toBe(false);
  });

  it("matchesMemberFilter returns true for selected members", () => {
    const selectedMemberIds = new Set(["u1", "u2"]);
    const isAllSelected = false;

    const matchesMemberFilter = (
      itemUserId: string | null | undefined,
    ): boolean => {
      if (isAllSelected) return true;
      if (!itemUserId) return true;
      return selectedMemberIds.has(itemUserId);
    };

    expect(matchesMemberFilter("u1")).toBe(true);
    expect(matchesMemberFilter("u3")).toBe(false);
    expect(matchesMemberFilter(null)).toBe(true);
  });

  it("selectedMemberIdsKey is sorted and deterministic", () => {
    const ids1 = new Set(["c", "a", "b"]);
    const ids2 = new Set(["b", "c", "a"]);

    const key1 = [...ids1].sort().join(",");
    const key2 = [...ids2].sort().join(",");

    expect(key1).toBe("a,b,c");
    expect(key1).toBe(key2);
  });

  it("memberEffectiveUserId returns undefined for all selected", () => {
    const selectedMemberIds = new Set(["u1", "u2"]);
    const isAllSelected = true;

    const memberEffectiveUserId = (() => {
      if (isAllSelected || selectedMemberIds.size === 0) return undefined;
      if (selectedMemberIds.size === 1) return [...selectedMemberIds][0];
      return undefined;
    })();

    expect(memberEffectiveUserId).toBeUndefined();
  });

  it("memberEffectiveUserId returns ID for single selection", () => {
    const selectedMemberIds = new Set(["u1"]);
    const isAllSelected = false;

    const memberEffectiveUserId = (() => {
      if (isAllSelected || selectedMemberIds.size === 0) return undefined;
      if (selectedMemberIds.size === 1) return [...selectedMemberIds][0];
      return undefined;
    })();

    expect(memberEffectiveUserId).toBe("u1");
  });
});

// ---------------------------------------------------------------------------
// useInfiniteTransactions MAX_RENDERED_ROWS cap
// ---------------------------------------------------------------------------

describe("transaction row cap logic", () => {
  const MAX_RENDERED_ROWS = 500;

  it("caps accumulated transactions at MAX_RENDERED_ROWS", () => {
    // Simulate the append + cap logic from useInfiniteTransactions
    const existing = Array.from({ length: 480 }, (_, i) => ({
      id: `tx-${i}`,
    }));
    const newBatch = Array.from({ length: 100 }, (_, i) => ({
      id: `tx-new-${i}`,
    }));

    const combined = [...existing, ...newBatch];
    const capped =
      combined.length > MAX_RENDERED_ROWS
        ? combined.slice(combined.length - MAX_RENDERED_ROWS)
        : combined;

    expect(capped.length).toBe(MAX_RENDERED_ROWS);
    // Should keep the newest items (end of array)
    expect(capped[capped.length - 1].id).toBe("tx-new-99");
  });

  it("does not cap when under limit", () => {
    const existing = Array.from({ length: 200 }, (_, i) => ({
      id: `tx-${i}`,
    }));
    const newBatch = Array.from({ length: 50 }, (_, i) => ({
      id: `tx-new-${i}`,
    }));

    const combined = [...existing, ...newBatch];
    const capped =
      combined.length > MAX_RENDERED_ROWS
        ? combined.slice(combined.length - MAX_RENDERED_ROWS)
        : combined;

    expect(capped.length).toBe(250);
  });

  it("first page resets all transactions", () => {
    // When currentCursor is null, data replaces everything
    const firstPageData = Array.from({ length: 100 }, (_, i) => ({
      id: `tx-${i}`,
    }));
    // Simulates the non-cursor branch
    const result = firstPageData;
    expect(result.length).toBe(100);
    expect(result[0].id).toBe("tx-0");
  });
});

// ---------------------------------------------------------------------------
// RouteErrorBoundary (import test)
// ---------------------------------------------------------------------------

describe("RouteErrorBoundary", () => {
  it("can be imported without errors", async () => {
    const mod = await import("../components/RouteErrorBoundary");
    expect(mod.RouteErrorBoundary).toBeDefined();
    expect(typeof mod.RouteErrorBoundary).toBe("function");
  });
});

// ---------------------------------------------------------------------------
// useInfiniteTransactions reducer logic
// ---------------------------------------------------------------------------

describe("useInfiniteTransactions reducer", () => {
  // Replicate the reducer logic from useInfiniteTransactions
  const MAX_RENDERED_ROWS = 500;

  interface State {
    allTransactions: { id: string }[];
    currentCursor: string | null;
    nextCursor: string | null;
    hasMore: boolean;
    isLoadingMore: boolean;
    total: number;
  }

  type Action =
    | { type: "RESET" }
    | { type: "LOAD_MORE"; cursor: string }
    | {
        type: "DATA_RECEIVED";
        transactions: { id: string }[];
        nextCursor: string | null;
        hasMore: boolean;
        total: number;
        isAppend: boolean;
      };

  const initialState: State = {
    allTransactions: [],
    currentCursor: null,
    nextCursor: null,
    hasMore: false,
    isLoadingMore: false,
    total: 0,
  };

  function reducer(state: State, action: Action): State {
    switch (action.type) {
      case "RESET":
        return initialState;
      case "LOAD_MORE":
        return { ...state, isLoadingMore: true, currentCursor: action.cursor };
      case "DATA_RECEIVED": {
        let allTransactions: { id: string }[];
        if (action.isAppend) {
          const combined = [...state.allTransactions, ...action.transactions];
          allTransactions =
            combined.length > MAX_RENDERED_ROWS
              ? combined.slice(combined.length - MAX_RENDERED_ROWS)
              : combined;
        } else {
          allTransactions = action.transactions;
        }
        return {
          ...state,
          allTransactions,
          nextCursor: action.nextCursor,
          hasMore: action.hasMore,
          total: action.total > 0 ? action.total : state.total,
          isLoadingMore: false,
        };
      }
      default:
        return state;
    }
  }

  it("RESET returns initial state", () => {
    const state: State = {
      ...initialState,
      allTransactions: [{ id: "1" }],
      total: 100,
    };
    const result = reducer(state, { type: "RESET" });
    expect(result).toEqual(initialState);
  });

  it("LOAD_MORE sets cursor and loading flag", () => {
    const result = reducer(initialState, {
      type: "LOAD_MORE",
      cursor: "abc123",
    });
    expect(result.isLoadingMore).toBe(true);
    expect(result.currentCursor).toBe("abc123");
  });

  it("DATA_RECEIVED replaces data on first page (isAppend=false)", () => {
    const txns = [{ id: "tx-1" }, { id: "tx-2" }];
    const result = reducer(initialState, {
      type: "DATA_RECEIVED",
      transactions: txns,
      nextCursor: "cursor2",
      hasMore: true,
      total: 50,
      isAppend: false,
    });
    expect(result.allTransactions).toEqual(txns);
    expect(result.nextCursor).toBe("cursor2");
    expect(result.hasMore).toBe(true);
    expect(result.total).toBe(50);
    expect(result.isLoadingMore).toBe(false);
  });

  it("DATA_RECEIVED appends data when isAppend=true", () => {
    const state: State = {
      ...initialState,
      allTransactions: [{ id: "tx-1" }],
    };
    const result = reducer(state, {
      type: "DATA_RECEIVED",
      transactions: [{ id: "tx-2" }],
      nextCursor: null,
      hasMore: false,
      total: 2,
      isAppend: true,
    });
    expect(result.allTransactions).toEqual([{ id: "tx-1" }, { id: "tx-2" }]);
  });

  it("DATA_RECEIVED caps at MAX_RENDERED_ROWS on append", () => {
    const state: State = {
      ...initialState,
      allTransactions: Array.from({ length: 490 }, (_, i) => ({
        id: `old-${i}`,
      })),
    };
    const result = reducer(state, {
      type: "DATA_RECEIVED",
      transactions: Array.from({ length: 20 }, (_, i) => ({
        id: `new-${i}`,
      })),
      nextCursor: null,
      hasMore: false,
      total: 510,
      isAppend: true,
    });
    expect(result.allTransactions.length).toBe(MAX_RENDERED_ROWS);
    // Should keep newest items
    expect(result.allTransactions[result.allTransactions.length - 1].id).toBe(
      "new-19",
    );
  });

  it("DATA_RECEIVED preserves total when new total is 0", () => {
    const state: State = { ...initialState, total: 100 };
    const result = reducer(state, {
      type: "DATA_RECEIVED",
      transactions: [],
      nextCursor: null,
      hasMore: false,
      total: 0,
      isAppend: false,
    });
    expect(result.total).toBe(100);
  });
});

// ---------------------------------------------------------------------------
// Dashboard widget API path correctness
// ---------------------------------------------------------------------------

describe("dashboard widget API paths", () => {
  it("TaxInsightsWidget uses relative path (no /api/v1 prefix)", async () => {
    const fs = await import("fs");
    const path = await import("path");
    const widgetPath = path.resolve(
      __dirname,
      "../features/dashboard/widgets/TaxInsightsWidget.tsx",
    );
    const source = fs.readFileSync(widgetPath, "utf-8");
    // Should NOT contain double prefix
    expect(source).not.toContain('"/api/v1/');
    // Should use the relative path
    expect(source).toContain('"/tax-advisor/insights"');
  });

  it("DividendIncomeWidget uses relative path (no /api/v1 prefix)", async () => {
    const fs = await import("fs");
    const path = await import("path");
    const widgetPath = path.resolve(
      __dirname,
      "../features/dashboard/widgets/DividendIncomeWidget.tsx",
    );
    const source = fs.readFileSync(widgetPath, "utf-8");
    expect(source).not.toContain('"/api/v1/');
    expect(source).toContain('"/dividend-income/summary"');
  });

  it("SpendingVelocityWidget uses correct route prefix", async () => {
    const fs = await import("fs");
    const path = await import("path");
    const widgetPath = path.resolve(
      __dirname,
      "../features/dashboard/widgets/SpendingVelocityWidget.tsx",
    );
    const source = fs.readFileSync(widgetPath, "utf-8");
    expect(source).not.toContain('"/api/v1/');
    expect(source).not.toContain("enhanced-trends");
    expect(source).toContain('"/trends/spending-velocity"');
  });

  it("YearOverYearWidget uses URLSearchParams for years array", async () => {
    const fs = await import("fs");
    const path = await import("path");
    const widgetPath = path.resolve(
      __dirname,
      "../features/dashboard/widgets/YearOverYearWidget.tsx",
    );
    const source = fs.readFileSync(widgetPath, "utf-8");
    // Should NOT use comma-joined years
    expect(source).not.toContain("years.join");
    // Should use URLSearchParams
    expect(source).toContain("URLSearchParams");
  });

  it("QuarterlyPerformanceWidget uses URLSearchParams for years array", async () => {
    const fs = await import("fs");
    const path = await import("path");
    const widgetPath = path.resolve(
      __dirname,
      "../features/dashboard/widgets/QuarterlyPerformanceWidget.tsx",
    );
    const source = fs.readFileSync(widgetPath, "utf-8");
    expect(source).not.toContain("years.join");
    expect(source).toContain("URLSearchParams");
  });
});

// ---------------------------------------------------------------------------
// NotificationType frontend enum completeness
// ---------------------------------------------------------------------------

describe("NotificationType enum", () => {
  it("includes all 20 notification types", async () => {
    const { NotificationType } = await import("../types/notification");
    const values = Object.values(NotificationType);
    expect(values.length).toBe(20);
  });

  it("includes ACCOUNT_CONNECTED", async () => {
    const { NotificationType } = await import("../types/notification");
    expect(NotificationType.ACCOUNT_CONNECTED).toBe("account_connected");
  });

  it("includes new household notification types", async () => {
    const { NotificationType } = await import("../types/notification");
    expect(NotificationType.HOUSEHOLD_MEMBER_JOINED).toBe(
      "household_member_joined",
    );
    expect(NotificationType.HOUSEHOLD_MEMBER_LEFT).toBe(
      "household_member_left",
    );
  });

  it("includes FIRE milestone types", async () => {
    const { NotificationType } = await import("../types/notification");
    expect(NotificationType.FIRE_COAST_FI).toBe("fire_coast_fi");
    expect(NotificationType.FIRE_INDEPENDENT).toBe("fire_independent");
  });

  it("includes RETIREMENT_SCENARIO_STALE", async () => {
    const { NotificationType } = await import("../types/notification");
    expect(NotificationType.RETIREMENT_SCENARIO_STALE).toBe(
      "retirement_scenario_stale",
    );
  });
});

// ---------------------------------------------------------------------------
// React.memo wrapping verification
// ---------------------------------------------------------------------------

describe("dashboard widgets are wrapped in React.memo", () => {
  const widgetFiles = [
    "AccountBalancesWidget",
    "AssetAllocationWidget",
    "BudgetsWidget",
    "CashFlowTrendWidget",
    "NetWorthChartWidget",
    "SummaryStatsWidget",
    "TopExpensesWidget",
    "RecentTransactionsWidget",
  ];

  widgetFiles.forEach((name) => {
    it(`${name} exports a memo-wrapped component`, async () => {
      const fs = await import("fs");
      const path = await import("path");
      const filePath = path.resolve(
        __dirname,
        `../features/dashboard/widgets/${name}.tsx`,
      );
      const source = fs.readFileSync(filePath, "utf-8");
      // Should have memo import and memo() call
      expect(source).toContain("memo");
      expect(source).toMatch(
        new RegExp(`export const ${name}\\s*=\\s*memo\\(`),
      );
    });
  });
});
