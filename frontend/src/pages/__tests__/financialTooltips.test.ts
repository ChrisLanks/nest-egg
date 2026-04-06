/**
 * Tests verifying that key financial pages have tooltips on complex terms.
 */

import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { join } from "path";

const PAGES_DIR = join(__dirname, "..");

function readPage(filename: string): string {
  return readFileSync(join(PAGES_DIR, filename), "utf-8");
}

describe("financial tooltip coverage", () => {
  it("InvestmentsPage should have tooltips on key metrics", () => {
    const content = readPage("InvestmentsPage.tsx");
    // Should have Tooltip import
    expect(content).toContain("Tooltip");
    // Key terms that need tooltips
    expect(content).toContain("Total Gain/Loss");
    expect(content).toContain("Annual Fees");
  });

  it("RetirementHubPage should have tooltips on tab labels", () => {
    const content = readPage("RetirementHubPage.tsx");
    expect(content).toContain("Tooltip");
    // Tab-level tooltips for non-obvious features
    expect(content).toContain("RMD");
    expect(content).toContain("Social Security");
  });

  it("DebtPayoffPage should have tooltips on amortization terms", () => {
    const content = readPage("DebtPayoffPage.tsx");
    expect(content).toContain("Tooltip");
    expect(content).toContain("Amortization");
    expect(content).toContain("Principal");
  });

  it("CashFlowPage should have tooltips on projection metrics", () => {
    const content = readPage("CashFlowPage.tsx");
    // Should import Chakra Tooltip (not just Recharts Tooltip)
    expect(content).toMatch(/Tooltip.*chakra|ChakraTooltip|from.*chakra.*Tooltip/i);
  });

  it("TaxBucketsPage should already have tooltips via InfoTip", () => {
    const content = readPage("TaxBucketsPage.tsx");
    // Uses InfoTip pattern for comprehensive tooltips
    expect(content).toMatch(/InfoTip|Tooltip/);
  });

  it("FireMetricsPage should already have tooltips on stats", () => {
    const content = readPage("FireMetricsPage.tsx");
    expect(content).toMatch(/Tooltip|HelpHint/);
  });

  it("BondLadderPage should already have tooltips via InfoTip", () => {
    const content = readPage("BondLadderPage.tsx");
    expect(content).toMatch(/InfoTip|Tooltip/);
  });
});
