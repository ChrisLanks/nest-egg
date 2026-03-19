/**
 * Tests for NetWorthTimelinePage logic:
 * - getDateRange date calculations for all time range buttons
 * - chartData mapping (asset layers, debt negation, summary fields)
 * - stat card calculations (netWorthChange, netWorthChangePct)
 */

import { describe, it, expect } from "vitest";

// ── Types (mirrored from NetWorthTimelinePage.tsx) ───────────────────────────

type TimeRange = "1M" | "3M" | "6M" | "1Y" | "2Y" | "ALL" | "CUSTOM";

interface NetWorthPoint {
  snapshot_date: string;
  total_net_worth: number;
  total_assets: number;
  total_liabilities: number;
  cash_and_checking: number;
  savings: number;
  investments: number;
  retirement: number;
  property: number;
  vehicles: number;
  other_assets: number;
  credit_cards: number;
  loans: number;
  mortgages: number;
  student_loans: number;
  other_debts: number;
}

// ── Logic helpers (mirrored from NetWorthTimelinePage.tsx) ───────────────────

function getDateRange(
  range: TimeRange,
  customStart: string,
  customEnd: string,
  now: Date,
): { start: Date; end: Date | null } {
  let start: Date;
  let end: Date | null = null;

  switch (range) {
    case "1M":
      start = new Date(now.getFullYear(), now.getMonth() - 1, now.getDate());
      break;
    case "3M":
      start = new Date(now.getFullYear(), now.getMonth() - 3, now.getDate());
      break;
    case "6M":
      start = new Date(now.getFullYear(), now.getMonth() - 6, now.getDate());
      break;
    case "1Y":
      start = new Date(now.getFullYear() - 1, now.getMonth(), now.getDate());
      break;
    case "2Y":
      start = new Date(now.getFullYear() - 2, now.getMonth(), now.getDate());
      break;
    case "ALL":
      start = new Date(now.getFullYear() - 20, 0, 1);
      break;
    case "CUSTOM":
      start = customStart
        ? new Date(customStart)
        : new Date(now.getFullYear() - 1, now.getMonth(), now.getDate());
      if (customEnd) end = new Date(customEnd);
      break;
    default:
      start = new Date(now.getFullYear() - 1, now.getMonth(), now.getDate());
  }
  return { start, end };
}

const ASSET_LAYERS = [
  "cash_and_checking",
  "savings",
  "investments",
  "retirement",
  "property",
  "vehicles",
  "other_assets",
] as const;

const DEBT_LAYERS = [
  "mortgages",
  "credit_cards",
  "loans",
  "student_loans",
  "other_debts",
] as const;

function buildChartData(data: NetWorthPoint[]) {
  return data.map((pt) => ({
    date: new Date(pt.snapshot_date + "T00:00:00").toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    }),
    ...Object.fromEntries(
      ASSET_LAYERS.map((key) => [
        key,
        pt[key as keyof NetWorthPoint] as number,
      ]),
    ),
    ...Object.fromEntries(
      DEBT_LAYERS.map((key) => [
        key,
        -Math.abs(pt[key as keyof NetWorthPoint] as number),
      ]),
    ),
    total_net_worth: pt.total_net_worth,
    total_assets: pt.total_assets,
    total_liabilities: pt.total_liabilities,
  }));
}

// ── Reference date ───────────────────────────────────────────────────────────
const NOW = new Date(2025, 2, 15); // March 15, 2025 (month is 0-indexed)

// ── Sample data ──────────────────────────────────────────────────────────────
const SAMPLE_POINT: NetWorthPoint = {
  snapshot_date: "2025-03-15",
  total_net_worth: 120_000,
  total_assets: 150_000,
  total_liabilities: 30_000,
  cash_and_checking: 10_000,
  savings: 20_000,
  investments: 50_000,
  retirement: 60_000,
  property: 5_000,
  vehicles: 5_000,
  other_assets: 0,
  credit_cards: 2_000,
  loans: 3_000,
  mortgages: 20_000,
  student_loans: 5_000,
  other_debts: 0,
};

// ===========================================================================
// getDateRange
// ===========================================================================

describe("getDateRange", () => {
  it("1M goes back one month", () => {
    const { start, end } = getDateRange("1M", "", "", NOW);
    expect(start.getFullYear()).toBe(2025);
    expect(start.getMonth()).toBe(1); // February
    expect(start.getDate()).toBe(15);
    expect(end).toBeNull();
  });

  it("3M goes back three months", () => {
    const { start } = getDateRange("3M", "", "", NOW);
    expect(start.getMonth()).toBe(11); // December (wraps to prev year)
    expect(start.getFullYear()).toBe(2024);
  });

  it("6M goes back six months", () => {
    const { start } = getDateRange("6M", "", "", NOW);
    expect(start.getMonth()).toBe(8); // September
    expect(start.getFullYear()).toBe(2024);
  });

  it("1Y goes back one year", () => {
    const { start } = getDateRange("1Y", "", "", NOW);
    expect(start.getFullYear()).toBe(2024);
    expect(start.getMonth()).toBe(2); // March
    expect(start.getDate()).toBe(15);
  });

  it("2Y goes back two years", () => {
    const { start } = getDateRange("2Y", "", "", NOW);
    expect(start.getFullYear()).toBe(2023);
  });

  it("ALL goes back 20 years to Jan 1", () => {
    const { start } = getDateRange("ALL", "", "", NOW);
    expect(start.getFullYear()).toBe(2005);
    expect(start.getMonth()).toBe(0); // January
    expect(start.getDate()).toBe(1);
  });

  it("CUSTOM with start and end sets both", () => {
    const { start, end } = getDateRange(
      "CUSTOM",
      "2024-06-15",
      "2024-12-15",
      NOW,
    );
    // Compare UTC ISO string prefix to avoid timezone offset issues with Date.parse
    expect(start.toISOString().startsWith("2024-06")).toBe(true);
    expect(end).not.toBeNull();
    expect(end!.toISOString().startsWith("2024-12")).toBe(true);
  });

  it("CUSTOM with start only sets end to null", () => {
    const { start, end } = getDateRange("CUSTOM", "2024-06-15", "", NOW);
    expect(start.toISOString().startsWith("2024-06")).toBe(true);
    expect(end).toBeNull();
  });

  it("CUSTOM with empty start falls back to 1Y ago", () => {
    const { start } = getDateRange("CUSTOM", "", "", NOW);
    expect(start.getFullYear()).toBe(2024);
    expect(start.getMonth()).toBe(2); // March
  });
});

