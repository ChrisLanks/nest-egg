import { describe, it, expect } from "vitest";

const ACCOUNT_TYPE_LABELS: Record<string, string> = {
  retirement_401k: "401(k)",
  retirement_403b: "403(b)",
  retirement_roth: "Roth IRA",
  retirement_ira: "Traditional IRA",
  checking: "Checking",
  savings: "Savings",
  cd: "Certificate of Deposit (CD)",
  brokerage: "Brokerage",
  hsa: "Health Savings Account (HSA)",
};

interface Account {
  name: string;
  institution_name: string | null;
  account_type: string;
}

/** Mirrors the filteredAccounts logic in AccountsPage.tsx */
const filterAccounts = (accounts: Account[], query: string): Account[] => {
  const terms = query.toLowerCase().trim().split(/\s+/).filter(Boolean);
  if (terms.length === 0) return accounts;
  return accounts.filter((a) => {
    const haystack = [
      a.name ?? "",
      a.institution_name ?? "",
      ACCOUNT_TYPE_LABELS[a.account_type] ?? "",
      a.account_type ?? "",
    ].join(" ").toLowerCase();
    return terms.every((term) => haystack.includes(term));
  });
};

describe("AccountsPage search filter", () => {
  const accounts: Account[] = [
    { name: "My Roth IRA", institution_name: "Vanguard", account_type: "retirement_roth" },
    { name: "Chase Checking", institution_name: "Chase", account_type: "checking" },
    { name: "High Yield Savings", institution_name: "Marcus", account_type: "savings" },
    { name: "12-Month CD", institution_name: "Ally", account_type: "cd" },
    { name: "Fidelity 401k", institution_name: "Fidelity", account_type: "retirement_401k" },
    { name: "My Traditional IRA", institution_name: "Schwab", account_type: "retirement_ira" },
    { name: "HSA Account", institution_name: "Optum", account_type: "hsa" },
  ];

  it("empty query returns all accounts", () => {
    expect(filterAccounts(accounts, "")).toHaveLength(accounts.length);
  });

  it("single-word: matches on account name (case-insensitive)", () => {
    expect(filterAccounts(accounts, "chase")).toHaveLength(1);
    expect(filterAccounts(accounts, "CHASE")).toHaveLength(1);
  });

  it("single-word: matches on institution name", () => {
    expect(filterAccounts(accounts, "vanguard")).toHaveLength(1);
    expect(filterAccounts(accounts, "ally")).toHaveLength(1);
  });

  it("single-word: matches on friendly account type label", () => {
    expect(filterAccounts(accounts, "roth")).toHaveLength(1);
    expect(filterAccounts(accounts, "IRA")).toHaveLength(2); // Roth IRA + Traditional IRA
  });

  it("single-word: matches on raw account_type value", () => {
    // 'retirement_401k' raw type contains '401k'
    const r = filterAccounts(accounts, "401k");
    expect(r.length).toBeGreaterThanOrEqual(1);
    expect(r.some((a) => a.account_type === "retirement_401k")).toBe(true);
  });

  it("multi-word: 'retirement 401k' finds 401k account (cross-field AND)", () => {
    // 'retirement' matches raw type 'retirement_401k'; '401k' matches label '401(k)' and raw type
    const r = filterAccounts(accounts, "retirement 401k");
    expect(r.length).toBeGreaterThanOrEqual(1);
    expect(r.every((a) => a.account_type.startsWith("retirement"))).toBe(true);
  });

  it("multi-word: 'roth ira' finds the Roth IRA", () => {
    const r = filterAccounts(accounts, "roth ira");
    expect(r).toHaveLength(1);
    expect(r[0].account_type).toBe("retirement_roth");
  });

  it("multi-word: 'traditional ira' finds Traditional IRA", () => {
    const r = filterAccounts(accounts, "traditional ira");
    expect(r).toHaveLength(1);
    expect(r[0].account_type).toBe("retirement_ira");
  });

  it("multi-word: 'fidelity retirement' finds Fidelity 401k", () => {
    const r = filterAccounts(accounts, "fidelity retirement");
    expect(r).toHaveLength(1);
    expect(r[0].institution_name).toBe("Fidelity");
  });

  it("multi-word: all terms must match (AND logic)", () => {
    // 'chase roth' should not match — Chase is checking, Vanguard has roth
    expect(filterAccounts(accounts, "chase roth")).toHaveLength(0);
  });

  it("matches on raw account type when no label exists", () => {
    const custom: Account[] = [{ name: "Test", institution_name: null, account_type: "custom_type" }];
    expect(filterAccounts(custom, "custom")).toHaveLength(1);
    expect(filterAccounts(custom, "custom type")).toHaveLength(1);
  });

  it("returns empty when no match", () => {
    expect(filterAccounts(accounts, "zzznomatch")).toHaveLength(0);
  });
});
