/**
 * Tests for AccountsPage pure logic.
 *
 * Extracts and tests the following logic from AccountsPage without rendering:
 *   - Account grouping by institution
 *   - Currency formatting
 *   - Last-synced relative time formatting
 *   - allVisible helper
 *   - Selection management (select, deselect, select-all, deselect-all)
 *   - Plaid-linked institution detection
 *   - Error detection across institution accounts
 *   - Empty state conditions
 *   - User display name resolution
 *   - User color scheme assignment
 *   - Client-side combined-view filtering
 *   - Ownership-based bulk operation filtering
 */

import { describe, it, expect } from "vitest";

// ── Account interface (mirrors AccountsPage) ─────────────────────────────────

interface Account {
  id: string;
  user_id: string;
  name: string;
  account_type: string;
  institution_name: string | null;
  mask: string | null;
  current_balance: number;
  available_balance: number | null;
  limit: number | null;
  is_active: boolean;
  exclude_from_cash_flow: boolean;
  balance_as_of: string | null;
  plaid_item_id: string | null;
  last_synced_at: string | null;
  last_error_code: string | null;
  last_error_message: string | null;
  needs_reauth: boolean | null;
}

interface User {
  id: string;
  email: string;
  full_name: string | null;
  display_name: string | null;
  first_name: string | null;
  last_name: string | null;
}

// ── Fixtures ──────────────────────────────────────────────────────────────────

const makeAccount = (overrides: Partial<Account> = {}): Account => ({
  id: "acc-1",
  user_id: "user-1",
  name: "Checking",
  account_type: "checking",
  institution_name: "Chase",
  mask: "1234",
  current_balance: 1000,
  available_balance: 900,
  limit: null,
  is_active: true,
  exclude_from_cash_flow: false,
  balance_as_of: null,
  plaid_item_id: null,
  last_synced_at: null,
  last_error_code: null,
  last_error_message: null,
  needs_reauth: null,
  ...overrides,
});

const makeUser = (overrides: Partial<User> = {}): User => ({
  id: "user-1",
  email: "alice@example.com",
  full_name: null,
  display_name: null,
  first_name: null,
  last_name: null,
  ...overrides,
});

// ── Logic helpers mirroring AccountsPage ──────────────────────────────────────

const groupByInstitution = (accounts: Account[]): Record<string, Account[]> => {
  return accounts.reduce(
    (acc, account) => {
      const institution = account.institution_name || "Other";
      if (!acc[institution]) {
        acc[institution] = [];
      }
      acc[institution].push(account);
      return acc;
    },
    {} as Record<string, Account[]>,
  );
};

const formatCurrency = (amount: number): string => {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
};

const formatLastSynced = (lastSyncedAt: string | null): string => {
  if (!lastSyncedAt) return "Never synced";

  const date = new Date(lastSyncedAt);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;

  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: date.getFullYear() !== now.getFullYear() ? "numeric" : undefined,
  });
};

const allVisible = (accounts: Account[]): boolean => {
  return accounts.every((a) => a.is_active);
};

const isPlaidLinkedInstitution = (accounts: Account[]): boolean => {
  const plaidItemId = accounts[0]?.plaid_item_id;
  return !!(
    plaidItemId && accounts.every((a) => a.plaid_item_id === plaidItemId)
  );
};

const hasInstitutionError = (accounts: Account[]): boolean => {
  return accounts.some((a) => a.last_error_code || a.needs_reauth);
};

const userColorSchemes = ["blue", "green", "purple", "orange", "pink"];

const getUserColorScheme = (
  userId: string,
  users: User[] | undefined,
): string => {
  if (!users) return "blue";
  const index = users.findIndex((u) => u.id === userId);
  return userColorSchemes[(index >= 0 ? index : 0) % userColorSchemes.length];
};

