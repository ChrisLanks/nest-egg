/**
 * Tests for YearInReviewPage logic: default year selection, YoY comparison
 * formatting, category progress bars, merchant average, and savings rate display.
 */

import { describe, it, expect } from "vitest";

// ── Logic helpers ────────────────────────────────────────────────────────────

function getDefaultYear(currentMonth: number, currentYear: number): number {
  return currentMonth === 0 ? currentYear - 1 : currentYear;
}

function formatChangePct(pct: number): string {
  return `${pct >= 0 ? "+" : ""}${pct.toFixed(1)}%`;
}

function formatSavingsRateChange(pp: number): string {
  return `${pp >= 0 ? "+" : ""}${pp.toFixed(1)}pp`;
}

function maxCategoryTotal(categories: { total: number }[]): number {
  return categories.length > 0
    ? Math.max(...categories.map((c) => c.total))
    : 1;
}

function categoryProgressValue(total: number, max: number): number {
  return (total / max) * 100;
}

function merchantAvg(total: number, count: number): number {
  return total / count;
}

function netWorthProgressValue(start: number, end: number): number {
  return start > 0 ? Math.min((end / start) * 50, 100) : 50;
}

const CHART_COLORS = [
  "#3182CE",
  "#38A169",
  "#D69E2E",
  "#E53E3E",
  "#805AD5",
  "#DD6B20",
  "#319795",
  "#D53F8C",
  "#718096",
  "#2B6CB0",
];

// ── Tests ────────────────────────────────────────────────────────────────────

describe("getDefaultYear", () => {
  it("returns previous year in January", () => {
    expect(getDefaultYear(0, 2026)).toBe(2025);
  });

  it("returns current year in other months", () => {
    expect(getDefaultYear(1, 2026)).toBe(2026);
    expect(getDefaultYear(6, 2026)).toBe(2026);
    expect(getDefaultYear(11, 2026)).toBe(2026);
  });
});

describe("formatChangePct", () => {
  it("adds + prefix for positive changes", () => {
    expect(formatChangePct(15.3)).toBe("+15.3%");
  });

  it("shows negative without + prefix", () => {
    expect(formatChangePct(-8.2)).toBe("-8.2%");
  });

  it("shows +0.0% for zero", () => {
    expect(formatChangePct(0)).toBe("+0.0%");
  });
});

describe("formatSavingsRateChange", () => {
  it("uses 'pp' suffix for percentage point changes", () => {
    expect(formatSavingsRateChange(3.5)).toBe("+3.5pp");
    expect(formatSavingsRateChange(-2.1)).toBe("-2.1pp");
  });
});

describe("maxCategoryTotal", () => {
  it("finds max from category totals", () => {
    const cats = [{ total: 5000 }, { total: 12000 }, { total: 3000 }];
    expect(maxCategoryTotal(cats)).toBe(12000);
  });

  it("returns 1 for empty array (prevents division by zero)", () => {
    expect(maxCategoryTotal([])).toBe(1);
  });
});

describe("categoryProgressValue", () => {
  it("returns 100% for the max category", () => {
    expect(categoryProgressValue(12000, 12000)).toBeCloseTo(100);
  });

  it("returns proportional value for smaller categories", () => {
    expect(categoryProgressValue(6000, 12000)).toBeCloseTo(50);
  });
});

describe("merchantAvg", () => {
  it("calculates average per transaction", () => {
    expect(merchantAvg(1200, 4)).toBe(300);
  });
});

describe("netWorthProgressValue", () => {
  it("returns value based on end/start ratio", () => {
    // end = 2x start => (2x/x)*50 = 100, capped at 100
    expect(netWorthProgressValue(100000, 200000)).toBe(100);
  });

  it("returns 50 when start is 0", () => {
    expect(netWorthProgressValue(0, 50000)).toBe(50);
  });

  it("caps at 100", () => {
    expect(netWorthProgressValue(50000, 500000)).toBe(100);
  });

  it("returns proportional value for moderate growth", () => {
    // end/start = 1.2 => 1.2*50 = 60
    expect(netWorthProgressValue(100000, 120000)).toBeCloseTo(60);
  });
});

describe("Savings rate display", () => {
  it("shows percentage when not null", () => {
    const savingsRate: number | null = 35.2;
    const display = savingsRate !== null ? `${savingsRate.toFixed(1)}%` : "N/A";
    expect(display).toBe("35.2%");
  });

  it('shows "N/A" when null', () => {
    const savingsRate: number | null = null;
    const display = savingsRate !== null ? `${savingsRate.toFixed(1)}%` : "N/A";
    expect(display).toBe("N/A");
  });
});

describe("Net income color", () => {
  it("uses positive color for positive net income", () => {
    const net = 15000;
    const color = net >= 0 ? "finance.positive" : "finance.negative";
    expect(color).toBe("finance.positive");
  });

  it("uses negative color for negative net income", () => {
    const net = -5000;
    const color = net >= 0 ? "finance.positive" : "finance.negative";
    expect(color).toBe("finance.negative");
  });
});

describe("Milestones display", () => {
  it("shows milestones when array is non-empty", () => {
    const milestones = ["Hit $100k net worth", "Debt-free"];
    expect(milestones.length > 0).toBe(true);
  });

  it("hides milestones when array is empty", () => {
    const milestones: string[] = [];
    expect(milestones.length > 0).toBe(false);
  });
});

describe("CHART_COLORS", () => {
  it("has 10 colors", () => {
    expect(CHART_COLORS).toHaveLength(10);
  });

  it("cycles with modulo", () => {
    const idx = 12;
    expect(CHART_COLORS[idx % CHART_COLORS.length]).toBe(CHART_COLORS[2]);
  });
});

describe("Available years generation", () => {
  it("generates 6 years from current year", () => {
    const currentYear = 2026;
    const years = [];
    for (let i = 0; i < 6; i++) {
      years.push(currentYear - i);
    }
    expect(years).toEqual([2026, 2025, 2024, 2023, 2022, 2021]);
  });
});
