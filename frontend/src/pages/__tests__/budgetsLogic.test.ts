/**
 * Tests for BudgetsPage logic: budget filtering by user, filter tab logic,
 * active/inactive splitting, and permission guards.
 */

import { describe, it, expect } from "vitest";

// ── Types (mirrored from budget.ts) ──────────────────────────────────────────

interface Budget {
  id: string;
  user_id: string | null;
  name: string;
  category_id: string | null;
  label_id: string | null;
  is_active: boolean;
  is_shared: boolean;
  shared_user_ids: string[] | null;
}

type FilterTab = "all" | "category" | "label";

// ── Logic helpers (mirrored from BudgetsPage.tsx) ────────────────────────────

function filterByUser(
  list: Budget[],
  opts: {
    isSelfView: boolean;
    currentUserId: string | null;
    isPartialSelection: boolean;
    matchesFilter: (userId: string | null) => boolean;
    selectedIds: Set<string>;
  },
): Budget[] {
  const {
    isSelfView,
    currentUserId,
    isPartialSelection,
    matchesFilter,
    selectedIds,
  } = opts;

  if (isSelfView && currentUserId) {
    return list.filter((b) => {
      if (b.user_id === currentUserId) return true;
      if (b.is_shared && !b.shared_user_ids) return true;
      if (b.is_shared && b.shared_user_ids?.includes(currentUserId))
        return true;
      if (!b.user_id) return true;
      return false;
    });
  }

  if (isPartialSelection) {
    return list.filter((b) => {
      if (matchesFilter(b.user_id)) return true;
      if (b.is_shared && !b.shared_user_ids) return true;
      if (b.is_shared && b.shared_user_ids?.some((id) => selectedIds.has(id)))
        return true;
      return false;
    });
  }

  return list;
}

function filterByTab(list: Budget[], tab: FilterTab): Budget[] {
  if (tab === "category") return list.filter((b) => !!b.category_id);
  if (tab === "label") return list.filter((b) => !!b.label_id);
  return list;
}

// ── Fixtures ─────────────────────────────────────────────────────────────────

const USER_ID = "user-1";
const OTHER_USER_ID = "user-2";

const BUDGETS: Budget[] = [
  {
    id: "b1",
    user_id: USER_ID,
    name: "Groceries",
    category_id: "cat-1",
    label_id: null,
    is_active: true,
    is_shared: false,
    shared_user_ids: null,
  },
  {
    id: "b2",
    user_id: OTHER_USER_ID,
    name: "Dining Out",
    category_id: "cat-2",
    label_id: null,
    is_active: true,
    is_shared: false,
    shared_user_ids: null,
  },
  {
    id: "b3",
    user_id: USER_ID,
    name: "Tax Prep",
    category_id: null,
    label_id: "label-1",
    is_active: false,
    is_shared: false,
    shared_user_ids: null,
  },
  {
    id: "b4",
    user_id: null,
    name: "Household Shared",
    category_id: null,
    label_id: null,
    is_active: true,
    is_shared: true,
    shared_user_ids: null,
  },
  {
    id: "b5",
    user_id: OTHER_USER_ID,
    name: "Shared with User1",
    category_id: "cat-3",
    label_id: null,
    is_active: true,
    is_shared: true,
    shared_user_ids: [USER_ID, OTHER_USER_ID],
  },
];

// ── Tests ────────────────────────────────────────────────────────────────────

describe("filterByUser — self view", () => {
  const selfOpts = {
    isSelfView: true,
    currentUserId: USER_ID,
    isPartialSelection: false,
    matchesFilter: () => false,
    selectedIds: new Set<string>(),
  };

  it("includes own budgets", () => {
    const result = filterByUser(BUDGETS, selfOpts);
    expect(result.some((b) => b.id === "b1")).toBe(true);
  });

  it("excludes other users' non-shared budgets", () => {
    const result = filterByUser(BUDGETS, selfOpts);
    expect(result.some((b) => b.id === "b2")).toBe(false);
  });

  it("includes shared budgets with no user restriction", () => {
    const result = filterByUser(BUDGETS, selfOpts);
    expect(result.some((b) => b.id === "b4")).toBe(true);
  });

  it("includes shared budgets where current user is in shared_user_ids", () => {
    const result = filterByUser(BUDGETS, selfOpts);
    expect(result.some((b) => b.id === "b5")).toBe(true);
  });

  it("includes budgets with null user_id", () => {
    const result = filterByUser(BUDGETS, selfOpts);
    expect(result.some((b) => b.id === "b4")).toBe(true);
  });
});

