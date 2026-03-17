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
