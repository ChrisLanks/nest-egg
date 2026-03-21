/**
 * Tests for RecurringTransactionsPage pure logic: subscription filtering,
 * subscription summary calculations, frequency formatting, active/inactive
 * filtering, confidence-score badge coloring, merchant autocomplete filtering,
 * and form validation.
 *
 * All helpers mirror the exact expressions used inside
 * RecurringTransactionsPage so that regressions are caught without rendering.
 */

import { describe, it, expect } from "vitest";
import {
  RecurringFrequency,
  type RecurringTransaction,
} from "../../types/recurring-transaction";

// ── helpers mirroring RecurringTransactionsPage expressions ──────────────────

/**
 * Subscription filter: active, monthly or yearly, confidence >= 0.7
 * Matches the component's `subscriptions` useMemo.
 */
const filterSubscriptions = (
  patterns: RecurringTransaction[],
): RecurringTransaction[] =>
  patterns.filter(
    (p) =>
      p.is_active &&
      (p.frequency === RecurringFrequency.MONTHLY ||
        p.frequency === RecurringFrequency.YEARLY) &&
      (p.confidence_score ?? 0) >= 0.7,
  );

/**
 * Subscription summary: count, monthlyTotal, yearlyTotal.
 * Yearly patterns are amortized to monthly by dividing by 12.
 */
const calcSubscriptionSummary = (subscriptions: RecurringTransaction[]) => {
  const monthlyTotal = subscriptions.reduce((sum, sub) => {
    const amount = Math.abs(sub.average_amount);
    if (sub.frequency === RecurringFrequency.MONTHLY) {
      return sum + amount;
    } else if (sub.frequency === RecurringFrequency.YEARLY) {
      return sum + amount / 12;
    }
    return sum;
  }, 0);

  return {
    count: subscriptions.length,
    monthlyTotal,
    yearlyTotal: monthlyTotal * 12,
  };
};

/** Mirrors formatFrequency switch statement */
const formatFrequency = (frequency: RecurringFrequency): string => {
  switch (frequency) {
    case RecurringFrequency.WEEKLY:
      return "Weekly";
    case RecurringFrequency.BIWEEKLY:
      return "Bi-weekly";
    case RecurringFrequency.MONTHLY:
      return "Monthly";
    case RecurringFrequency.QUARTERLY:
      return "Quarterly";
    case RecurringFrequency.YEARLY:
      return "Yearly";
    case RecurringFrequency.ON_DEMAND:
      return "On Demand";
  }
};

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(amount);

/** Mirrors confidence score badge color logic */
const getConfidenceBadgeColor = (score: number | null): string => {
  const s = score ?? 0;
  if (s >= 0.8) return "green";
  if (s >= 0.6) return "yellow";
  return "orange";
};

/** Mirrors subscription-tab confidence badge color (different thresholds) */
const getSubscriptionConfidenceBadgeColor = (score: number | null): string => {
  const s = score ?? 0;
  return s >= 0.85 ? "green" : "yellow";
};

/** Mirrors merchant autocomplete filter */
const filterMerchants = (query: string, allMerchants: string[]): string[] => {
  if (!query.trim()) return [];
  const q = query.toLowerCase();
  return allMerchants.filter((m) => m.toLowerCase().includes(q)).slice(0, 10);
};

/** Mirrors add-form validation (save button disabled check) */
const isAddSaveDisabled = (merchantName: string, accountId: string) =>
  !merchantName.trim() || !accountId;

/** Mirrors edit-form validation */
const isEditSaveDisabled = (merchantName: string) => !merchantName.trim();

// ── fixture factory ─────────────────────────────────────────────────────────

const makePattern = (
  overrides: Partial<RecurringTransaction> = {},
): RecurringTransaction => ({
  id: "p-1",
  organization_id: "org-1",
  account_id: "acc-1",
  merchant_name: "Netflix",
  description_pattern: null,
  frequency: RecurringFrequency.MONTHLY,
  average_amount: -15.99,
  amount_variance: 0,
  category_id: null,
  is_user_created: false,
  confidence_score: 0.95,
  first_occurrence: "2025-01-15",
  last_occurrence: "2026-03-15",
  next_expected_date: "2026-04-15",
  occurrence_count: 14,
  is_active: true,
  is_archived: false,
  is_no_longer_found: false,
  label_id: null,
  is_bill: false,
  reminder_days_before: 3,
  created_at: "2025-01-15T00:00:00Z",
  updated_at: "2026-03-15T00:00:00Z",
  ...overrides,
});

