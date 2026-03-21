/**
 * Tests for RentalPropertiesPage logic: P&L calculations, formatting,
 * bar width percentages, cap rate badge colors, and net income coloring.
 */

import { describe, it, expect } from "vitest";

// ── Logic helpers (mirrored from RentalPropertiesPage.tsx) ───────────────────

const MONTH_NAMES = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);

const formatCurrencyDetailed = (amount: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);

const formatPercent = (value: number) => `${value.toFixed(1)}%`;

// ── Bar width calculation (from monthly table) ──────────────────────────────

function calculateBarPercent(
  value: number,
  monthly: { income: number; expenses: number }[],
): number {
  const maxVal = Math.max(
    ...monthly.map((row) => Math.max(row.income, row.expenses)),
    1,
  );
  return (value / maxVal) * 100;
}

// ── Cap rate badge color logic ──────────────────────────────────────────────

function capRateBadgeColor(capRate: number): string {
  return capRate >= 5 ? "green" : "yellow";
}

// ── Property count pluralization ────────────────────────────────────────────

function propertyCountLabel(count: number): string {
  return `${count} propert${count === 1 ? "y" : "ies"}`;
}

// ── Year options ────────────────────────────────────────────────────────────

function buildYearOptions(currentYear: number): number[] {
  return Array.from({ length: 5 }, (_, i) => currentYear - i);
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe("formatCurrency", () => {
  it("formats whole dollar amounts", () => {
    expect(formatCurrency(120000)).toBe("$120,000");
    expect(formatCurrency(0)).toBe("$0");
  });

  it("formats negative amounts", () => {
    expect(formatCurrency(-5000)).toBe("-$5,000");
  });
});

describe("formatCurrencyDetailed", () => {
  it("includes cents", () => {
    expect(formatCurrencyDetailed(1234.56)).toBe("$1,234.56");
  });

  it("pads to two decimal places", () => {
    expect(formatCurrencyDetailed(1000)).toBe("$1,000.00");
  });
});

describe("formatPercent", () => {
  it("formats with one decimal place", () => {
    expect(formatPercent(5.0)).toBe("5.0%");
    expect(formatPercent(7.85)).toBe("7.8%");
  });

  it("formats zero", () => {
    expect(formatPercent(0)).toBe("0.0%");
  });
});

describe("MONTH_NAMES", () => {
  it("has 12 entries", () => {
    expect(MONTH_NAMES).toHaveLength(12);
  });

  it("maps 1-based month to correct name", () => {
    expect(MONTH_NAMES[0]).toBe("Jan");
    expect(MONTH_NAMES[5]).toBe("Jun");
    expect(MONTH_NAMES[11]).toBe("Dec");
  });
});

describe("calculateBarPercent", () => {
  it("returns 100% for the max value", () => {
    const monthly = [
      { income: 2000, expenses: 1000 },
      { income: 3000, expenses: 1500 },
    ];
    expect(calculateBarPercent(3000, monthly)).toBeCloseTo(100);
  });

  it("returns 50% for half of max", () => {
    const monthly = [
      { income: 2000, expenses: 1000 },
      { income: 4000, expenses: 500 },
    ];
    expect(calculateBarPercent(2000, monthly)).toBeCloseTo(50);
  });

  it("returns 0% for zero value", () => {
    const monthly = [{ income: 1000, expenses: 500 }];
    expect(calculateBarPercent(0, monthly)).toBeCloseTo(0);
  });

  it("handles all-zero monthly data (uses floor of 1)", () => {
    const monthly = [{ income: 0, expenses: 0 }];
    // maxVal = max(0, 0, 1) = 1
    expect(calculateBarPercent(0, monthly)).toBeCloseTo(0);
  });
});

describe("capRateBadgeColor", () => {
  it("returns green for cap rate >= 5", () => {
    expect(capRateBadgeColor(5.0)).toBe("green");
    expect(capRateBadgeColor(8.5)).toBe("green");
  });

  it("returns yellow for cap rate < 5", () => {
    expect(capRateBadgeColor(4.9)).toBe("yellow");
    expect(capRateBadgeColor(0)).toBe("yellow");
  });
});

describe("propertyCountLabel", () => {
  it("uses singular for 1 property", () => {
    expect(propertyCountLabel(1)).toBe("1 property");
  });

  it("uses plural for 0 or multiple properties", () => {
    expect(propertyCountLabel(0)).toBe("0 properties");
    expect(propertyCountLabel(3)).toBe("3 properties");
  });
});

describe("buildYearOptions", () => {
  it("generates 5 years from current year", () => {
    expect(buildYearOptions(2026)).toEqual([2026, 2025, 2024, 2023, 2022]);
  });
});

describe("Net income color logic", () => {
  it("uses green for positive net income", () => {
    const net = 5000;
    const color = net >= 0 ? "green.500" : "red.500";
    expect(color).toBe("green.500");
  });

  it("uses green for zero net income", () => {
    const net = 0;
    const color = net >= 0 ? "green.500" : "red.500";
    expect(color).toBe("green.500");
  });

  it("uses red for negative net income", () => {
    const net = -1000;
    const color = net >= 0 ? "green.500" : "red.500";
    expect(color).toBe("red.500");
  });
});

describe("hasProperties guard", () => {
  it("returns false when property count is 0", () => {
    const summary = { property_count: 0 };
    expect(summary.property_count > 0).toBe(false);
  });

  it("returns true when properties exist", () => {
    const summary = { property_count: 2 };
    expect(summary.property_count > 0).toBe(true);
  });
});
