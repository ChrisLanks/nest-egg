/**
 * Tests for FIRE metrics page logic: hasNoData detection, scoreColor,
 * formatPercent, formatCurrency, empty-data guards, and household filtering.
 */

import { describe, it, expect, beforeEach } from "vitest";
import type { FireMetricsResponse } from "../../api/fire";

// ── Helper functions (mirrored from FireMetricsPage.tsx) ─────────────────────

const scoreColor = (ratio: number): string => {
  if (ratio >= 1) return "green.400";
  if (ratio >= 0.5) return "yellow.400";
  return "red.400";
};

const formatPercent = (value: number) => {
  const pct = value * 100;
  // Drop unnecessary trailing ".0" (e.g. 100.0% -> 100%)
  return `${pct % 1 === 0 ? pct.toFixed(0) : pct.toFixed(1)}%`;
};

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);

const hasNoData = (data: FireMetricsResponse): boolean =>
  data.fi_ratio.investable_assets === 0 &&
  data.fi_ratio.annual_expenses === 0 &&
  data.savings_rate.income === 0 &&
  data.savings_rate.spending === 0;

// ── Fixtures ─────────────────────────────────────────────────────────────────

const ZERO_DATA: FireMetricsResponse = {
  fi_ratio: {
    fi_ratio: 0,
    investable_assets: 0,
    annual_expenses: 0,
    fi_number: 0,
  },
  savings_rate: {
    savings_rate: 0,
    income: 0,
    spending: 0,
    savings: 0,
    months: 12,
  },
  years_to_fi: {
    years_to_fi: null,
    fi_number: 0,
    investable_assets: 0,
    annual_savings: 0,
    withdrawal_rate: 0.04,
    expected_return: 0.07,
    already_fi: false,
  },
  coast_fi: {
    coast_fi_number: 0,
    fi_number: 0,
    investable_assets: 0,
    is_coast_fi: false,
    retirement_age: 65,
    years_until_retirement: 30,
    expected_return: 0.07,
  },
};

const REAL_DATA: FireMetricsResponse = {
  fi_ratio: {
    fi_ratio: 0.45,
    investable_assets: 450000,
    annual_expenses: 40000,
    fi_number: 1000000,
  },
  savings_rate: {
    savings_rate: 0.35,
    income: 100000,
    spending: 65000,
    savings: 35000,
    months: 12,
  },
  years_to_fi: {
    years_to_fi: 12.5,
    fi_number: 1000000,
    investable_assets: 450000,
    annual_savings: 35000,
    withdrawal_rate: 0.04,
    expected_return: 0.07,
    already_fi: false,
  },
  coast_fi: {
    coast_fi_number: 300000,
    fi_number: 1000000,
    investable_assets: 450000,
    is_coast_fi: true,
    retirement_age: 65,
    years_until_retirement: 30,
    expected_return: 0.07,
  },
};

const FI_ACHIEVED_DATA: FireMetricsResponse = {
  fi_ratio: {
    fi_ratio: 1.2,
    investable_assets: 1200000,
    annual_expenses: 40000,
    fi_number: 1000000,
  },
  savings_rate: {
    savings_rate: 0.55,
    income: 120000,
    spending: 54000,
    savings: 66000,
    months: 12,
  },
  years_to_fi: {
    years_to_fi: 0,
    fi_number: 1000000,
    investable_assets: 1200000,
    annual_savings: 66000,
    withdrawal_rate: 0.04,
    expected_return: 0.07,
    already_fi: true,
  },
  coast_fi: {
    coast_fi_number: 300000,
    fi_number: 1000000,
    investable_assets: 1200000,
    is_coast_fi: true,
    retirement_age: 65,
    years_until_retirement: 30,
    expected_return: 0.07,
  },
};

// ── Tests ────────────────────────────────────────────────────────────────────

