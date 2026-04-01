/**
 * Tests for beginner jargon and empty-state fixes (P, Q, R).
 *
 * P — TransactionsPage: 'Pending' badge tooltip + smarter empty state
 * Q — BudgetCard: 'Rollover' tooltip + dollar overage label
 * R — SmartInsightsPage: 'All clear!' rewording + category pill tooltips
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

const txSrc = readSrc("pages/TransactionsPage.tsx");
const budgetCardSrc = readSrc("features/budgets/components/BudgetCard.tsx");
const insightsSrc = readSrc("pages/SmartInsightsPage.tsx");

// ── P: TransactionsPage ───────────────────────────────────────────────────────

describe("TransactionsPage beginner fixes (P)", () => {
  it("wraps the Pending badge in a Tooltip", () => {
    const pendingIdx = txSrc.indexOf("is_pending");
    expect(pendingIdx).toBeGreaterThan(-1);
    const context = txSrc.slice(pendingIdx, pendingIdx + 400);
    expect(context).toMatch(/Tooltip/);
  });

  it("Pending tooltip explains bank clearing in plain language", () => {
    expect(txSrc).toMatch(/initiated but not yet.*processed|awaiting.*bank|not yet.*bank/i);
  });

  it("Pending tooltip mentions that pending transactions may be adjusted or cancelled", () => {
    expect(txSrc).toMatch(/adjusted or cancelled|cancelled|may still change/i);
  });

  it("empty state distinguishes 'no accounts' from 'filters returned nothing'", () => {
    expect(txSrc).toMatch(/accounts\.length === 0/);
  });

  it("empty state shows filter-specific message when accounts exist but no results", () => {
    expect(txSrc).toMatch(/expand.*date|expanding.*date|current filters|date range/i);
  });

  it("empty state only shows 'Go to Accounts' CTA when there are no accounts", () => {
    // The action should be gated on accounts.length === 0
    const actionIdx = txSrc.indexOf("Go to Accounts");
    expect(actionIdx).toBeGreaterThan(-1);
    const context = txSrc.slice(Math.max(0, actionIdx - 200), actionIdx + 50);
    expect(context).toMatch(/accounts\.length === 0/);
  });
});

// ── Q: BudgetCard beginner fixes ──────────────────────────────────────────────

describe("BudgetCard beginner fixes (Q)", () => {
  it("shows dollar overage amount, not just 'Over budget'", () => {
    expect(budgetCardSrc).toMatch(/Over budget by/);
  });

  it("uses formatCurrency for the overage amount", () => {
    const overIdx = budgetCardSrc.indexOf("Over budget by");
    expect(overIdx).toBeGreaterThan(-1);
    const context = budgetCardSrc.slice(overIdx, overIdx + 100);
    expect(context).toMatch(/formatCurrency/);
  });

  it("wraps the rollover line in a Tooltip", () => {
    const rolloverIdx = budgetCardSrc.indexOf("rollover from last period");
    expect(rolloverIdx).toBeGreaterThan(-1);
    const context = budgetCardSrc.slice(Math.max(0, rolloverIdx - 300), rolloverIdx + 50);
    expect(context).toMatch(/Tooltip/);
  });

  it("rollover tooltip explains what rollover means in plain language", () => {
    expect(budgetCardSrc).toMatch(/unused budget.*carried forward|carried forward.*unused/i);
  });

  it("rollover tooltip explains the effect (increases available budget)", () => {
    expect(budgetCardSrc).toMatch(/increases.*available|available.*budget.*this period/i);
  });
});

// ── R: SmartInsightsPage beginner fixes ──────────────────────────────────────

describe("SmartInsightsPage beginner fixes (R)", () => {
  it("does not use the old ambiguous 'All clear!' as a standalone heading", () => {
    // Old text: fontWeight="semibold">All clear! — replaced with a clearer message
    expect(insightsSrc).not.toMatch(/semibold">All clear!</);
  });

  it("has an empty state that explains when insights appear", () => {
    expect(insightsSrc).toMatch(/insights appear.*when|when.*insights appear|detects.*opportunit/i);
  });

  it("empty state mentions concrete examples of what triggers an insight", () => {
    expect(insightsSrc).toMatch(/high.?fee|savings gap|tax move|tax.*move/i);
  });

  it("has a categoryTooltip map for each category", () => {
    expect(insightsSrc).toMatch(/categoryTooltip/);
    expect(insightsSrc).toMatch(/cash:.*".*savings|cash:.*liquid/i);
    expect(insightsSrc).toMatch(/investing:.*".*fee|investing:.*portfolio/i);
    expect(insightsSrc).toMatch(/tax:.*".*tax|tax:.*deduct/i);
    expect(insightsSrc).toMatch(/retirement:.*".*retirement/i);
  });

  it("category pills are wrapped in Tooltips using categoryTooltip", () => {
    // The Tooltip wraps the Badge — look for both within a reasonable window
    // pill-${cat} is inside the Badge; categoryTooltip[cat] is on the outer Tooltip
    const pillIdx = insightsSrc.indexOf("pill-${cat}");
    expect(pillIdx).toBeGreaterThan(-1);
    // Search within ±500 chars of the pill test id
    const context = insightsSrc.slice(Math.max(0, pillIdx - 500), pillIdx + 100);
    expect(context).toMatch(/categoryTooltip\[cat\]/);
  });

  it("category pill tooltips have an openDelay for non-intrusive UX", () => {
    expect(insightsSrc).toMatch(/openDelay.*400|400.*openDelay/);
  });
});
