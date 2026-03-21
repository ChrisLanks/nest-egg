/**
 * Tests for budget suggestion logic: period labels, suggestion-to-prefill
 * conversion, and display formatting.
 */

import { describe, it, expect } from "vitest";
import type { BudgetSuggestion } from "../../../types/budget";
import { BudgetPeriod } from "../../../types/budget";

// ---------------------------------------------------------------------------
// Period label formatting (mirrors BudgetSuggestions.tsx)
// ---------------------------------------------------------------------------

function periodLabel(period: string): string {
  switch (period) {
    case "monthly":
      return "Monthly";
    case "quarterly":
      return "Quarterly";
    case "semi_annual":
      return "Every 6 Months";
    case "yearly":
      return "Yearly";
    default:
      return period;
  }
}

describe("periodLabel", () => {
  it.each([
    ["monthly", "Monthly"],
    ["quarterly", "Quarterly"],
    ["semi_annual", "Every 6 Months"],
    ["yearly", "Yearly"],
  ])("formats %s as %s", (input, expected) => {
    expect(periodLabel(input)).toBe(expected);
  });

  it("returns raw value for unknown period", () => {
    expect(periodLabel("custom")).toBe("custom");
  });
});

// ---------------------------------------------------------------------------
// Suggestion to prefill conversion (mirrors BudgetsPage handleAcceptSuggestion)
// ---------------------------------------------------------------------------

interface PrefillValues {
  name: string;
  amount: number;
  period: BudgetPeriod;
  category_id?: string;
  start_date: string;
}

function suggestionToPrefill(suggestion: BudgetSuggestion): PrefillValues {
  return {
    name: suggestion.category_name,
    amount: suggestion.suggested_amount,
    period: suggestion.suggested_period as BudgetPeriod,
    category_id: suggestion.category_id ?? undefined,
    start_date: new Date().toISOString().split("T")[0],
  };
}

const makeSuggestion = (
  overrides: Partial<BudgetSuggestion> = {},
): BudgetSuggestion => ({
  category_name: "Groceries",
  category_id: "cat-123",
  suggested_amount: 500,
  suggested_period: BudgetPeriod.MONTHLY,
  avg_monthly_spend: 450,
  total_spend: 2700,
  month_count: 6,
  transaction_count: 45,
  ...overrides,
});