describe("filterByUser — combined view (no partial selection)", () => {
  it("returns all budgets when not partial", () => {
    const result = filterByUser(BUDGETS, {
      isSelfView: false,
      currentUserId: USER_ID,
      isPartialSelection: false,
      matchesFilter: () => false,
      selectedIds: new Set<string>(),
    });
    expect(result).toHaveLength(BUDGETS.length);
  });
});

describe("filterByUser — partial member selection", () => {
  it("includes budgets for selected members", () => {
    const result = filterByUser(BUDGETS, {
      isSelfView: false,
      currentUserId: USER_ID,
      isPartialSelection: true,
      matchesFilter: (uid) => uid === USER_ID,
      selectedIds: new Set([USER_ID]),
    });
    // b1 (user_id matches), b4 (shared, no restriction), b5 (shared, user in list)
    expect(result.some((b) => b.id === "b1")).toBe(true);
    expect(result.some((b) => b.id === "b2")).toBe(false);
    expect(result.some((b) => b.id === "b4")).toBe(true);
    expect(result.some((b) => b.id === "b5")).toBe(true);
  });
});

describe("filterByTab", () => {
  it("returns all budgets for 'all' tab", () => {
    const result = filterByTab(BUDGETS, "all");
    expect(result).toHaveLength(BUDGETS.length);
  });

  it("returns only category budgets for 'category' tab", () => {
    const result = filterByTab(BUDGETS, "category");
    expect(result.every((b) => !!b.category_id)).toBe(true);
    expect(result).toHaveLength(3); // b1, b2, b5
  });

  it("returns only label budgets for 'label' tab", () => {
    const result = filterByTab(BUDGETS, "label");
    expect(result.every((b) => !!b.label_id)).toBe(true);
    expect(result).toHaveLength(1); // b3
  });
});

describe("Active/inactive splitting", () => {
  it("separates active and inactive budgets", () => {
    const active = BUDGETS.filter((b) => b.is_active);
    const inactive = BUDGETS.filter((b) => !b.is_active);
    expect(active).toHaveLength(4);
    expect(inactive).toHaveLength(1);
    expect(inactive[0].name).toBe("Tax Prep");
  });
});

describe("Filter badge counts", () => {
  it("counts category budgets", () => {
    const count = BUDGETS.filter((b) => !!b.category_id).length;
    expect(count).toBe(3);
  });

  it("counts label budgets", () => {
    const count = BUDGETS.filter((b) => !!b.label_id).length;
    expect(count).toBe(1);
  });
});

// ── Button disabled logic (mirrors BudgetsPage.tsx) ─────────────────────────

/**
 * Pure function mirroring the "New Budget" button disabled check.
 * The key fix: self-view users can always create, even when
 * isPartialSelection is true (1-of-N members selected = self).
 */
function isCreateDisabled(
  canEdit: boolean,
  isPartialSelection: boolean,
  isSelfView: boolean,
): boolean {
  return !canEdit || (isPartialSelection && !isSelfView);
}

describe("New Budget button — disabled state", () => {
  it("enabled in self view even when isPartialSelection is true", () => {
    expect(isCreateDisabled(true, true, true)).toBe(false);
  });

  it("enabled in combined view with no partial selection", () => {
    expect(isCreateDisabled(true, false, false)).toBe(false);
  });

  it("disabled when canEdit is false", () => {
    expect(isCreateDisabled(false, false, true)).toBe(true);
    expect(isCreateDisabled(false, true, true)).toBe(true);
    expect(isCreateDisabled(false, false, false)).toBe(true);
  });

  it("disabled when partial selection and NOT self view", () => {
    expect(isCreateDisabled(true, true, false)).toBe(true);
  });

  it("enabled when not partial selection and not self view", () => {
    expect(isCreateDisabled(true, false, false)).toBe(false);
  });
});