describe("hasNoData", () => {
  it("returns true when all key values are zero", () => {
    expect(hasNoData(ZERO_DATA)).toBe(true);
  });

  it("returns false when real data is present", () => {
    expect(hasNoData(REAL_DATA)).toBe(false);
  });

  it("returns false when only income is present", () => {
    const partial = {
      ...ZERO_DATA,
      savings_rate: { ...ZERO_DATA.savings_rate, income: 5000 },
    };
    expect(hasNoData(partial)).toBe(false);
  });

  it("returns false when only investable assets are present", () => {
    const partial = {
      ...ZERO_DATA,
      fi_ratio: { ...ZERO_DATA.fi_ratio, investable_assets: 10000 },
    };
    expect(hasNoData(partial)).toBe(false);
  });
});

describe("scoreColor", () => {
  it("returns green for ratio >= 1", () => {
    expect(scoreColor(1.0)).toBe("green.400");
    expect(scoreColor(1.5)).toBe("green.400");
  });

  it("returns yellow for ratio >= 0.5 and < 1", () => {
    expect(scoreColor(0.5)).toBe("yellow.400");
    expect(scoreColor(0.75)).toBe("yellow.400");
    expect(scoreColor(0.99)).toBe("yellow.400");
  });

  it("returns red for ratio < 0.5", () => {
    expect(scoreColor(0)).toBe("red.400");
    expect(scoreColor(0.1)).toBe("red.400");
    expect(scoreColor(0.49)).toBe("red.400");
  });
});

describe("formatPercent", () => {
  it("formats whole percentages without trailing .0", () => {
    expect(formatPercent(0.5)).toBe("50%");
    expect(formatPercent(1.0)).toBe("100%");
  });

  it("formats fractional percentages with one decimal", () => {
    expect(formatPercent(0.456)).toBe("45.6%");
    expect(formatPercent(0.753)).toBe("75.3%");
  });

  it("formats zero without trailing .0", () => {
    expect(formatPercent(0)).toBe("0%");
  });

  it("handles exact integer percentages", () => {
    expect(formatPercent(0.25)).toBe("25%");
    expect(formatPercent(0.1)).toBe("10%");
  });
});

describe("formatCurrency", () => {
  it("formats positive amounts", () => {
    expect(formatCurrency(1000000)).toBe("$1,000,000");
    expect(formatCurrency(450000)).toBe("$450,000");
  });

  it("formats zero", () => {
    expect(formatCurrency(0)).toBe("$0");
  });

  it("rounds to whole dollars", () => {
    expect(formatCurrency(999.99)).toBe("$1,000");
  });
});

// ── Achievement badge guards ────────────────────────────────────────────────

describe("FI Achievement Guards", () => {
  it('should NOT show "Financially Independent!" when data is all zeros', () => {
    const d = ZERO_DATA.years_to_fi;
    // The guard: already_fi AND investable_assets > 0
    const showBadge = d.already_fi && d.investable_assets > 0;
    expect(showBadge).toBe(false);
  });

  it('should show "Financially Independent!" when actually FI with assets', () => {
    const d = FI_ACHIEVED_DATA.years_to_fi;
    const showBadge = d.already_fi && d.investable_assets > 0;
    expect(showBadge).toBe(true);
  });

  it('should NOT show "Coast FI Achieved!" when investable_assets is 0', () => {
    const d = ZERO_DATA.coast_fi;
    const showBadge = d.is_coast_fi && d.investable_assets > 0;
    expect(showBadge).toBe(false);
  });

  it('should show "Coast FI Achieved!" when actually coast FI with assets', () => {
    const d = FI_ACHIEVED_DATA.coast_fi;
    const showBadge = d.is_coast_fi && d.investable_assets > 0;
    expect(showBadge).toBe(true);
  });
});

// ── Per-card empty data detection ───────────────────────────────────────────