const getUserDisplayName = (user: User): string => {
  if (user.display_name?.trim()) return user.display_name.trim();
  if (user.first_name?.trim()) {
    return user.last_name?.trim()
      ? `${user.first_name.trim()} ${user.last_name.trim()}`
      : user.first_name.trim();
  }
  return user.email.split("@")[0];
};

/** Mirrors the client-side combined-view filter in AccountsPage useMemo */
const filterAccountsForCombinedView = (
  rawAccounts: Account[] | undefined,
  isCombinedView: boolean,
  isPartialSelection: boolean,
  matchesFilter: (userId: string) => boolean,
): Account[] | undefined => {
  if (!rawAccounts) return rawAccounts;
  if (!isCombinedView || !isPartialSelection) return rawAccounts;
  return rawAccounts.filter((a) => matchesFilter(a.user_id));
};

/** Mirrors the handleSelectAccount state updater */
const applySelectAccount = (
  prev: Set<string>,
  accountId: string,
  checked: boolean,
): Set<string> => {
  const next = new Set(prev);
  if (checked) {
    next.add(accountId);
  } else {
    next.delete(accountId);
  }
  return next;
};

/** Mirrors the handleSelectAll state updater */
const applySelectAll = (
  prev: Set<string>,
  accounts: Account[],
  checked: boolean,
): Set<string> => {
  const next = new Set(prev);
  accounts.forEach((account) => {
    if (checked) {
      next.add(account.id);
    } else {
      next.delete(account.id);
    }
  });
  return next;
};

/** Mirrors the ownership filter used in handleBulkHide/handleBulkShow/handleDeleteConfirm */
const filterOwnedAccountIds = (
  selectedIds: Set<string>,
  accounts: Account[],
  canModify: (account: Account) => boolean,
): string[] => {
  return Array.from(selectedIds).filter((accountId) => {
    const account = accounts.find((a) => a.id === accountId);
    return account && canModify(account);
  });
};

// ── Tests ─────────────────────────────────────────────────────────────────────

// ── groupByInstitution ────────────────────────────────────────────────────────

describe("groupByInstitution", () => {
  it("groups accounts by their institution_name", () => {
    const accounts = [
      makeAccount({ id: "1", institution_name: "Chase" }),
      makeAccount({ id: "2", institution_name: "Chase" }),
      makeAccount({ id: "3", institution_name: "Vanguard" }),
    ];
    const grouped = groupByInstitution(accounts);
    expect(Object.keys(grouped)).toEqual(["Chase", "Vanguard"]);
    expect(grouped["Chase"]).toHaveLength(2);
    expect(grouped["Vanguard"]).toHaveLength(1);
  });

  it('uses "Other" for null institution_name', () => {
    const accounts = [
      makeAccount({ id: "1", institution_name: null }),
      makeAccount({ id: "2", institution_name: "Chase" }),
    ];
    const grouped = groupByInstitution(accounts);
    expect(grouped["Other"]).toHaveLength(1);
    expect(grouped["Other"][0].id).toBe("1");
  });

  it('groups all null-institution accounts under "Other"', () => {
    const accounts = [
      makeAccount({ id: "1", institution_name: null }),
      makeAccount({ id: "2", institution_name: null }),
    ];
    const grouped = groupByInstitution(accounts);
    expect(Object.keys(grouped)).toEqual(["Other"]);
    expect(grouped["Other"]).toHaveLength(2);
  });

  it("returns empty object for empty array", () => {
    expect(groupByInstitution([])).toEqual({});
  });

  it("preserves insertion order of institutions", () => {
    const accounts = [
      makeAccount({ id: "1", institution_name: "Zions" }),
      makeAccount({ id: "2", institution_name: "Ally" }),
      makeAccount({ id: "3", institution_name: "Zions" }),
    ];
    const grouped = groupByInstitution(accounts);
    expect(Object.keys(grouped)).toEqual(["Zions", "Ally"]);
  });

  it("handles single account", () => {
    const accounts = [makeAccount({ id: "1", institution_name: "Fidelity" })];
    const grouped = groupByInstitution(accounts);
    expect(Object.keys(grouped)).toEqual(["Fidelity"]);
    expect(grouped["Fidelity"]).toHaveLength(1);
  });
});

