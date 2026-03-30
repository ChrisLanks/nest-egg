/**
 * Tests for nav visibility logic centralised in useNavDefaults.ts.
 *
 * Three layers:
 * 1. User overrides  (localStorage "nest-egg-nav-visibility")
 * 2. Account/age-based conditional defaults  (buildConditionalDefaults)
 * 3. Always-visible fallback  (?? true)
 *
 * Uses buildConditionalDefaults directly from the hook so tests stay in sync
 * with the single source of truth.
 *
 * @vitest-environment jsdom
 */

import { describe, it, expect, beforeEach } from "vitest";
import { buildConditionalDefaults } from "../../hooks/useNavDefaults";

// ── Account fixture helpers ───────────────────────────────────────────────────

interface Account {
  account_type: string;
  user_id?: string;
  is_rental_property?: boolean;
  plaid_item_id?: string | null;
  plaid_item_hash?: string | null;
}

const checking = (): Account => ({ account_type: "checking" });
const savings = (): Account => ({ account_type: "savings" });
const creditCard = (): Account => ({ account_type: "credit_card" });
const loan = (): Account => ({ account_type: "loan" });
const studentLoan = (): Account => ({ account_type: "student_loan" });
const mortgage = (): Account => ({ account_type: "mortgage" });
const brokerage = (): Account => ({ account_type: "brokerage" });
const ira = (): Account => ({ account_type: "retirement_ira" });
const k401 = (): Account => ({ account_type: "retirement_401k" });
const plan529 = (): Account => ({ account_type: "retirement_529" });
const crypto = (): Account => ({ account_type: "crypto" });
const rental = (): Account => ({
  account_type: "property",
  is_rental_property: true,
});
const nonRentalProperty = (): Account => ({
  account_type: "property",
  is_rental_property: false,
});
const linkedChecking = (): Account => ({
  account_type: "checking",
  plaid_item_id: "plaid-123",
  plaid_item_hash: null,
});
const linkedViaHash = (): Account => ({
  account_type: "checking",
  plaid_item_id: null,
  plaid_item_hash: "hash-abc",
});

// ── localStorage helpers (mirror Layout / PreferencesPage) ───────────────────

const STORAGE_KEY = "nest-egg-nav-visibility";

const loadOverrides = (): Record<string, boolean> => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
};

/** Mirror of Layout isNavVisible — override wins, then account default, then true */
const isNavVisible = (
  path: string,
  overrides: Record<string, boolean>,
  defaults: Record<string, boolean>,
  accountsLoading = false,
): boolean => {
  if (path in overrides) return overrides[path];
  if (accountsLoading) return true;
  return defaults[path] ?? true;
};

// ── /debt-payoff ──────────────────────────────────────────────────────────────

describe("buildConditionalDefaults: /debt-payoff", () => {
  it("hidden with no accounts", () => {
    expect(buildConditionalDefaults([], null)["/debt-payoff"]).toBe(false);
  });
  it("hidden with only checking/savings", () => {
    expect(
      buildConditionalDefaults([checking(), savings()], null)["/debt-payoff"],
    ).toBe(false);
  });
  it("shown with credit_card", () => {
    expect(buildConditionalDefaults([creditCard()], null)["/debt-payoff"]).toBe(
      true,
    );
  });
  it("shown with loan", () => {
    expect(buildConditionalDefaults([loan()], null)["/debt-payoff"]).toBe(true);
  });
  it("shown with student_loan", () => {
    expect(
      buildConditionalDefaults([studentLoan()], null)["/debt-payoff"],
    ).toBe(true);
  });
  it("shown with mortgage (mortgage is also a debt type)", () => {
    expect(buildConditionalDefaults([mortgage()], null)["/debt-payoff"]).toBe(
      true,
    );
  });
});

// ── /mortgage ─────────────────────────────────────────────────────────────────

describe("buildConditionalDefaults: /mortgage", () => {
  it("hidden with no accounts", () => {
    expect(buildConditionalDefaults([], null)["/mortgage"]).toBe(false);
  });
  it("hidden with loan account (not mortgage type)", () => {
    expect(buildConditionalDefaults([loan()], null)["/mortgage"]).toBe(false);
  });
  it("shown when mortgage account exists", () => {
    expect(buildConditionalDefaults([mortgage()], null)["/mortgage"]).toBe(
      true,
    );
  });
  it("shown alongside other account types", () => {
    expect(
      buildConditionalDefaults([checking(), mortgage()], null)["/mortgage"],
    ).toBe(true);
  });
});