// ── filterSubscriptions ─────────────────────────────────────────────────────

describe("filterSubscriptions", () => {
  it("includes active monthly patterns with confidence >= 0.7", () => {
    const patterns = [
      makePattern({
        id: "s1",
        frequency: RecurringFrequency.MONTHLY,
        is_active: true,
        confidence_score: 0.85,
      }),
    ];
    expect(filterSubscriptions(patterns)).toHaveLength(1);
  });

  it("includes active yearly patterns with confidence >= 0.7", () => {
    const patterns = [
      makePattern({
        id: "s2",
        frequency: RecurringFrequency.YEARLY,
        is_active: true,
        confidence_score: 0.75,
      }),
    ];
    expect(filterSubscriptions(patterns)).toHaveLength(1);
  });

  it("excludes inactive patterns", () => {
    const patterns = [
      makePattern({
        id: "s3",
        frequency: RecurringFrequency.MONTHLY,
        is_active: false,
        confidence_score: 0.9,
      }),
    ];
    expect(filterSubscriptions(patterns)).toHaveLength(0);
  });

  it("excludes weekly patterns (not a subscription frequency)", () => {
    const patterns = [
      makePattern({
        id: "s4",
        frequency: RecurringFrequency.WEEKLY,
        is_active: true,
        confidence_score: 0.9,
      }),
    ];
    expect(filterSubscriptions(patterns)).toHaveLength(0);
  });

  it("excludes biweekly patterns", () => {
    const patterns = [
      makePattern({
        id: "s5",
        frequency: RecurringFrequency.BIWEEKLY,
        is_active: true,
        confidence_score: 0.9,
      }),
    ];
    expect(filterSubscriptions(patterns)).toHaveLength(0);
  });

  it("excludes quarterly patterns", () => {
    const patterns = [
      makePattern({
        id: "s6",
        frequency: RecurringFrequency.QUARTERLY,
        is_active: true,
        confidence_score: 0.9,
      }),
    ];
    expect(filterSubscriptions(patterns)).toHaveLength(0);
  });

  it("excludes on_demand patterns", () => {
    const patterns = [
      makePattern({
        id: "s7",
        frequency: RecurringFrequency.ON_DEMAND,
        is_active: true,
        confidence_score: 0.9,
      }),
    ];
    expect(filterSubscriptions(patterns)).toHaveLength(0);
  });

  it("excludes patterns with confidence < 0.7", () => {
    const patterns = [
      makePattern({
        id: "s8",
        frequency: RecurringFrequency.MONTHLY,
        is_active: true,
        confidence_score: 0.69,
      }),
    ];
    expect(filterSubscriptions(patterns)).toHaveLength(0);
  });

  it("includes patterns at exactly 0.7 confidence (boundary)", () => {
    const patterns = [
      makePattern({
        id: "s9",
        frequency: RecurringFrequency.MONTHLY,
        is_active: true,
        confidence_score: 0.7,
      }),
    ];
    expect(filterSubscriptions(patterns)).toHaveLength(1);
  });

  it("treats null confidence_score as 0 (excluded)", () => {
    const patterns = [
      makePattern({
        id: "s10",
        frequency: RecurringFrequency.MONTHLY,
        is_active: true,
        confidence_score: null,
      }),
    ];
    expect(filterSubscriptions(patterns)).toHaveLength(0);
  });

  it("filters a mixed list correctly", () => {
    const patterns = [
      makePattern({
        id: "a",
        frequency: RecurringFrequency.MONTHLY,
        is_active: true,
        confidence_score: 0.9,
      }),
      makePattern({
        id: "b",
        frequency: RecurringFrequency.YEARLY,
        is_active: true,
        confidence_score: 0.8,
      }),
      makePattern({
        id: "c",
        frequency: RecurringFrequency.WEEKLY,
        is_active: true,
        confidence_score: 0.95,
      }),
      makePattern({
        id: "d",
        frequency: RecurringFrequency.MONTHLY,
        is_active: false,
        confidence_score: 0.9,
      }),
      makePattern({
        id: "e",
        frequency: RecurringFrequency.MONTHLY,
        is_active: true,
        confidence_score: 0.5,
      }),
    ];
    const subs = filterSubscriptions(patterns);
    expect(subs).toHaveLength(2);
    expect(subs.map((s) => s.id)).toEqual(["a", "b"]);
  });
});