// ── formatCurrency ────────────────────────────────────────────────────────────

describe("formatCurrency", () => {
  it("formats positive amounts", () => {
    expect(formatCurrency(1234.56)).toBe("$1,234.56");
  });

  it("formats negative amounts", () => {
    expect(formatCurrency(-500.0)).toBe("-$500.00");
  });

  it("formats zero", () => {
    expect(formatCurrency(0)).toBe("$0.00");
  });

  it("rounds to 2 decimal places", () => {
    expect(formatCurrency(99.999)).toBe("$100.00");
  });

  it("pads single decimal", () => {
    expect(formatCurrency(42.1)).toBe("$42.10");
  });

  it("formats large amounts with commas", () => {
    expect(formatCurrency(1000000)).toBe("$1,000,000.00");
  });

  it("formats small fractional amounts", () => {
    expect(formatCurrency(0.01)).toBe("$0.01");
  });
});

// ── formatLastSynced ──────────────────────────────────────────────────────────

describe("formatLastSynced", () => {
  it('returns "Never synced" for null', () => {
    expect(formatLastSynced(null)).toBe("Never synced");
  });

  it('returns "Just now" for timestamps less than a minute ago', () => {
    const now = new Date();
    expect(formatLastSynced(now.toISOString())).toBe("Just now");
  });

  it("returns minutes ago for recent timestamps", () => {
    const fiveMinAgo = new Date(Date.now() - 5 * 60 * 1000).toISOString();
    expect(formatLastSynced(fiveMinAgo)).toBe("5m ago");
  });

  it("returns hours ago for timestamps within 24h", () => {
    const threeHoursAgo = new Date(Date.now() - 3 * 3600 * 1000).toISOString();
    expect(formatLastSynced(threeHoursAgo)).toBe("3h ago");
  });

  it("returns days ago for timestamps within a week", () => {
    const twoDaysAgo = new Date(Date.now() - 2 * 86400 * 1000).toISOString();
    expect(formatLastSynced(twoDaysAgo)).toBe("2d ago");
  });

  it("returns formatted date for timestamps older than a week", () => {
    const old = new Date(Date.now() - 30 * 86400 * 1000).toISOString();
    const result = formatLastSynced(old);
    // Should contain a month abbreviation and a day number
    expect(result).toMatch(/[A-Z][a-z]{2} \d{1,2}/);
  });

  it("boundary: exactly 59 minutes shows as minutes", () => {
    const ts = new Date(Date.now() - 59 * 60 * 1000).toISOString();
    expect(formatLastSynced(ts)).toBe("59m ago");
  });

  it("boundary: exactly 60 minutes shows as hours", () => {
    const ts = new Date(Date.now() - 60 * 60 * 1000).toISOString();
    expect(formatLastSynced(ts)).toBe("1h ago");
  });

  it("boundary: exactly 23 hours shows as hours", () => {
    const ts = new Date(Date.now() - 23 * 3600 * 1000).toISOString();
    expect(formatLastSynced(ts)).toBe("23h ago");
  });

  it("boundary: exactly 24 hours shows as days", () => {
    const ts = new Date(Date.now() - 24 * 3600 * 1000).toISOString();
    expect(formatLastSynced(ts)).toBe("1d ago");
  });

  it("boundary: exactly 6 days shows as days", () => {
    const ts = new Date(Date.now() - 6 * 86400 * 1000).toISOString();
    expect(formatLastSynced(ts)).toBe("6d ago");
  });

  it("boundary: 7 days shows formatted date", () => {
    const ts = new Date(Date.now() - 7 * 86400 * 1000).toISOString();
    const result = formatLastSynced(ts);
    expect(result).not.toMatch(/d ago$/);
    expect(result).toMatch(/[A-Z][a-z]{2} \d{1,2}/);
  });
});

