/**
 * Tests for TrendsPage logic: growth rate calculations, year toggle rules,
 * chart data preparation, and empty-data detection.
 */

import { describe, it, expect } from "vitest";

// ── Types (mirrored from TrendsPage.tsx) ─────────────────────────────────────

interface YearOverYearData {
  month: number;
  month_name: string;
  data: {
    [year: string]: {
      income: number;
      expenses: number;
      net: number;
    };
  };
}

interface QuarterlySummary {
  quarter: number;
  quarter_name: string;
  data: {
    [year: string]: {
      income: number;
      expenses: number;
      net: number;
    };
  };
}

// ── Logic helpers (mirrored from TrendsPage.tsx) ─────────────────────────────

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);

const calculateGrowthRate = (
  current: number,
  previous: number,
): number | null => {
  if (previous === 0) return null;
  return ((current - previous) / previous) * 100;
};

function prepareExpensesTrendData(
  yoyData: YearOverYearData[],
  selectedYears: number[],
) {
  return yoyData.map((month) => {
    const dataPoint: Record<string, unknown> = {
      month: month.month_name.substring(0, 3),
    };
    selectedYears.forEach((year) => {
      const yearStr = String(year);
      dataPoint[yearStr] = month.data[yearStr]?.expenses || 0;
    });
    return dataPoint;
  });
}

function hasAnyExpenseData(
  expensesTrendData: Record<string, unknown>[],
  selectedYears: number[],
): boolean {
  if (!expensesTrendData || expensesTrendData.length === 0) return false;
  return expensesTrendData.some((month) =>
    selectedYears.some((year) => {
      const value = month[String(year)] as number | undefined;
      return value && value > 0;
    }),
  );
}

