/**
 * Tests for Investments page logic: formatCurrency, formatPercent, formatShares,
 * portfolio filtering, account grouping, gain/loss calculations, empty/loading
 * state guards, section toggle, price age labels, treemap conversion, and
 * non-investment asset detection.
 */

import { describe, it, expect } from "vitest";

// ── Interfaces (mirrored from InvestmentsPage.tsx) ───────────────────────────

interface Holding {
  id: string;
  ticker: string;
  name: string | null;
  shares: number;
  cost_basis_per_share: number | null;
  total_cost_basis: number | null;
  current_price_per_share: number | null;
  current_total_value: number | null;
  price_as_of: string | null;
  asset_type: string | null;
}

interface AccountHoldings {
  account_id: string;
  account_name: string;
  account_type: string;
  account_value: number;
  holdings: Holding[];
}

interface HoldingSummary {
  ticker: string;
  name: string | null;
  total_shares: number;
  total_cost_basis: number | null;
  current_price_per_share: number | null;
  current_total_value: number | null;
  price_as_of: string | null;
  asset_type: string | null;
  expense_ratio: number | null;
  gain_loss: number | null;
  gain_loss_percent: number | null;
  annual_fee: number | null;
}

interface CategoryBreakdown {
  retirement_value: number;
  retirement_percent: number | null;
  taxable_value: number;
  taxable_percent: number | null;
  other_value: number;
  other_percent: number | null;
}

interface GeographicBreakdown {
  domestic_value: number;
  domestic_percent: number | null;
  international_value: number;
  international_percent: number | null;
  unknown_value: number;
  unknown_percent: number | null;
}

interface TreemapNode {
  name: string;
  value: number;
  percent: number;
  children?: TreemapNode[];
  color?: string;
  [key: string]: any;
}

interface PortfolioSummary {
  total_value: number;
  total_cost_basis: number | null;
  total_gain_loss: number | null;
  total_gain_loss_percent: number | null;
  holdings_by_ticker: HoldingSummary[];
  holdings_by_account: AccountHoldings[];
  stocks_value: number;
  bonds_value: number;
  etf_value: number;
  mutual_funds_value: number;
  cash_value: number;
  other_value: number;
  category_breakdown: CategoryBreakdown | null;
  geographic_breakdown: GeographicBreakdown | null;
  treemap_data: TreemapNode | null;
  total_annual_fees: number | null;
}

// ── Helper functions (mirrored from InvestmentsPage.tsx) ─────────────────────

const formatCurrency = (amount: number | null) => {
  if (amount === null || amount === undefined) return "N/A";
  const num = Number(amount);
  if (isNaN(num)) return "N/A";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(num);
};

const formatPercent = (percent: number | null) => {
  if (percent === null || percent === undefined) return "N/A";
  const num = Number(percent);
  if (isNaN(num)) return "N/A";
  return `${num >= 0 ? "+" : ""}${num.toFixed(2)}%`;
};

const formatShares = (shares: number) => {
  const num = Number(shares);
  if (isNaN(num)) return "0";
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 6,
  }).format(num);
};

const convertTreemapNode = (node: any): TreemapNode => {
  return {
    name: node.name,
    value: Number(node.value),
    percent: Number(node.percent),
    children: node.children?.map(convertTreemapNode),
    color: node.color,
  };
};

/** Toggle a section in/out of the expandedSections array */
const toggleSection = (prev: string[], section: string): string[] =>
  prev.includes(section)
    ? prev.filter((s) => s !== section)
    : [...prev, section];

/** Group accounts by type with preferred ordering */
const groupAccountsByType = (
  allAccounts: { account_type: string; [key: string]: any }[],
): Record<string, any[]> => {
  const groups: Record<string, any[]> = {};
  allAccounts.forEach((account) => {
    const type = account.account_type?.toLowerCase() || "other";
    if (!groups[type]) groups[type] = [];
    groups[type].push(account);
  });

  const typeOrder = ["retirement", "taxable", "crypto", "property", "vehicle"];
  const sortedGroups: Record<string, any[]> = {};
  typeOrder.forEach((type) => {
    if (groups[type]) sortedGroups[type] = groups[type];
  });
  Object.keys(groups).forEach((type) => {
    if (!typeOrder.includes(type)) sortedGroups[type] = groups[type];
  });
  return sortedGroups;
};

/** Detect non-investment assets that should be hidden by default */
const getNonInvestmentAssetIds = (
  accounts: {
    id: string;
    account_type: string;
    property_type?: string;
  }[],
): string[] =>
  accounts
    .filter((account) => {
      if (account.account_type === "vehicle") return true;
      if (account.account_type === "property") {
        return (
          account.property_type === "personal_residence" ||
          account.property_type === "vacation_home"
        );
      }
      return false;
    })
    .map((account) => account.id);

