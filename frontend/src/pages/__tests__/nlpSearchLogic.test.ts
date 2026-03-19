/**
 * Tests for the NLP (natural-language) transaction search UI logic in
 * TransactionsPage — specifically the filter state derived from the
 * naturalLanguageSearch API response and the active chip display logic.
 */

import { describe, it, expect } from "vitest";

// ── Types (mirrored from TransactionsPage.tsx) ────────────────────────────────

interface NLPSearchResult {
  search: string | null;
  start_date: string | null;
  end_date: string | null;
  min_amount: number | null;
  max_amount: number | null;
  is_income: boolean | null;
  raw_query: string;
}

// ── Logic helpers (mirrored from TransactionsPage.tsx) ───────────────────────

/** Derive a human-readable date range chip label. */
function buildDateRangeLabel(
  startDate: string | null,
  endDate: string | null,
): string | null {
  if (!startDate) return null;
  const fmt = (d: string) =>
    new Date(d + "T00:00:00").toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  if (endDate) return `${fmt(startDate)} – ${fmt(endDate)}`;
  return `from ${fmt(startDate)}`;
}

/** Derive an amount range chip label. */
function buildAmountRangeLabel(
  minAmount: number | null,
  maxAmount: number | null,
): string | null {
  if (minAmount === null && maxAmount === null) return null;
  const fmt = (v: number) => `$${v.toLocaleString()}`;
  if (minAmount !== null && maxAmount !== null)
    return `${fmt(minAmount)} – ${fmt(maxAmount)}`;
  if (minAmount !== null) return `over ${fmt(minAmount)}`;
  return `under ${fmt(maxAmount!)}`;
}

/** Check whether there are any active NLP chips to display. */
function hasActiveNlpFilters(result: NLPSearchResult): boolean {
  return !!(
    result.search ||
    result.start_date ||
    result.min_amount !== null ||
    result.max_amount !== null ||
    result.is_income !== null
  );
}

/** Determine which filters are applied from an NLP result. */
function deriveActiveFilters(result: NLPSearchResult) {
  return {
    keyword: result.search ?? null,
    dateRange: buildDateRangeLabel(result.start_date, result.end_date),
    amountRange: buildAmountRangeLabel(result.min_amount, result.max_amount),
    incomeLabel:
      result.is_income === true
        ? "Income only"
        : result.is_income === false
          ? "Expenses only"
          : null,
  };
}

// ===========================================================================
// buildDateRangeLabel
// ===========================================================================

describe("buildDateRangeLabel", () => {
  it("returns null when no start date", () => {
    expect(buildDateRangeLabel(null, null)).toBeNull();
  });

  it("formats start + end range", () => {
    const label = buildDateRangeLabel("2025-02-01", "2025-02-28");
    expect(label).toContain("Feb 1");
    expect(label).toContain("Feb 28");
    expect(label).toContain("–");
  });

  it("formats start-only with 'from' prefix", () => {
    const label = buildDateRangeLabel("2025-01-01", null);
    expect(label).toContain("from");
    expect(label).toContain("Jan 1");
  });

  it("includes year in label", () => {
    const label = buildDateRangeLabel("2024-06-15", "2024-06-30");
    expect(label).toContain("2024");
  });
});

// ===========================================================================
// buildAmountRangeLabel
// ===========================================================================

describe("buildAmountRangeLabel", () => {
  it("returns null when no amounts", () => {
    expect(buildAmountRangeLabel(null, null)).toBeNull();
  });

  it("formats min-only as 'over $X'", () => {
    expect(buildAmountRangeLabel(50, null)).toBe("over $50");
  });

  it("formats max-only as 'under $X'", () => {
    expect(buildAmountRangeLabel(null, 100)).toBe("under $100");
  });

  it("formats both as range with –", () => {
    expect(buildAmountRangeLabel(20, 80)).toBe("$20 – $80");
  });

  it("formats large amounts with commas", () => {
    expect(buildAmountRangeLabel(1000, null)).toBe("over $1,000");
  });

  it("formats zero min correctly", () => {
    expect(buildAmountRangeLabel(0, 50)).toBe("$0 – $50");
  });
});

