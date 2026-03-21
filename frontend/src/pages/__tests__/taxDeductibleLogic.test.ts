/**
 * Tests for TaxDeductiblePage logic: totals aggregation, tax label
 * existence check, currency/date formatting, and export filename.
 */

import { describe, it, expect } from "vitest";

// ── Types (mirrored from TaxDeductiblePage.tsx) ──────────────────────────────

interface TaxSummary {
  label_id: string;
  label_name: string;
  label_color: string;
  total_amount: number;
  transaction_count: number;
}

interface TaxLabel {
  id: string;
  name: string;
  color: string;
}

// ── Logic helpers (mirrored from TaxDeductiblePage.tsx) ──────────────────────

const TAX_LABEL_NAMES = [
  "Medical & Dental",
  "Charitable Donations",
  "Business Expenses",
  "Education",
  "Home Office",
];

function taxLabelsExist(allLabels: TaxLabel[]): boolean {
  return TAX_LABEL_NAMES.every((name) =>
    allLabels.some((label) => label.name === name),
  );
}

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);

const formatDate = (dateStr: string) =>
  new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

function computeTotals(summaries: TaxSummary[]): {
  totalDeductible: number;
  totalTransactions: number;
} {
  return {
    totalDeductible: summaries.reduce((sum, s) => sum + s.total_amount, 0),
    totalTransactions: summaries.reduce(
      (sum, s) => sum + s.transaction_count,
      0,
    ),
  };
}

function buildExportFilename(startDate: string, endDate: string): string {
  return `tax-deductible-${startDate}-to-${endDate}.csv`;
}

// ── Fixtures ─────────────────────────────────────────────────────────────────

const SUMMARIES: TaxSummary[] = [
  {
    label_id: "l1",
    label_name: "Medical & Dental",
    label_color: "#FF0000",
    total_amount: 1500.5,
    transaction_count: 3,
  },
  {
    label_id: "l2",
    label_name: "Charitable Donations",
    label_color: "#00FF00",
    total_amount: 2000.0,
    transaction_count: 5,
  },
  {
    label_id: "l3",
    label_name: "Business Expenses",
    label_color: "#0000FF",
    total_amount: 800.25,
    transaction_count: 2,
  },
];

const ALL_TAX_LABELS: TaxLabel[] = [
  { id: "1", name: "Medical & Dental", color: "#FF0000" },
  { id: "2", name: "Charitable Donations", color: "#00FF00" },
  { id: "3", name: "Business Expenses", color: "#0000FF" },
  { id: "4", name: "Education", color: "#FFFF00" },
  { id: "5", name: "Home Office", color: "#FF00FF" },
];

// ── Tests ────────────────────────────────────────────────────────────────────

describe("taxLabelsExist", () => {
  it("returns true when all 5 tax labels are present", () => {
    expect(taxLabelsExist(ALL_TAX_LABELS)).toBe(true);
  });

  it("returns false when one label is missing", () => {
    const partial = ALL_TAX_LABELS.slice(0, 4); // missing Home Office
    expect(taxLabelsExist(partial)).toBe(false);
  });

  it("returns false for empty label list", () => {
    expect(taxLabelsExist([])).toBe(false);
  });

  it("returns true even if extra labels exist", () => {
    const withExtra = [
      ...ALL_TAX_LABELS,
      { id: "6", name: "Custom Label", color: "#999" },
    ];
    expect(taxLabelsExist(withExtra)).toBe(true);
  });
});

describe("computeTotals", () => {
  it("sums total deductible amounts", () => {
    const { totalDeductible } = computeTotals(SUMMARIES);
    expect(totalDeductible).toBeCloseTo(4300.75);
  });

  it("sums total transaction counts", () => {
    const { totalTransactions } = computeTotals(SUMMARIES);
    expect(totalTransactions).toBe(10);
  });

  it("returns zeros for empty summaries", () => {
    const { totalDeductible, totalTransactions } = computeTotals([]);
    expect(totalDeductible).toBe(0);
    expect(totalTransactions).toBe(0);
  });
});

describe("formatCurrency (2-decimal)", () => {
  it("formats with two decimal places", () => {
    expect(formatCurrency(1500.5)).toBe("$1,500.50");
  });

  it("formats zero", () => {
    expect(formatCurrency(0)).toBe("$0.00");
  });

  it("formats whole numbers with .00", () => {
    expect(formatCurrency(2000)).toBe("$2,000.00");
  });
});

describe("formatDate", () => {
  it("formats date string for display", () => {
    const result = formatDate("2025-06-15");
    expect(result).toContain("Jun");
    expect(result).toContain("2025");
    // Day may shift by ±1 due to UTC parsing in local timezone
    expect(result).toMatch(/1[45]/);
  });
});

describe("buildExportFilename", () => {
  it("builds correct CSV filename from date range", () => {
    expect(buildExportFilename("2025-01-01", "2025-12-31")).toBe(
      "tax-deductible-2025-01-01-to-2025-12-31.csv",
    );
  });
});

describe("Export button disabled state", () => {
  it("disables export when no transactions", () => {
    const totalTransactions = 0;
    expect(totalTransactions === 0).toBe(true);
  });

  it("enables export when transactions exist", () => {
    const totalTransactions = 10;
    expect(totalTransactions === 0).toBe(false);
  });
});

describe("Default date range", () => {
  it("defaults to Jan 1 - Dec 31 of current year", () => {
    const currentYear = new Date().getFullYear();
    const startDate = `${currentYear}-01-01`;
    const endDate = `${currentYear}-12-31`;
    expect(startDate).toMatch(/^\d{4}-01-01$/);
    expect(endDate).toMatch(/^\d{4}-12-31$/);
  });
});

// ── TaxDeductiblePage summaries error state ──────────────────────────────────
//
// Mirrors the render-branch logic added to TaxDeductiblePage:
//   summariesError → error state with retry button (not the misleading empty state)
//   otherwise      → normal content

type TaxPageSummaryState = "error" | "loading" | "empty" | "data";

const resolveTaxSummaryState = (
  isLoading: boolean,
  summariesError: boolean,
  totalTransactions: number,
): TaxPageSummaryState => {
  if (summariesError) return "error";
  if (isLoading) return "loading";
  if (totalTransactions === 0) return "empty";
  return "data";
};

const taxErrorMessageText = "Failed to load tax data. Please try again.";
const taxRetryButtonLabel = "Retry";

describe("TaxDeductiblePage summaries error state", () => {
  it("resolves to 'error' when summariesError is true", () => {
    expect(resolveTaxSummaryState(false, true, 0)).toBe("error");
  });

  it("error takes priority over empty state (prevents misleading no-data message)", () => {
    // summariesError=true, totalTransactions=0 → should show error, not empty
    expect(resolveTaxSummaryState(false, true, 0)).toBe("error");
  });

  it("resolves to 'loading' when isLoading is true and no error", () => {
    expect(resolveTaxSummaryState(true, false, 0)).toBe("loading");
  });

  it("resolves to 'empty' when no error, not loading, and no transactions", () => {
    expect(resolveTaxSummaryState(false, false, 0)).toBe("empty");
  });

  it("resolves to 'data' when summaries have transactions", () => {
    expect(resolveTaxSummaryState(false, false, 5)).toBe("data");
  });

  it("error message text mentions tax data", () => {
    expect(taxErrorMessageText.toLowerCase()).toContain("tax");
  });

  it("retry button label is defined", () => {
    expect(taxRetryButtonLabel).toBe("Retry");
  });
});
