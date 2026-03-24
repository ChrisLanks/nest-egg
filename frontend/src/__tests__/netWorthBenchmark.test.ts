/**
 * Tests for net worth benchmark insight logic.
 *
 * Covers:
 * 1. InsightItem data_vintage / data_is_stale field contract
 * 2. Stale-data badge visibility logic (mirrors InsightCard in SmartInsightsPage)
 * 3. Age-bucket mapping (mirrors scf_benchmark_service.age_bucket)
 * 4. Fidelity milestone target calculation
 */

import { describe, it, expect } from "vitest";
import type { InsightItem } from "../api/smartInsights";

// ---------------------------------------------------------------------------
// 1. InsightItem type contract — data_vintage / data_is_stale
// ---------------------------------------------------------------------------

describe("InsightItem data_vintage / data_is_stale contract", () => {
  /** Build a minimal InsightItem with overrideable benchmark fields. */
  function makeInsight(
    overrides: Partial<InsightItem> = {},
  ): InsightItem {
    return {
      type: "net_worth_benchmark",
      title: "Net worth vs. peers (ages 35-44)",
      message: "Your net worth of $80,000 is below the median.",
      action: "Review your savings rate.",
      priority: "medium",
      category: "retirement",
      icon: "📊",
      priority_score: 55,
      amount: 80_000,
      data_vintage: null,
      data_is_stale: null,
      ...overrides,
    };
  }

  it("accepts null data_vintage", () => {
    const item = makeInsight({ data_vintage: null });
    expect(item.data_vintage).toBeNull();
  });

  it("accepts a year string data_vintage", () => {
    const item = makeInsight({ data_vintage: "2022" });
    expect(item.data_vintage).toBe("2022");
  });

  it("accepts null data_is_stale", () => {
    const item = makeInsight({ data_is_stale: null });
    expect(item.data_is_stale).toBeNull();
  });

  it("accepts true data_is_stale", () => {
    const item = makeInsight({ data_is_stale: true });
    expect(item.data_is_stale).toBe(true);
  });

  it("accepts false data_is_stale", () => {
    const item = makeInsight({ data_is_stale: false });
    expect(item.data_is_stale).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// 2. Stale-data badge visibility logic (mirrors InsightCard showStaleBadge)
// ---------------------------------------------------------------------------

/** Mirrors the showStaleBadge logic in SmartInsightsPage InsightCard. */
function computeShowStaleBadge(insight: InsightItem): boolean {
  return insight.data_is_stale === true && insight.data_vintage != null;
}

describe("InsightCard stale-data badge visibility", () => {
  function makeInsight(overrides: Partial<InsightItem> = {}): InsightItem {
    return {
      type: "net_worth_benchmark",
      title: "T",
      message: "M",
      action: "A",
      priority: "medium",
      category: "retirement",
      icon: "📊",
      priority_score: 55,
      amount: null,
      data_vintage: null,
      data_is_stale: null,
      ...overrides,
    };
  }

  it("shows badge when data_is_stale=true and data_vintage is set", () => {
    const insight = makeInsight({ data_is_stale: true, data_vintage: "2022" });
    expect(computeShowStaleBadge(insight)).toBe(true);
  });

  it("hides badge when data_is_stale=false", () => {
    const insight = makeInsight({ data_is_stale: false, data_vintage: "2022" });
    expect(computeShowStaleBadge(insight)).toBe(false);
  });

  it("hides badge when data_is_stale=null", () => {
    const insight = makeInsight({ data_is_stale: null, data_vintage: "2022" });
    expect(computeShowStaleBadge(insight)).toBe(false);
  });

  it("hides badge when data_vintage is null even if stale=true", () => {
    const insight = makeInsight({ data_is_stale: true, data_vintage: null });
    expect(computeShowStaleBadge(insight)).toBe(false);
  });

  it("hides badge for non-benchmark insight types", () => {
    const insight = makeInsight({
      type: "emergency_fund_low",
      data_is_stale: null,
      data_vintage: null,
    });
    expect(computeShowStaleBadge(insight)).toBe(false);
  });

  it("badge label includes data_vintage year", () => {
    const insight = makeInsight({ data_is_stale: true, data_vintage: "2019" });
    const show = computeShowStaleBadge(insight);
    expect(show).toBe(true);
    // Label should reference the year
    const label = show ? `Data as of ${insight.data_vintage} · update in progress` : "";
    expect(label).toContain("2019");
  });
});

// ---------------------------------------------------------------------------
// 3. Age-bucket mapping (mirrors scf_benchmark_service.age_bucket)
// ---------------------------------------------------------------------------

/** Mirrors the age_bucket function in scf_benchmark_service.py */
function ageBucket(age: number): string {
  if (age < 35) return "under 35";
  if (age < 45) return "35-44";
  if (age < 55) return "45-54";
  if (age < 65) return "55-64";
  if (age < 75) return "65-74";
  return "75+";
}

describe("age bucket mapping", () => {
  it("maps age 25 → under 35", () => expect(ageBucket(25)).toBe("under 35"));
  it("maps age 34 → under 35", () => expect(ageBucket(34)).toBe("under 35"));
  it("maps age 35 → 35-44", () => expect(ageBucket(35)).toBe("35-44"));
  it("maps age 44 → 35-44", () => expect(ageBucket(44)).toBe("35-44"));
  it("maps age 45 → 45-54", () => expect(ageBucket(45)).toBe("45-54"));
  it("maps age 54 → 45-54", () => expect(ageBucket(54)).toBe("45-54"));
  it("maps age 55 → 55-64", () => expect(ageBucket(55)).toBe("55-64"));
  it("maps age 64 → 55-64", () => expect(ageBucket(64)).toBe("55-64"));
  it("maps age 65 → 65-74", () => expect(ageBucket(65)).toBe("65-74"));
  it("maps age 74 → 65-74", () => expect(ageBucket(74)).toBe("65-74"));
  it("maps age 75 → 75+", () => expect(ageBucket(75)).toBe("75+"));
  it("maps age 90 → 75+", () => expect(ageBucket(90)).toBe("75+"));
});

// ---------------------------------------------------------------------------
// 4. Fidelity milestone target calculation (mirrors fidelity_target in service)
// ---------------------------------------------------------------------------

const FIDELITY_MILESTONES: Record<number, number> = {
  30: 1.0,
  35: 2.0,
  40: 3.0,
  45: 4.0,
  50: 6.0,
  55: 7.0,
  60: 8.0,
  67: 10.0,
};

/** Mirrors fidelity_target in scf_benchmark_service.py */
function fidelityTarget(age: number, annualIncome: number): number | null {
  if (annualIncome <= 0) return null;
  const applicableAges = Object.keys(FIDELITY_MILESTONES)
    .map(Number)
    .filter((a) => a <= age)
    .sort((a, b) => a - b);
  if (applicableAges.length === 0) return null;
  const closest = applicableAges[applicableAges.length - 1];
  return FIDELITY_MILESTONES[closest] * annualIncome;
}

describe("Fidelity milestone target calculation", () => {
  it("age 40, income $100k → 3× = $300k", () => {
    expect(fidelityTarget(40, 100_000)).toBe(300_000);
  });

  it("age 50, income $80k → 6× = $480k", () => {
    expect(fidelityTarget(50, 80_000)).toBe(480_000);
  });

  it("age 67, income $120k → 10× = $1.2M", () => {
    expect(fidelityTarget(67, 120_000)).toBe(1_200_000);
  });

  it("age 70 uses 67 milestone → 10×", () => {
    expect(fidelityTarget(70, 100_000)).toBe(1_000_000);
  });

  it("returns null for zero income", () => {
    expect(fidelityTarget(40, 0)).toBeNull();
  });

  it("returns null for negative income", () => {
    expect(fidelityTarget(40, -1)).toBeNull();
  });

  it("returns null for age below first milestone (30)", () => {
    expect(fidelityTarget(25, 50_000)).toBeNull();
  });

  it("age exactly 30 → 1× salary", () => {
    expect(fidelityTarget(30, 75_000)).toBe(75_000);
  });
});