// ── /rental-properties ────────────────────────────────────────────────────────

describe("buildConditionalDefaults: /rental-properties", () => {
  it("hidden with no accounts", () => {
    expect(buildConditionalDefaults([], null)["/rental-properties"]).toBe(
      false,
    );
  });
  it("hidden with non-rental property account", () => {
    expect(
      buildConditionalDefaults([nonRentalProperty()], null)[
        "/rental-properties"
      ],
    ).toBe(false);
  });
  it("shown when is_rental_property = true", () => {
    expect(
      buildConditionalDefaults([rental()], null)["/rental-properties"],
    ).toBe(true);
  });
});

// ── investment-gated paths ────────────────────────────────────────────────────

describe("buildConditionalDefaults: /tax-deductible", () => {
  it("hidden with no investments or rental", () => {
    expect(
      buildConditionalDefaults([checking()], null)["/tax-deductible"],
    ).toBe(false);
  });
  it("shown with investment account", () => {
    expect(
      buildConditionalDefaults([brokerage()], null)["/tax-deductible"],
    ).toBe(true);
  });
  it("shown with rental property (no investments)", () => {
    expect(buildConditionalDefaults([rental()], null)["/tax-deductible"]).toBe(
      true,
    );
  });
});

// ── /education (529) ──────────────────────────────────────────────────────────

describe("buildConditionalDefaults: /education", () => {
  it("hidden with no accounts", () => {
    expect(buildConditionalDefaults([], null)["/education"]).toBe(false);
  });
  it("hidden with non-529 retirement account", () => {
    expect(buildConditionalDefaults([ira()], null)["/education"]).toBe(false);
  });
  it("shown with 529 account", () => {
    expect(buildConditionalDefaults([plan529()], null)["/education"]).toBe(
      true,
    );
  });
});

// ── /recurring-bills (linked accounts) ───────────────────────────────────────
// /recurring and /bills were merged into the /recurring-bills hub

describe("buildConditionalDefaults: /recurring-bills", () => {
  it("hidden with no accounts", () => {
    const d = buildConditionalDefaults([], null);
    expect(d["/recurring-bills"]).toBe(false);
  });
  it("hidden with manual (non-linked) account", () => {
    const d = buildConditionalDefaults(
      [
        {
          account_type: "checking",
          plaid_item_id: null,
          plaid_item_hash: null,
        },
      ],
      null,
    );
    expect(d["/recurring-bills"]).toBe(false);
  });
  it("shown when plaid_item_id is set", () => {
    const d = buildConditionalDefaults([linkedChecking()], null);
    expect(d["/recurring-bills"]).toBe(true);
  });
  it("shown when plaid_item_hash is set (Teller/MX)", () => {
    const d = buildConditionalDefaults([linkedViaHash()], null);
    expect(d["/recurring-bills"]).toBe(true);
  });
  it("old /recurring and /bills paths are NOT in the map", () => {
    const d = buildConditionalDefaults([linkedChecking()], null);
    expect("/recurring" in d).toBe(false);
    expect("/bills" in d).toBe(false);
  });
});

// ── /rules ────────────────────────────────────────────────────────────────────

describe("buildConditionalDefaults: /rules", () => {
  it("hidden with no accounts", () => {
    expect(buildConditionalDefaults([], null)["/rules"]).toBe(false);
  });
  it("shown once any account exists (manual checking is enough)", () => {
    expect(buildConditionalDefaults([checking()], null)["/rules"]).toBe(true);
  });
});

// ── Hub paths consolidated into /life-planning, /tax-center, /investment-tools ─
// /ss-claiming, /fire, /tax-projection are no longer individual nav items;
// they are rendered as tabs inside hub pages which are always visible.