// ===========================================================================
// buildChartData
// ===========================================================================

describe("buildChartData", () => {
  it("maps asset layers as positive values", () => {
    const [pt] = buildChartData([SAMPLE_POINT]);
    expect(pt.cash_and_checking).toBe(10_000);
    expect(pt.savings).toBe(20_000);
    expect(pt.investments).toBe(50_000);
    expect(pt.retirement).toBe(60_000);
  });

  it("maps debt layers as negative values", () => {
    const [pt] = buildChartData([SAMPLE_POINT]);
    expect(pt.mortgages).toBe(-20_000);
    expect(pt.credit_cards).toBe(-2_000);
    expect(pt.loans).toBe(-3_000);
    expect(pt.student_loans).toBe(-5_000);
    expect(pt.other_debts).toBe(-0); // 0 stays 0
  });

  it("preserves total_net_worth and total_assets/liabilities", () => {
    const [pt] = buildChartData([SAMPLE_POINT]);
    expect(pt.total_net_worth).toBe(120_000);
    expect(pt.total_assets).toBe(150_000);
    expect(pt.total_liabilities).toBe(30_000);
  });

  it("formats date as short month + day", () => {
    const [pt] = buildChartData([SAMPLE_POINT]);
    // "Mar 15" (locale-dependent but consistent in test environment)
    expect(pt.date).toMatch(/Mar/);
    expect(pt.date).toMatch(/15/);
  });

  it("handles empty array", () => {
    expect(buildChartData([])).toHaveLength(0);
  });

  it("handles multiple points in order", () => {
    const second: NetWorthPoint = {
      ...SAMPLE_POINT,
      snapshot_date: "2025-03-16",
      total_net_worth: 121_000,
    };
    const result = buildChartData([SAMPLE_POINT, second]);
    expect(result).toHaveLength(2);
    expect(result[1].total_net_worth).toBe(121_000);
  });

  it("negates already-negative debt values correctly (abs)", () => {
    // If the API returned debt as negative, abs ensures we store as negative
    const withNegDebt: NetWorthPoint = {
      ...SAMPLE_POINT,
      mortgages: -20_000, // already negative from API
    };
    const [pt] = buildChartData([withNegDebt]);
    expect(pt.mortgages).toBe(-20_000); // -abs(-20000) = -20000
  });
});

// ===========================================================================
// Stat card calculations
// ===========================================================================

describe("stat card change calculations", () => {
  const earliest: NetWorthPoint = {
    ...SAMPLE_POINT,
    snapshot_date: "2024-03-15",
    total_net_worth: 100_000,
  };
  const latest: NetWorthPoint = {
    ...SAMPLE_POINT,
    snapshot_date: "2025-03-15",
    total_net_worth: 120_000,
  };

  it("calculates absolute net worth change", () => {
    const change = latest.total_net_worth - earliest.total_net_worth;
    expect(change).toBe(20_000);
  });

  it("calculates percentage net worth change", () => {
    const change = latest.total_net_worth - earliest.total_net_worth;
    const pct = (change / Math.abs(earliest.total_net_worth)) * 100;
    expect(pct).toBe(20);
  });

  it("handles zero earliest net worth (no division by zero)", () => {
    const zeroEarliest = { ...earliest, total_net_worth: 0 };
    const pct =
      zeroEarliest.total_net_worth !== 0
        ? ((latest.total_net_worth - zeroEarliest.total_net_worth) /
            Math.abs(zeroEarliest.total_net_worth)) *
          100
        : null;
    expect(pct).toBeNull();
  });

  it("change is negative when net worth decreased", () => {
    const lowerLatest = { ...latest, total_net_worth: 90_000 };
    const change = lowerLatest.total_net_worth - earliest.total_net_worth;
    expect(change).toBe(-10_000);
  });

  it("returns null change when data is empty", () => {
    const data: NetWorthPoint[] = [];
    const latestPt = data[data.length - 1];
    const earliestPt = data[0];
    const change =
      latestPt && earliestPt
        ? latestPt.total_net_worth - earliestPt.total_net_worth
        : null;
    expect(change).toBeNull();
  });

  it("returns zero change for single data point", () => {
    const data = [SAMPLE_POINT];
    const latestPt = data[data.length - 1];
    const earliestPt = data[0];
    const change =
      latestPt && earliestPt
        ? latestPt.total_net_worth - earliestPt.total_net_worth
        : null;
    expect(change).toBe(0);
  });
});