describe("Per-Card No-Data Guards", () => {
  it("FI Ratio card shows hint when annual_expenses is 0", () => {
    expect(ZERO_DATA.fi_ratio.annual_expenses === 0).toBe(true);
  });

  it("FI Ratio card shows data when expenses exist", () => {
    expect(REAL_DATA.fi_ratio.annual_expenses === 0).toBe(false);
  });

  it("Savings Rate card shows hint when both income and spending are 0", () => {
    const d = ZERO_DATA.savings_rate;
    expect(d.income === 0 && d.spending === 0).toBe(true);
  });

  it("Savings Rate card shows data when income exists", () => {
    const d = REAL_DATA.savings_rate;
    expect(d.income === 0 && d.spending === 0).toBe(false);
  });

  it("Years to FI card shows hint when both fi_number and assets are 0", () => {
    const d = ZERO_DATA.years_to_fi;
    expect(d.fi_number === 0 && d.investable_assets === 0).toBe(true);
  });

  it("Coast FI card shows hint when both fi_number and assets are 0", () => {
    const d = ZERO_DATA.coast_fi;
    expect(d.fi_number === 0 && d.investable_assets === 0).toBe(true);
  });
});

// ── Household member filtering logic ────────────────────────────────────────

describe("Household Member Filtering Logic", () => {
  it("uses filterUserId when in combined view", () => {
    const isCombinedView = true;
    const selectedUserId = "user-1";
    const filterUserId = "user-2";
    const effectiveUserId = isCombinedView ? filterUserId : selectedUserId;
    expect(effectiveUserId).toBe("user-2");
  });

  it("uses selectedUserId when NOT in combined view", () => {
    const isCombinedView = false;
    const selectedUserId = "user-1";
    const filterUserId = "user-2";
    const effectiveUserId = isCombinedView ? filterUserId : selectedUserId;
    expect(effectiveUserId).toBe("user-1");
  });

  it('uses null filterUserId for "Household" option in combined view', () => {
    const isCombinedView = true;
    const selectedUserId = "user-1";
    const filterUserId = null;
    const effectiveUserId = isCombinedView ? filterUserId : selectedUserId;
    expect(effectiveUserId).toBeNull();
  });

  it("shows member filter only in combined view with multiple members", () => {
    const cases = [
      { isCombinedView: true, memberCount: 2, expected: true },
      { isCombinedView: true, memberCount: 1, expected: false },
      { isCombinedView: true, memberCount: 0, expected: false },
      { isCombinedView: false, memberCount: 2, expected: false },
      { isCombinedView: false, memberCount: 0, expected: false },
    ];
    for (const { isCombinedView, memberCount, expected } of cases) {
      const showMemberFilter = isCombinedView && memberCount > 1;
      expect(
        showMemberFilter,
        `combined=${isCombinedView}, members=${memberCount}`,
      ).toBe(expected);
    }
  });
});

// ── Query key construction ──────────────────────────────────────────────────

describe("FIRE Query Parameters", () => {
  it("converts UI percentages to decimals for API", () => {
    const withdrawalRate = 4; // UI shows 4%
    const expectedReturn = 7; // UI shows 7%
    expect(withdrawalRate / 100).toBe(0.04);
    expect(expectedReturn / 100).toBe(0.07);
  });

  it("passes undefined user_id when effectiveUserId is null", () => {
    const effectiveUserId: string | null = null;
    const params = { user_id: effectiveUserId || undefined };
    expect(params.user_id).toBeUndefined();
  });

  it("passes user_id when effectiveUserId is set", () => {
    const effectiveUserId: string | null = "user-123";
    const params = { user_id: effectiveUserId || undefined };
    expect(params.user_id).toBe("user-123");
  });
});

// ── String-based input parsing ──────────────────────────────────────────────

