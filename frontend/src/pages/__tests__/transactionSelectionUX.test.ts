/**
 * Tests that the transaction selection UX shows the correct button:
 * - 1 selected → "Edit" button (opens detail modal)
 * - 2+ selected → "Bulk Edit" button (opens bulk modal)
 *
 * These are structural tests reading the TransactionsPage source.
 */

import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { resolve } from "path";

const ROOT = resolve(__dirname, "..", "..", "..");

function readSource(relPath: string): string {
  return readFileSync(resolve(ROOT, relPath), "utf-8");
}

describe("Transaction selection — Edit vs Bulk Edit button", () => {
  const source = readSource("src/pages/TransactionsPage.tsx");

  it("shows Edit button when exactly 1 transaction is selected", () => {
    expect(source).toContain("selectedTransactions.size === 1");
    // The Edit button should open the detail modal
    expect(source).toContain("setSelectedTransaction(txn)");
    expect(source).toContain("setIsModalOpen(true)");
  });

  it("shows Bulk Edit button when 2+ transactions are selected", () => {
    // The else branch (size > 1) shows Bulk Edit
    expect(source).toContain("onBulkEditOpen");
    expect(source).toContain("Bulk Edit");
  });

  it("Edit button finds the transaction from processedTransactions", () => {
    // Single-select Edit looks up the transaction by ID
    expect(source).toContain("processedTransactions.find((t) => t.id === txnId)");
  });

  it("single selection label says 'transaction' (singular)", () => {
    // Pluralization: "1 transaction" vs "3 transactions"
    expect(source).toContain('selectedTransactions.size > 1 ? "s" : ""');
  });

  it("both Edit and Bulk Edit buttons exist in the selection action bar", () => {
    // Both buttons are conditionally rendered inside the same selection UI
    // JSX may have line breaks, so check for the button text content
    expect(source).toMatch(/>\s*Edit\s*</);
    expect(source).toMatch(/>\s*Bulk Edit\s*</);
  });
});