describe("buildConditionalDefaults: consolidated hub paths always visible", () => {
  it("/tax-center always true regardless of accounts", () => {
    expect(buildConditionalDefaults([], null)["/tax-center"]).toBe(true);
    expect(buildConditionalDefaults([checking()], null)["/tax-center"]).toBe(true);
  });
  it("/life-planning always true regardless of accounts or age", () => {
    expect(buildConditionalDefaults([], null)["/life-planning"]).toBe(true);
    expect(buildConditionalDefaults([], 35)["/life-planning"]).toBe(true);
  });
  it("/investment-tools always true regardless of accounts", () => {
    expect(buildConditionalDefaults([], null)["/investment-tools"]).toBe(true);
    expect(buildConditionalDefaults([brokerage()], 25)["/investment-tools"]).toBe(true);
  });
  it("old individual paths NOT in conditionalDefaults map (except ss-claiming which is age-gated)", () => {
    const d = buildConditionalDefaults([brokerage()], 35);
    // /ss-claiming is age-gated (shown at 50+), so it IS in the map
    expect("/ss-claiming" in d).toBe(true);
    expect("/fire" in d).toBe(false);
    expect("/tax-projection" in d).toBe(false);
    expect("/hsa" in d).toBe(false);
  });
});

// ── Paths not in the map default to true ─────────────────────────────────────

describe("buildConditionalDefaults: paths not in map default to true via ?? true", () => {
  it("/overview not in map", () => {
    expect(buildConditionalDefaults([], null)["/overview"]).toBeUndefined();
    expect(buildConditionalDefaults([], null)["/overview"] ?? true).toBe(true);
  });
  it("/transactions not in map", () => {
    expect(buildConditionalDefaults([], null)["/transactions"] ?? true).toBe(
      true,
    );
  });
  it("/retirement not in map", () => {
    expect(buildConditionalDefaults([], null)["/retirement"] ?? true).toBe(
      true,
    );
  });
});

// ── Reset to defaults: visibility matches account data (no overrides) ─────────

describe("reset to defaults: post-reset visibility is account-aware", () => {
  it("mortgage visible after reset when mortgage account exists", () => {
    const defaults = buildConditionalDefaults([mortgage()], null);
    expect(isNavVisible("/mortgage", {}, defaults)).toBe(true);
  });
  it("mortgage hidden after reset when no mortgage account", () => {
    const defaults = buildConditionalDefaults([checking()], null);
    expect(isNavVisible("/mortgage", {}, defaults)).toBe(false);
  });
  it("recurring-bills visible after reset with linked bank account", () => {
    const defaults = buildConditionalDefaults([linkedChecking()], null);
    expect(isNavVisible("/recurring-bills", {}, defaults)).toBe(true);
  });
  it("rental-properties hidden after reset without rental account", () => {
    const defaults = buildConditionalDefaults([checking()], null);
    expect(isNavVisible("/rental-properties", {}, defaults)).toBe(false);
  });
  it("hub pages always visible after reset regardless of accounts", () => {
    const defaults = buildConditionalDefaults([], null);
    expect(isNavVisible("/tax-center", {}, defaults)).toBe(true);
    expect(isNavVisible("/life-planning", {}, defaults)).toBe(true);
    expect(isNavVisible("/investment-tools", {}, defaults)).toBe(true);
  });
  it("ss-claiming hidden after reset for user aged 35 (age-gated: requires 50+)", () => {
    // /ss-claiming is age-gated: shown at 50+. Age 35 → condition not met → hidden
    const defaults = buildConditionalDefaults([], 35);
    expect(isNavVisible("/ss-claiming", {}, defaults)).toBe(false);
  });
});

// ── isNavVisible: override priority ───────────────────────────────────────────

describe("isNavVisible: override priority", () => {
  beforeEach(() => localStorage.clear());

  it("override true shows item even when account-default is false", () => {
    const defaults = buildConditionalDefaults([], null);
    expect(isNavVisible("/mortgage", { "/mortgage": true }, defaults)).toBe(
      true,
    );
  });
  it("override false hides item even when account-default is true", () => {
    const defaults = buildConditionalDefaults([mortgage()], null);
    expect(isNavVisible("/mortgage", { "/mortgage": false }, defaults)).toBe(
      false,
    );
  });
  it("shows all items while accounts loading (no override)", () => {
    const defaults = buildConditionalDefaults([], null);
    expect(isNavVisible("/mortgage", {}, defaults, true)).toBe(true);
    expect(isNavVisible("/fire", {}, defaults, true)).toBe(true);
  });
  it("override still wins while loading", () => {
    const defaults = buildConditionalDefaults([], null);
    expect(
      isNavVisible("/mortgage", { "/mortgage": false }, defaults, true),
    ).toBe(false);
  });
  it("localStorage overrides parsed and applied correctly", () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ "/mortgage": false }));
    const overrides = loadOverrides();
    const defaults = buildConditionalDefaults([mortgage()], null);
    expect(isNavVisible("/mortgage", overrides, defaults)).toBe(false);
  });
  it("corrupt localStorage returns empty overrides", () => {
    localStorage.setItem(STORAGE_KEY, "not-json!!!");
    expect(loadOverrides()).toEqual({});
  });
});