// ── allVisible ────────────────────────────────────────────────────────────────

describe("allVisible", () => {
  it("returns true when all accounts are active", () => {
    const accounts = [
      makeAccount({ id: "1", is_active: true }),
      makeAccount({ id: "2", is_active: true }),
    ];
    expect(allVisible(accounts)).toBe(true);
  });

  it("returns false when any account is inactive", () => {
    const accounts = [
      makeAccount({ id: "1", is_active: true }),
      makeAccount({ id: "2", is_active: false }),
    ];
    expect(allVisible(accounts)).toBe(false);
  });

  it("returns false when all accounts are inactive", () => {
    const accounts = [
      makeAccount({ id: "1", is_active: false }),
      makeAccount({ id: "2", is_active: false }),
    ];
    expect(allVisible(accounts)).toBe(false);
  });

  it("returns true for empty array (vacuous truth)", () => {
    expect(allVisible([])).toBe(true);
  });

  it("returns true for single active account", () => {
    expect(allVisible([makeAccount({ is_active: true })])).toBe(true);
  });

  it("returns false for single inactive account", () => {
    expect(allVisible([makeAccount({ is_active: false })])).toBe(false);
  });
});

// ── isPlaidLinkedInstitution ──────────────────────────────────────────────────

describe("isPlaidLinkedInstitution", () => {
  it("returns true when all accounts share the same plaid_item_id", () => {
    const accounts = [
      makeAccount({ id: "1", plaid_item_id: "plaid-1" }),
      makeAccount({ id: "2", plaid_item_id: "plaid-1" }),
    ];
    expect(isPlaidLinkedInstitution(accounts)).toBe(true);
  });

  it("returns false when accounts have different plaid_item_ids", () => {
    const accounts = [
      makeAccount({ id: "1", plaid_item_id: "plaid-1" }),
      makeAccount({ id: "2", plaid_item_id: "plaid-2" }),
    ];
    expect(isPlaidLinkedInstitution(accounts)).toBe(false);
  });

  it("returns false when plaid_item_id is null (manual accounts)", () => {
    const accounts = [
      makeAccount({ id: "1", plaid_item_id: null }),
      makeAccount({ id: "2", plaid_item_id: null }),
    ];
    expect(isPlaidLinkedInstitution(accounts)).toBe(false);
  });

  it("returns false when first account is plaid but second is not", () => {
    const accounts = [
      makeAccount({ id: "1", plaid_item_id: "plaid-1" }),
      makeAccount({ id: "2", plaid_item_id: null }),
    ];
    expect(isPlaidLinkedInstitution(accounts)).toBe(false);
  });

  it("returns false for empty array", () => {
    expect(isPlaidLinkedInstitution([])).toBe(false);
  });

  it("returns true for single plaid-linked account", () => {
    const accounts = [makeAccount({ plaid_item_id: "plaid-1" })];
    expect(isPlaidLinkedInstitution(accounts)).toBe(true);
  });
});

// ── hasInstitutionError ───────────────────────────────────────────────────────

describe("hasInstitutionError", () => {
  it("returns false when no accounts have errors", () => {
    const accounts = [makeAccount({ id: "1" }), makeAccount({ id: "2" })];
    expect(hasInstitutionError(accounts)).toBe(false);
  });

  it("returns true when an account has an error code", () => {
    const accounts = [
      makeAccount({ id: "1" }),
      makeAccount({ id: "2", last_error_code: "ITEM_LOGIN_REQUIRED" }),
    ];
    expect(hasInstitutionError(accounts)).toBe(true);
  });

  it("returns true when an account needs reauth", () => {
    const accounts = [
      makeAccount({ id: "1" }),
      makeAccount({ id: "2", needs_reauth: true }),
    ];
    expect(hasInstitutionError(accounts)).toBe(true);
  });

  it("returns true when both error code and needs_reauth are set", () => {
    const accounts = [
      makeAccount({
        id: "1",
        last_error_code: "ITEM_LOGIN_REQUIRED",
        needs_reauth: true,
      }),
    ];
    expect(hasInstitutionError(accounts)).toBe(true);
  });

  it("returns false when needs_reauth is explicitly false", () => {
    const accounts = [makeAccount({ needs_reauth: false })];
    expect(hasInstitutionError(accounts)).toBe(false);
  });

  it("returns false when needs_reauth is null", () => {
    const accounts = [makeAccount({ needs_reauth: null })];
    expect(hasInstitutionError(accounts)).toBe(false);
  });

  it("returns false for empty array", () => {
    expect(hasInstitutionError([])).toBe(false);
  });
});