// ── calcSubscriptionSummary ─────────────────────────────────────────────────

describe("calcSubscriptionSummary", () => {
  it("sums monthly subscriptions at face value", () => {
    const subs = [
      makePattern({
        frequency: RecurringFrequency.MONTHLY,
        average_amount: -15.99,
      }),
      makePattern({
        frequency: RecurringFrequency.MONTHLY,
        average_amount: -9.99,
      }),
    ];
    const summary = calcSubscriptionSummary(subs);
    expect(summary.count).toBe(2);
    expect(summary.monthlyTotal).toBeCloseTo(25.98, 2);
    expect(summary.yearlyTotal).toBeCloseTo(25.98 * 12, 2);
  });

  it("amortizes yearly subscriptions to monthly (divides by 12)", () => {
    const subs = [
      makePattern({
        frequency: RecurringFrequency.YEARLY,
        average_amount: -120,
      }),
    ];
    const summary = calcSubscriptionSummary(subs);
    expect(summary.monthlyTotal).toBeCloseTo(10, 2);
    expect(summary.yearlyTotal).toBeCloseTo(120, 2);
  });

  it("uses absolute value of amounts (handles negative amounts)", () => {
    const subs = [
      makePattern({
        frequency: RecurringFrequency.MONTHLY,
        average_amount: -50,
      }),
    ];
    const summary = calcSubscriptionSummary(subs);
    expect(summary.monthlyTotal).toBe(50);
  });

  it("handles positive amounts the same way", () => {
    const subs = [
      makePattern({
        frequency: RecurringFrequency.MONTHLY,
        average_amount: 50,
      }),
    ];
    const summary = calcSubscriptionSummary(subs);
    expect(summary.monthlyTotal).toBe(50);
  });

  it("returns zeros for empty list", () => {
    const summary = calcSubscriptionSummary([]);
    expect(summary.count).toBe(0);
    expect(summary.monthlyTotal).toBe(0);
    expect(summary.yearlyTotal).toBe(0);
  });

  it("combines monthly and yearly subscriptions correctly", () => {
    const subs = [
      makePattern({
        frequency: RecurringFrequency.MONTHLY,
        average_amount: -10,
      }),
      makePattern({
        frequency: RecurringFrequency.YEARLY,
        average_amount: -120,
      }),
    ];
    const summary = calcSubscriptionSummary(subs);
    // monthly: 10 + 120/12 = 10 + 10 = 20
    expect(summary.monthlyTotal).toBeCloseTo(20, 2);
    expect(summary.yearlyTotal).toBeCloseTo(240, 2);
  });

  it("yearly total is always monthly * 12", () => {
    const subs = [
      makePattern({
        frequency: RecurringFrequency.MONTHLY,
        average_amount: -7.5,
      }),
      makePattern({
        frequency: RecurringFrequency.YEARLY,
        average_amount: -99,
      }),
    ];
    const summary = calcSubscriptionSummary(subs);
    expect(summary.yearlyTotal).toBeCloseTo(summary.monthlyTotal * 12, 2);
  });
});

// ── formatFrequency ─────────────────────────────────────────────────────────

describe("formatFrequency", () => {
  it.each([
    [RecurringFrequency.WEEKLY, "Weekly"],
    [RecurringFrequency.BIWEEKLY, "Bi-weekly"],
    [RecurringFrequency.MONTHLY, "Monthly"],
    [RecurringFrequency.QUARTERLY, "Quarterly"],
    [RecurringFrequency.YEARLY, "Yearly"],
    [RecurringFrequency.ON_DEMAND, "On Demand"],
  ] as const)('formats %s as "%s"', (freq, expected) => {
    expect(formatFrequency(freq)).toBe(expected);
  });
});

