/**
 * Tests for PM audit round 67b:
 * - AccountsPage search normalization (401k matches 401(k), underscores match spaces)
 * - RothConversionPage assumed future rate input field
 * - Tax Projection married filing household income aggregation
 */

import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { resolve } from "path";

const ACCOUNTS_PAGE = resolve(
  __dirname,
  "../../pages/AccountsPage.tsx"
);
const ROTH_PAGE = resolve(
  __dirname,
  "../../pages/RothConversionPage.tsx"
);
const SMART_INSIGHTS_API = resolve(
  __dirname,
  "../../api/smartInsights.ts"
);

const accountsSrc = readFileSync(ACCOUNTS_PAGE, "utf-8");
const rothSrc = readFileSync(ROTH_PAGE, "utf-8");
const smartInsightsApiSrc = readFileSync(SMART_INSIGHTS_API, "utf-8");

// ---------------------------------------------------------------------------
// AccountsPage search normalization
// ---------------------------------------------------------------------------

it("AccountsPage strips parentheses from haystack for search normalization", () => {
  // The fix replaces ( ) _ - with spaces so "401k" matches "401(k)"
  expect(accountsSrc).toContain('replace(/[()_-]/g, " ")');
});

it("AccountsPage creates normalized haystack alongside raw", () => {
  expect(accountsSrc).toContain("normalized");
  expect(accountsSrc).toContain("haystack = raw + \" \" + normalized");
});

it("AccountsPage search still uses ACCOUNT_TYPE_LABELS in haystack", () => {
  expect(accountsSrc).toContain("ACCOUNT_TYPE_LABELS[a.account_type]");
});

it("AccountsPage search still includes raw account_type in haystack", () => {
  expect(accountsSrc).toContain("a.account_type");
});

// ---------------------------------------------------------------------------
// RothConversionPage assumed future rate
// ---------------------------------------------------------------------------

it("RothConversionPage has assumedFutureRate state", () => {
  expect(rothSrc).toContain("assumedFutureRate");
  expect(rothSrc).toContain("setAssumedFutureRate");
});

it("RothConversionPage computes futureRateNum from assumedFutureRate", () => {
  expect(rothSrc).toContain("futureRateNum");
  expect(rothSrc).toContain("/ 100");
});

it("RothConversionPage passes assumed_future_rate to API call", () => {
  expect(rothSrc).toContain("assumed_future_rate: futureRateNum");
});

it("RothConversionPage includes futureRateNum in queryKey", () => {
  expect(rothSrc).toContain("futureRateNum");
  // queryKey includes it
  const queryKeyMatch = rothSrc.match(/queryKey:\s*\[([\s\S]*?)\]/);
  expect(queryKeyMatch).not.toBeNull();
  if (queryKeyMatch) {
    expect(queryKeyMatch[0]).toContain("futureRateNum");
  }
});

it("RothConversionPage has Future Tax Rate input field", () => {
  expect(rothSrc).toContain("Future Tax Rate");
});

it("RothConversionPage has tooltip on future rate field", () => {
  expect(rothSrc).toContain("assumed future marginal tax rate");
});

// ---------------------------------------------------------------------------
// smartInsights.ts API type
// ---------------------------------------------------------------------------

it("RothConversionParams includes assumed_future_rate field", () => {
  expect(smartInsightsApiSrc).toContain("assumed_future_rate?: number");
});