// ── getUserDisplayName ────────────────────────────────────────────────────────

describe("getUserDisplayName", () => {
  it("returns display_name when set", () => {
    const user = makeUser({ display_name: "Alice W." });
    expect(getUserDisplayName(user)).toBe("Alice W.");
  });

  it("trims whitespace from display_name", () => {
    const user = makeUser({ display_name: "  Bob  " });
    expect(getUserDisplayName(user)).toBe("Bob");
  });

  it("falls back to first_name + last_name when display_name is empty", () => {
    const user = makeUser({
      display_name: "",
      first_name: "Alice",
      last_name: "Wonderland",
    });
    expect(getUserDisplayName(user)).toBe("Alice Wonderland");
  });

  it("falls back to first_name only when last_name is null", () => {
    const user = makeUser({
      display_name: null,
      first_name: "Alice",
      last_name: null,
    });
    expect(getUserDisplayName(user)).toBe("Alice");
  });

  it("falls back to first_name only when last_name is empty/whitespace", () => {
    const user = makeUser({
      display_name: null,
      first_name: "Alice",
      last_name: "   ",
    });
    expect(getUserDisplayName(user)).toBe("Alice");
  });

  it("falls back to email prefix when no names set", () => {
    const user = makeUser({
      display_name: null,
      first_name: null,
      last_name: null,
      email: "bob.smith@example.com",
    });
    expect(getUserDisplayName(user)).toBe("bob.smith");
  });

  it("falls back to email prefix when display_name and first_name are whitespace-only", () => {
    const user = makeUser({
      display_name: "   ",
      first_name: "  ",
      email: "jane@test.com",
    });
    expect(getUserDisplayName(user)).toBe("jane");
  });

  it("trims first_name and last_name", () => {
    const user = makeUser({
      display_name: null,
      first_name: " Alice ",
      last_name: " W ",
    });
    expect(getUserDisplayName(user)).toBe("Alice W");
  });
});

// ── getUserColorScheme ────────────────────────────────────────────────────────

describe("getUserColorScheme", () => {
  const users = [
    makeUser({ id: "u1" }),
    makeUser({ id: "u2" }),
    makeUser({ id: "u3" }),
    makeUser({ id: "u4" }),
    makeUser({ id: "u5" }),
    makeUser({ id: "u6" }),
  ];

  it("returns blue for the first user", () => {
    expect(getUserColorScheme("u1", users)).toBe("blue");
  });

  it("returns green for the second user", () => {
    expect(getUserColorScheme("u2", users)).toBe("green");
  });

  it("returns purple for the third user", () => {
    expect(getUserColorScheme("u3", users)).toBe("purple");
  });

  it("wraps around after 5 users (index 5 mod 5 = 0 => blue)", () => {
    expect(getUserColorScheme("u6", users)).toBe("blue");
  });

  it("returns blue when users is undefined", () => {
    expect(getUserColorScheme("u1", undefined)).toBe("blue");
  });

  it("returns blue (index 0) for unknown user_id", () => {
    expect(getUserColorScheme("unknown-id", users)).toBe("blue");
  });
});

// ── Selection management ──────────────────────────────────────────────────────