describe("suggestionToPrefill", () => {
  it("maps suggestion fields to form prefill values", () => {
    const suggestion = makeSuggestion();
    const prefill = suggestionToPrefill(suggestion);

    expect(prefill.name).toBe("Groceries");
    expect(prefill.amount).toBe(500);
    expect(prefill.period).toBe(BudgetPeriod.MONTHLY);
    expect(prefill.category_id).toBe("cat-123");
    expect(prefill.start_date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  it("handles null category_id (provider categories)", () => {
    const suggestion = makeSuggestion({ category_id: null });
    const prefill = suggestionToPrefill(suggestion);

    expect(prefill.category_id).toBeUndefined();
  });

  it("preserves semi_annual period", () => {
    const suggestion = makeSuggestion({
      suggested_period: BudgetPeriod.SEMI_ANNUAL,
      suggested_amount: 600,
    });
    const prefill = suggestionToPrefill(suggestion);

    expect(prefill.period).toBe(BudgetPeriod.SEMI_ANNUAL);
    expect(prefill.amount).toBe(600);
  });

  it("preserves yearly period", () => {
    const suggestion = makeSuggestion({
      suggested_period: BudgetPeriod.YEARLY,
      suggested_amount: 1200,
    });
    const prefill = suggestionToPrefill(suggestion);

    expect(prefill.period).toBe(BudgetPeriod.YEARLY);
  });
});

// ---------------------------------------------------------------------------
// Auto-poll / scanning logic (mirrors BudgetSuggestions.tsx)
// ---------------------------------------------------------------------------

interface BudgetSuggestionsResponse {
  suggestions: BudgetSuggestion[];
  scanning: boolean;
}

/**
 * Mirrors the component's derived `isScanning` display flag:
 * show the scanning UI when the response reports scanning=true AND
 * no suggestions have arrived yet.
 */
function shouldShowScanning(response: BudgetSuggestionsResponse): boolean {
  return response.scanning && response.suggestions.length === 0;
}

/**
 * Mirrors the refetchInterval callback in BudgetSuggestions.tsx.
 * Returns the poll interval (ms) while scanning with no results, otherwise false.
 */
function getRefetchInterval(data: BudgetSuggestionsResponse | undefined): number | false {
  return data?.scanning && (!data?.suggestions || data.suggestions.length === 0)
    ? 15_000
    : false;
}

/** Text shown in the heading while scanning (from the component JSX). */
const SCANNING_HEADING = "Analysing your spending history…";

/** Text shown in the body while scanning (from the component JSX). */
const SCANNING_BODY =
  "We're scanning your transactions in the background to find smart budget suggestions. This usually takes under a minute.";

describe("shouldShowScanning", () => {
  it("is true when scanning=true and suggestions array is empty", () => {
    expect(shouldShowScanning({ scanning: true, suggestions: [] })).toBe(true);
  });

  it("is false when scanning=true but suggestions already present", () => {
    const response: BudgetSuggestionsResponse = {
      scanning: true,
      suggestions: [makeSuggestion()],
    };
    expect(shouldShowScanning(response)).toBe(false);
  });

  it("is false when scanning=false and suggestions are empty", () => {
    expect(shouldShowScanning({ scanning: false, suggestions: [] })).toBe(false);
  });

  it("is false when scanning=false and suggestions are present", () => {
    const response: BudgetSuggestionsResponse = {
      scanning: false,
      suggestions: [makeSuggestion()],
    };
    expect(shouldShowScanning(response)).toBe(false);
  });
});

describe("getRefetchInterval", () => {
  it("returns 15000 when scanning with no suggestions", () => {
    expect(getRefetchInterval({ scanning: true, suggestions: [] })).toBe(15_000);
  });

  it("returns false when not scanning (empty suggestions)", () => {
    expect(getRefetchInterval({ scanning: false, suggestions: [] })).toBe(false);
  });

  it("returns false when scanning but suggestions have arrived", () => {
    expect(
      getRefetchInterval({ scanning: true, suggestions: [makeSuggestion()] }),
    ).toBe(false);
  });

  it("returns false when not scanning and suggestions present", () => {
    expect(
      getRefetchInterval({ scanning: false, suggestions: [makeSuggestion()] }),
    ).toBe(false);
  });

  it("returns false when data is undefined", () => {
    expect(getRefetchInterval(undefined)).toBe(false);
  });
});

describe("scanning message content", () => {
  it("heading contains 'alysing' (Analysing / Analyzing)", () => {
    expect(SCANNING_HEADING.toLowerCase()).toMatch(/anal[yz]s/);
  });

  it("body contains 'scanning'", () => {
    expect(SCANNING_BODY.toLowerCase()).toContain("scanning");
  });

  it("body mentions transactions", () => {
    expect(SCANNING_BODY.toLowerCase()).toContain("transactions");
  });

  it("body mentions background processing", () => {
    expect(SCANNING_BODY.toLowerCase()).toContain("background");
  });
});

// ---------------------------------------------------------------------------
// Visibility rules (mirrors BudgetsPage conditions)
// ---------------------------------------------------------------------------

function shouldShowSuggestions(
  budgetCount: number,
  canEdit: boolean,
  isOtherUserView: boolean,
): boolean {
  return budgetCount <= 3 && canEdit && !isOtherUserView;
}

describe("shouldShowSuggestions", () => {
  it("shows when user has no budgets and can edit", () => {
    expect(shouldShowSuggestions(0, true, false)).toBe(true);
  });

  it("shows when user has 1-3 budgets", () => {
    expect(shouldShowSuggestions(1, true, false)).toBe(true);
    expect(shouldShowSuggestions(3, true, false)).toBe(true);
  });

  it("hides when user has more than 3 budgets", () => {
    expect(shouldShowSuggestions(4, true, false)).toBe(false);
    expect(shouldShowSuggestions(10, true, false)).toBe(false);
  });

  it("hides when user cannot edit", () => {
    expect(shouldShowSuggestions(0, false, false)).toBe(false);
  });

  it("hides when viewing another user", () => {
    expect(shouldShowSuggestions(0, true, true)).toBe(false);
  });
});