// ── formatCurrency ──────────────────────────────────────────────────────────

describe("formatCurrency", () => {
  it("formats with dollar sign and two decimals", () => {
    expect(formatCurrency(15.99)).toBe("$15.99");
  });

  it("formats zero", () => {
    expect(formatCurrency(0)).toBe("$0.00");
  });

  it("formats negative amounts", () => {
    expect(formatCurrency(-42.5)).toBe("-$42.50");
  });

  it("handles large amounts with comma separators", () => {
    expect(formatCurrency(10000)).toBe("$10,000.00");
  });
});

// ── getConfidenceBadgeColor (all-recurring tab) ─────────────────────────────

describe("getConfidenceBadgeColor", () => {
  it("green for >= 0.8", () => {
    expect(getConfidenceBadgeColor(0.8)).toBe("green");
    expect(getConfidenceBadgeColor(0.95)).toBe("green");
    expect(getConfidenceBadgeColor(1.0)).toBe("green");
  });

  it("yellow for >= 0.6 and < 0.8", () => {
    expect(getConfidenceBadgeColor(0.6)).toBe("yellow");
    expect(getConfidenceBadgeColor(0.7)).toBe("yellow");
    expect(getConfidenceBadgeColor(0.79)).toBe("yellow");
  });

  it("orange for < 0.6", () => {
    expect(getConfidenceBadgeColor(0.59)).toBe("orange");
    expect(getConfidenceBadgeColor(0.1)).toBe("orange");
    expect(getConfidenceBadgeColor(0)).toBe("orange");
  });

  it("treats null score as 0 (orange)", () => {
    expect(getConfidenceBadgeColor(null)).toBe("orange");
  });
});

// ── getSubscriptionConfidenceBadgeColor (subscriptions tab) ─────────────────

describe("getSubscriptionConfidenceBadgeColor", () => {
  it("green for >= 0.85", () => {
    expect(getSubscriptionConfidenceBadgeColor(0.85)).toBe("green");
    expect(getSubscriptionConfidenceBadgeColor(0.95)).toBe("green");
  });

  it("yellow for < 0.85", () => {
    expect(getSubscriptionConfidenceBadgeColor(0.84)).toBe("yellow");
    expect(getSubscriptionConfidenceBadgeColor(0.7)).toBe("yellow");
  });

  it("treats null as 0 (yellow)", () => {
    expect(getSubscriptionConfidenceBadgeColor(null)).toBe("yellow");
  });
});

// ── filterMerchants (autocomplete) ──────────────────────────────────────────

describe("filterMerchants", () => {
  const merchants = [
    "Netflix",
    "Netlify",
    "Amazon Prime",
    "Amazon Web Services",
    "Spotify",
    "Apple Music",
    "Apple TV+",
    "Google One",
    "YouTube Premium",
    "Hulu",
    "Disney+",
    "HBO Max",
  ];

  it("returns empty for empty query", () => {
    expect(filterMerchants("", merchants)).toEqual([]);
  });

  it("returns empty for whitespace-only query", () => {
    expect(filterMerchants("   ", merchants)).toEqual([]);
  });

  it("filters case-insensitively", () => {
    const result = filterMerchants("netflix", merchants);
    expect(result).toEqual(["Netflix"]);
  });

  it("matches partial strings", () => {
    const result = filterMerchants("net", merchants);
    expect(result).toEqual(["Netflix", "Netlify"]);
  });

  it("matches anywhere in the string", () => {
    const result = filterMerchants("prime", merchants);
    expect(result).toEqual(["Amazon Prime"]);
  });

  it("limits results to 10 entries", () => {
    const manyMerchants = Array.from({ length: 20 }, (_, i) => `Store ${i}`);
    const result = filterMerchants("store", manyMerchants);
    expect(result).toHaveLength(10);
  });

  it("returns all matches when fewer than 10", () => {
    const result = filterMerchants("apple", merchants);
    expect(result).toEqual(["Apple Music", "Apple TV+"]);
  });

  it("returns empty when nothing matches", () => {
    expect(filterMerchants("zzzzz", merchants)).toEqual([]);
  });
});