/** Filter portfolio holdings_by_account based on hidden account IDs */
const filterVisibleAccounts = (
  holdingsByAccount: AccountHoldings[],
  hiddenAccountIds: string[],
): AccountHoldings[] =>
  holdingsByAccount.filter(
    (account) => !hiddenAccountIds.includes(account.account_id),
  );

/** Filter holdings_by_ticker to only those present in visible accounts */
const filterVisibleHoldingsByTicker = (
  holdingsByTicker: HoldingSummary[],
  visibleAccounts: AccountHoldings[],
): HoldingSummary[] =>
  holdingsByTicker.filter((holding) =>
    visibleAccounts.some((account) =>
      account.holdings.some((h) => h.ticker === holding.ticker),
    ),
  );

/** Calculate new total value by subtracting hidden accounts */
const calcFilteredTotalValue = (
  originalTotal: number,
  hiddenAccountIds: string[],
  allAccounts: { id: string; current_balance?: number }[],
  holdingsByAccount: AccountHoldings[],
): number => {
  let newTotal = originalTotal;
  const hiddenAccounts = allAccounts.filter((a) =>
    hiddenAccountIds.includes(a.id),
  );
  hiddenAccounts.forEach((account) => {
    const holdingsAccount = holdingsByAccount.find(
      (h) => h.account_id === account.id,
    );
    if (holdingsAccount) {
      newTotal -= Number(holdingsAccount.account_value || 0);
    } else {
      newTotal -= Number(account.current_balance || 0);
    }
  });
  return newTotal;
};

/** Compute oldest price_as_of date from holdings */
const getOldestPriceDate = (holdings: HoldingSummary[]): Date | null => {
  const dates = holdings
    .map((h) => h.price_as_of)
    .filter(Boolean)
    .map((d) => new Date(d!));
  if (dates.length === 0) return null;
  return dates.reduce((oldest, d) => (d < oldest ? d : oldest));
};

/** Compute price age label from oldest price date */
const getPriceAgeLabel = (
  oldestPriceAsOf: Date | null,
  now: number,
): string | null => {
  if (!oldestPriceAsOf) return null;
  const diffMs = now - oldestPriceAsOf.getTime();
  const diffH = Math.floor(diffMs / 3_600_000);
  if (diffH < 1) return "Prices updated < 1h ago";
  if (diffH < 24) return `Prices updated ${diffH}h ago`;
  const diffD = Math.floor(diffH / 24);
  return `Prices updated ${diffD}d ago`;
};

/** Compute annual fee percentage */
const annualFeePercent = (totalFees: number, totalValue: number): string =>
  ((totalFees / totalValue) * 100).toFixed(3);

/** Compute asset percentage of portfolio */
const assetPercent = (assetValue: number, totalValue: number): string =>
  ((assetValue / totalValue) * 100).toFixed(1);

// ── Fixtures ─────────────────────────────────────────────────────────────────

const makeHolding = (overrides: Partial<Holding> = {}): Holding => ({
  id: "h1",
  ticker: "VTI",
  name: "Vanguard Total Stock Market ETF",
  shares: 100,
  cost_basis_per_share: 200,
  total_cost_basis: 20000,
  current_price_per_share: 250,
  current_total_value: 25000,
  price_as_of: "2026-03-14T16:00:00Z",
  asset_type: "etf",
  ...overrides,
});

const makeHoldingSummary = (
  overrides: Partial<HoldingSummary> = {},
): HoldingSummary => ({
  ticker: "VTI",
  name: "Vanguard Total Stock Market ETF",
  total_shares: 100,
  total_cost_basis: 20000,
  current_price_per_share: 250,
  current_total_value: 25000,
  price_as_of: "2026-03-14T16:00:00Z",
  asset_type: "etf",
  expense_ratio: 0.03,
  gain_loss: 5000,
  gain_loss_percent: 25,
  annual_fee: 7.5,
  ...overrides,
});

const makeAccountHoldings = (
  overrides: Partial<AccountHoldings> = {},
): AccountHoldings => ({
  account_id: "acct-1",
  account_name: "My 401k",
  account_type: "retirement",
  account_value: 25000,
  holdings: [makeHolding()],
  ...overrides,
});

const EMPTY_PORTFOLIO: PortfolioSummary = {
  total_value: 0,
  total_cost_basis: null,
  total_gain_loss: null,
  total_gain_loss_percent: null,
  holdings_by_ticker: [],
  holdings_by_account: [],
  stocks_value: 0,
  bonds_value: 0,
  etf_value: 0,
  mutual_funds_value: 0,
  cash_value: 0,
  other_value: 0,
  category_breakdown: null,
  geographic_breakdown: null,
  treemap_data: null,
  total_annual_fees: null,
};

