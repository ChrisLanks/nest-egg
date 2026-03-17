/**
 * Tests for accountTypeGroups — verifies group membership for all account
 * types, with special focus on Trump Account, Trust, and UGMA/UTMA.
 */

import { describe, it, expect } from "vitest";
import { AccountType } from "../../types/account";
import {
  TRADITIONAL_IRA_TYPES,
  ALL_RETIREMENT_TYPES,
  CONTRIBUTION_ACCOUNT_TYPES,
  HOLDINGS_ACCOUNT_TYPES,
  ASSET_ACCOUNT_TYPES,
  DEBT_ACCOUNT_TYPES,
  TAX_TREATMENT_ACCOUNT_TYPES,
  EMPLOYER_PLAN_TYPES,
  ROTH_TYPES,
  TAX_FREE_SAVINGS_TYPES,
  ACCOUNT_TYPE_SIDEBAR_CONFIG,
} from "../accountTypeGroups";

// ---------------------------------------------------------------------------
// Trump Account group membership
// ---------------------------------------------------------------------------

describe("Trump Account group membership", () => {
  it("is in TRADITIONAL_IRA_TYPES", () => {
    expect(TRADITIONAL_IRA_TYPES).toContain(AccountType.TRUMP_ACCOUNT);
  });

  it("is in ALL_RETIREMENT_TYPES (via TRADITIONAL_IRA_TYPES spread)", () => {
    expect(ALL_RETIREMENT_TYPES).toContain(AccountType.TRUMP_ACCOUNT);
  });

  it("is in CONTRIBUTION_ACCOUNT_TYPES", () => {
    expect(CONTRIBUTION_ACCOUNT_TYPES).toContain(AccountType.TRUMP_ACCOUNT);
  });

  it("is in HOLDINGS_ACCOUNT_TYPES", () => {
    expect(HOLDINGS_ACCOUNT_TYPES).toContain(AccountType.TRUMP_ACCOUNT);
  });

  it("is in TAX_TREATMENT_ACCOUNT_TYPES", () => {
    expect(TAX_TREATMENT_ACCOUNT_TYPES).toContain(AccountType.TRUMP_ACCOUNT);
  });

  it("is NOT in ASSET_ACCOUNT_TYPES", () => {
    expect(ASSET_ACCOUNT_TYPES).not.toContain(AccountType.TRUMP_ACCOUNT);
  });

  it("is NOT in DEBT_ACCOUNT_TYPES", () => {
    expect(DEBT_ACCOUNT_TYPES).not.toContain(AccountType.TRUMP_ACCOUNT);
  });

  it("is NOT in EMPLOYER_PLAN_TYPES", () => {
    expect(EMPLOYER_PLAN_TYPES).not.toContain(AccountType.TRUMP_ACCOUNT);
  });
});

// ---------------------------------------------------------------------------
// Sidebar config
// ---------------------------------------------------------------------------

describe("Sidebar config — Children's Savings group", () => {
  it("places Trump Account in Children's Savings", () => {
    const config = ACCOUNT_TYPE_SIDEBAR_CONFIG[AccountType.TRUMP_ACCOUNT];
    expect(config).toBeDefined();
    expect(config.label).toBe("Children's Savings");
    expect(config.order).toBe(11);
  });

  it("places Trust in Children's Savings", () => {
    const config = ACCOUNT_TYPE_SIDEBAR_CONFIG[AccountType.TRUST];
    expect(config).toBeDefined();
    expect(config.label).toBe("Children's Savings");
  });

  it("places UGMA/UTMA in Children's Savings", () => {
    const config = ACCOUNT_TYPE_SIDEBAR_CONFIG[AccountType.CUSTODIAL_UGMA];
    expect(config).toBeDefined();
    expect(config.label).toBe("Children's Savings");
  });
});

// ---------------------------------------------------------------------------
// Composed group integrity
// ---------------------------------------------------------------------------

describe("ALL_RETIREMENT_TYPES composition", () => {
  it("includes all employer plan types", () => {
    for (const t of EMPLOYER_PLAN_TYPES) {
      expect(ALL_RETIREMENT_TYPES).toContain(t);
    }
  });

  it("includes all traditional IRA types", () => {
    for (const t of TRADITIONAL_IRA_TYPES) {
      expect(ALL_RETIREMENT_TYPES).toContain(t);
    }
  });

  it("includes Roth types", () => {
    for (const t of ROTH_TYPES) {
      expect(ALL_RETIREMENT_TYPES).toContain(t);
    }
  });

  it("includes tax-free savings types", () => {
    for (const t of TAX_FREE_SAVINGS_TYPES) {
      expect(ALL_RETIREMENT_TYPES).toContain(t);
    }
  });

  it("has no duplicates", () => {
    const unique = new Set(ALL_RETIREMENT_TYPES);
    expect(unique.size).toBe(ALL_RETIREMENT_TYPES.length);
  });
});

// ---------------------------------------------------------------------------
// Sidebar config completeness
// ---------------------------------------------------------------------------

describe("Sidebar config completeness", () => {
  it("has an entry for every AccountType enum value", () => {
    const enumValues = Object.values(AccountType);
    const configuredTypes = Object.keys(ACCOUNT_TYPE_SIDEBAR_CONFIG);
    for (const t of enumValues) {
      expect(configuredTypes).toContain(t);
    }
  });
});
