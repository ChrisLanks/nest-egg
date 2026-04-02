/**
 * Tests that pages show a compact subtitle in advanced mode and a verbose
 * beginner subtitle in simple mode.
 *
 * Each affected page gates its subtitle on:
 *   localStorage.getItem("nest-egg-show-advanced-nav") === "true"
 *
 * Tests read source files directly — no DOM rendering needed.
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

const budgetsSrc = readSrc("pages/BudgetsPage.tsx");
const recurringSrc = readSrc("pages/RecurringTransactionsPage.tsx");
const catSrc = readSrc("pages/CategoriesPage.tsx");
const invSrc = readSrc("pages/InvestmentsPage.tsx");
const nwtSrc = readSrc("pages/NetWorthTimelinePage.tsx");
const forecastSrc = readSrc("pages/CashFlowForecastPage.tsx");

// Helper: assert a file has both a short advanced subtitle and a long beginner one
function assertDualSubtitle(src: string, advancedSnippet: string | RegExp, beginnerSnippet: string | RegExp, label: string) {
  const advRe = typeof advancedSnippet === "string" ? new RegExp(advancedSnippet.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")) : advancedSnippet;
  const begRe = typeof beginnerSnippet === "string" ? new RegExp(beginnerSnippet.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")) : beginnerSnippet;
  expect(src, `${label}: advanced subtitle missing`).toMatch(advRe);
  expect(src, `${label}: beginner subtitle missing`).toMatch(begRe);
  expect(src, `${label}: not gated on advanced nav flag`).toMatch(/nest-egg-show-advanced-nav/);
}

describe("Advanced mode compact subtitles", () => {
  it("BudgetsPage shows compact subtitle in advanced mode", () => {
    assertDualSubtitle(
      budgetsSrc,
      "Spending limits by category.",
      /reset each period|rollover/i,
      "BudgetsPage"
    );
  });

  it("RecurringTransactionsPage drops Netflix/rent examples in advanced mode", () => {
    assertDualSubtitle(
      recurringSrc,
      /Recurring charges and subscriptions detected/i,
      /Netflix.*rent|rent.*utilities/i,
      "RecurringTransactionsPage"
    );
  });

  it("CategoriesPage shows compact subtitle in advanced mode", () => {
    assertDualSubtitle(
      catSrc,
      /Organize transactions by category and sub-category/i,
      /e\.g\. Food|Groceries.*Rent/i,
      "CategoriesPage"
    );
  });

  it("InvestmentsPage drops 'hidden annual fees' framing in advanced mode", () => {
    assertDualSubtitle(
      invSrc,
      /Portfolio overview.*allocation.*expense ratios/i,
      /hidden annual fees/i,
      "InvestmentsPage"
    );
  });

  it("NetWorthTimelinePage drops the Assets−Liabilities definition in advanced mode", () => {
    assertDualSubtitle(
      nwtSrc,
      /Historical and forecast breakdown of assets, liabilities/i,
      /what you own.*what you owe/i,
      "NetWorthTimelinePage"
    );
  });

  it("CashFlowForecastPage drops 'Will you run low on cash?' in advanced mode", () => {
    assertDualSubtitle(
      forecastSrc,
      /30\/60\/90-day projected account balance/i,
      /Will you run low on cash/i,
      "CashFlowForecastPage"
    );
  });
});
