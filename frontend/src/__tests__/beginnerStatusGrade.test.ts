/**
 * Tests for beginner clarity improvements (AA, AB, AC).
 *
 * AA — FinancialRatiosTab: grade letter shows a visible word label (Excellent/Good/Fair/…)
 * AB — BudgetsPage: subtitle explains budget reset and rollover behavior
 * AC — TransactionsPage: Pending tooltip explains the lifecycle (what happens when it clears)
 *
 * Tests read source files directly (no DOM rendering needed).
 */

import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const srcRoot = join(__dirname, "..");

function readSrc(rel: string): string {
  return readFileSync(join(srcRoot, rel), "utf-8");
}

const ratiosSrc = readSrc("pages/FinancialRatiosTab.tsx");
const budgetsSrc = readSrc("pages/BudgetsPage.tsx");
const txnSrc = readSrc("pages/TransactionsPage.tsx");

// ── AA: FinancialRatiosTab grade label ────────────────────────────────────────

describe("FinancialRatiosTab visible grade label (AA)", () => {
  it("renders a plain-English label next to the grade letter", () => {
    // Should have Excellent, Good, Fair, Needs work, At risk as inline text
    expect(ratiosSrc).toMatch(/Excellent/);
    expect(ratiosSrc).toMatch(/Needs work/i);
    expect(ratiosSrc).toMatch(/At risk/i);
  });

  it("maps each grade letter to a plain-English word", () => {
    // The ternary chain should cover A → Excellent, B → Good, C → Fair, D → Needs work, F → At risk
    expect(ratiosSrc).toMatch(/overall_grade.*===.*"A".*Excellent/s);
    expect(ratiosSrc).toMatch(/overall_grade.*===.*"B".*Good/s);
    expect(ratiosSrc).toMatch(/overall_grade.*===.*"C".*Fair/s);
  });

  it("label is inside the same Tooltip as the grade letter (always visible)", () => {
    // VStack wrapping both the grade Text and the label Text inside Tooltip
    const tooltipIdx = ratiosSrc.lastIndexOf("A = 90");
    const after = ratiosSrc.slice(tooltipIdx, tooltipIdx + 800);
    expect(after).toMatch(/VStack/);
    expect(after).toMatch(/Excellent|Good|Fair/);
  });

  it("tooltip still shows the full A–F numeric scale", () => {
    expect(ratiosSrc).toMatch(/A = 90.*100.*excellent/i);
    expect(ratiosSrc).toMatch(/F.*below 60.*at risk/i);
  });
});

// ── AB: BudgetsPage rollover/reset explanation ────────────────────────────────

describe("BudgetsPage subtitle explains budget reset and rollover (AB)", () => {
  it("subtitle mentions budgets reset each period", () => {
    expect(budgetsSrc).toMatch(/reset each period|reset.*monthly|budgets reset/i);
  });

  it("subtitle explains unused amounts don't carry over by default", () => {
    expect(budgetsSrc).toMatch(/unused|don't carry over|carry over unless/i);
  });

  it("subtitle mentions rollover as an option", () => {
    expect(budgetsSrc).toMatch(/rollover/i);
  });

  it("subtitle still mentions spending limits and alerts", () => {
    expect(budgetsSrc).toMatch(/spending.*limit|limit.*spending/i);
  });
});

// ── AC: TransactionsPage Pending tooltip explains lifecycle ───────────────────

describe("TransactionsPage Pending tooltip explains the full lifecycle (AC)", () => {
  it("Pending tooltip mentions the transaction is not yet fully processed", () => {
    expect(txnSrc).toMatch(/not yet fully processed/i);
  });

  it("Pending tooltip explains pending transactions may be adjusted or cancelled", () => {
    expect(txnSrc).toMatch(/may still be adjusted or cancelled/i);
  });

  it("Pending tooltip explains what happens when it clears (disappears)", () => {
    expect(txnSrc).toMatch(/disappears|confirmed.*disappear|clears/i);
  });
});