const REAL_PORTFOLIO: PortfolioSummary = {
  total_value: 500000,
  total_cost_basis: 350000,
  total_gain_loss: 150000,
  total_gain_loss_percent: 42.86,
  holdings_by_ticker: [
    makeHoldingSummary({ ticker: "VTI", current_total_value: 250000 }),
    makeHoldingSummary({
      ticker: "VXUS",
      name: "Vanguard Total International",
      current_total_value: 150000,
      gain_loss: -5000,
      gain_loss_percent: -3.23,
    }),
    makeHoldingSummary({
      ticker: "BND",
      name: "Vanguard Total Bond",
      current_total_value: 100000,
      asset_type: "bond",
      gain_loss: 2000,
      gain_loss_percent: 2.04,
    }),
  ],
  holdings_by_account: [
    makeAccountHoldings({
      account_id: "acct-1",
      account_name: "My 401k",
      account_type: "retirement",
      account_value: 300000,
      holdings: [
        makeHolding({ id: "h1", ticker: "VTI" }),
        makeHolding({ id: "h2", ticker: "BND" }),
      ],
    }),
    makeAccountHoldings({
      account_id: "acct-2",
      account_name: "Brokerage",
      account_type: "taxable",
      account_value: 200000,
      holdings: [
        makeHolding({ id: "h3", ticker: "VTI" }),
        makeHolding({ id: "h4", ticker: "VXUS" }),
      ],
    }),
  ],
  stocks_value: 250000,
  bonds_value: 100000,
  etf_value: 400000,
  mutual_funds_value: 0,
  cash_value: 0,
  other_value: 0,
  category_breakdown: {
    retirement_value: 300000,
    retirement_percent: 60,
    taxable_value: 200000,
    taxable_percent: 40,
    other_value: 0,
    other_percent: 0,
  },
  geographic_breakdown: {
    domestic_value: 350000,
    domestic_percent: 70,
    international_value: 150000,
    international_percent: 30,
    unknown_value: 0,
    unknown_percent: 0,
  },
  treemap_data: {
    name: "Portfolio",
    value: 500000,
    percent: 100,
    children: [
      { name: "Stocks", value: 250000, percent: 50 },
      { name: "Bonds", value: 100000, percent: 20 },
      { name: "ETFs", value: 150000, percent: 30 },
    ],
  },
  total_annual_fees: 150,
};

// ── Tests ────────────────────────────────────────────────────────────────────

describe("formatCurrency", () => {
  it("formats positive amounts with two decimals", () => {
    expect(formatCurrency(1234.56)).toBe("$1,234.56");
    expect(formatCurrency(500000)).toBe("$500,000.00");
  });

  it("formats zero", () => {
    expect(formatCurrency(0)).toBe("$0.00");
  });

  it("formats negative amounts", () => {
    expect(formatCurrency(-5000)).toBe("-$5,000.00");
  });

  it("returns N/A for null", () => {
    expect(formatCurrency(null)).toBe("N/A");
  });

  it("returns N/A for undefined", () => {
    expect(formatCurrency(undefined as any)).toBe("N/A");
  });

  it("returns N/A for NaN", () => {
    expect(formatCurrency(NaN)).toBe("N/A");
  });

  it("handles very large numbers", () => {
    expect(formatCurrency(1_000_000_000)).toBe("$1,000,000,000.00");
  });

  it("handles small fractional amounts", () => {
    expect(formatCurrency(0.01)).toBe("$0.01");
    expect(formatCurrency(0.005)).toBe("$0.01"); // rounds up
  });
});

describe("formatPercent", () => {
  it("formats positive percentages with + prefix", () => {
    expect(formatPercent(25)).toBe("+25.00%");
    expect(formatPercent(42.86)).toBe("+42.86%");
  });

  it("formats zero with + prefix", () => {
    expect(formatPercent(0)).toBe("+0.00%");
  });

  it("formats negative percentages without + prefix", () => {
    expect(formatPercent(-3.23)).toBe("-3.23%");
    expect(formatPercent(-100)).toBe("-100.00%");
  });

  it("returns N/A for null", () => {
    expect(formatPercent(null)).toBe("N/A");
  });

  it("returns N/A for undefined", () => {
    expect(formatPercent(undefined as any)).toBe("N/A");
  });

  it("returns N/A for NaN", () => {
    expect(formatPercent(NaN)).toBe("N/A");
  });

  it("formats small fractions", () => {
    expect(formatPercent(0.123)).toBe("+0.12%");
  });
});

describe("formatShares", () => {
  it("formats whole shares without decimals", () => {
    expect(formatShares(100)).toBe("100");
    expect(formatShares(1000)).toBe("1,000");
  });

  it("formats fractional shares up to 6 decimals", () => {
    expect(formatShares(1.123456)).toBe("1.123456");
  });

  it("formats zero", () => {
    expect(formatShares(0)).toBe("0");
  });

  it("returns 0 for NaN input", () => {
    expect(formatShares(NaN)).toBe("0");
  });

  it("handles very small fractional shares", () => {
    expect(formatShares(0.000001)).toBe("0.000001");
  });
});

// ── Treemap conversion ──────────────────────────────────────────────────────

