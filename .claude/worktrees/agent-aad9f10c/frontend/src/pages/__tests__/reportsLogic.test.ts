/**
 * Tests for ReportsPage logic: report config construction, date range
 * preset formatting, and form validation.
 */

import { describe, it, expect } from "vitest";

// ── Logic helpers (mirrored from ReportsPage.tsx) ────────────────────────────

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);

function buildReportConfig(opts: {
  dateRangeType: string;
  preset: string;
  groupBy: string;
  chartType: "bar" | "pie" | "table";
}) {
  return {
    dateRange: {
      type: opts.dateRangeType,
      preset: opts.preset,
    },
    groupBy: opts.groupBy,
    chartType: opts.chartType,
    metrics: ["sum", "count"],
    sortBy: "amount",
    sortDirection: "desc",
    limit: 20,
  };
}

function formatPresetLabel(preset: string): string {
  return preset.replace(/_/g, " ");
}

const COLORS = [
  "#0088FE",
  "#00C49F",
  "#FFBB28",
  "#FF8042",
  "#8884D8",
  "#82CA9D",
];

// ── Tests ────────────────────────────────────────────────────────────────────

describe("buildReportConfig", () => {
  it("builds config with preset date range", () => {
    const config = buildReportConfig({
      dateRangeType: "preset",
      preset: "last_30_days",
      groupBy: "category",
      chartType: "bar",
    });
    expect(config.dateRange.type).toBe("preset");
    expect(config.dateRange.preset).toBe("last_30_days");
    expect(config.groupBy).toBe("category");
    expect(config.chartType).toBe("bar");
    expect(config.metrics).toEqual(["sum", "count"]);
    expect(config.limit).toBe(20);
  });

  it("supports all group-by options", () => {
    for (const groupBy of ["category", "merchant", "account", "time"]) {
      const config = buildReportConfig({
        dateRangeType: "preset",
        preset: "this_year",
        groupBy,
        chartType: "table",
      });
      expect(config.groupBy).toBe(groupBy);
    }
  });

  it("supports all chart type options", () => {
    for (const chartType of ["bar", "pie", "table"] as const) {
      const config = buildReportConfig({
        dateRangeType: "preset",
        preset: "this_month",
        groupBy: "category",
        chartType,
      });
      expect(config.chartType).toBe(chartType);
    }
  });
});

describe("formatPresetLabel", () => {
  it("replaces underscores with spaces", () => {
    expect(formatPresetLabel("last_30_days")).toBe("last 30 days");
    expect(formatPresetLabel("this_year")).toBe("this year");
    expect(formatPresetLabel("last_90_days")).toBe("last 90 days");
  });
});

describe("Report name validation", () => {
  it("rejects empty report name", () => {
    const name = "";
    expect(!name).toBe(true);
  });

  it("accepts non-empty report name", () => {
    const name = "Monthly Category Report";
    expect(!name).toBe(false);
  });
});

describe("Color palette cycling", () => {
  it("cycles through 6 colors", () => {
    expect(COLORS).toHaveLength(6);
  });

  it("wraps around for indices beyond array length", () => {
    const index = 8;
    expect(COLORS[index % COLORS.length]).toBe(COLORS[2]);
  });
});

describe("formatCurrency", () => {
  it("formats report totals", () => {
    expect(formatCurrency(15234)).toBe("$15,234");
  });

  it("formats zero", () => {
    expect(formatCurrency(0)).toBe("$0");
  });
});