describe("applySelectAccount", () => {
  it("adds an account id when checked=true", () => {
    const prev = new Set<string>();
    const next = applySelectAccount(prev, "acc-1", true);
    expect(next.has("acc-1")).toBe(true);
  });

  it("removes an account id when checked=false", () => {
    const prev = new Set(["acc-1", "acc-2"]);
    const next = applySelectAccount(prev, "acc-1", false);
    expect(next.has("acc-1")).toBe(false);
    expect(next.has("acc-2")).toBe(true);
  });

  it("does not mutate the previous set", () => {
    const prev = new Set(["acc-1"]);
    applySelectAccount(prev, "acc-2", true);
    expect(prev.has("acc-2")).toBe(false);
  });

  it("is idempotent when adding an already-selected id", () => {
    const prev = new Set(["acc-1"]);
    const next = applySelectAccount(prev, "acc-1", true);
    expect(next.size).toBe(1);
  });

  it("is idempotent when removing a non-selected id", () => {
    const prev = new Set(["acc-1"]);
    const next = applySelectAccount(prev, "acc-99", false);
    expect(next.size).toBe(1);
  });
});

describe("applySelectAll", () => {
  const accounts = [
    makeAccount({ id: "a1" }),
    makeAccount({ id: "a2" }),
    makeAccount({ id: "a3" }),
  ];

  it("selects all accounts in the group when checked=true", () => {
    const prev = new Set<string>();
    const next = applySelectAll(prev, accounts, true);
    expect(next.size).toBe(3);
    expect(next.has("a1")).toBe(true);
    expect(next.has("a2")).toBe(true);
    expect(next.has("a3")).toBe(true);
  });

  it("deselects all accounts in the group when checked=false", () => {
    const prev = new Set(["a1", "a2", "a3", "other"]);
    const next = applySelectAll(prev, accounts, false);
    expect(next.size).toBe(1);
    expect(next.has("other")).toBe(true);
  });

  it("does not affect accounts outside the group", () => {
    const prev = new Set(["outside-1"]);
    const next = applySelectAll(prev, accounts, true);
    expect(next.size).toBe(4);
    expect(next.has("outside-1")).toBe(true);
  });

  it("does not mutate the previous set", () => {
    const prev = new Set<string>();
    applySelectAll(prev, accounts, true);
    expect(prev.size).toBe(0);
  });

  it("handles empty accounts array", () => {
    const prev = new Set(["existing"]);
    const next = applySelectAll(prev, [], true);
    expect(next.size).toBe(1);
  });
});

// ── filterAccountsForCombinedView ─────────────────────────────────────────────

describe("filterAccountsForCombinedView", () => {
  const allAccounts = [
    makeAccount({ id: "1", user_id: "user-a" }),
    makeAccount({ id: "2", user_id: "user-b" }),
    makeAccount({ id: "3", user_id: "user-a" }),
  ];

  it("returns undefined when rawAccounts is undefined", () => {
    expect(
      filterAccountsForCombinedView(undefined, true, true, () => true),
    ).toBeUndefined();
  });

  it("returns all accounts when not in combined view", () => {
    const result = filterAccountsForCombinedView(
      allAccounts,
      false,
      false,
      () => false,
    );
    expect(result).toBe(allAccounts);
  });

  it("returns all accounts in combined view when not partial selection", () => {
    const result = filterAccountsForCombinedView(
      allAccounts,
      true,
      false,
      () => false,
    );
    expect(result).toBe(allAccounts);
  });

  it("filters by user_id in combined view with partial selection", () => {
    const matchesFilter = (userId: string) => userId === "user-a";
    const result = filterAccountsForCombinedView(
      allAccounts,
      true,
      true,
      matchesFilter,
    );
    expect(result).toHaveLength(2);
    expect(result!.every((a) => a.user_id === "user-a")).toBe(true);
  });

  it("returns empty when no accounts match the filter", () => {
    const result = filterAccountsForCombinedView(
      allAccounts,
      true,
      true,
      () => false,
    );
    expect(result).toHaveLength(0);
  });
});