describe("convertTreemapNode", () => {
  it("converts string values to numbers", () => {
    const raw = { name: "Stocks", value: "250000", percent: "50" };
    const result = convertTreemapNode(raw);
    expect(result.value).toBe(250000);
    expect(result.percent).toBe(50);
    expect(typeof result.value).toBe("number");
    expect(typeof result.percent).toBe("number");
  });

  it("preserves numeric values", () => {
    const raw = { name: "Bonds", value: 100000, percent: 20 };
    const result = convertTreemapNode(raw);
    expect(result.value).toBe(100000);
    expect(result.percent).toBe(20);
  });

  it("recursively converts children", () => {
    const raw = {
      name: "Portfolio",
      value: "500000",
      percent: "100",
      children: [
        { name: "Stocks", value: "250000", percent: "50" },
        { name: "Bonds", value: "100000", percent: "20" },
      ],
    };
    const result = convertTreemapNode(raw);
    expect(result.value).toBe(500000);
    expect(result.children).toHaveLength(2);
    expect(result.children![0].value).toBe(250000);
    expect(result.children![1].value).toBe(100000);
  });

  it("handles node without children", () => {
    const raw = { name: "VTI", value: "25000", percent: "5" };
    const result = convertTreemapNode(raw);
    expect(result.children).toBeUndefined();
  });

  it("preserves color property", () => {
    const raw = { name: "Stocks", value: 100, percent: 10, color: "#ff0000" };
    const result = convertTreemapNode(raw);
    expect(result.color).toBe("#ff0000");
  });
});

// ── Section toggle ──────────────────────────────────────────────────────────

describe("toggleSection", () => {
  it("adds a section not currently expanded", () => {
    const result = toggleSection(["summary", "holdings"], "breakdown");
    expect(result).toContain("breakdown");
    expect(result).toHaveLength(3);
  });

  it("removes a section currently expanded", () => {
    const result = toggleSection(
      ["summary", "breakdown", "holdings"],
      "breakdown",
    );
    expect(result).not.toContain("breakdown");
    expect(result).toHaveLength(2);
  });

  it("handles empty array", () => {
    const result = toggleSection([], "summary");
    expect(result).toEqual(["summary"]);
  });

  it("handles removing the only section", () => {
    const result = toggleSection(["summary"], "summary");
    expect(result).toEqual([]);
  });
});

// ── Account grouping ────────────────────────────────────────────────────────

describe("groupAccountsByType", () => {
  const accounts = [
    { id: "1", account_type: "taxable", name: "Brokerage" },
    { id: "2", account_type: "retirement", name: "401k" },
    { id: "3", account_type: "crypto", name: "Coinbase" },
    { id: "4", account_type: "retirement", name: "IRA" },
    { id: "5", account_type: "property", name: "House" },
    { id: "6", account_type: "vehicle", name: "Car" },
    { id: "7", account_type: "savings", name: "HYSA" },
  ];

  it("groups accounts by type", () => {
    const groups = groupAccountsByType(accounts);
    expect(groups["retirement"]).toHaveLength(2);
    expect(groups["taxable"]).toHaveLength(1);
    expect(groups["crypto"]).toHaveLength(1);
    expect(groups["property"]).toHaveLength(1);
    expect(groups["vehicle"]).toHaveLength(1);
    expect(groups["savings"]).toHaveLength(1);
  });

  it("orders known types before unknown types", () => {
    const groups = groupAccountsByType(accounts);
    const keys = Object.keys(groups);
    const retirementIdx = keys.indexOf("retirement");
    const savingsIdx = keys.indexOf("savings");
    expect(retirementIdx).toBeLessThan(savingsIdx);
  });

  it("follows preferred order: retirement, taxable, crypto, property, vehicle", () => {
    const groups = groupAccountsByType(accounts);
    const keys = Object.keys(groups);
    expect(keys.indexOf("retirement")).toBeLessThan(keys.indexOf("taxable"));
    expect(keys.indexOf("taxable")).toBeLessThan(keys.indexOf("crypto"));
    expect(keys.indexOf("crypto")).toBeLessThan(keys.indexOf("property"));
    expect(keys.indexOf("property")).toBeLessThan(keys.indexOf("vehicle"));
  });

  it("handles empty array", () => {
    const groups = groupAccountsByType([]);
    expect(Object.keys(groups)).toHaveLength(0);
  });

  it("lowercases account type", () => {
    const groups = groupAccountsByType([
      { id: "1", account_type: "Retirement", name: "401k" },
    ]);
    expect(groups["retirement"]).toHaveLength(1);
    expect(groups["Retirement"]).toBeUndefined();
  });

  it("defaults to 'other' when account_type is missing", () => {
    const groups = groupAccountsByType([
      { id: "1", account_type: "", name: "Unknown" },
    ]);
    expect(groups["other"]).toHaveLength(1);
  });
});