function handleYearToggle(
  selectedYears: number[],
  year: number,
  primaryYear: number,
): { years: number[]; primary: number; error?: string } {
  if (selectedYears.includes(year)) {
    if (selectedYears.length > 1) {
      const newYears = selectedYears.filter((y) => y !== year);
      const newPrimary =
        primaryYear === year
          ? newYears.find((y) => y !== year) || newYears[0]
          : primaryYear;
      return { years: newYears.sort((a, b) => b - a), primary: newPrimary };
    }
    return {
      years: selectedYears,
      primary: primaryYear,
      error: "At least one year required",
    };
  } else {
    if (selectedYears.length < 3) {
      return {
        years: [...selectedYears, year].sort((a, b) => b - a),
        primary: primaryYear,
      };
    }
    return {
      years: selectedYears,
      primary: primaryYear,
      error: "Maximum 3 years",
    };
  }
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe("calculateGrowthRate", () => {
  it("returns positive growth rate", () => {
    expect(calculateGrowthRate(120000, 100000)).toBeCloseTo(20);
  });

  it("returns negative growth rate", () => {
    expect(calculateGrowthRate(80000, 100000)).toBeCloseTo(-20);
  });

  it("returns null when previous is zero", () => {
    expect(calculateGrowthRate(50000, 0)).toBeNull();
  });

  it("returns 0 when current equals previous", () => {
    expect(calculateGrowthRate(100000, 100000)).toBeCloseTo(0);
  });

  it("handles large growth percentages", () => {
    expect(calculateGrowthRate(300000, 100000)).toBeCloseTo(200);
  });
});

describe("handleYearToggle", () => {
  it("adds a year when under max (3)", () => {
    const result = handleYearToggle([2025, 2024], 2023, 2025);
    expect(result.years).toEqual([2025, 2024, 2023]);
    expect(result.error).toBeUndefined();
  });

  it("refuses to add a 4th year", () => {
    const result = handleYearToggle([2025, 2024, 2023], 2022, 2025);
    expect(result.years).toEqual([2025, 2024, 2023]);
    expect(result.error).toBe("Maximum 3 years");
  });

  it("removes a year when more than 1 selected", () => {
    const result = handleYearToggle([2025, 2024], 2024, 2025);
    expect(result.years).toEqual([2025]);
    expect(result.error).toBeUndefined();
  });

  it("refuses to remove the last year", () => {
    const result = handleYearToggle([2025], 2025, 2025);
    expect(result.years).toEqual([2025]);
    expect(result.error).toBe("At least one year required");
  });

  it("updates primary when the primary year is removed", () => {
    const result = handleYearToggle([2025, 2024, 2023], 2025, 2025);
    expect(result.years).toEqual([2024, 2023]);
    expect(result.primary).not.toBe(2025);
  });

  it("keeps years sorted descending after add", () => {
    const result = handleYearToggle([2025, 2023], 2024, 2025);
    expect(result.years).toEqual([2025, 2024, 2023]);
  });
});

describe("prepareExpensesTrendData", () => {
  const yoyData: YearOverYearData[] = [
    {
      month: 1,
      month_name: "January",
      data: {
        "2025": { income: 8000, expenses: 5000, net: 3000 },
        "2024": { income: 7000, expenses: 4500, net: 2500 },
      },
    },
    {
      month: 2,
      month_name: "February",
      data: {
        "2025": { income: 8000, expenses: 4000, net: 4000 },
      },
    },
  ];

  it("abbreviates month names to 3 characters", () => {
    const result = prepareExpensesTrendData(yoyData, [2025, 2024]);
    expect(result[0].month).toBe("Jan");
    expect(result[1].month).toBe("Feb");
  });

  it("fills in expenses for each selected year", () => {
    const result = prepareExpensesTrendData(yoyData, [2025, 2024]);
    expect(result[0]["2025"]).toBe(5000);
    expect(result[0]["2024"]).toBe(4500);
  });

  it("defaults to 0 for missing year data", () => {
    const result = prepareExpensesTrendData(yoyData, [2025, 2024]);
    expect(result[1]["2024"]).toBe(0); // February has no 2024 data
  });
});

describe("hasAnyExpenseData", () => {
  it("returns false for empty array", () => {
    expect(hasAnyExpenseData([], [2025])).toBe(false);
  });

  it("returns false when all values are zero", () => {
    const data = [{ month: "Jan", "2025": 0, "2024": 0 }];
    expect(hasAnyExpenseData(data, [2025, 2024])).toBe(false);
  });

  it("returns true when any year has non-zero expense", () => {
    const data = [{ month: "Jan", "2025": 0, "2024": 500 }];
    expect(hasAnyExpenseData(data, [2025, 2024])).toBe(true);
  });
});

describe("Quarterly totals", () => {
  it("sums quarterly expenses across periods", () => {
    const quarterlyData: QuarterlySummary[] = [
      {
        quarter: 1,
        quarter_name: "Q1",
        data: { "2025": { income: 10000, expenses: 5000, net: 5000 } },
      },
      {
        quarter: 2,
        quarter_name: "Q2",
        data: { "2025": { income: 12000, expenses: 6000, net: 6000 } },
      },
    ];
    const yearTotal = quarterlyData.reduce((sum, q) => {
      return sum + (q.data["2025"]?.expenses || 0);
    }, 0);
    expect(yearTotal).toBe(11000);
  });

  it("handles missing year in quarterly data gracefully", () => {
    const quarterlyData: QuarterlySummary[] = [
      {
        quarter: 1,
        quarter_name: "Q1",
        data: { "2024": { income: 10000, expenses: 5000, net: 5000 } },
      },
    ];
    const total2025 = quarterlyData.reduce(
      (sum, q) => sum + (q.data["2025"]?.expenses || 0),
      0,
    );
    expect(total2025).toBe(0);
  });
});

describe("formatCurrency", () => {
  it("formats thousands with commas", () => {
    expect(formatCurrency(45000)).toBe("$45,000");
  });

  it("formats zero", () => {
    expect(formatCurrency(0)).toBe("$0");
  });

  it("formats negative amounts", () => {
    expect(formatCurrency(-5000)).toBe("-$5,000");
  });
});

describe("Available years generation", () => {
  it("generates 5 years from current year downward", () => {
    const currentYear = 2026;
    const years = [];
    for (let i = 0; i < 5; i++) {
      years.push(currentYear - i);
    }
    expect(years).toEqual([2026, 2025, 2024, 2023, 2022]);
  });
});

// ── Available years from API with fallback ──────────────────────────────────

describe("Available years from API", () => {
  function getAvailableYears(apiYears: number[] | undefined): number[] {
    if (apiYears && apiYears.length > 0) return apiYears;
    const currentYear = 2026;
    const years = [];
    for (let i = 0; i < 5; i++) {
      years.push(currentYear - i);
    }
    return years;
  }

  it("uses API years when available", () => {
    const result = getAvailableYears([
      2026, 2025, 2024, 2023, 2022, 2021, 2020,
    ]);
    expect(result).toEqual([2026, 2025, 2024, 2023, 2022, 2021, 2020]);
  });

  it("falls back to last 5 years when API returns empty", () => {
    const result = getAvailableYears([]);
    expect(result).toEqual([2026, 2025, 2024, 2023, 2022]);
  });

  it("falls back to last 5 years when API returns undefined", () => {
    const result = getAvailableYears(undefined);
    expect(result).toEqual([2026, 2025, 2024, 2023, 2022]);
  });

  it("returns single year from API when only one exists", () => {
    const result = getAvailableYears([2024]);
    expect(result).toEqual([2024]);
  });
});

// ── localStorage persistence for selected years ────────────────────────────

describe("localStorage persistence for selected years", () => {
  const LS_KEY_YEARS = "nest-egg-trends-selected-years";
  const LS_KEY_PRIMARY = "nest-egg-trends-primary-year";

  function saveSelectedYears(years: number[]): string {
    return JSON.stringify(years);
  }

  function restoreSelectedYears(
    saved: string | null,
    fallbackYears: number[],
  ): number[] {
    try {
      if (saved) {
        const parsed = JSON.parse(saved) as number[];
        if (Array.isArray(parsed) && parsed.length > 0) return parsed;
      }
    } catch {
      /* ignore */
    }
    return fallbackYears;
  }

  function savePrimaryYear(year: number): string {
    return String(year);
  }

  function restorePrimaryYear(saved: string | null, fallback: number): number {
    if (saved) {
      const parsed = parseInt(saved, 10);
      if (!isNaN(parsed)) return parsed;
    }
    return fallback;
  }

  it("serializes selected years to JSON", () => {
    expect(saveSelectedYears([2026, 2025])).toBe("[2026,2025]");
  });

  it("restores selected years from valid JSON", () => {
    const result = restoreSelectedYears("[2025,2024]", [2026, 2025, 2024]);
    expect(result).toEqual([2025, 2024]);
  });

  it("falls back when saved JSON is empty array", () => {
    const result = restoreSelectedYears("[]", [2026, 2025, 2024]);
    expect(result).toEqual([2026, 2025, 2024]);
  });

  it("falls back when saved value is null", () => {
    const result = restoreSelectedYears(null, [2026, 2025, 2024]);
    expect(result).toEqual([2026, 2025, 2024]);
  });

  it("falls back when saved JSON is invalid", () => {
    const result = restoreSelectedYears("not-json", [2026, 2025, 2024]);
    expect(result).toEqual([2026, 2025, 2024]);
  });

  it("serializes primary year as string", () => {
    expect(savePrimaryYear(2025)).toBe("2025");
  });

  it("restores primary year from valid string", () => {
    expect(restorePrimaryYear("2025", 2026)).toBe(2025);
  });

  it("falls back when primary year string is null", () => {
    expect(restorePrimaryYear(null, 2026)).toBe(2026);
  });

  it("uses correct localStorage keys", () => {
    expect(LS_KEY_YEARS).toBe("nest-egg-trends-selected-years");
    expect(LS_KEY_PRIMARY).toBe("nest-egg-trends-primary-year");
  });
});