describe("FIRE input string-to-number parsing", () => {
  /**
   * Mirrors the parsing logic in FireMetricsPage:
   * - State is stored as strings to allow typing decimals (e.g., "4.")
   * - Parsed to numbers for the query key and API call
   */

  it("parses whole number strings", () => {
    expect(parseFloat("4") || 0).toBe(4);
    expect(parseFloat("7") || 0).toBe(7);
    expect(parseInt("65", 10) || 65).toBe(65);
  });

  it("parses decimal strings with 2 places", () => {
    expect(parseFloat("3.75") || 0).toBe(3.75);
    expect(parseFloat("7.25") || 0).toBe(7.25);
  });

  it("handles intermediate decimal input (e.g., '4.')", () => {
    // "4." is a valid intermediate state while typing "4.5"
    expect(parseFloat("4.") || 0).toBe(4);
  });

  it("falls back to 0 for empty string", () => {
    expect(parseFloat("") || 0).toBe(0);
  });

  it("falls back to 0 for non-numeric string", () => {
    expect(parseFloat("abc") || 0).toBe(0);
  });

  it("retirement age falls back to 65 for empty string", () => {
    expect(parseInt("", 10) || 65).toBe(65);
  });

  it("converts string percentages to API decimals correctly", () => {
    const withdrawalRate = "3.50";
    const expectedReturn = "7.25";
    expect((parseFloat(withdrawalRate) || 0) / 100).toBeCloseTo(0.035);
    expect((parseFloat(expectedReturn) || 0) / 100).toBeCloseTo(0.0725);
  });

  it("query key uses parsed numbers, not raw strings", () => {
    const withdrawalRate = "4.00";
    const expectedReturn = "7.50";
    const retirementAge = "65";

    const withdrawalNum = parseFloat(withdrawalRate) || 0;
    const returnNum = parseFloat(expectedReturn) || 0;
    const retirementNum = parseInt(retirementAge, 10) || 65;

    const queryKey = [
      "fire-metrics",
      null,
      "",
      withdrawalNum,
      returnNum,
      retirementNum,
    ];

    expect(queryKey[3]).toBe(4);
    expect(queryKey[4]).toBe(7.5);
    expect(queryKey[5]).toBe(65);
  });

  it("intermediate typing states produce stable parsed values", () => {
    // User types "3" then "." then "5" → "3", "3.", "3.5"
    // Query key should not thrash: 3, 3, 3.5
    const states = ["3", "3.", "3.5"];
    const parsed = states.map((s) => parseFloat(s) || 0);
    expect(parsed).toEqual([3, 3, 3.5]);
    // "3" and "3." produce the same number → no extra refetch
    expect(parsed[0]).toBe(parsed[1]);
  });
});

// ── placeholderData keeps previous data during refetch ───────────────────────

describe("FIRE query placeholderData behavior", () => {
  it("placeholderData callback returns previous data", () => {
    // Mirrors: placeholderData: (prev) => prev
    const placeholderData = (prev: unknown) => prev;
    const prevData = { fi_ratio: { fi_ratio: 0.45 } };

    expect(placeholderData(prevData)).toBe(prevData);
    expect(placeholderData(undefined)).toBeUndefined();
  });

  it("cards stay visible when placeholderData returns previous data", () => {
    const prevData = {
      fi_ratio: { fi_ratio: 0.45, investable_assets: 450000 },
    };
    const placeholderData = (prev: unknown) => prev;

    // Simulate: query key changes (user typed), isLoading becomes true,
    // but data = placeholderData(prevData) keeps the old data visible
    const data = placeholderData(prevData);
    expect(data).not.toBeUndefined();
    expect((data as typeof prevData).fi_ratio.fi_ratio).toBe(0.45);
  });
});

// ── localStorage persistence for assumptions ────────────────────────────────