// ── Non-investment asset detection ──────────────────────────────────────────

describe("getNonInvestmentAssetIds", () => {
  it("identifies vehicles as non-investment", () => {
    const ids = getNonInvestmentAssetIds([
      { id: "v1", account_type: "vehicle" },
    ]);
    expect(ids).toEqual(["v1"]);
  });

  it("identifies personal residences as non-investment", () => {
    const ids = getNonInvestmentAssetIds([
      {
        id: "p1",
        account_type: "property",
        property_type: "personal_residence",
      },
    ]);
    expect(ids).toEqual(["p1"]);
  });

  it("identifies vacation homes as non-investment", () => {
    const ids = getNonInvestmentAssetIds([
      { id: "p2", account_type: "property", property_type: "vacation_home" },
    ]);
    expect(ids).toEqual(["p2"]);
  });

  it("does NOT hide investment properties", () => {
    const ids = getNonInvestmentAssetIds([
      { id: "p3", account_type: "property", property_type: "investment" },
    ]);
    expect(ids).toEqual([]);
  });

  it("does NOT hide rental properties", () => {
    const ids = getNonInvestmentAssetIds([
      { id: "p4", account_type: "property", property_type: "rental" },
    ]);
    expect(ids).toEqual([]);
  });

  it("does NOT hide retirement or taxable accounts", () => {
    const ids = getNonInvestmentAssetIds([
      { id: "r1", account_type: "retirement" },
      { id: "t1", account_type: "taxable" },
      { id: "c1", account_type: "crypto" },
    ]);
    expect(ids).toEqual([]);
  });

  it("returns multiple IDs for mixed non-investment accounts", () => {
    const ids = getNonInvestmentAssetIds([
      { id: "v1", account_type: "vehicle" },
      {
        id: "p1",
        account_type: "property",
        property_type: "personal_residence",
      },
      { id: "r1", account_type: "retirement" },
      { id: "p2", account_type: "property", property_type: "vacation_home" },
    ]);
    expect(ids).toEqual(["v1", "p1", "p2"]);
  });

  it("handles empty array", () => {
    expect(getNonInvestmentAssetIds([])).toEqual([]);
  });
});

// ── Portfolio filtering ─────────────────────────────────────────────────────

describe("filterVisibleAccounts", () => {
  const accounts = REAL_PORTFOLIO.holdings_by_account;

  it("returns all accounts when no IDs hidden", () => {
    const result = filterVisibleAccounts(accounts, []);
    expect(result).toHaveLength(2);
  });

  it("filters out hidden accounts", () => {
    const result = filterVisibleAccounts(accounts, ["acct-1"]);
    expect(result).toHaveLength(1);
    expect(result[0].account_id).toBe("acct-2");
  });

  it("filters out all accounts when all hidden", () => {
    const result = filterVisibleAccounts(accounts, ["acct-1", "acct-2"]);
    expect(result).toHaveLength(0);
  });

  it("ignores non-existent hidden IDs", () => {
    const result = filterVisibleAccounts(accounts, ["acct-999"]);
    expect(result).toHaveLength(2);
  });
});

describe("filterVisibleHoldingsByTicker", () => {
  const holdingsByTicker = REAL_PORTFOLIO.holdings_by_ticker;
  const allAccounts = REAL_PORTFOLIO.holdings_by_account;

  it("returns all holdings when all accounts visible", () => {
    const result = filterVisibleHoldingsByTicker(holdingsByTicker, allAccounts);
    expect(result).toHaveLength(3);
  });

  it("filters holdings to only those in visible accounts", () => {
    // acct-1 has VTI and BND; acct-2 has VTI and VXUS
    // hiding acct-2 means VXUS should remain since VTI is in acct-1, BND is in acct-1
    const visibleAccounts = filterVisibleAccounts(allAccounts, ["acct-2"]);
    const result = filterVisibleHoldingsByTicker(
      holdingsByTicker,
      visibleAccounts,
    );
    // VTI is in acct-1, BND is in acct-1, VXUS is NOT in acct-1
    expect(result.map((h) => h.ticker)).toContain("VTI");
    expect(result.map((h) => h.ticker)).toContain("BND");
    expect(result.map((h) => h.ticker)).not.toContain("VXUS");
  });

  it("returns empty when no accounts visible", () => {
    const result = filterVisibleHoldingsByTicker(holdingsByTicker, []);
    expect(result).toHaveLength(0);
  });
});

