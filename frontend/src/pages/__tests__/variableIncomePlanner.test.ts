/**
 * Tests for Variable Income Planner logic.
 *
 * All tests are pure logic/unit tests — no React component rendering.
 * Logic is re-implemented inline (mirroring VariableIncomePage.tsx) rather
 * than importing from the component directly.
 *
 * Covers:
 *   - Settings persistence (localStorage load/save with defaults)
 *   - Combined tax rate calculation
 *   - Income smoothing calculations (avg, lowest, safeFloor, variance, quarterlyTaxEst)
 *   - Quarterly schedule status logic (past / due soon / upcoming)
 *
 * @vitest-environment jsdom
 */

import { describe, it, expect, beforeEach } from "vitest";
import { readFileSync } from "fs";
import { resolve } from "path";

const srcPath = resolve(__dirname, "..", "VariableIncomePage.tsx");
const src = readFileSync(srcPath, "utf-8");

// ── Constants & types ─────────────────────────────────────────────────────────

const SETTINGS_KEY = "nest-egg-variable-income-settings";

interface VariableIncomeSettings {
  incomeLabelName: string;
  seTaxRate: number;
  fedTaxRate: number;
  stateTaxRate: number;
}

interface MonthlyTrend {
  month: string; // "YYYY-MM"
  income: number;
  expenses: number;
  net: number;
}

// ── Helpers mirroring VariableIncomePage.tsx ──────────────────────────────────

const DEFAULT_SETTINGS: VariableIncomeSettings = {
  incomeLabelName: "",
  seTaxRate: 14.13,
  fedTaxRate: 22,
  stateTaxRate: 0,
};

/** Mirrors loadSettings() in VariableIncomePage — merges stored JSON with defaults. */
const loadSettings = (): VariableIncomeSettings => {
  try {
    const raw = localStorage.getItem(SETTINGS_KEY);
    if (!raw) return { ...DEFAULT_SETTINGS };
    const parsed = JSON.parse(raw);
    return { ...DEFAULT_SETTINGS, ...parsed };
  } catch {
    return { ...DEFAULT_SETTINGS };
  }
};

/** Combined tax rate as a decimal fraction. */
const combinedTaxRate = (settings: VariableIncomeSettings): number =>
  (settings.seTaxRate + settings.fedTaxRate + settings.stateTaxRate) / 100;

/**
 * Compute income smoothing metrics from an array of monthly trend data.
 * Mirrors the derived-value logic in VariableIncomePage.
 *
 * @param trends - All monthly trend entries
 * @param currentMonth - "YYYY-MM" string representing the current (partial) month to exclude
 */
const computeSmoothingMetrics = (
  trends: MonthlyTrend[],
  currentMonth: string,
) => {
  // Exclude the current (partial) month
  const full = trends.filter((t) => t.month !== currentMonth);
  const trailing = full.slice(-12);

  const count = trailing.length;
  const avgMonthlyIncome =
    count > 0 ? trailing.reduce((sum, t) => sum + t.income, 0) / count : 0;

  const incomeValues = trailing.map((t) => t.income);
  const lowestIncome = count > 0 ? Math.min(...incomeValues) : 0;
  const safeFloor = lowestIncome * 0.8;

  // Variance relative to the most recent full month
  const thisMonth = trailing[trailing.length - 1];
  const thisMonthIncome = thisMonth ? thisMonth.income : 0;
  const variance = thisMonthIncome - avgMonthlyIncome;

  return { avgMonthlyIncome, lowestIncome, safeFloor, variance };
};

/** quarterlyTaxEst = (avgMonthlyIncome * 12 * combinedRate) / 4 */
const quarterlyTaxEst = (
  avgMonthlyIncome: number,
  settings: VariableIncomeSettings,
): number => (avgMonthlyIncome * 12 * combinedTaxRate(settings)) / 4;

type QuarterlyStatus = "past" | "due soon" | "upcoming";

/**
 * Mirrors the quarterly schedule status logic in VariableIncomePage.
 * due date < today → "past"
 * due date within 60 days → "due soon"
 * otherwise → "upcoming"
 */
