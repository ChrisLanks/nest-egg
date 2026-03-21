/**
 * Pure-logic tests for Transaction Merge feature.
 *
 * No React rendering — all helpers are extracted as plain functions so they
 * can run in a standard Node/Vitest environment.
 */

import { describe, test, expect } from "vitest";
import {
  buildDuplicateGroups,
  isPrimaryValid,
  allGroupsHavePrimary,
  groupByDateAndAmount,
  type DuplicateGroup,
} from "../../features/transactions/components/TransactionMergeModal";
import type { Transaction } from "../../types/transaction";

// ── Fixtures ──────────────────────────────────────────────────────────────────

function makeTxn(overrides: Partial<Transaction> & { id: string }): Transaction {
  return {
    id: overrides.id,
    account_id: "acct-1",
    date: overrides.date ?? "2024-03-15",
    amount: overrides.amount ?? -42.5,
    merchant_name: overrides.merchant_name ?? "Coffee Shop",
    description: overrides.description ?? null,
    category_primary: overrides.category_primary ?? "Food",
    category_detailed: overrides.category_detailed ?? null,
    is_pending: overrides.is_pending ?? false,
    is_transfer: overrides.is_transfer ?? false,
    notes: overrides.notes ?? null,
    flagged_for_review: overrides.flagged_for_review ?? false,
    account_name: overrides.account_name ?? "Checking",
    account_mask: overrides.account_mask ?? "1234",
    ...overrides,
  };
}

const txnA = makeTxn({ id: "txn-a", date: "2024-03-15", amount: -42.5 });
const txnB = makeTxn({ id: "txn-b", date: "2024-03-15", amount: -42.5 });
const txnC = makeTxn({ id: "txn-c", date: "2024-04-01", amount: -100.0 });
const txnD = makeTxn({ id: "txn-d", date: "2024-04-01", amount: -100.0 });

// ── buildDuplicateGroups ──────────────────────────────────────────────────────

describe("buildDuplicateGroups", () => {
  test("maps backend matches to DuplicateGroup array", () => {
    const matches = [{ primary: txnA, duplicates: [txnB] }];
    const groups = buildDuplicateGroups(matches);
    expect(groups).toHaveLength(1);
    expect(groups[0].primary.id).toBe("txn-a");
    expect(groups[0].duplicates).toHaveLength(1);
    expect(groups[0].duplicates[0].id).toBe("txn-b");
  });

  test("returns empty array for empty matches", () => {
    expect(buildDuplicateGroups([])).toEqual([]);
  });

  test("preserves multiple groups", () => {
    const matches = [
      { primary: txnA, duplicates: [txnB] },
      { primary: txnC, duplicates: [txnD] },
    ];
    const groups = buildDuplicateGroups(matches);
    expect(groups).toHaveLength(2);
    expect(groups[1].primary.id).toBe("txn-c");
  });
});

// ── isPrimaryValid ────────────────────────────────────────────────────────────

describe("isPrimaryValid", () => {
  const group: DuplicateGroup = { primary: txnA, duplicates: [txnB] };

  test("valid when primaryId matches the suggested primary", () => {
    expect(isPrimaryValid(group, "txn-a")).toBe(true);
  });

  test("valid when primaryId matches a duplicate", () => {
    expect(isPrimaryValid(group, "txn-b")).toBe(true);
  });

  test("invalid when primaryId is empty string", () => {
    expect(isPrimaryValid(group, "")).toBe(false);
  });

  test("invalid when primaryId is not in the group", () => {
    expect(isPrimaryValid(group, "txn-z")).toBe(false);
  });
});

// ── allGroupsHavePrimary ──────────────────────────────────────────────────────

