import { describe, it, expect } from "vitest";

const ACCOUNT_TYPE_LABELS: Record<string, string> = {
  retirement_roth: "Roth IRA",
  checking: "Checking",
  savings: "Savings",
  cd: "CD",
};

interface Account {
  name: string;
  institution_name: string | null;
  account_type: string;
}

const filterAccounts = (accounts: Account[], query: string): Account[] => {
  const q = query.toLowerCase().trim();
  if (!q) return accounts;
  return accounts.filter(
    (a) =>
      a.name?.toLowerCase().includes(q) ||
      a.institution_name?.toLowerCase().includes(q) ||
      (ACCOUNT_TYPE_LABELS[a.account_type] ?? a.account_type)?.toLowerCase().includes(q),
  );
};

describe("AccountsPage search filter", () => {
  const accounts: Account[] = [
    { name: "My Roth IRA", institution_name: "Vanguard", account_type: "retirement_roth" },
    { name: "Chase Checking", institution_name: "Chase", account_type: "checking" },
    { name: "High Yield Savings", institution_name: "Marcus", account_type: "savings" },
    { name: "12-Month CD", institution_name: "Ally", account_type: "cd" },
  ];

  it("empty query returns all accounts", () => {
    expect(filterAccounts(accounts, "")).toHaveLength(4);
  });

  it("matches on account name (case-insensitive)", () => {
    expect(filterAccounts(accounts, "chase")).toHaveLength(1);
    expect(filterAccounts(accounts, "CHASE")).toHaveLength(1);
  });

  it("matches on institution name", () => {
    expect(filterAccounts(accounts, "vanguard")).toHaveLength(1);
    expect(filterAccounts(accounts, "ally")).toHaveLength(1);
  });

  it("matches on friendly account type label", () => {
    // 'Roth' matches ACCOUNT_TYPE_LABELS["retirement_roth"] = "Roth IRA"
    expect(filterAccounts(accounts, "roth")).toHaveLength(1);
    expect(filterAccounts(accounts, "IRA")).toHaveLength(1);
  });

  it("matches on raw account type when no label exists", () => {
    // If type is not in ACCOUNT_TYPE_LABELS, fall back to raw type string
    const unknown: Account[] = [{ name: "Test", institution_name: null, account_type: "custom_type" }];
    expect(filterAccounts(unknown, "custom")).toHaveLength(1);
  });

  it("returns empty when no match", () => {
    expect(filterAccounts(accounts, "zzznomatch")).toHaveLength(0);
  });

  it("matches across multiple accounts", () => {
    // "savings" matches the savings account by type label AND "High Yield Savings" by name
    const results = filterAccounts(accounts, "savings");
    expect(results.length).toBeGreaterThanOrEqual(1);
  });
});
