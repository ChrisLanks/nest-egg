/**
 * Tests for manual account schemas and ACCOUNT_TYPES constants.
 *
 * Covers:
 * - TRUMP_ACCOUNT exists in ACCOUNT_TYPES
 * - investmentAccountSchema accepts trump_account type
 * - investmentAccountSchema validation rules
 */

import { describe, it, expect } from "vitest";
import {
  ACCOUNT_TYPES,
  investmentAccountSchema,
} from "../schemas/manualAccountSchemas";

// ── ACCOUNT_TYPES ───────────────────────────────────────────────────────────

describe("ACCOUNT_TYPES", () => {
  it("has TRUMP_ACCOUNT with value 'trump_account'", () => {
    expect(ACCOUNT_TYPES.TRUMP_ACCOUNT).toBe("trump_account");
  });

  it("has all expected investment account types", () => {
    expect(ACCOUNT_TYPES.BROKERAGE).toBe("brokerage");
    expect(ACCOUNT_TYPES.RETIREMENT_401K).toBe("retirement_401k");
    expect(ACCOUNT_TYPES.RETIREMENT_ROTH).toBe("retirement_roth");
    expect(ACCOUNT_TYPES.HSA).toBe("hsa");
    expect(ACCOUNT_TYPES.CRYPTO).toBe("crypto");
  });

  it("has all expected cash account types", () => {
    expect(ACCOUNT_TYPES.CHECKING).toBe("checking");
    expect(ACCOUNT_TYPES.SAVINGS).toBe("savings");
    expect(ACCOUNT_TYPES.MONEY_MARKET).toBe("money_market");
  });

  it("has all expected debt account types", () => {
    expect(ACCOUNT_TYPES.CREDIT_CARD).toBe("credit_card");
    expect(ACCOUNT_TYPES.LOAN).toBe("loan");
    expect(ACCOUNT_TYPES.MORTGAGE).toBe("mortgage");
    expect(ACCOUNT_TYPES.STUDENT_LOAN).toBe("student_loan");
  });
});

// ── investmentAccountSchema ─────────────────────────────────────────────────

describe("investmentAccountSchema", () => {
  it("accepts trump_account type with a balance", () => {
    const result = investmentAccountSchema.safeParse({
      name: "My Trump Account",
      account_type: "trump_account",
      balance: 10000,
    });
    expect(result.success).toBe(true);
  });

  it("accepts trump_account type with holdings", () => {
    const result = investmentAccountSchema.safeParse({
      name: "My Trump Account",
      account_type: "trump_account",
      holdings: [{ ticker: "VTI", shares: 100, price_per_share: 200 }],
    });
    expect(result.success).toBe(true);
  });

  it("rejects unknown account type", () => {
    const result = investmentAccountSchema.safeParse({
      name: "Bad Account",
      account_type: "nonexistent_type",
      balance: 5000,
    });
    expect(result.success).toBe(false);
  });

  it("rejects missing name", () => {
    const result = investmentAccountSchema.safeParse({
      account_type: "brokerage",
      balance: 5000,
    });
    expect(result.success).toBe(false);
  });

  it("rejects when neither holdings nor balance provided", () => {
    const result = investmentAccountSchema.safeParse({
      name: "Empty Account",
      account_type: "brokerage",
    });
    expect(result.success).toBe(false);
  });
});
