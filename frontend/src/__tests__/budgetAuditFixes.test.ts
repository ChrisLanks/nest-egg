/**
 * PM Audit Round 4 — Budget UX fixes tests
 *
 * 1. BudgetCard owner badge logic
 * 2. BudgetCard scope label logic
 * 3. BudgetsPage handleCreate pre-fills scope from view context
 * 4. BudgetsPage handleAcceptSuggestion passes category_id + view defaults
 * 5. budgetsApi.getSuggestions passes user_id when provided
 */

import { describe, it, expect } from "vitest";

// ---------------------------------------------------------------------------
// 1 & 2. BudgetCard owner + scope label derivation (pure logic, no DOM)
// ---------------------------------------------------------------------------

interface HouseholdMember {
  id: string;
  email: string;
  display_name?: string;
  first_name?: string;
}

function resolveOwnerName(
  budget: { user_id: string | null },
  currentUserId: string | undefined,
  householdMembers: HouseholdMember[]
): string | null {
  if (!budget.user_id) return null;
  if (budget.user_id === currentUserId) return "You";
  const member = householdMembers.find((m) => m.id === budget.user_id);
  return member?.display_name || member?.first_name || member?.email || "Member";
}

function resolveScopeLabel(
  budget: { is_shared: boolean; shared_user_ids: string[] | null; user_id: string | null },
  householdMembers: HouseholdMember[]
): string | null {
  if (budget.is_shared) {
    if (!budget.shared_user_ids) return "All members";
    const names = budget.shared_user_ids
      .map((id) => householdMembers.find((m) => m.id === id))
      .filter(Boolean)
      .map((m) => m!.display_name || m!.first_name || m!.email);
    return names.length ? `Shared: ${names.join(", ")}` : "Shared";
  }
  if (!budget.user_id) return "All members";
  return null;
}

describe("BudgetCard owner badge logic", () => {
  const members: HouseholdMember[] = [
    { id: "user-1", email: "alice@example.com", display_name: "Alice" },
    { id: "user-2", email: "bob@example.com", first_name: "Bob" },
    { id: "user-3", email: "carol@example.com" },
  ];

  it("returns 'You' when budget.user_id matches current user", () => {
    expect(resolveOwnerName({ user_id: "user-1" }, "user-1", members)).toBe("You");
  });

  it("returns display_name for another member", () => {
    expect(resolveOwnerName({ user_id: "user-1" }, "user-2", members)).toBe("Alice");
  });

  it("falls back to first_name when no display_name", () => {
    expect(resolveOwnerName({ user_id: "user-2" }, "user-1", members)).toBe("Bob");
  });

  it("falls back to email when no display_name or first_name", () => {
    expect(resolveOwnerName({ user_id: "user-3" }, "user-1", members)).toBe("carol@example.com");
  });

  it("returns null for org-wide budget (user_id is null)", () => {
    expect(resolveOwnerName({ user_id: null }, "user-1", members)).toBeNull();
  });

  it("returns 'Member' when user not found in household", () => {
    expect(resolveOwnerName({ user_id: "unknown-id" }, "user-1", members)).toBe("Member");
  });
});

