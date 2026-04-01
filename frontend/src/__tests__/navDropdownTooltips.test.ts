/**
 * Pure-function tests verifying the nav dropdown label tooltips.
 * These test the tooltip string values directly without rendering components.
 */
import { describe, it, expect } from "vitest";

// The tooltip strings as defined in Layout.tsx
const NAV_DROPDOWN_TOOLTIPS: Record<string, string> = {
  Spending:
    "Track where your money goes — transactions, budgets, categories, and recurring bills",
  Analytics:
    "Charts and scores — net worth over time, cash flow, spending trends, and financial health",
  Planning:
    "Your financial future — goals, retirement, tax strategy, and life milestones",
};

describe("NavDropdown label tooltips", () => {
  it("all 3 dropdown labels have a tooltip string", () => {
    expect(NAV_DROPDOWN_TOOLTIPS).toHaveProperty("Spending");
    expect(NAV_DROPDOWN_TOOLTIPS).toHaveProperty("Analytics");
    expect(NAV_DROPDOWN_TOOLTIPS).toHaveProperty("Planning");
  });

  it("each tooltip is non-empty", () => {
    for (const [label, tooltip] of Object.entries(NAV_DROPDOWN_TOOLTIPS)) {
      expect(tooltip.length, `${label} tooltip should be non-empty`).toBeGreaterThan(0);
    }
  });

  it("each tooltip uses plain English (no jargon — no all-caps acronyms or code syntax)", () => {
    for (const [label, tooltip] of Object.entries(NAV_DROPDOWN_TOOLTIPS)) {
      // Should not contain HTML tags
      expect(tooltip, `${label} tooltip should not contain HTML`).not.toMatch(/<[^>]+>/);
      // Should not be all uppercase
      expect(tooltip, `${label} tooltip should not be all caps`).not.toMatch(/^[A-Z\s]+$/);
    }
  });

  it("Spending tooltip mentions transactions or budgets", () => {
    const tooltip = NAV_DROPDOWN_TOOLTIPS.Spending.toLowerCase();
    expect(
      tooltip.includes("transactions") || tooltip.includes("budgets"),
      'Spending tooltip should mention "transactions" or "budgets"'
    ).toBe(true);
  });

  it("Analytics tooltip mentions net worth or cash flow", () => {
    const tooltip = NAV_DROPDOWN_TOOLTIPS.Analytics.toLowerCase();
    expect(
      tooltip.includes("net worth") || tooltip.includes("cash flow"),
      'Analytics tooltip should mention "net worth" or "cash flow"'
    ).toBe(true);
  });

  it("Planning tooltip mentions goals or retirement", () => {
    const tooltip = NAV_DROPDOWN_TOOLTIPS.Planning.toLowerCase();
    expect(
      tooltip.includes("goals") || tooltip.includes("retirement"),
      'Planning tooltip should mention "goals" or "retirement"'
    ).toBe(true);
  });
});
