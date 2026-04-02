/**
 * Tests for beginner clarity improvements (AE–AH).
 *
 * AE — FinancialPlanPage: Health Score has tooltip + visible word label; page has subtitle
 * AF — FinancialPlanPage: success_rate badge has tooltip explaining what it means
 * AG — SmartInsightsPage: subtitle clarifies what "Recommendations" covers
 * AH — CashFlowForecastPage: subtitle rewritten from jargon to plain question; empty state updated
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

const planSrc = readSrc("pages/FinancialPlanPage.tsx");
const insightsSrc = readSrc("pages/SmartInsightsPage.tsx");
const forecastSrc = readSrc("pages/CashFlowForecastPage.tsx");

// ── AE: FinancialPlanPage Health Score tooltip + page subtitle ────────────────

describe("FinancialPlanPage Health Score clarity (AE)", () => {
  it("page has a subtitle explaining what the dashboard covers", () => {
    expect(planSrc).toMatch(/retirement.*debt.*savings|snapshot.*financial health/i);
  });

  it("Health Score has a Tooltip wrapping it", () => {
    // The Tooltip wraps the CircularProgress block; find the comment marker
    const commentIdx = planSrc.indexOf("{/* Health Score */}");
    expect(commentIdx).toBeGreaterThan(-1);
    const after = planSrc.slice(commentIdx, commentIdx + 200);
    expect(after).toMatch(/Tooltip/);
  });

  it("Health Score tooltip explains what contributes to the score", () => {
    expect(planSrc).toMatch(/retirement readiness|emergency fund|debt levels/i);
  });

  it("Health Score tooltip explains what the number means (70+ solid)", () => {
    expect(planSrc).toMatch(/70.*solid|solid.*70/i);
  });

  it("visible word label below Health Score (Solid / Needs work / At risk)", () => {
    expect(planSrc).toMatch(/Solid.*out of 100|Needs work.*out of 100|At risk.*out of 100/i);
  });
});

// ── AF: FinancialPlanPage success_rate tooltip ────────────────────────────────

describe("FinancialPlanPage retirement success rate tooltip (AF)", () => {
  it("success rate badge is wrapped in a Tooltip", () => {
    const srIdx = planSrc.indexOf("success rate");
    expect(srIdx).toBeGreaterThan(-1);
    const before = planSrc.slice(Math.max(0, srIdx - 300), srIdx);
    expect(before).toMatch(/Tooltip/);
  });

  it("success rate tooltip explains money lasting through retirement", () => {
    expect(planSrc).toMatch(/money lasts.*retirement|lasts through retirement/i);
  });

  it("success rate tooltip gives a target (80%+)", () => {
    expect(planSrc).toMatch(/80%.*solid|80\+.*solid/i);
  });
});

// ── AG: SmartInsightsPage subtitle clarity ────────────────────────────────────

describe("SmartInsightsPage subtitle clarifies scope (AG)", () => {
  it("subtitle does not use bare 'Personalized Recommendations' without context", () => {
    expect(insightsSrc).not.toMatch(/Personalized Recommendations based on your live account data — no\s+manual input required/);
  });

  it("subtitle mentions what areas are covered (spending, savings, taxes, retirement)", () => {
    expect(insightsSrc).toMatch(/spending.*savings|taxes.*retirement|savings.*taxes/i);
  });

  it("subtitle explains insights appear automatically from account data", () => {
    expect(insightsSrc).toMatch(/generated from.*account|actual account data|as your data grows/i);
  });
});

// ── AH: CashFlowForecastPage subtitle + empty state ──────────────────────────

describe("CashFlowForecastPage plain-English subtitle and empty state (AH)", () => {
  it("subtitle asks a plain question a beginner would relate to", () => {
    expect(forecastSrc).toMatch(/run low on cash|enough money|low on cash/i);
  });

  it("subtitle mentions 30, 60, 90 day projection horizon", () => {
    expect(forecastSrc).toMatch(/30.*60.*90|next.*30.*days/i);
  });

  it("empty state heading does not say 'No recurring transactions found'", () => {
    expect(forecastSrc).not.toMatch(/No recurring transactions found/);
  });

  it("empty state heading uses plain language about bills or income", () => {
    expect(forecastSrc).toMatch(/No bills or income set up|bills.*income/i);
  });

  it("empty state explains the app will project balance automatically", () => {
    expect(forecastSrc).toMatch(/project.*balance.*automatically|automatically.*project/i);
  });
});