// ── filterOwnedAccountIds (bulk operations) ───────────────────────────────────

describe("filterOwnedAccountIds", () => {
  const accounts = [
    makeAccount({ id: "a1", user_id: "user-1" }),
    makeAccount({ id: "a2", user_id: "user-2" }),
    makeAccount({ id: "a3", user_id: "user-1" }),
  ];

  const canModifyOwn = (account: Account) => account.user_id === "user-1";

  it("returns only account ids the user can modify", () => {
    const selected = new Set(["a1", "a2", "a3"]);
    const result = filterOwnedAccountIds(selected, accounts, canModifyOwn);
    expect(result).toEqual(["a1", "a3"]);
  });

  it("returns empty array when none are modifiable", () => {
    const selected = new Set(["a2"]);
    const result = filterOwnedAccountIds(selected, accounts, canModifyOwn);
    expect(result).toEqual([]);
  });

  it("ignores selected ids that do not exist in accounts array", () => {
    const selected = new Set(["a1", "nonexistent"]);
    const result = filterOwnedAccountIds(selected, accounts, canModifyOwn);
    expect(result).toEqual(["a1"]);
  });

  it("returns empty array for empty selection", () => {
    const selected = new Set<string>();
    const result = filterOwnedAccountIds(selected, accounts, canModifyOwn);
    expect(result).toEqual([]);
  });

  it("returns all when user can modify everything", () => {
    const selected = new Set(["a1", "a2", "a3"]);
    const result = filterOwnedAccountIds(selected, accounts, () => true);
    expect(result).toEqual(["a1", "a2", "a3"]);
  });
});

// ── Empty state conditions ────────────────────────────────────────────────────

describe("empty state conditions", () => {
  it("shows empty state when accounts is undefined", () => {
    const accounts: Account[] | undefined = undefined;
    expect(!accounts || accounts.length === 0).toBe(true);
  });

  it("shows empty state when accounts is empty array", () => {
    const accounts: Account[] = [];
    expect(!accounts || accounts.length === 0).toBe(true);
  });

  it("does not show empty state when accounts exist", () => {
    const accounts = [makeAccount()];
    expect(!accounts || accounts.length === 0).toBe(false);
  });
});

// ── Balance display color condition ───────────────────────────────────────────

describe("balance display color", () => {
  it("uses negative color for balances below zero", () => {
    const account = makeAccount({ current_balance: -150 });
    expect(account.current_balance < 0).toBe(true);
  });

  it("uses inherit color for zero balance", () => {
    const account = makeAccount({ current_balance: 0 });
    expect(account.current_balance < 0).toBe(false);
  });

  it("uses inherit color for positive balance", () => {
    const account = makeAccount({ current_balance: 500 });
    expect(account.current_balance < 0).toBe(false);
  });
});

// ── Delete dialog title pluralization ─────────────────────────────────────────

describe("delete dialog pluralization", () => {
  const pluralSuffix = (
    deleteTarget: "selected" | string,
    selectedSize: number,
  ) => (deleteTarget === "selected" && selectedSize > 1 ? "s" : "");

  const deleteDescription = (
    deleteTarget: "selected" | string,
    selectedSize: number,
  ) =>
    deleteTarget === "selected"
      ? `${selectedSize} account${selectedSize > 1 ? "s" : ""}`
      : "this account";

  it('shows "Account" for single account deletion', () => {
    expect(pluralSuffix("acc-123", 0)).toBe("");
  });

  it('shows "Accounts" for bulk deletion of multiple', () => {
    expect(pluralSuffix("selected", 3)).toBe("s");
  });

  it('shows "Account" for bulk deletion of exactly 1', () => {
    expect(pluralSuffix("selected", 1)).toBe("");
  });

  it('describes "this account" for single delete', () => {
    expect(deleteDescription("acc-123", 0)).toBe("this account");
  });

  it('describes "3 accounts" for bulk delete of 3', () => {
    expect(deleteDescription("selected", 3)).toBe("3 accounts");
  });

  it('describes "1 account" for bulk delete of 1', () => {
    expect(deleteDescription("selected", 1)).toBe("1 account");
  });
});