// ── UserMenu permissions visibility ──────────────────────────────────────────

describe("Nav: UserMenu permissions visibility", () => {
  const buildMenuItems = (isMultiMemberHousehold: boolean) => [
    { label: "Household Settings", path: "/household" },
    ...(isMultiMemberHousehold
      ? [{ label: "My Permissions", path: "/permissions" }]
      : []),
    { label: "My Preferences", path: "/preferences" },
  ];

  const computeIsMultiMember = (members: unknown[] | null | undefined) =>
    (members?.length ?? 0) >= 2;

  it("single-member: no Permissions item", () => {
    expect(buildMenuItems(false).map((i) => i.label)).not.toContain(
      "My Permissions",
    );
  });
  it("multi-member: shows My Permissions", () => {
    expect(buildMenuItems(true).map((i) => i.label)).toContain(
      "My Permissions",
    );
  });
  it("always shows My Preferences and Household Settings", () => {
    for (const multi of [false, true]) {
      const labels = buildMenuItems(multi).map((i) => i.label);
      expect(labels).toContain("My Preferences");
      expect(labels).toContain("Household Settings");
    }
  });
  it("null/undefined/empty/single → not multi-member", () => {
    expect(computeIsMultiMember(null)).toBe(false);
    expect(computeIsMultiMember(undefined)).toBe(false);
    expect(computeIsMultiMember([])).toBe(false);
    expect(computeIsMultiMember([{}])).toBe(false);
  });
  it("two or more members → multi-member", () => {
    expect(computeIsMultiMember([{}, {}])).toBe(true);
    expect(computeIsMultiMember([{}, {}, {}])).toBe(true);
  });
});

// ── useNavDefaults member filter: queryUserId derivation ─────────────────────
//
// Mirrors the logic in useNavDefaults:
//   queryUserId = selectedUserId ?? memberEffectiveUserId ?? null
//
// This determines what user_id (if any) is sent to the /accounts API.

const USER_CHRIS = "chris-id";
const USER_TEST = "test-user-id";
const USER_TEST2 = "test-user2-id";

function computeNavQueryUserId(
  selectedUserId: string | null | undefined,
  memberEffectiveUserId: string | null | undefined,
): string | null {
  return selectedUserId ?? memberEffectiveUserId ?? null;
}

describe("useNavDefaults: queryUserId derivation", () => {
  it("uses selectedUserId when it is set (single other-user view)", () => {
    expect(computeNavQueryUserId(USER_CHRIS, undefined)).toBe(USER_CHRIS);
  });

  it("uses memberEffectiveUserId when selectedUserId is null (combined, single member selected)", () => {
    expect(computeNavQueryUserId(null, USER_TEST)).toBe(USER_TEST);
  });

  it("returns null when both are null/undefined (all members selected — fetch all)", () => {
    expect(computeNavQueryUserId(null, undefined)).toBeNull();
    expect(computeNavQueryUserId(undefined, undefined)).toBeNull();
    expect(computeNavQueryUserId(null, null)).toBeNull();
  });

  it("returns null when partial selection (2+ members) — memberEffectiveUserId is undefined for partial", () => {
    // Partial multi-select: memberEffectiveUserId=undefined, isPartialMemberSelection=true
    // queryUserId will be null → fetch all, then filter client-side
    expect(computeNavQueryUserId(null, undefined)).toBeNull();
  });

  it("selectedUserId always wins over memberEffectiveUserId", () => {
    // When viewing another user's data, selectedUserId is their ID — member filter is irrelevant
    expect(computeNavQueryUserId(USER_CHRIS, USER_TEST)).toBe(USER_CHRIS);
  });
});

// ── useNavDefaults member filter: client-side account filtering ───────────────
//
// When isPartialMemberSelection=true, accounts are filtered client-side using
// matchesMemberFilter. This mirrors the fix applied to useNavDefaults.

