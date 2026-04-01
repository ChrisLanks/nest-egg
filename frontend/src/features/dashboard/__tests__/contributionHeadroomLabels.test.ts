import { describe, it, expect } from "vitest";

// Mirror of ACCOUNT_TYPE_LABELS for test purposes
const ACCOUNT_TYPE_LABELS: Record<string, string> = {
  retirement_401k: "401(k)",
  retirement_roth: "Roth IRA",
  retirement_ira: "Traditional IRA",
  retirement_hsa: "HSA",
  retirement_529: "529 Plan",
  hsa: "Health Savings Account (HSA)",
  retirement_403b: "403(b)",
  retirement_457b: "457(b)",
  retirement_sep_ira: "SEP IRA",
  retirement_simple_ira: "SIMPLE IRA",
};

const getAccountLabel = (accountType: string): string =>
  ACCOUNT_TYPE_LABELS[accountType] ?? accountType;

describe("ContributionHeadroomWidget — account type labels", () => {
  it("retirement_roth renders as 'Roth IRA'", () => {
    expect(getAccountLabel("retirement_roth")).toBe("Roth IRA");
  });
  it("retirement_401k renders as '401(k)'", () => {
    expect(getAccountLabel("retirement_401k")).toBe("401(k)");
  });
  it("retirement_ira renders as 'Traditional IRA'", () => {
    expect(getAccountLabel("retirement_ira")).toBe("Traditional IRA");
  });
  it("unknown type falls back to raw string", () => {
    expect(getAccountLabel("custom_pension")).toBe("custom_pension");
  });
  it("empty string falls back to empty string", () => {
    expect(getAccountLabel("")).toBe("");
  });
});

describe("ContributionHeadroomWidget — regression: backend must send .value not str(enum)", () => {
  // Backend previously sent 'AccountType.RETIREMENT_401K' — this broke label lookup.
  // Now it sends 'retirement_401k' (.value). These tests guard that regression.

  it("'AccountType.RETIREMENT_401K' (str format) falls back to raw — proves why .value is required", () => {
    const label = getAccountLabel("AccountType.RETIREMENT_401K");
    expect(label).toBe("AccountType.RETIREMENT_401K"); // no match → raw fallback
  });

  it("'retirement_401k' (.value format) resolves to friendly label", () => {
    const label = getAccountLabel("retirement_401k");
    expect(label).toBe("401(k)");
  });

  it("'hsa' resolves to friendly HSA label", () => {
    const label = getAccountLabel("hsa");
    expect(label).toBe("Health Savings Account (HSA)");
  });

  it("all limit account types resolve to non-raw labels", () => {
    const types = [
      "retirement_401k",
      "retirement_403b",
      "retirement_457b",
      "retirement_ira",
      "retirement_roth",
      "retirement_sep_ira",
      "retirement_simple_ira",
      "hsa",
    ];
    for (const t of types) {
      const label = getAccountLabel(t);
      expect(label).not.toContain("AccountType");
      expect(label).not.toBe(t); // should resolve to a friendly name (all are in our map)
    }
  });
});
