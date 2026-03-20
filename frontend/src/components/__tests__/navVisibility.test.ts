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

describe("buildConditionalDefaults: /investment-health", () => {
  it("hidden with no investment accounts", () => {
    expect(
      buildConditionalDefaults([checking()], null)["/investment-health"],
    ).toBe(false);
  });
  it("shown with brokerage", () => {
    expect(
      buildConditionalDefaults([brokerage()], null)["/investment-health"],
    ).toBe(true);
  });
  it("shown with 401k", () => {
    expect(buildConditionalDefaults([k401()], null)["/investment-health"]).toBe(
      true,
    );
  });
  it("shown with IRA", () => {
    expect(buildConditionalDefaults([ira()], null)["/investment-health"]).toBe(
      true,
    );
  });
  it("shown with crypto", () => {
    expect(
      buildConditionalDefaults([crypto()], null)["/investment-health"],
    ).toBe(true);
  });
});

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

// ── /recurring and /bills (linked accounts) ───────────────────────────────────

describe("buildConditionalDefaults: /recurring and /bills", () => {
  it("both hidden with no accounts", () => {
    const d = buildConditionalDefaults([], null);
    expect(d["/recurring"]).toBe(false);
    expect(d["/bills"]).toBe(false);
  });
  it("both hidden with manual (non-linked) account", () => {
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
    expect(d["/recurring"]).toBe(false);
    expect(d["/bills"]).toBe(false);
  });
  it("both shown when plaid_item_id is set", () => {
    const d = buildConditionalDefaults([linkedChecking()], null);
    expect(d["/recurring"]).toBe(true);
    expect(d["/bills"]).toBe(true);
  });
  it("both shown when plaid_item_hash is set (Teller/MX)", () => {
    const d = buildConditionalDefaults([linkedViaHash()], null);
    expect(d["/recurring"]).toBe(true);
    expect(d["/bills"]).toBe(true);
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

// ── /ss-claiming (age-gated) ──────────────────────────────────────────────────

describe("buildConditionalDefaults: /ss-claiming", () => {
  it("shown when userAge is null (no birthdate set)", () => {
    expect(buildConditionalDefaults([], null)["/ss-claiming"]).toBe(true);
  });
  it("shown for age 50", () => {
    expect(buildConditionalDefaults([], 50)["/ss-claiming"]).toBe(true);
  });
  it("shown for age 65", () => {
    expect(buildConditionalDefaults([], 65)["/ss-claiming"]).toBe(true);
  });
  it("hidden for age 49", () => {
    expect(buildConditionalDefaults([], 49)["/ss-claiming"]).toBe(false);
  });
  it("hidden for age 30", () => {
    expect(buildConditionalDefaults([], 30)["/ss-claiming"]).toBe(false);
  });
});

// ── /fire (investments + under 50) ───────────────────────────────────────────

describe("buildConditionalDefaults: /fire", () => {
  it("hidden with no investments", () => {
    expect(buildConditionalDefaults([checking()], 35)["/fire"]).toBe(false);
  });
  it("hidden when userAge is null (no birthdate)", () => {
    expect(buildConditionalDefaults([brokerage()], null)["/fire"]).toBe(false);
  });
  it("hidden when age >= 50", () => {
    expect(buildConditionalDefaults([brokerage()], 50)["/fire"]).toBe(false);
    expect(buildConditionalDefaults([brokerage()], 65)["/fire"]).toBe(false);
  });
  it("shown for investor under 50", () => {
    expect(buildConditionalDefaults([brokerage()], 35)["/fire"]).toBe(true);
    expect(buildConditionalDefaults([k401()], 49)["/fire"]).toBe(true);
  });
});

// ── /tax-projection ───────────────────────────────────────────────────────────

describe("buildConditionalDefaults: /tax-projection", () => {
  it("hidden with no investment accounts", () => {
    expect(
      buildConditionalDefaults([checking()], null)["/tax-projection"],
    ).toBe(false);
  });
  it("shown with brokerage regardless of age", () => {
    expect(
      buildConditionalDefaults([brokerage()], null)["/tax-projection"],
    ).toBe(true);
    expect(buildConditionalDefaults([brokerage()], 65)["/tax-projection"]).toBe(
      true,
    );
  });
  it("shown with IRA", () => {
    expect(buildConditionalDefaults([ira()], 65)["/tax-projection"]).toBe(true);
  });
  it("shown with crypto", () => {
    expect(buildConditionalDefaults([crypto()], 25)["/tax-projection"]).toBe(
      true,
    );
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
  it("FIRE visible after reset for young investor with investments", () => {
    const defaults = buildConditionalDefaults([brokerage()], 32);
    expect(isNavVisible("/fire", {}, defaults)).toBe(true);
  });
  it("recurring visible after reset with linked bank account", () => {
    const defaults = buildConditionalDefaults([linkedChecking()], null);
    expect(isNavVisible("/recurring", {}, defaults)).toBe(true);
  });
  it("rental-properties hidden after reset without rental account", () => {
    const defaults = buildConditionalDefaults([checking()], null);
    expect(isNavVisible("/rental-properties", {}, defaults)).toBe(false);
  });
  it("investment-health visible after reset with 401k", () => {
    const defaults = buildConditionalDefaults([k401()], null);
    expect(isNavVisible("/investment-health", {}, defaults)).toBe(true);
  });
  it("ss-claiming hidden after reset for user aged 35", () => {
    const defaults = buildConditionalDefaults([], 35);
    expect(isNavVisible("/ss-claiming", {}, defaults)).toBe(false);
  });
  it("tax-projection visible after reset with any investment", () => {
    const defaults = buildConditionalDefaults([ira()], null);
    expect(isNavVisible("/tax-projection", {}, defaults)).toBe(true);
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