describe("FIRE assumptions localStorage persistence", () => {
  const defaults = {
    withdrawalRate: "4",
    expectedReturn: "7",
    retirementAge: "65",
  };

  /** Mirrors loadAssumptions using an in-memory store */
  function loadAssumptions(
    store: Map<string, string>,
    key: string,
  ): typeof defaults {
    try {
      const raw = store.get(key);
      if (raw) return JSON.parse(raw);
    } catch {
      /* ignore */
    }
    return { ...defaults };
  }

  const store = new Map<string, string>();
  const KEY = "fire-assumptions";

  beforeEach(() => {
    store.clear();
  });

  it("returns defaults when nothing is stored", () => {
    expect(loadAssumptions(store, KEY)).toEqual(defaults);
  });

  it("returns saved values when present", () => {
    const saved = {
      withdrawalRate: "3.5",
      expectedReturn: "8",
      retirementAge: "60",
    };
    store.set(KEY, JSON.stringify(saved));
    expect(loadAssumptions(store, KEY)).toEqual(saved);
  });

  it("returns defaults when stored JSON is invalid", () => {
    store.set(KEY, "not-json");
    expect(loadAssumptions(store, KEY)).toEqual(defaults);
  });

  it("persists values on change", () => {
    const updated = {
      withdrawalRate: "3.75",
      expectedReturn: "6.5",
      retirementAge: "62",
    };
    store.set(KEY, JSON.stringify(updated));
    const loaded = loadAssumptions(store, KEY);
    expect(loaded.withdrawalRate).toBe("3.75");
    expect(loaded.expectedReturn).toBe("6.5");
    expect(loaded.retirementAge).toBe("62");
  });

  it("survives round-trip with decimal values", () => {
    const vals = {
      withdrawalRate: "3.50",
      expectedReturn: "7.25",
      retirementAge: "67",
    };
    store.set(KEY, JSON.stringify(vals));
    const loaded = loadAssumptions(store, KEY);
    expect(parseFloat(loaded.withdrawalRate)).toBe(3.5);
    expect(parseFloat(loaded.expectedReturn)).toBe(7.25);
    expect(parseInt(loaded.retirementAge, 10)).toBe(67);
  });
});

// ── FIRE page tooltip content ────────────────────────────────────────────────

describe("FIRE page tooltip content", () => {
  const INPUT_TOOLTIPS: Record<string, string> = {
    withdrawalRate:
      "The percentage of your portfolio you plan to withdraw each year in retirement — 4% is a common starting point",
    expectedReturn:
      "The average annual growth you expect from your investments — historically stocks average ~7% after inflation",
    retirementAge:
      "The age you plan to stop working — used to calculate Coast FI and years remaining",
  };

  const STAT_TOOLTIPS: Record<string, string> = {
    investableAssets: "Total value of your investment and retirement accounts",
    fiNumber:
      "The portfolio size needed to live off investments — your annual expenses divided by your withdrawal rate",
    annualExpenses: "Your total spending over the last 12 months",
    income: "Total income from all sources over the period",
    spending: "Total expenses across all categories over the period",
    savings: "Income minus spending — the amount available to invest or save",
    annualSavings:
      "How much you save per year — higher savings means reaching FI faster",
    fiNumberYears:
      "The total portfolio value you need to be financially independent",
    coastFiNumber:
      "The minimum portfolio value needed today so that investment growth alone reaches your FI number by retirement",
    coastInvestable: "Your current investment and retirement account balances",
    yearsToRetirement:
      "How many years until you reach your target retirement age",
    retirementAge: "The age you set in the Assumptions section above",
  };

  it("all input tooltips are non-empty", () => {
    for (const label of Object.values(INPUT_TOOLTIPS)) {
      expect(typeof label).toBe("string");
      expect(label.length).toBeGreaterThan(10);
    }
  });

  it("covers all 3 input fields", () => {
    expect(Object.keys(INPUT_TOOLTIPS)).toHaveLength(3);
  });

  it("all stat tooltips are non-empty", () => {
    for (const label of Object.values(STAT_TOOLTIPS)) {
      expect(typeof label).toBe("string");
      expect(label.length).toBeGreaterThan(10);
    }
  });

  it("covers all 12 stat labels", () => {
    expect(Object.keys(STAT_TOOLTIPS)).toHaveLength(12);
  });
});