// ── Period display labels ────────────────────────────────────────────────────

function formatPeriod(
  period: "monthly" | "quarterly" | "semi_annual" | "yearly",
): string {
  switch (period) {
    case "monthly":
      return "Monthly";
    case "quarterly":
      return "Quarterly";
    case "semi_annual":
      return "Every 6 Months";
    case "yearly":
      return "Yearly";
  }
}

describe("Budget period display labels", () => {
  it("formats monthly", () => {
    expect(formatPeriod("monthly")).toBe("Monthly");
  });

  it("formats quarterly", () => {
    expect(formatPeriod("quarterly")).toBe("Quarterly");
  });

  it("formats semi_annual as 'Every 6 Months'", () => {
    expect(formatPeriod("semi_annual")).toBe("Every 6 Months");
  });

  it("formats yearly", () => {
    expect(formatPeriod("yearly")).toBe("Yearly");
  });
});

describe("Empty state detection", () => {
  it("detects when filtered results are empty", () => {
    const active = filterByTab(
      BUDGETS.filter((b) => b.is_active),
      "label",
    );
    const inactive = filterByTab(
      BUDGETS.filter((b) => !b.is_active),
      "label",
    );
    // Only b3 is a label budget, and it's inactive
    expect(active).toHaveLength(0);
    expect(inactive).toHaveLength(1);
    const filteredEmpty = active.length === 0 && inactive.length === 0;
    expect(filteredEmpty).toBe(false);
  });
});

// ── Suggestion visibility rules ─────────────────────────────────────────────

/**
 * Suggestions should only be visible when:
 * - Self view (viewing own data)
 * - Other user view AND canEdit (write permission granted)
 * NOT in combined view (ambiguous who the budget is for)
 */
function shouldShowSuggestions(
  isSelfView: boolean,
  isOtherUserView: boolean,
  canEdit: boolean,
): boolean {
  return isSelfView || (isOtherUserView && canEdit);
}

describe("Budget suggestions visibility", () => {
  it("visible in self view", () => {
    expect(shouldShowSuggestions(true, false, true)).toBe(true);
  });

  it("visible when viewing other user with write permission", () => {
    expect(shouldShowSuggestions(false, true, true)).toBe(true);
  });

  it("hidden in combined view", () => {
    // isSelfView=false, isOtherUserView=false → combined view
    expect(shouldShowSuggestions(false, false, true)).toBe(false);
  });

  it("hidden when viewing other user without write permission", () => {
    expect(shouldShowSuggestions(false, true, false)).toBe(false);
  });
});

// ── Source-level verification ───────────────────────────────────────────────

describe("BudgetsPage suggestion gating", () => {
  it("uses isSelfView and isOtherUserView for suggestion visibility", async () => {
    const fs = await import("fs");
    const source = fs.readFileSync("src/pages/BudgetsPage.tsx", "utf-8");
    // Suggestions should be gated on isSelfView or (isOtherUserView && canEdit)
    expect(source).toContain("isSelfView");
    expect(source).toContain("isOtherUserView && canEdit");
  });
});

// ── Unique budget name per owner (backend contract) ─────────────────────────

describe("Budget unique name constraint", () => {
  it("budget model has unique index on user_id + name", async () => {
    const fs = await import("fs");
    const source = fs.readFileSync("../backend/app/models/budget.py", "utf-8");
    expect(source).toContain("uq_budgets_user_name");
  });

  it("budget service checks for duplicate names on create", async () => {
    const fs = await import("fs");
    const source = fs.readFileSync(
      "../backend/app/services/budget_service.py",
      "utf-8",
    );
    expect(source).toContain("409_CONFLICT");
    expect(source).toMatch(/already have a budget named/);
  });
});
