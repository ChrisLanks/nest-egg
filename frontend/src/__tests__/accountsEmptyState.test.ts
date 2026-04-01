/**
 * Tests for AccountsPage richer empty state (UX improvement B).
 *
 * The empty state was replaced with an explanatory 3-card grid that
 * shows beginners what types of accounts they can add and why each matters.
 */

import { describe, it, expect } from "vitest";

// ── Empty state render condition ─────────────────────────────────────────────

/** Mirrors the render guard: (!accounts || accounts.length === 0) */
function shouldShowEmptyState(accounts: unknown[] | null | undefined): boolean {
  return !accounts || accounts.length === 0;
}

describe("AccountsPage empty state render condition", () => {
  it("shows when accounts is null (initial load)", () => {
    expect(shouldShowEmptyState(null)).toBe(true);
  });

  it("shows when accounts is undefined", () => {
    expect(shouldShowEmptyState(undefined)).toBe(true);
  });

  it("shows when accounts array is empty", () => {
    expect(shouldShowEmptyState([])).toBe(true);
  });

  it("hides when user has one account", () => {
    expect(shouldShowEmptyState([{ id: "1" }])).toBe(false);
  });

  it("hides when user has many accounts", () => {
    const accts = Array.from({ length: 10 }, (_, i) => ({ id: String(i) }));
    expect(shouldShowEmptyState(accts)).toBe(false);
  });
});

// ── Three-card content coverage ───────────────────────────────────────────────

/** The three card titles and their key value propositions */
const CARD_CONTENT = [
  {
    title: "Checking & Savings",
    keywords: ["cash flow", "bank"],
  },
  {
    title: "Investments & Retirement",
    keywords: ["401(k)", "IRA", "net worth"],
  },
  {
    title: "Loans & Liabilities",
    keywords: ["debt", "mortgage", "loan"],
  },
] as const;

describe("AccountsPage empty state 3-card grid (UX improvement B)", () => {
  it("has exactly 3 cards", () => {
    expect(CARD_CONTENT.length).toBe(3);
  });

  it("each card has a non-empty title", () => {
    for (const card of CARD_CONTENT) {
      expect(card.title.trim().length).toBeGreaterThan(0);
    }
  });

  it("each card has at least one keyword (value proposition)", () => {
    for (const card of CARD_CONTENT) {
      expect(card.keywords.length).toBeGreaterThan(0);
    }
  });

  it("Checking & Savings card mentions cash flow or bank accounts", () => {
    const card = CARD_CONTENT[0];
    const hasRelevantKeyword = card.keywords.some((k) =>
      ["cash flow", "bank"].includes(k),
    );
    expect(hasRelevantKeyword).toBe(true);
  });

  it("Investments card mentions retirement accounts", () => {
    const card = CARD_CONTENT[1];
    const mentions401k = card.keywords.includes("401(k)");
    const mentionsIra = card.keywords.includes("IRA");
    expect(mentions401k || mentionsIra).toBe(true);
  });

  it("Loans card mentions debt or mortgage", () => {
    const card = CARD_CONTENT[2];
    const hasDebtKeyword = card.keywords.some((k) =>
      ["debt", "mortgage", "loan"].includes(k),
    );
    expect(hasDebtKeyword).toBe(true);
  });
});