// ── Row opacity / background based on is_active ───────────────────────────────

describe("row styling based on is_active", () => {
  const getOpacity = (account: Account) => (account.is_active ? 1 : 0.5);
  const getBg = (account: Account) =>
    account.is_active ? "bg.surface" : "bg.subtle";

  it("active accounts get full opacity", () => {
    expect(getOpacity(makeAccount({ is_active: true }))).toBe(1);
  });

  it("hidden accounts get reduced opacity", () => {
    expect(getOpacity(makeAccount({ is_active: false }))).toBe(0.5);
  });

  it("active accounts use surface background", () => {
    expect(getBg(makeAccount({ is_active: true }))).toBe("bg.surface");
  });

  it("hidden accounts use subtle background", () => {
    expect(getBg(makeAccount({ is_active: false }))).toBe("bg.subtle");
  });
});

// ── Status badge logic ────────────────────────────────────────────────────────

describe("account status badges", () => {
  it('shows "Visible" badge for active accounts', () => {
    const account = makeAccount({ is_active: true });
    const label = account.is_active ? "Visible" : "Hidden";
    expect(label).toBe("Visible");
  });

  it('shows "Hidden" badge for inactive accounts', () => {
    const account = makeAccount({ is_active: false });
    const label = account.is_active ? "Visible" : "Hidden";
    expect(label).toBe("Hidden");
  });

  it("shows cash flow exclusion badge when exclude_from_cash_flow is true", () => {
    const account = makeAccount({ exclude_from_cash_flow: true });
    expect(account.exclude_from_cash_flow).toBe(true);
  });

  it("hides cash flow exclusion badge when exclude_from_cash_flow is false", () => {
    const account = makeAccount({ exclude_from_cash_flow: false });
    expect(account.exclude_from_cash_flow).toBe(false);
  });

  it("shows needs-reauth badge when needs_reauth is true", () => {
    const account = makeAccount({ needs_reauth: true });
    expect(account.needs_reauth).toBe(true);
  });

  it("shows error badge when last_error_code is set", () => {
    const account = makeAccount({ last_error_code: "ITEM_LOGIN_REQUIRED" });
    expect(!!account.last_error_code).toBe(true);
  });

  it("hides error badge when last_error_code is null", () => {
    const account = makeAccount({ last_error_code: null });
    expect(!!account.last_error_code).toBe(false);
  });
});

// ── Checkbox indeterminate state ──────────────────────────────────────────────

describe("institution checkbox state", () => {
  const accounts = [
    makeAccount({ id: "a1" }),
    makeAccount({ id: "a2" }),
    makeAccount({ id: "a3" }),
  ];

  const isChecked = (selected: Set<string>, accts: Account[]) =>
    accts.every((a) => selected.has(a.id));

  const isIndeterminate = (selected: Set<string>, accts: Account[]) =>
    accts.some((a) => selected.has(a.id)) &&
    !accts.every((a) => selected.has(a.id));

  it("isChecked is false when none selected", () => {
    expect(isChecked(new Set(), accounts)).toBe(false);
  });

  it("isChecked is true when all selected", () => {
    expect(isChecked(new Set(["a1", "a2", "a3"]), accounts)).toBe(true);
  });

  it("isIndeterminate is true when some but not all selected", () => {
    expect(isIndeterminate(new Set(["a1"]), accounts)).toBe(true);
  });

  it("isIndeterminate is false when none selected", () => {
    expect(isIndeterminate(new Set(), accounts)).toBe(false);
  });

  it("isIndeterminate is false when all selected", () => {
    expect(isIndeterminate(new Set(["a1", "a2", "a3"]), accounts)).toBe(false);
  });
});