describe("allGroupsHavePrimary — merge validation", () => {
  const groups: DuplicateGroup[] = [
    { primary: txnA, duplicates: [txnB] },
    { primary: txnC, duplicates: [txnD] },
  ];

  test("returns true when all groups have a valid selection", () => {
    const selections = { 0: "txn-a", 1: "txn-c" };
    expect(allGroupsHavePrimary(groups, selections)).toBe(true);
  });

  test("returns false when one group has no selection", () => {
    const selections = { 0: "txn-a" }; // group 1 missing
    expect(allGroupsHavePrimary(groups, selections)).toBe(false);
  });

  test("returns false when one selection is empty string", () => {
    const selections = { 0: "txn-a", 1: "" };
    expect(allGroupsHavePrimary(groups, selections)).toBe(false);
  });

  test("returns false when a selection is an unknown id", () => {
    const selections = { 0: "txn-a", 1: "txn-unknown" };
    expect(allGroupsHavePrimary(groups, selections)).toBe(false);
  });

  test("returns true for empty groups list", () => {
    // Vacuously true — nothing to validate
    expect(allGroupsHavePrimary([], {})).toBe(true);
  });

  test("a duplicate can be selected as primary and still validates", () => {
    const selections = { 0: "txn-b", 1: "txn-d" };
    expect(allGroupsHavePrimary(groups, selections)).toBe(true);
  });
});

// ── groupByDateAndAmount ──────────────────────────────────────────────────────

describe("groupByDateAndAmount — local duplicate grouping", () => {
  test("groups transactions with same date and amount", () => {
    const transactions = [txnA, txnB, txnC];
    const groups = groupByDateAndAmount(transactions);
    expect(groups).toHaveLength(1);
    expect(groups[0]).toHaveLength(2);
    const ids = groups[0].map((t) => t.id).sort();
    expect(ids).toEqual(["txn-a", "txn-b"]);
  });

  test("groups multiple sets of duplicates", () => {
    const transactions = [txnA, txnB, txnC, txnD];
    const groups = groupByDateAndAmount(transactions);
    expect(groups).toHaveLength(2);
    for (const g of groups) {
      expect(g).toHaveLength(2);
    }
  });

  test("does not group transactions with different amounts", () => {
    const t1 = makeTxn({ id: "t1", date: "2024-03-15", amount: -10 });
    const t2 = makeTxn({ id: "t2", date: "2024-03-15", amount: -20 });
    const groups = groupByDateAndAmount([t1, t2]);
    expect(groups).toHaveLength(0);
  });

  test("does not group transactions with different dates", () => {
    const t1 = makeTxn({ id: "t1", date: "2024-03-15", amount: -42.5 });
    const t2 = makeTxn({ id: "t2", date: "2024-03-16", amount: -42.5 });
    const groups = groupByDateAndAmount([t1, t2]);
    expect(groups).toHaveLength(0);
  });

  test("returns empty array when no duplicates exist", () => {
    const t1 = makeTxn({ id: "t1", date: "2024-01-01", amount: -10 });
    const t2 = makeTxn({ id: "t2", date: "2024-02-01", amount: -20 });
    const t3 = makeTxn({ id: "t3", date: "2024-03-01", amount: -30 });
    expect(groupByDateAndAmount([t1, t2, t3])).toHaveLength(0);
  });

  test("returns empty array for empty input", () => {
    expect(groupByDateAndAmount([])).toHaveLength(0);
  });

  test("treats amounts with same absolute value as duplicates", () => {
    // Both -42.5 — same absolute amount, same date
    const t1 = makeTxn({ id: "t1", date: "2024-03-15", amount: -42.5 });
    const t2 = makeTxn({ id: "t2", date: "2024-03-15", amount: -42.5 });
    const groups = groupByDateAndAmount([t1, t2]);
    expect(groups).toHaveLength(1);
  });

  test("groups three-way duplicates into a single group", () => {
    const t1 = makeTxn({ id: "t1", date: "2024-06-01", amount: -5.0 });
    const t2 = makeTxn({ id: "t2", date: "2024-06-01", amount: -5.0 });
    const t3 = makeTxn({ id: "t3", date: "2024-06-01", amount: -5.0 });
    const groups = groupByDateAndAmount([t1, t2, t3]);
    expect(groups).toHaveLength(1);
    expect(groups[0]).toHaveLength(3);
  });
});

// ── empty state ───────────────────────────────────────────────────────────────

describe("empty state — no duplicates", () => {
  test("buildDuplicateGroups returns empty for zero matches", () => {
    const groups = buildDuplicateGroups([]);
    expect(groups).toHaveLength(0);
  });

  test("allGroupsHavePrimary is vacuously true for empty groups", () => {
    // Merge button should not block when there's nothing to merge
    expect(allGroupsHavePrimary([], {})).toBe(true);
  });
});
