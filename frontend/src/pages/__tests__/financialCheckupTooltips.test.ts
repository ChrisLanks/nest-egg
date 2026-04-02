/**
 * Tests for PM audit item 5 — Financial Checkup: tooltips on every field.
 *
 * Covers:
 * - CreditScoreTab: stat tooltips (Latest Score, Change, Entries Tracked)
 * - CreditScoreTab: form field tooltips (Score, Date Pulled, Bureau/Source, Notes)
 * - CreditScoreTab: Chakra Tooltip imported (recharts aliased as RechartsTooltip)
 * - FinancialRatiosTab: tooltips on Monthly Income, Monthly Spending, and context stats
 * - LiquidityDashboardTab: tooltips on Monthly Spending, key stats
 */

import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { resolve } from "path";

const CREDIT_SCORE = resolve(__dirname, "../../pages/CreditScoreTab.tsx");
const RATIOS = resolve(__dirname, "../../pages/FinancialRatiosTab.tsx");
const LIQUIDITY = resolve(__dirname, "../../pages/LiquidityDashboardTab.tsx");

const creditSrc = readFileSync(CREDIT_SCORE, "utf-8");
const ratiosSrc = readFileSync(RATIOS, "utf-8");
const liquiditySrc = readFileSync(LIQUIDITY, "utf-8");

// ---------------------------------------------------------------------------
// CreditScoreTab — imports
// ---------------------------------------------------------------------------

it("CreditScoreTab imports Tooltip from @chakra-ui/react", () => {
  expect(creditSrc).toContain("Tooltip,");
  expect(creditSrc).toContain("@chakra-ui/react");
});

it("CreditScoreTab aliases recharts Tooltip as RechartsTooltip", () => {
  expect(creditSrc).toContain("Tooltip as RechartsTooltip");
});

it("CreditScoreTab uses RechartsTooltip inside the LineChart", () => {
  expect(creditSrc).toContain("<RechartsTooltip");
});

// ---------------------------------------------------------------------------
// CreditScoreTab — stat tooltips
// ---------------------------------------------------------------------------

it("CreditScoreTab has tooltip on Latest Score stat", () => {
  expect(creditSrc).toContain("Your most recently recorded credit score");
});

it("CreditScoreTab has tooltip on Change stat", () => {
  expect(creditSrc).toContain("How many points your score moved since the previous entry");
});

it("CreditScoreTab has tooltip on Entries Tracked stat", () => {
  expect(creditSrc).toContain("Total number of score records you have entered");
});

// ---------------------------------------------------------------------------
// CreditScoreTab — form field tooltips
// ---------------------------------------------------------------------------

it("CreditScoreTab has tooltip on Score form field", () => {
  expect(creditSrc).toContain("FICO scores range from 300");
});

it("CreditScoreTab has tooltip on Date Pulled form field", () => {
  expect(creditSrc).toContain("The date the score was pulled");
});

it("CreditScoreTab has tooltip on Bureau/Source form field", () => {
  expect(creditSrc).toContain("Equifax, Experian, and TransUnion each maintain separate");
});

it("CreditScoreTab has tooltip on Notes form field", () => {
  expect(creditSrc).toContain("Optional context");
});

// ---------------------------------------------------------------------------
// FinancialRatiosTab — tooltips on inputs and stats
// ---------------------------------------------------------------------------

it("FinancialRatiosTab has tooltip on Monthly Income input", () => {
  expect(ratiosSrc).toContain("total gross monthly income");
});

it("FinancialRatiosTab has tooltip on Monthly Spending input", () => {
  expect(ratiosSrc).toContain("monthly essential and discretionary spending");
});

it("FinancialRatiosTab has tooltip on Net Worth stat", () => {
  expect(ratiosSrc).toContain("Total assets minus total liabilities");
});

it("FinancialRatiosTab has tooltip on Liquid Assets stat", () => {
  expect(ratiosSrc).toContain("Cash, savings, and money-market balances");
});

it("FinancialRatiosTab has tooltip on Total Debt stat", () => {
  expect(ratiosSrc).toContain("Sum of all outstanding loan balances");
});

// ---------------------------------------------------------------------------
// LiquidityDashboardTab — tooltips
// ---------------------------------------------------------------------------

it("LiquidityDashboardTab has tooltip on Monthly Spending input", () => {
  expect(liquiditySrc).toContain("average monthly essential spending");
});

it("LiquidityDashboardTab has tooltip on Immediately Accessible stat", () => {
  expect(liquiditySrc).toContain("Cash in checking, savings, and money market");
});

it("LiquidityDashboardTab has tooltip on Total Liquid stat", () => {
  expect(liquiditySrc).toContain("All liquid assets including brokerage");
});

it("LiquidityDashboardTab has tooltip on Coverage Gap/Surplus stat", () => {
  expect(liquiditySrc).toContain("Amount needed to reach your");
});