// ===========================================================================
// hasActiveNlpFilters
// ===========================================================================

describe("hasActiveNlpFilters", () => {
  const base: NLPSearchResult = {
    search: null,
    start_date: null,
    end_date: null,
    min_amount: null,
    max_amount: null,
    is_income: null,
    raw_query: "",
  };

  it("returns false for empty result", () => {
    expect(hasActiveNlpFilters(base)).toBe(false);
  });

  it("returns true when keyword set", () => {
    expect(hasActiveNlpFilters({ ...base, search: "amazon" })).toBe(true);
  });

  it("returns true when start_date set", () => {
    expect(hasActiveNlpFilters({ ...base, start_date: "2025-01-01" })).toBe(
      true,
    );
  });

  it("returns true when min_amount set", () => {
    expect(hasActiveNlpFilters({ ...base, min_amount: 50 })).toBe(true);
  });

  it("returns true when max_amount set", () => {
    expect(hasActiveNlpFilters({ ...base, max_amount: 200 })).toBe(true);
  });

  it("returns true when is_income is true", () => {
    expect(hasActiveNlpFilters({ ...base, is_income: true })).toBe(true);
  });

  it("returns true when is_income is false (expenses filter)", () => {
    expect(hasActiveNlpFilters({ ...base, is_income: false })).toBe(true);
  });
});

// ===========================================================================
// deriveActiveFilters — full pipeline
// ===========================================================================

describe("deriveActiveFilters", () => {
  it("full query: keyword + date + amount", () => {
    const result: NLPSearchResult = {
      search: "amazon",
      start_date: "2024-01-01",
      end_date: "2024-12-31",
      min_amount: 50,
      max_amount: null,
      is_income: null,
      raw_query: "amazon over $50 in 2024",
    };
    const filters = deriveActiveFilters(result);
    expect(filters.keyword).toBe("amazon");
    expect(filters.dateRange).toContain("2024");
    expect(filters.amountRange).toBe("over $50");
    expect(filters.incomeLabel).toBeNull();
  });

  it("income-only query", () => {
    const result: NLPSearchResult = {
      search: null,
      start_date: "2025-01-01",
      end_date: "2025-03-15",
      min_amount: null,
      max_amount: null,
      is_income: true,
      raw_query: "income ytd",
    };
    const filters = deriveActiveFilters(result);
    expect(filters.keyword).toBeNull();
    expect(filters.incomeLabel).toBe("Income only");
    expect(filters.amountRange).toBeNull();
  });

  it("expenses-only query", () => {
    const result: NLPSearchResult = {
      search: null,
      start_date: null,
      end_date: null,
      min_amount: null,
      max_amount: null,
      is_income: false,
      raw_query: "expenses",
    };
    const filters = deriveActiveFilters(result);
    expect(filters.incomeLabel).toBe("Expenses only");
  });

  it("amount range query", () => {
    const result: NLPSearchResult = {
      search: "dining",
      start_date: null,
      end_date: null,
      min_amount: 20,
      max_amount: 100,
      is_income: null,
      raw_query: "dining between $20 and $100",
    };
    const filters = deriveActiveFilters(result);
    expect(filters.amountRange).toBe("$20 – $100");
    expect(filters.keyword).toBe("dining");
  });

  it("blank result yields all nulls", () => {
    const result: NLPSearchResult = {
      search: null,
      start_date: null,
      end_date: null,
      min_amount: null,
      max_amount: null,
      is_income: null,
      raw_query: "show me everything",
    };
    const filters = deriveActiveFilters(result);
    expect(filters.keyword).toBeNull();
    expect(filters.dateRange).toBeNull();
    expect(filters.amountRange).toBeNull();
    expect(filters.incomeLabel).toBeNull();
  });
});
