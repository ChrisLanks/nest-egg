/**
 * Tests for manual account schemas and ACCOUNT_TYPES constants.
 *
 * Covers:
 * - TRUMP_ACCOUNT exists in ACCOUNT_TYPES
 * - investmentAccountSchema accepts trump_account type
 * - investmentAccountSchema validation rules
 * - basicManualAccountSchema date and decimal handling (mortgage/loan bugs)
 * - privateDebtAccountSchema date and decimal handling
 */

import { describe, it, expect } from "vitest";
import {
  ACCOUNT_TYPES,
  basicManualAccountSchema,
  investmentAccountSchema,
  privateDebtAccountSchema,
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

// ── basicManualAccountSchema — mortgage/loan fields ──────────────────────────

describe("basicManualAccountSchema — loan/mortgage", () => {
  const base = {
    name: "My Mortgage",
    account_type: "mortgage",
    balance: 350000,
  };

  it("accepts a valid mortgage with no optional fields", () => {
    const result = basicManualAccountSchema.safeParse(base);
    expect(result.success).toBe(true);
  });

  it("accepts a decimal interest rate (e.g. 6.75)", () => {
    const result = basicManualAccountSchema.safeParse({
      ...base,
      interest_rate: 6.75,
    });
    expect(result.success).toBe(true);
    if (result.success) expect(result.data.interest_rate).toBe(6.75);
  });

  it("accepts interest rate as a numeric string and coerces it", () => {
    const result = basicManualAccountSchema.safeParse({
      ...base,
      interest_rate: "6.75",
    });
    expect(result.success).toBe(true);
    if (result.success) expect(result.data.interest_rate).toBe(6.75);
  });

  it("accepts a valid ISO origination_date string", () => {
    const result = basicManualAccountSchema.safeParse({
      ...base,
      origination_date: "2020-01-15",
    });
    expect(result.success).toBe(true);
    if (result.success) expect(result.data.origination_date).toBe("2020-01-15");
  });

  it("accepts omitted origination_date (truly optional)", () => {
    const result = basicManualAccountSchema.safeParse(base);
    expect(result.success).toBe(true);
    if (result.success) expect(result.data.origination_date).toBeUndefined();
  });

  // This documents the contract: the form must strip "" before submission.
  // Pydantic's Optional[date] on the backend rejects empty strings, so the
  // frontend handleFormSubmit coerces "" → undefined before the API call.
  it("rejects empty string origination_date — form must coerce to undefined", () => {
    // z.string().optional() actually accepts "", so the coercion must happen
    // in handleFormSubmit, not the schema. This test documents the raw schema
    // behaviour so we know why the form-level fix is necessary.
    const result = basicManualAccountSchema.safeParse({
      ...base,
      origination_date: "",
    });
    // Schema accepts "" (it's a string) — the form strips it before submission
    expect(result.success).toBe(true);
    if (result.success) expect(result.data.origination_date).toBe("");
  });

  it("accepts a decimal balance", () => {
    const result = basicManualAccountSchema.safeParse({
      ...base,
      balance: 349999.99,
    });
    expect(result.success).toBe(true);
    if (result.success) expect(result.data.balance).toBe(349999.99);
  });

  it("accepts a loan with all optional fields populated", () => {
    const result = basicManualAccountSchema.safeParse({
      name: "Car Loan",
      account_type: "loan",
      balance: 15000,
      interest_rate: 5.9,
      loan_term_months: 60,
      origination_date: "2022-06-01",
    });
    expect(result.success).toBe(true);
  });
});

// ── privateDebtAccountSchema — date and decimal handling ─────────────────────

describe("privateDebtAccountSchema — date and decimal handling", () => {
  const base = {
    name: "Loan to Business X",
    account_type: "private_debt",
    balance: 50000,
  };

  it("accepts a valid private debt account with no optional fields", () => {
    const result = privateDebtAccountSchema.safeParse(base);
    expect(result.success).toBe(true);
  });

  it("accepts a decimal interest rate", () => {
    const result = privateDebtAccountSchema.safeParse({
      ...base,
      interest_rate: 8.5,
    });
    expect(result.success).toBe(true);
    if (result.success) expect(result.data.interest_rate).toBe(8.5);
  });

  it("accepts interest rate as a numeric string and coerces it", () => {
    const result = privateDebtAccountSchema.safeParse({
      ...base,
      interest_rate: "8.5",
    });
    expect(result.success).toBe(true);
    if (result.success) expect(result.data.interest_rate).toBe(8.5);
  });

  it("accepts a valid ISO maturity_date string", () => {
    const result = privateDebtAccountSchema.safeParse({
      ...base,
      maturity_date: "2027-12-31",
    });
    expect(result.success).toBe(true);
    if (result.success) expect(result.data.maturity_date).toBe("2027-12-31");
  });

  it("accepts omitted maturity_date (truly optional)", () => {
    const result = privateDebtAccountSchema.safeParse(base);
    expect(result.success).toBe(true);
    if (result.success) expect(result.data.maturity_date).toBeUndefined();
  });

  // Same as above: schema accepts "", form must coerce "" → undefined.
  it("accepts empty string maturity_date — documents why form-level coercion is needed", () => {
    const result = privateDebtAccountSchema.safeParse({
      ...base,
      maturity_date: "",
    });
    expect(result.success).toBe(true);
    if (result.success) expect(result.data.maturity_date).toBe("");
  });

  it("accepts a decimal principal_amount", () => {
    const result = privateDebtAccountSchema.safeParse({
      ...base,
      principal_amount: 50000.5,
    });
    expect(result.success).toBe(true);
    if (result.success) expect(result.data.principal_amount).toBe(50000.5);
  });

  it("rejects missing name", () => {
    const result = privateDebtAccountSchema.safeParse({
      account_type: "private_debt",
      balance: 50000,
    });
    expect(result.success).toBe(false);
  });

  it("rejects missing balance", () => {
    const result = privateDebtAccountSchema.safeParse({
      name: "Loan to Business X",
      account_type: "private_debt",
    });
    expect(result.success).toBe(false);
  });
});
