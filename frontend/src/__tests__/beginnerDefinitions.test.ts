/**
 * Tests for beginner definition tooltips (S, T, U).
 *
 * S — NetWorthTimelinePage: tooltips on Net Worth, Total Assets, Total Liabilities
 * T — FinancialRatiosTab: score scale tooltip + specific income/spending entry prompt
 * U — DebtPayoffPage: plain-English strategy recommendation badge labels
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

const nwSrc = readSrc("pages/NetWorthTimelinePage.tsx");
const ratiosSrc = readSrc("pages/FinancialRatiosTab.tsx");
const debtSrc = readSrc("pages/DebtPayoffPage.tsx");

// ── S: NetWorthTimelinePage stat card tooltips ────────────────────────────────

describe("NetWorthTimelinePage stat card tooltips (S)", () => {
  it("Net Worth stat card is wrapped in a Tooltip", () => {
    // Tooltip opens before the label — search the whole stat card block
    expect(nwSrc).toMatch(/Tooltip[^>]*>[\s\S]{0,400}Net Worth/);
  });

  it("Net Worth tooltip explains it as assets minus liabilities", () => {
    expect(nwSrc).toMatch(/everything you own minus everything you owe|assets.*minus.*liabilities/i);
  });

  it("Total Assets stat card is wrapped in a Tooltip", () => {
    expect(nwSrc).toMatch(/Tooltip[^>]*>[\s\S]{0,400}Total Assets/);
  });

  it("Total Assets tooltip explains what assets are in plain language", () => {
    expect(nwSrc).toMatch(/bank accounts.*investments|investments.*real estate/i);
  });

  it("Total Liabilities stat card is wrapped in a Tooltip", () => {
    expect(nwSrc).toMatch(/Tooltip[^>]*>[\s\S]{0,400}Total Liabilities/);
  });

  it("Total Liabilities tooltip explains what liabilities are in plain language", () => {
    expect(nwSrc).toMatch(/everything you owe|credit card.*loans.*mortgages/i);
  });

  it("Liabilities tooltip explains the direct link to net worth", () => {
    expect(nwSrc).toMatch(/reduces.*net worth|increases.*net worth|directly increases/i);
  });
});

// ── T: FinancialRatiosTab score scale + entry prompt ─────────────────────────

describe("FinancialRatiosTab score scale and entry prompt (T)", () => {
  it("overall grade letter has a tooltip with the A–F scale", () => {
    const gradeIdx = ratiosSrc.indexOf("overall_grade}");
    expect(gradeIdx).toBeGreaterThan(-1);
    const context = ratiosSrc.slice(Math.max(0, gradeIdx - 300), gradeIdx + 50);
    expect(context).toMatch(/Tooltip/);
  });

  it("score scale tooltip explains what A means (90-100 or excellent)", () => {
    expect(ratiosSrc).toMatch(/A.*90|90.*100.*excellent|A.*excellent/i);
  });

  it("score scale tooltip explains what F means (below 60 or at risk)", () => {
    expect(ratiosSrc).toMatch(/F.*below 60|below 60.*F|at risk/i);
  });

  it("score scale tooltip says higher is better", () => {
    expect(ratiosSrc).toMatch(/higher is better/i);
  });

  it("income/spending entry prompt is specific when both are missing", () => {
    expect(ratiosSrc).toMatch(/savings rate.*debt-to-income|unlock.*savings rate/i);
  });

  it("income/spending prompt distinguishes missing income vs missing spending", () => {
    expect(ratiosSrc).toMatch(/income_provided/);
    expect(ratiosSrc).toMatch(/spending_provided/);
    // Should have at least 2 distinct messages
    expect(ratiosSrc).toMatch(/monthly income above/i);
    expect(ratiosSrc).toMatch(/monthly spending above/i);
  });
});

// ── U: DebtPayoffPage strategy badge labels ───────────────────────────────────

describe("DebtPayoffPage strategy recommendation badges (U)", () => {
  it("Snowball recommendation badge no longer says 'Best Psychology'", () => {
    expect(debtSrc).not.toMatch(/Best Psychology/);
  });

  it("Avalanche recommendation badge no longer says 'Best Savings'", () => {
    expect(debtSrc).not.toMatch(/Best Savings/);
  });

  it("Snowball badge explains motivation benefit in plain language", () => {
    expect(debtSrc).toMatch(/motivation|quick.*win|stick with/i);
  });

  it("Avalanche badge explains interest saving in plain language", () => {
    expect(debtSrc).toMatch(/saves.*interest|least interest|saving money/i);
  });

  it("both strategy badges are wrapped in Tooltips", () => {
    // Find the JSX recommendation === "SNOWBALL" (not the enum definition)
    const snowballIdx = debtSrc.indexOf('recommendation === "SNOWBALL"');
    const avalancheIdx = debtSrc.indexOf('recommendation === "AVALANCHE"');
    expect(snowballIdx).toBeGreaterThan(-1);
    expect(avalancheIdx).toBeGreaterThan(-1);
    const snow = debtSrc.slice(snowballIdx, snowballIdx + 400);
    const aval = debtSrc.slice(avalancheIdx, avalancheIdx + 400);
    expect(snow).toMatch(/Tooltip/);
    expect(aval).toMatch(/Tooltip/);
  });

  it("Tooltip is imported in DebtPayoffPage", () => {
    expect(debtSrc).toMatch(/Tooltip,/);
  });
});
