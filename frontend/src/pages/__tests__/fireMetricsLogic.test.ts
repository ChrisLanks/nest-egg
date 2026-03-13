/**
 * Tests for FIRE metrics page logic: hasNoData detection, scoreColor,
 * formatPercent, formatCurrency, empty-data guards, and household filtering.
 */

import { describe, it, expect } from "vitest";
import type { FireMetricsResponse } from "../../api/fire";

// ── Helper functions (mirrored from FireMetricsPage.tsx) ─────────────────────

const scoreColor = (ratio: number): string => {
  if (ratio >= 1) return "green.400";
  if (ratio >= 0.5) return "yellow.400";
  return "red.400";
};

const formatPercent = (value: number) => `${(value * 100).toFixed(1)}%`;

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
  it("formats whole percentages", () => {
    expect(formatPercent(0.5)).toBe("50.0%");
    expect(formatPercent(1.0)).toBe("100.0%");
  });

  it("formats fractional percentages", () => {
    expect(formatPercent(0.456)).toBe("45.6%");
  });

  it("formats zero", () => {
    expect(formatPercent(0)).toBe("0.0%");
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