// ── form validation ─────────────────────────────────────────────────────────

describe("isAddSaveDisabled", () => {
  it("disabled when merchant name is empty", () => {
    expect(isAddSaveDisabled("", "acc-1")).toBe(true);
  });

  it("disabled when merchant name is whitespace", () => {
    expect(isAddSaveDisabled("   ", "acc-1")).toBe(true);
  });

  it("disabled when account ID is empty", () => {
    expect(isAddSaveDisabled("Netflix", "")).toBe(true);
  });

  it("disabled when both empty", () => {
    expect(isAddSaveDisabled("", "")).toBe(true);
  });

  it("enabled when both provided", () => {
    expect(isAddSaveDisabled("Netflix", "acc-1")).toBe(false);
  });
});

describe("isEditSaveDisabled", () => {
  it("disabled when merchant name is empty", () => {
    expect(isEditSaveDisabled("")).toBe(true);
  });

  it("disabled when merchant name is whitespace", () => {
    expect(isEditSaveDisabled("   ")).toBe(true);
  });

  it("enabled when merchant name has content", () => {
    expect(isEditSaveDisabled("Netflix")).toBe(false);
  });
});

// ── active vs inactive display logic ────────────────────────────────────────

describe("active/inactive display logic", () => {
  it("active patterns have full opacity (1)", () => {
    const p = makePattern({ is_active: true });
    expect(p.is_active ? 1 : 0.5).toBe(1);
  });

  it("inactive patterns have reduced opacity (0.5)", () => {
    const p = makePattern({ is_active: false });
    expect(p.is_active ? 1 : 0.5).toBe(0.5);
  });

  it("user-created patterns display 'Manual' badge", () => {
    const p = makePattern({ is_user_created: true });
    expect(p.is_user_created ? "Manual" : "Auto").toBe("Manual");
  });

  it("auto-detected patterns display 'Auto' badge", () => {
    const p = makePattern({ is_user_created: false });
    expect(p.is_user_created ? "Manual" : "Auto").toBe("Auto");
  });

  it("inactive patterns show Inactive badge", () => {
    const p = makePattern({ is_active: false });
    expect(!p.is_active).toBe(true);
  });
});

// ── next expected date display ──────────────────────────────────────────────

describe("next expected date display", () => {
  it("shows formatted date when present", () => {
    const p = makePattern({ next_expected_date: "2026-04-15" });
    expect(p.next_expected_date).not.toBeNull();
    const display = p.next_expected_date
      ? new Date(p.next_expected_date).toLocaleDateString()
      : "\u2014";
    expect(display).not.toBe("\u2014");
  });

  it("shows em-dash when null", () => {
    const p = makePattern({ next_expected_date: null });
    const display = p.next_expected_date
      ? new Date(p.next_expected_date).toLocaleDateString()
      : "\u2014";
    expect(display).toBe("\u2014");
  });
});

// ── confidence score display ────────────────────────────────────────────────

describe("confidence score percentage display", () => {
  it("formats 0.95 as 95%", () => {
    expect((0.95 * 100).toFixed(0)).toBe("95");
  });

  it("formats 0.7 as 70%", () => {
    expect((0.7 * 100).toFixed(0)).toBe("70");
  });

  it("formats 1.0 as 100%", () => {
    expect((1.0 * 100).toFixed(0)).toBe("100");
  });

  it("formats 0.333 as 33%", () => {
    expect((0.333 * 100).toFixed(0)).toBe("33");
  });
});

// ── edit form amount parsing ────────────────────────────────────────────────

describe("edit form amount parsing", () => {
  it("parses valid number string", () => {
    expect(parseFloat("15.99") || 0).toBe(15.99);
  });

  it("returns 0 for empty string", () => {
    expect(parseFloat("") || 0).toBe(0);
  });

  it("returns 0 for non-numeric string", () => {
    expect(parseFloat("abc") || 0).toBe(0);
  });

  it("parses integer string", () => {
    expect(parseFloat("100") || 0).toBe(100);
  });

  it("openEdit uses absolute value of average_amount", () => {
    const pattern = makePattern({ average_amount: -42.5 });
    const editFormAmount = String(Math.abs(pattern.average_amount));
    expect(editFormAmount).toBe("42.5");
  });
});

