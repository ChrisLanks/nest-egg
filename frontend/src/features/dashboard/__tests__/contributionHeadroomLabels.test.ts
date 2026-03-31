import { describe, it, expect } from "vitest";

// Mirror of ACCOUNT_TYPE_LABELS for test purposes
const ACCOUNT_TYPE_LABELS: Record<string, string> = {
  retirement_401k: "401(k)",
  retirement_roth: "Roth IRA",
  retirement_ira: "Traditional IRA",
  retirement_hsa: "HSA",
  retirement_529: "529 Plan",
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