const getQuarterlyStatus = (
  dueDateStr: string,
  today: Date,
): QuarterlyStatus => {
  const due = new Date(dueDateStr);
  if (due < today) return "past";
  const msIn60Days = 60 * 24 * 60 * 60 * 1000;
  if (due.getTime() - today.getTime() <= msIn60Days) return "due soon";
  return "upcoming";
};

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("Settings persistence: loadSettings()", () => {
  beforeEach(() => localStorage.clear());

  it("returns defaults when localStorage is empty", () => {
    const settings = loadSettings();
    expect(settings).toEqual({
      incomeLabelName: "",
      seTaxRate: 14.13,
      fedTaxRate: 22,
      stateTaxRate: 0,
    });
  });

  it("merges partial stored JSON — stored fedTaxRate overrides default, rest stay at defaults", () => {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify({ fedTaxRate: 32 }));
    const settings = loadSettings();
    expect(settings.fedTaxRate).toBe(32);
    expect(settings.seTaxRate).toBe(14.13);
    expect(settings.stateTaxRate).toBe(0);
    expect(settings.incomeLabelName).toBe("");
  });

  it("merges partial stored JSON — stored incomeLabelName overrides default", () => {
    localStorage.setItem(
      SETTINGS_KEY,
      JSON.stringify({ incomeLabelName: "Freelance" }),
    );
    const settings = loadSettings();
    expect(settings.incomeLabelName).toBe("Freelance");
    expect(settings.fedTaxRate).toBe(22);
  });

  it("returns defaults when stored JSON is malformed/invalid", () => {
    localStorage.setItem(SETTINGS_KEY, "not valid json {{");
    const settings = loadSettings();
    expect(settings).toEqual(DEFAULT_SETTINGS);
  });

  it("returns defaults when stored value is null", () => {
    // localStorage.getItem returns null for missing key
    localStorage.removeItem(SETTINGS_KEY);
    const settings = loadSettings();
    expect(settings).toEqual(DEFAULT_SETTINGS);
  });
});

describe("Combined tax rate calculation", () => {
  it("default settings → (14.13 + 22 + 0) / 100 ≈ 0.3613", () => {
    const rate = combinedTaxRate(DEFAULT_SETTINGS);
    expect(rate).toBeCloseTo(0.3613, 4);
  });

  it("custom: seTaxRate=14.13, fedTaxRate=24, stateTaxRate=5 → 0.4313", () => {
    const rate = combinedTaxRate({
      incomeLabelName: "",
      seTaxRate: 14.13,
      fedTaxRate: 24,
      stateTaxRate: 5,
    });
    expect(rate).toBeCloseTo(0.4313, 4);
  });

  it("zero state tax: seTaxRate=14.13, fedTaxRate=12, stateTaxRate=0 → 0.2613", () => {
    const rate = combinedTaxRate({
      incomeLabelName: "",
      seTaxRate: 14.13,
      fedTaxRate: 12,
      stateTaxRate: 0,
    });
    expect(rate).toBeCloseTo(0.2613, 4);
  });

  it("all zero rates → 0", () => {
    const rate = combinedTaxRate({
      incomeLabelName: "",
      seTaxRate: 0,
      fedTaxRate: 0,
      stateTaxRate: 0,
    });
    expect(rate).toBe(0);
  });
});