function applyMemberFilter(
  accounts: Account[],
  isPartialMemberSelection: boolean,
  matchesMemberFilter: (userId: string | null | undefined) => boolean,
): Account[] {
  if (!isPartialMemberSelection) return accounts;
  return accounts.filter((a) => matchesMemberFilter(a.user_id));
}

function makeMatcher(selectedIds: Set<string>, isAllSelected: boolean) {
  return (userId: string | null | undefined): boolean => {
    if (isAllSelected) return true;
    if (!userId) return true;
    return selectedIds.has(userId);
  };
}

describe("useNavDefaults: client-side member filter on accounts", () => {
  const chrisChecking: Account = { account_type: "checking", user_id: USER_CHRIS };
  const testSavings: Account = { account_type: "savings", user_id: USER_TEST };
  const test2Mortgage: Account = { account_type: "mortgage", user_id: USER_TEST2 };
  const allAccounts = [chrisChecking, testSavings, test2Mortgage];

  it("returns all accounts when isPartialMemberSelection=false (all selected)", () => {
    const matcher = makeMatcher(new Set([USER_CHRIS, USER_TEST, USER_TEST2]), true);
    const result = applyMemberFilter(allAccounts, false, matcher);
    expect(result).toHaveLength(3);
  });

  it("filters to only selected members when partial selection (Chris + Test User, not test-user2)", () => {
    const selected = new Set([USER_CHRIS, USER_TEST]);
    const matcher = makeMatcher(selected, false);
    const result = applyMemberFilter(allAccounts, true, matcher);
    expect(result).toHaveLength(2);
    expect(result.map((a) => a.user_id)).toContain(USER_CHRIS);
    expect(result.map((a) => a.user_id)).toContain(USER_TEST);
    expect(result.map((a) => a.user_id)).not.toContain(USER_TEST2);
  });

  it("test-user2 mortgage excluded → /mortgage nav item hidden after filter", () => {
    // When only Chris + Test User selected, test-user2's mortgage should be excluded
    const selected = new Set([USER_CHRIS, USER_TEST]);
    const matcher = makeMatcher(selected, false);
    const filtered = applyMemberFilter(allAccounts, true, matcher);
    const defaults = buildConditionalDefaults(filtered, null);
    // No mortgage account in the filtered set → /mortgage should be hidden
    expect(defaults["/mortgage"]).toBe(false);
  });

  it("test-user2 mortgage included when all members selected → /mortgage shown", () => {
    const matcher = makeMatcher(new Set([USER_CHRIS, USER_TEST, USER_TEST2]), true);
    const filtered = applyMemberFilter(allAccounts, false, matcher);
    const defaults = buildConditionalDefaults(filtered, null);
    expect(defaults["/mortgage"]).toBe(true);
  });

  it("accounts with no user_id always pass the filter (legacy items)", () => {
    const legacyAccount: Account = { account_type: "checking" }; // no user_id
    const selected = new Set([USER_CHRIS]);
    const matcher = makeMatcher(selected, false);
    const result = applyMemberFilter([legacyAccount], true, matcher);
    expect(result).toHaveLength(1);
  });

  it("single member selected via memberEffectiveUserId — no client-side filter needed", () => {
    // When exactly one member selected, query uses user_id param → API returns only that user's accounts
    // isPartialMemberSelection=false for single member → filter pass-through
    const matcher = makeMatcher(new Set([USER_CHRIS]), false);
    const result = applyMemberFilter([chrisChecking], false, matcher);
    expect(result).toHaveLength(1);
  });

  it("conditional nav correctly reflects filtered accounts (no debt → debt-payoff hidden)", () => {
    const chrisMortgage: Account = { account_type: "mortgage", user_id: USER_CHRIS };
    const test2CreditCard: Account = { account_type: "credit_card", user_id: USER_TEST2 };
    const selected = new Set([USER_CHRIS]);
    const matcher = makeMatcher(selected, false);
    const filtered = applyMemberFilter([chrisMortgage, test2CreditCard], true, matcher);
    const defaults = buildConditionalDefaults(filtered, null);
    // Chris has mortgage → debt-payoff shown (mortgage is a DEBT_TYPE)
    expect(defaults["/mortgage"]).toBe(true);
    expect(defaults["/debt-payoff"]).toBe(true);
  });
});
