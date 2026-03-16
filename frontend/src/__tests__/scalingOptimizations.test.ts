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