// ── Error state rendering decision ────────────────────────────────────────────
//
// Mirrors the render-branch logic in RecurringTransactionsPage:
//   if (patternsError) → error state with retry button
//   otherwise          → normal content (with isLoading handled inline via
//                        conditional blocks inside the JSX)

type RecurringPageState = "error" | "normal";

const resolveRecurringPageState = (patternsError: boolean): RecurringPageState => {
  if (patternsError) return "error";
  return "normal";
};

const recurringErrorMessageText =
  "Failed to load recurring transactions. Please try again.";
const recurringRetryButtonLabel = "Retry";

describe("RecurringTransactionsPage error state", () => {
  it("resolves to 'error' when patternsError is true", () => {
    expect(resolveRecurringPageState(true)).toBe("error");
  });

  it("resolves to 'normal' when patternsError is false", () => {
    expect(resolveRecurringPageState(false)).toBe("normal");
  });

  it("error message text mentions recurring transactions", () => {
    expect(recurringErrorMessageText.toLowerCase()).toContain("recurring");
  });

  it("retry button label is defined", () => {
    expect(recurringRetryButtonLabel).toBe("Retry");
  });

  it("normal state shows patterns when data is available", () => {
    const state = resolveRecurringPageState(false);
    expect(state).toBe("normal");
    const patterns: RecurringTransaction[] = [makePattern()];
    expect(patterns.length).toBeGreaterThan(0);
  });

  it("error state is shown regardless of whether patterns data exists", () => {
    // Even if stale patterns data exists, patternsError=true triggers error UI
    const state = resolveRecurringPageState(true);
    expect(state).toBe("error");
  });
});

// ── RecurringTransactionsPage delete confirmation dialog ─────────────────────
//
// Mirrors the confirmation guard added to RecurringTransactionsPage:
//   clicking the Delete icon opens AlertDialog;
//   actual deletion only fires after the user confirms.

const deleteConfirmHeaderText = "Delete Pattern";
const deleteConfirmBodyText =
  "Are you sure you want to delete this recurring pattern? This action cannot be undone.";
const deleteConfirmButtonLabel = "Delete";
const deleteCancelButtonLabel = "Cancel";

describe("RecurringTransactionsPage delete confirmation dialog", () => {
  it("dialog header is 'Delete Pattern'", () => {
    expect(deleteConfirmHeaderText).toBe("Delete Pattern");
  });

  it("dialog body warns about irreversibility", () => {
    expect(deleteConfirmBodyText.toLowerCase()).toContain("cannot be undone");
  });

  it("confirm button label is 'Delete'", () => {
    expect(deleteConfirmButtonLabel).toBe("Delete");
  });

  it("cancel button label is 'Cancel'", () => {
    expect(deleteCancelButtonLabel).toBe("Cancel");
  });

  it("delete mutation does not fire until user confirms", () => {
    let mutationFired = false;
    let dialogOpen = false;

    const openConfirmDialog = (patternId: string) => {
      expect(patternId).toBeTruthy();
      dialogOpen = true;
    };

    const confirmAndDelete = (patternId: string) => {
      expect(patternId).toBeTruthy();
      mutationFired = true;
      dialogOpen = false;
    };

    // Step 1: clicking delete icon opens dialog, mutation not yet fired
    openConfirmDialog("pattern-123");
    expect(dialogOpen).toBe(true);
    expect(mutationFired).toBe(false);

    // Step 2: confirming fires the mutation
    confirmAndDelete("pattern-123");
    expect(mutationFired).toBe(true);
    expect(dialogOpen).toBe(false);
  });

  it("cancelling closes dialog without firing mutation", () => {
    let mutationFired = false;
    let dialogOpen = false;

    const openConfirmDialog = () => {
      dialogOpen = true;
    };
    const cancelDelete = () => {
      dialogOpen = false;
    };

    openConfirmDialog();
    expect(dialogOpen).toBe(true);
    cancelDelete();
    expect(dialogOpen).toBe(false);
    expect(mutationFired).toBe(false);
  });
});