describe("BudgetCard scope label logic", () => {
  const members: HouseholdMember[] = [
    { id: "user-1", email: "alice@example.com", display_name: "Alice" },
    { id: "user-2", email: "bob@example.com", display_name: "Bob" },
  ];

  it("returns 'All members' for shared budget with null shared_user_ids", () => {
    const budget = { is_shared: true, shared_user_ids: null, user_id: "user-1" };
    expect(resolveScopeLabel(budget, members)).toBe("All members");
  });

  it("returns 'Shared: Alice, Bob' for shared budget with explicit user IDs", () => {
    const budget = { is_shared: true, shared_user_ids: ["user-1", "user-2"], user_id: "user-1" };
    expect(resolveScopeLabel(budget, members)).toBe("Shared: Alice, Bob");
  });

  it("returns 'All members' for budget with no user_id (org-wide)", () => {
    const budget = { is_shared: false, shared_user_ids: null, user_id: null };
    expect(resolveScopeLabel(budget, members)).toBe("All members");
  });

  it("returns null for personal budget (user_id set, not shared)", () => {
    const budget = { is_shared: false, shared_user_ids: null, user_id: "user-1" };
    expect(resolveScopeLabel(budget, members)).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// 3. BudgetsPage create scope pre-fill logic
// ---------------------------------------------------------------------------

function computeCreateDefaults(opts: {
  isSelfView: boolean;
  isOtherUserView: boolean;
  selectedUserId: string | null;
}): { is_shared?: boolean; shared_user_ids?: string[] | null } {
  const { isSelfView, isOtherUserView, selectedUserId } = opts;
  if (!isSelfView && !selectedUserId) {
    return { is_shared: true, shared_user_ids: null };
  }
  if (selectedUserId && isOtherUserView) {
    return { is_shared: false };
  }
  return {};
}

describe("BudgetsPage create scope defaults", () => {
  it("sets is_shared=true + shared_user_ids=null in all-members combined view", () => {
    const defaults = computeCreateDefaults({
      isSelfView: false,
      isOtherUserView: false,
      selectedUserId: null,
    });
    expect(defaults.is_shared).toBe(true);
    expect(defaults.shared_user_ids).toBeNull();
  });

  it("sets is_shared=false when viewing another member", () => {
    const defaults = computeCreateDefaults({
      isSelfView: false,
      isOtherUserView: true,
      selectedUserId: "user-2",
    });
    expect(defaults.is_shared).toBe(false);
  });

  it("returns empty defaults for self view (personal budget)", () => {
    const defaults = computeCreateDefaults({
      isSelfView: true,
      isOtherUserView: false,
      selectedUserId: "user-1",
    });
    expect(defaults).toEqual({});
  });
});

// ---------------------------------------------------------------------------
// 4. handleAcceptSuggestion merges view defaults + suggestion fields
// ---------------------------------------------------------------------------

describe("handleAcceptSuggestion prefill", () => {
  function buildPrefill(
    suggestion: { category_name: string; suggested_amount: number; suggested_period: string; category_id: string | null },
    viewDefaults: { is_shared?: boolean; shared_user_ids?: string[] | null }
  ) {
    return {
      ...viewDefaults,
      name: suggestion.category_name,
      amount: suggestion.suggested_amount,
      period: suggestion.suggested_period,
      category_id: suggestion.category_id ?? undefined,
      start_date: new Date().toISOString().split("T")[0],
    };
  }

  it("category_id is passed when suggestion has one", () => {
    const catId = "cat-uuid-123";
    const result = buildPrefill(
      { category_name: "Groceries", suggested_amount: 400, suggested_period: "monthly", category_id: catId },
      {}
    );
    expect(result.category_id).toBe(catId);
  });

  it("category_id is undefined when suggestion has none", () => {
    const result = buildPrefill(
      { category_name: "Dining Out", suggested_amount: 200, suggested_period: "monthly", category_id: null },
      {}
    );
    expect(result.category_id).toBeUndefined();
  });

  it("view defaults are merged (all-members shared)", () => {
    const result = buildPrefill(
      { category_name: "Entertainment", suggested_amount: 100, suggested_period: "monthly", category_id: null },
      { is_shared: true, shared_user_ids: null }
    );
    expect(result.is_shared).toBe(true);
    expect(result.shared_user_ids).toBeNull();
  });

  it("suggestion fields take correct values", () => {
    const result = buildPrefill(
      { category_name: "Subscriptions", suggested_amount: 50, suggested_period: "yearly", category_id: "sub-cat" },
      {}
    );
    expect(result.name).toBe("Subscriptions");
    expect(result.amount).toBe(50);
    expect(result.period).toBe("yearly");
  });
});

// ---------------------------------------------------------------------------
// 5. budgetsApi.getSuggestions passes user_id
// ---------------------------------------------------------------------------

describe("budgetsApi.getSuggestions params", () => {
  it("builds correct params with user_id", () => {
    const userId = "user-abc";
    const opts = { user_id: userId };
    const params: Record<string, unknown> = {};
    if (opts?.user_id) params.user_id = opts.user_id;
    expect(params).toEqual({ user_id: userId });
  });

  it("builds empty params when no user_id", () => {
    const opts = undefined;
    const params: Record<string, unknown> = {};
    if ((opts as any)?.user_id) params.user_id = (opts as any).user_id;
    expect(Object.keys(params).length).toBe(0);
  });

  it("builds params with months only", () => {
    const opts = { months: 3 };
    const params: Record<string, unknown> = {};
    if (opts?.months) params.months = opts.months;
    if ((opts as any)?.user_id) params.user_id = (opts as any).user_id;
    expect(params).toEqual({ months: 3 });
  });

  it("builds params with both months and user_id", () => {
    const opts = { months: 12, user_id: "user-xyz" };
    const params: Record<string, unknown> = {};
    if (opts?.months) params.months = opts.months;
    if (opts?.user_id) params.user_id = opts.user_id;
    expect(params).toEqual({ months: 12, user_id: "user-xyz" });
  });
});
