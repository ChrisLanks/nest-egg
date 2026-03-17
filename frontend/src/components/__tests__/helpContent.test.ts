/**
 * Tests for helpContent — validates completeness and consistency of all hint text.
 */

import { describe, it, expect } from "vitest";
import { helpContent } from "../../constants/helpContent";

// Flatten all values from the nested helpContent object
function getAllHints(
  obj: Record<string, Record<string, string>>,
): { page: string; key: string; value: string }[] {
  const hints: { page: string; key: string; value: string }[] = [];
  for (const [page, section] of Object.entries(obj)) {
    for (const [key, value] of Object.entries(section)) {
      hints.push({ page, key, value: value as string });
    }
  }
  return hints;
}

describe("helpContent", () => {
  const allHints = getAllHints(
    helpContent as unknown as Record<string, Record<string, string>>,
  );

  it("has all expected page sections", () => {
    const pages = Object.keys(helpContent);
    expect(pages).toContain("fire");
    expect(pages).toContain("retirement");
    expect(pages).toContain("investments");
    expect(pages).toContain("debtPayoff");
    expect(pages).toContain("budgets");
    expect(pages).toContain("incomeExpenses");
    expect(pages).toContain("netWorth");
    expect(pages).toContain("savingsGoals");
  });

  it("has FIRE metrics hints", () => {
    expect(helpContent.fire.fiRatio).toBeDefined();
    expect(helpContent.fire.coastFi).toBeDefined();
    expect(helpContent.fire.savingsRate).toBeDefined();
    expect(helpContent.fire.withdrawalRate).toBeDefined();
    expect(helpContent.fire.yearsToFi).toBeDefined();
  });

  it("has retirement hints", () => {
    expect(helpContent.retirement.monteCarlo).toBeDefined();
    expect(helpContent.retirement.withdrawalStrategy).toBeDefined();
    expect(helpContent.retirement.readinessScore).toBeDefined();
    expect(helpContent.retirement.socialSecurityAge).toBeDefined();
    expect(helpContent.retirement.lifeEvents).toBeDefined();
  });

  it("has investment hints", () => {
    expect(helpContent.investments.taxLossHarvesting).toBeDefined();
    expect(helpContent.investments.rothConversion).toBeDefined();
    expect(helpContent.investments.fundOverlap).toBeDefined();
    expect(helpContent.investments.rmd).toBeDefined();
    expect(helpContent.investments.feeAnalysis).toBeDefined();
    expect(helpContent.investments.assetAllocation).toBeDefined();
  });

  it("every hint is a non-empty string", () => {
    for (const { page, key, value } of allHints) {
      expect(value, `${page}.${key} should be a non-empty string`).toBeTruthy();
      expect(typeof value).toBe("string");
      expect(value.length).toBeGreaterThan(10);
    }
  });

  it("no duplicate hint text across the entire object", () => {
    const seen = new Map<string, string>();
    for (const { page, key, value } of allHints) {
      const fullKey = `${page}.${key}`;
      const existing = seen.get(value);
      expect(
        existing,
        `Duplicate hint text between ${existing} and ${fullKey}`,
      ).toBeUndefined();
      seen.set(value, fullKey);
    }
  });

  it("hints are concise (under 300 characters)", () => {
    for (const { page, key, value } of allHints) {
      expect(
        value.length,
        `${page}.${key} is ${value.length} chars — too long for a tooltip`,
      ).toBeLessThanOrEqual(300);
    }
  });
});