describe("calcFilteredTotalValue", () => {
  const holdingsByAccount = REAL_PORTFOLIO.holdings_by_account;
  const allAccounts = [
    { id: "acct-1", current_balance: 300000 },
    { id: "acct-2", current_balance: 200000 },
  ];

  it("returns original total when nothing hidden", () => {
    const result = calcFilteredTotalValue(
      500000,
      [],
      allAccounts,
      holdingsByAccount,
    );
    expect(result).toBe(500000);
  });

  it("subtracts hidden account value using holdings_by_account", () => {
    // acct-1 has account_value 300000 in holdings_by_account
    const result = calcFilteredTotalValue(
      500000,
      ["acct-1"],
      allAccounts,
      holdingsByAccount,
    );
    expect(result).toBe(200000);
  });

  it("subtracts both hidden accounts", () => {
    const result = calcFilteredTotalValue(
      500000,
      ["acct-1", "acct-2"],
      allAccounts,
      holdingsByAccount,
    );
    expect(result).toBe(0);
  });

  it("falls back to current_balance when account not in holdings_by_account", () => {
    const extraAccounts = [
      ...allAccounts,
      { id: "acct-prop", current_balance: 400000 },
    ];
    const result = calcFilteredTotalValue(
      900000,
      ["acct-prop"],
      extraAccounts,
      holdingsByAccount,
    );
    expect(result).toBe(500000);
  });
});

// ── Price staleness ─────────────────────────────────────────────────────────

describe("getOldestPriceDate", () => {
  it("returns null when no holdings", () => {
    expect(getOldestPriceDate([])).toBeNull();
  });

  it("returns null when all price_as_of are null", () => {
    const holdings = [
      makeHoldingSummary({ price_as_of: null }),
      makeHoldingSummary({ price_as_of: null }),
    ];
    expect(getOldestPriceDate(holdings)).toBeNull();
  });

  it("returns the oldest date among holdings", () => {
    const holdings = [
      makeHoldingSummary({ price_as_of: "2026-03-14T16:00:00Z" }),
      makeHoldingSummary({ price_as_of: "2026-03-10T16:00:00Z" }),
      makeHoldingSummary({ price_as_of: "2026-03-12T16:00:00Z" }),
    ];
    const result = getOldestPriceDate(holdings);
    expect(result).toEqual(new Date("2026-03-10T16:00:00Z"));
  });

  it("handles single holding", () => {
    const holdings = [
      makeHoldingSummary({ price_as_of: "2026-03-14T16:00:00Z" }),
    ];
    const result = getOldestPriceDate(holdings);
    expect(result).toEqual(new Date("2026-03-14T16:00:00Z"));
  });
});

describe("getPriceAgeLabel", () => {
  it("returns null when no oldest date", () => {
    expect(getPriceAgeLabel(null, Date.now())).toBeNull();
  });

  it("returns '< 1h ago' for very recent prices", () => {
    const now = Date.now();
    const recent = new Date(now - 30 * 60 * 1000); // 30 min ago
    expect(getPriceAgeLabel(recent, now)).toBe("Prices updated < 1h ago");
  });

  it("returns hours for same-day prices", () => {
    const now = Date.now();
    const threeHoursAgo = new Date(now - 3 * 3_600_000);
    expect(getPriceAgeLabel(threeHoursAgo, now)).toBe("Prices updated 3h ago");
  });

  it("returns days for older prices", () => {
    const now = Date.now();
    const twoDaysAgo = new Date(now - 48 * 3_600_000);
    expect(getPriceAgeLabel(twoDaysAgo, now)).toBe("Prices updated 2d ago");
  });

  it("boundary: exactly 1 hour returns 1h", () => {
    const now = Date.now();
    const oneHourAgo = new Date(now - 3_600_000);
    expect(getPriceAgeLabel(oneHourAgo, now)).toBe("Prices updated 1h ago");
  });

  it("boundary: exactly 24 hours returns 1d", () => {
    const now = Date.now();
    const oneDayAgo = new Date(now - 24 * 3_600_000);
    expect(getPriceAgeLabel(oneDayAgo, now)).toBe("Prices updated 1d ago");
  });
});

// ── Empty state / visibility guards ─────────────────────────────────────────

describe("Empty State Guards", () => {
  it("detects empty portfolio (no holdings, no accounts, zero value)", () => {
    const p = EMPTY_PORTFOLIO;
    const showEmpty =
      p.holdings_by_ticker.length === 0 &&
      p.holdings_by_account.length === 0 &&
      p.total_value === 0;
    expect(showEmpty).toBe(true);
  });

  it("does NOT show empty state when portfolio has value", () => {
    const p = REAL_PORTFOLIO;
    const showEmpty =
      p.holdings_by_ticker.length === 0 &&
      p.holdings_by_account.length === 0 &&
      p.total_value === 0;
    expect(showEmpty).toBe(false);
  });

  it("does NOT show empty state when portfolio has holdings but zero value", () => {
    const p: PortfolioSummary = {
      ...EMPTY_PORTFOLIO,
      holdings_by_ticker: [makeHoldingSummary({ current_total_value: 0 })],
    };
    const showEmpty =
      p.holdings_by_ticker.length === 0 &&
      p.holdings_by_account.length === 0 &&
      p.total_value === 0;
    expect(showEmpty).toBe(false);
  });

  it("null portfolio triggers empty state", () => {
    const portfolio: PortfolioSummary | null = null;
    const showEmpty =
      !portfolio ||
      (portfolio.holdings_by_ticker.length === 0 &&
        portfolio.holdings_by_account.length === 0 &&
        portfolio.total_value === 0);
    expect(showEmpty).toBe(true);
  });
});

