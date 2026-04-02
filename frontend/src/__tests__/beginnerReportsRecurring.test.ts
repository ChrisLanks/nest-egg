/**
 * Tests for beginner clarity improvements (Z).
 *
 * Z1 — ReportsPage: tab tooltips for Trends / Year in Review / Tax Deductible / Custom Reports
 * Z2 — ReportsPage: "Group By" has dynamic FormHelperText explaining each option
 * Z3 — RecurringTransactionsPage: plain-English subtitle; empty state replaces "patterns" jargon
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

const reportsSrc = readSrc("pages/ReportsPage.tsx");
const recurringSrc = readSrc("pages/RecurringTransactionsPage.tsx");

// ── Z1: ReportsPage tab tooltips ─────────────────────────────────────────────

describe("ReportsPage tab tooltips (Z1)", () => {
  it("Trends tab has a tooltip explaining what trends it shows", () => {
    const trendsIdx = reportsSrc.indexOf(">Trends<");
    expect(trendsIdx).toBeGreaterThan(-1);
    // There should be a Tooltip wrapping the Trends tab
    const before = reportsSrc.slice(Math.max(0, trendsIdx - 200), trendsIdx);
    expect(before).toMatch(/Tooltip/);
  });

  it("Trends tooltip mentions spending, income, or comparing over time", () => {
    expect(reportsSrc).toMatch(/spending.*income.*time|compare.*month|changed over time/i);
  });

  it("Year in Review tab has a tooltip", () => {
    const yirIdx = reportsSrc.indexOf(">Year in Review<");
    expect(yirIdx).toBeGreaterThan(-1);
    const before = reportsSrc.slice(Math.max(0, yirIdx - 200), yirIdx);
    expect(before).toMatch(/Tooltip/);
  });

  it("Year in Review tooltip mentions annual summary or calendar year", () => {
    expect(reportsSrc).toMatch(/full-year|calendar year|annual/i);
  });

  it("Tax Deductible tab has a tooltip", () => {
    const tdIdx = reportsSrc.indexOf(">Tax Deductible<");
    expect(tdIdx).toBeGreaterThan(-1);
    const before = reportsSrc.slice(Math.max(0, tdIdx - 200), tdIdx);
    expect(before).toMatch(/Tooltip/);
  });

  it("Custom Reports tab has a tooltip", () => {
    const crIdx = reportsSrc.indexOf(">Custom Reports<");
    expect(crIdx).toBeGreaterThan(-1);
    const before = reportsSrc.slice(Math.max(0, crIdx - 200), crIdx);
    expect(before).toMatch(/Tooltip/);
  });
});

// ── Z2: ReportsPage Group By helper text ─────────────────────────────────────

describe("ReportsPage Group By helper text (Z2)", () => {
  it("has a FormHelperText near Group By field", () => {
    // Use lastIndexOf — the table header also has ">Group By<"; we want the FormLabel
    const gbIdx = reportsSrc.lastIndexOf(">Group By<");
    expect(gbIdx).toBeGreaterThan(-1);
    const after = reportsSrc.slice(gbIdx, gbIdx + 800);
    expect(after).toMatch(/FormHelperText/);
  });

  it("explains category grouping in plain English", () => {
    expect(reportsSrc).toMatch(/spending category|Totals rolled up by/i);
  });

  it("explains merchant grouping", () => {
    expect(reportsSrc).toMatch(/store or payee|per.*merchant/i);
  });

  it("explains time period grouping", () => {
    expect(reportsSrc).toMatch(/week.*month.*year|spot trends/i);
  });
});

// ── Z3: RecurringTransactionsPage plain language ──────────────────────────────

describe("RecurringTransactionsPage plain-English subtitle and empty state (Z3)", () => {
  it("subtitle does not use 'Auto-detected patterns'", () => {
    expect(recurringSrc).not.toMatch(/Auto-detected patterns/);
  });

  it("subtitle mentions bills, subscriptions, and schedule", () => {
    expect(recurringSrc).toMatch(/subscription|bills.*schedule|schedule.*bills/i);
  });

  it("subtitle gives a concrete example (Netflix, rent, utilities)", () => {
    expect(recurringSrc).toMatch(/Netflix|rent|utilities/i);
  });

  it("empty state title does not say 'patterns detected'", () => {
    expect(recurringSrc).not.toMatch(/patterns detected/i);
  });

  it("empty state action button says Scan rather than Detect Patterns", () => {
    expect(recurringSrc).toMatch(/Scan for Recurring/i);
  });

  it("empty state description avoids bare 'patterns' and explains what scanning does", () => {
    expect(recurringSrc).toMatch(/scan.*transaction.*history|transaction.*history.*scan/i);
  });
});