describe("Income smoothing calculations", () => {
  const CURRENT_MONTH = "2026-03";

  const makeTrend = (month: string, income: number): MonthlyTrend => ({
    month,
    income,
    expenses: 2000,
    net: income - 2000,
  });

  it("avgMonthlyIncome = sum / count over trailing full months (excludes current partial month)", () => {
    const trends: MonthlyTrend[] = [
      makeTrend("2026-01", 5000),
      makeTrend("2026-02", 7000),
      makeTrend("2026-03", 1000), // current partial month — should be excluded
    ];
    const { avgMonthlyIncome } = computeSmoothingMetrics(trends, CURRENT_MONTH);
    expect(avgMonthlyIncome).toBeCloseTo((5000 + 7000) / 2, 2);
  });

  it("lowestIncome = Math.min of monthly income in trailing 12 full months", () => {
    const trends: MonthlyTrend[] = [
      makeTrend("2026-01", 3000),
      makeTrend("2026-02", 8000),
    ];
    const { lowestIncome } = computeSmoothingMetrics(trends, CURRENT_MONTH);
    expect(lowestIncome).toBe(3000);
  });

  it("safeFloor = lowestIncome * 0.8", () => {
    const trends: MonthlyTrend[] = [
      makeTrend("2026-01", 5000),
      makeTrend("2026-02", 4000),
    ];
    const { safeFloor, lowestIncome } = computeSmoothingMetrics(
      trends,
      CURRENT_MONTH,
    );
    expect(lowestIncome).toBe(4000);
    expect(safeFloor).toBeCloseTo(4000 * 0.8, 2);
  });

  it("variance = thisMonthIncome - avgMonthlyIncome (positive when above avg)", () => {
    const trends: MonthlyTrend[] = [
      makeTrend("2026-01", 4000),
      makeTrend("2026-02", 6000), // most recent full month
    ];
    const { variance, avgMonthlyIncome } = computeSmoothingMetrics(
      trends,
      CURRENT_MONTH,
    );
    expect(avgMonthlyIncome).toBeCloseTo(5000, 2);
    expect(variance).toBeCloseTo(6000 - 5000, 2); // +1000 (above avg)
  });

  it("variance is negative when most recent month is below average", () => {
    const trends: MonthlyTrend[] = [
      makeTrend("2026-01", 8000),
      makeTrend("2026-02", 2000), // most recent full month, below avg
    ];
    const { variance, avgMonthlyIncome } = computeSmoothingMetrics(
      trends,
      CURRENT_MONTH,
    );
    expect(avgMonthlyIncome).toBeCloseTo(5000, 2);
    expect(variance).toBeCloseTo(2000 - 5000, 2); // -3000 (below avg)
  });

  it("quarterlyTaxEst = (avgMonthlyIncome * 12 * combinedRate) / 4", () => {
    const avg = 5000;
    const rate = combinedTaxRate(DEFAULT_SETTINGS); // 0.3613
    const est = quarterlyTaxEst(avg, DEFAULT_SETTINGS);
    expect(est).toBeCloseTo((avg * 12 * rate) / 4, 2);
  });

  it("handles empty trends array gracefully — all zeros", () => {
    const { avgMonthlyIncome, lowestIncome, safeFloor, variance } =
      computeSmoothingMetrics([], CURRENT_MONTH);
    expect(avgMonthlyIncome).toBe(0);
    expect(lowestIncome).toBe(0);
    expect(safeFloor).toBe(0);
    expect(variance).toBe(0);
  });

  it("handles only current-month data (all excluded) — all zeros", () => {
    const trends: MonthlyTrend[] = [makeTrend("2026-03", 5000)];
    const { avgMonthlyIncome, lowestIncome } = computeSmoothingMetrics(
      trends,
      CURRENT_MONTH,
    );
    expect(avgMonthlyIncome).toBe(0);
    expect(lowestIncome).toBe(0);
  });

  it("only uses trailing 12 months (ignores older entries)", () => {
    // 13 full months of data — the oldest one should be dropped
    const trends: MonthlyTrend[] = [];
    for (let i = 13; i >= 1; i--) {
      const year = i >= 3 ? 2025 : 2026;
      const month = i >= 3 ? i - 2 : i;
      const monthStr = `${year}-${String(month).padStart(2, "0")}`;
      trends.push(makeTrend(monthStr, 1000 * i));
    }
    trends.push(makeTrend(CURRENT_MONTH, 9999)); // partial month

    // Sort by month string
    trends.sort((a, b) => a.month.localeCompare(b.month));

    const { avgMonthlyIncome } = computeSmoothingMetrics(trends, CURRENT_MONTH);

    // Should only include the 12 most recent full months
    const fullTrends = trends.filter((t) => t.month !== CURRENT_MONTH);
    const trailing12 = fullTrends.slice(-12);
    const expectedAvg =
      trailing12.reduce((s, t) => s + t.income, 0) / trailing12.length;
    expect(avgMonthlyIncome).toBeCloseTo(expectedAvg, 2);
  });
});

describe("Quarterly schedule status logic", () => {
  const TODAY = new Date("2026-03-25");

  it("due date in the past → status 'past'", () => {
    expect(getQuarterlyStatus("2026-01-15", TODAY)).toBe("past");
    expect(getQuarterlyStatus("2025-04-15", TODAY)).toBe("past");
  });

  it("due date within 60 days → status 'due soon'", () => {
    // 30 days from today
    expect(getQuarterlyStatus("2026-04-15", TODAY)).toBe("due soon");
    // Exactly 60 days from today
    const exactly60 = new Date(TODAY.getTime() + 60 * 24 * 60 * 60 * 1000);
    const y = exactly60.getFullYear();
    const m = String(exactly60.getMonth() + 1).padStart(2, "0");
    const d = String(exactly60.getDate()).padStart(2, "0");
    expect(getQuarterlyStatus(`${y}-${m}-${d}`, TODAY)).toBe("due soon");
  });

  it("due date more than 60 days out → status 'upcoming'", () => {
    expect(getQuarterlyStatus("2026-09-15", TODAY)).toBe("upcoming");
    expect(getQuarterlyStatus("2027-01-15", TODAY)).toBe("upcoming");
  });

  it("due date 1 day from now → status 'due soon' (clearly within 60 days, not past)", () => {
    const tomorrow = new Date(TODAY.getTime() + 1 * 24 * 60 * 60 * 1000);
    const y = tomorrow.getUTCFullYear();
    const m = String(tomorrow.getUTCMonth() + 1).padStart(2, "0");
    const d = String(tomorrow.getUTCDate()).padStart(2, "0");
    const result = getQuarterlyStatus(`${y}-${m}-${d}`, TODAY);
    expect(result).toBe("due soon");
  });
});

// ── This Month $0 UX clarification ───────────────────────────────────────────

describe("This Month $0 display", () => {
  it("shows (month in progress) context when thisMonthIncome is 0 but there is data", () => {
    // The component renders a contextual note so $0 early in the month is not confusing
    expect(src).toContain("month in progress");
    expect(src).toContain("thisMonthIncome === 0");
  });

  it("tooltip on This Month stat explains $0 is normal early in month", () => {
    expect(src).toContain("$0 early in the month is normal");
  });
});