describe("Gain/Loss Visibility", () => {
  it("shows gain/loss card when total_gain_loss is not null", () => {
    expect(REAL_PORTFOLIO.total_gain_loss !== null).toBe(true);
  });

  it("hides gain/loss card when total_gain_loss is null", () => {
    expect(EMPTY_PORTFOLIO.total_gain_loss !== null).toBe(false);
  });

  it("detects positive gain", () => {
    const p = REAL_PORTFOLIO;
    const isPositive = p.total_gain_loss !== null && p.total_gain_loss >= 0;
    expect(isPositive).toBe(true);
  });

  it("detects negative gain (loss)", () => {
    const p: PortfolioSummary = {
      ...REAL_PORTFOLIO,
      total_gain_loss: -10000,
    };
    const isPositive = p.total_gain_loss !== null && p.total_gain_loss >= 0;
    expect(isPositive).toBe(false);
  });

  it("zero gain is treated as positive", () => {
    const p: PortfolioSummary = {
      ...REAL_PORTFOLIO,
      total_gain_loss: 0,
    };
    const isPositive = p.total_gain_loss !== null && p.total_gain_loss >= 0;
    expect(isPositive).toBe(true);
  });
});

describe("Annual Fees Visibility", () => {
  it("shows fees card when fees are positive", () => {
    const p = REAL_PORTFOLIO;
    const showFees = p.total_annual_fees !== null && p.total_annual_fees > 0;
    expect(showFees).toBe(true);
  });

  it("hides fees card when fees are null", () => {
    const showFees =
      EMPTY_PORTFOLIO.total_annual_fees !== null &&
      EMPTY_PORTFOLIO.total_annual_fees! > 0;
    expect(showFees).toBe(false);
  });

  it("hides fees card when fees are zero", () => {
    const p: PortfolioSummary = { ...REAL_PORTFOLIO, total_annual_fees: 0 };
    const showFees = p.total_annual_fees !== null && p.total_annual_fees > 0;
    expect(showFees).toBe(false);
  });
});

describe("Asset Type Card Visibility", () => {
  it("shows stocks card when stocks_value > 0", () => {
    expect(REAL_PORTFOLIO.stocks_value > 0).toBe(true);
  });

  it("hides stocks card when stocks_value is 0", () => {
    expect(EMPTY_PORTFOLIO.stocks_value > 0).toBe(false);
  });

  it("shows ETF card when etf_value > 0", () => {
    expect(REAL_PORTFOLIO.etf_value > 0).toBe(true);
  });

  it("hides mutual funds card when mutual_funds_value is 0", () => {
    expect(REAL_PORTFOLIO.mutual_funds_value > 0).toBe(false);
  });
});

describe("Category Breakdown Visibility", () => {
  it("shows category breakdown when present", () => {
    expect(REAL_PORTFOLIO.category_breakdown !== null).toBe(true);
  });

  it("hides category breakdown when null", () => {
    expect(EMPTY_PORTFOLIO.category_breakdown !== null).toBe(false);
  });

  it("shows retirement card when retirement_value > 0", () => {
    expect(REAL_PORTFOLIO.category_breakdown!.retirement_value > 0).toBe(true);
  });

  it("hides other card when other_value is 0", () => {
    expect(REAL_PORTFOLIO.category_breakdown!.other_value > 0).toBe(false);
  });
});

describe("Geographic Breakdown Visibility", () => {
  it("shows geographic breakdown when present", () => {
    expect(REAL_PORTFOLIO.geographic_breakdown !== null).toBe(true);
  });

  it("shows domestic when domestic_value > 0", () => {
    expect(REAL_PORTFOLIO.geographic_breakdown!.domestic_value > 0).toBe(true);
  });

  it("hides unknown when unknown_value is 0", () => {
    expect(REAL_PORTFOLIO.geographic_breakdown!.unknown_value > 0).toBe(false);
  });
});

// ── Percentage / fee calculations ───────────────────────────────────────────

describe("annualFeePercent", () => {
  it("calculates fee as percentage of portfolio", () => {
    expect(annualFeePercent(150, 500000)).toBe("0.030");
  });

  it("handles large fees", () => {
    expect(annualFeePercent(5000, 500000)).toBe("1.000");
  });

  it("handles small portfolio", () => {
    expect(annualFeePercent(10, 1000)).toBe("1.000");
  });
});

describe("assetPercent", () => {
  it("calculates asset percentage of total", () => {
    expect(assetPercent(250000, 500000)).toBe("50.0");
  });

  it("handles small percentages", () => {
    expect(assetPercent(1000, 500000)).toBe("0.2");
  });

  it("handles 100%", () => {
    expect(assetPercent(500000, 500000)).toBe("100.0");
  });
});

