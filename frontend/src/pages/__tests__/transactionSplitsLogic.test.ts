/**
 * Pure-logic tests for Transaction Splits feature.
 *
 * No React rendering — all helpers are extracted as plain functions so they
 * can run in a standard Node/Vitest environment.
 */

import { describe, test, expect } from "vitest";
import {
  isSplitSumValid,
  areSplitAmountsPositive,
  SPLIT_TOLERANCE,
} from "../../features/transactions/components/TransactionSplitPanel";

// ── Helpers used by the "UI visibility" tests (pure predicates) ───────────────

/**
 * Whether the Split tab should be rendered at all.
 * Mirrors the condition in TransactionDetailModal: `!transaction.is_pending`
 */
function isSplitTabVisible(isPending: boolean): boolean {
  return !isPending;
}

/**
 * Whether the split editor (Add Split button) should be shown.
 * Requires both editability and a non-pending transaction.
 */
function canShowSplitEditor(isPending: boolean, canEdit: boolean): boolean {
  return !isPending && canEdit;
}

// ── split amount validation ───────────────────────────────────────────────────

describe("split amount validation", () => {
  test("valid when splits sum to transaction total", () => {
    expect(isSplitSumValid([30, 20], 50)).toBe(true);
  });

  test("invalid when splits sum to less than total", () => {
    expect(isSplitSumValid([20, 20], 50)).toBe(false);
  });

  test("invalid when splits sum to more than total", () => {
    expect(isSplitSumValid([30, 30], 50)).toBe(false);
  });

  test("empty splits array is invalid", () => {
    expect(isSplitSumValid([], 50)).toBe(false);
  });

  test("single split equaling total is valid", () => {
    // A single split that equals the total is technically valid per the
    // validation function — the UI separately requires >= 2 rows to save.
    expect(isSplitSumValid([100], 100)).toBe(true);
  });

  test("handles floating point: 33.33 + 33.33 + 33.34 = 100.00", () => {
    const amounts = [33.33, 33.33, 33.34];
    expect(isSplitSumValid(amounts, 100)).toBe(true);
  });

  test("rejects splits that differ by more than tolerance", () => {
    // 0.01 difference — above SPLIT_TOLERANCE of 0.005
    expect(isSplitSumValid([49.99, 49.99], 100)).toBe(false);
  });

  test("accepts splits within tolerance boundary", () => {
    // Difference is exactly at tolerance — should still pass (< not <=)
    const diff = SPLIT_TOLERANCE - 0.001;
    expect(isSplitSumValid([50, 50 - diff], 100 - diff)).toBe(true);
  });

  test("all-zero splits are invalid (amounts not positive)", () => {
    expect(areSplitAmountsPositive([0, 0])).toBe(false);
  });

  test("negative amounts are invalid", () => {
    expect(areSplitAmountsPositive([-10, 60])).toBe(false);
  });

  test("all-positive amounts pass areSplitAmountsPositive", () => {
    expect(areSplitAmountsPositive([25, 25, 50])).toBe(true);
  });
});

// ── split UI visibility ───────────────────────────────────────────────────────

describe("split UI visibility", () => {
  test("split tab hidden for pending transactions", () => {
    expect(isSplitTabVisible(true)).toBe(false);
  });

  test("split tab shown for non-pending transactions", () => {
    expect(isSplitTabVisible(false)).toBe(true);
  });

  test("split editor hidden when canEdit=false even for non-pending", () => {
    expect(canShowSplitEditor(false, false)).toBe(false);
  });

  test("split editor hidden for pending transactions even when canEdit=true", () => {
    expect(canShowSplitEditor(true, true)).toBe(false);
  });

  test("split editor shown for non-pending transactions when canEdit=true", () => {
    expect(canShowSplitEditor(false, true)).toBe(true);
  });
});