// ── Household / user view logic ─────────────────────────────────────────────

describe("activeUserId Logic", () => {
  it("uses multiEffectiveUserId in combined view", () => {
    const isCombinedView = true;
    const selectedUserId = "user-1";
    const multiEffectiveUserId = "user-2";
    const activeUserId = isCombinedView
      ? (multiEffectiveUserId ?? null)
      : selectedUserId;
    expect(activeUserId).toBe("user-2");
  });

  it("uses selectedUserId when NOT in combined view", () => {
    const isCombinedView = false;
    const selectedUserId = "user-1";
    const multiEffectiveUserId = "user-2";
    const activeUserId = isCombinedView
      ? (multiEffectiveUserId ?? null)
      : selectedUserId;
    expect(activeUserId).toBe("user-1");
  });

  it("uses null in combined view when multiEffectiveUserId is undefined", () => {
    const isCombinedView = true;
    const selectedUserId = "user-1";
    const multiEffectiveUserId = undefined;
    const activeUserId = isCombinedView
      ? (multiEffectiveUserId ?? null)
      : selectedUserId;
    expect(activeUserId).toBeNull();
  });
});

describe("API params construction", () => {
  it("includes user_id when activeUserId is set", () => {
    const activeUserId: string | null = "user-123";
    const params = activeUserId ? { user_id: activeUserId } : {};
    expect(params).toEqual({ user_id: "user-123" });
  });

  it("passes empty params when activeUserId is null", () => {
    const activeUserId: string | null = null;
    const params = activeUserId ? { user_id: activeUserId } : {};
    expect(params).toEqual({});
  });
});

// ── Monthly contribution calculation ────────────────────────────────────────

describe("Monthly Contribution Calculation", () => {
  it("calculates monthly from annual contributions + employer match", () => {
    const retirementAccountData = {
      annual_contributions: 20000,
      employer_match_annual: 4000,
    };
    const monthly =
      (retirementAccountData.annual_contributions +
        retirementAccountData.employer_match_annual) /
      12;
    expect(monthly).toBe(2000);
  });

  it("returns undefined when no retirement data", () => {
    const retirementAccountData = null;
    const monthly = retirementAccountData
      ? (retirementAccountData.annual_contributions +
          retirementAccountData.employer_match_annual) /
        12
      : undefined;
    expect(monthly).toBeUndefined();
  });

  it("handles zero contributions", () => {
    const retirementAccountData = {
      annual_contributions: 0,
      employer_match_annual: 0,
    };
    const monthly =
      (retirementAccountData.annual_contributions +
        retirementAccountData.employer_match_annual) /
      12;
    expect(monthly).toBe(0);
  });
});

// ── Default expanded sections ───────────────────────────────────────────────

describe("Default Expanded Sections", () => {
  const defaultSections = ["summary", "breakdown", "treemap", "holdings"];

  it("includes all four default sections", () => {
    expect(defaultSections).toContain("summary");
    expect(defaultSections).toContain("breakdown");
    expect(defaultSections).toContain("treemap");
    expect(defaultSections).toContain("holdings");
    expect(defaultSections).toHaveLength(4);
  });
});

// ── Account holdings empty check ────────────────────────────────────────────

describe("Account Holdings Empty State", () => {
  it("detects account with no holdings", () => {
    const account = makeAccountHoldings({ holdings: [] });
    expect(account.holdings.length === 0).toBe(true);
  });

  it("detects account with holdings", () => {
    const account = makeAccountHoldings();
    expect(account.holdings.length === 0).toBe(false);
  });
});

// ── Expanded accounts toggle ────────────────────────────────────────────────

describe("Expanded Accounts Toggle", () => {
  it("expands a collapsed account", () => {
    const prev: string[] = [];
    const accountId = "acct-1";
    const next = prev.includes(accountId)
      ? prev.filter((id) => id !== accountId)
      : [...prev, accountId];
    expect(next).toEqual(["acct-1"]);
  });

  it("collapses an expanded account", () => {
    const prev = ["acct-1", "acct-2"];
    const accountId = "acct-1";
    const next = prev.includes(accountId)
      ? prev.filter((id) => id !== accountId)
      : [...prev, accountId];
    expect(next).toEqual(["acct-2"]);
  });
});

// ── Hidden accounts badge count ─────────────────────────────────────────────

describe("Hidden Accounts Badge", () => {
  it("shows badge when accounts are hidden", () => {
    const hiddenAccountIds = ["acct-1", "acct-2"];
    expect(hiddenAccountIds.length > 0).toBe(true);
    expect(hiddenAccountIds.length).toBe(2);
  });

  it("hides badge when no accounts hidden", () => {
    const hiddenAccountIds: string[] = [];
    expect(hiddenAccountIds.length > 0).toBe(false);
  });
});
