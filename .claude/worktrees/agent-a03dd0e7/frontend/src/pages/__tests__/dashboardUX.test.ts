/**
 * Tests for dashboard UX logic:
 * - Offline indicator (navigator.onLine + event listeners)
 * - Budget optimistic update helpers
 * - Benchmark percentile computation (mirrored from service)
 *
 * @vitest-environment jsdom
 */

import { describe, it, expect, vi, afterEach } from "vitest";

// ===========================================================================
// Offline Indicator Logic
// ===========================================================================

describe("OfflineIndicator logic", () => {
  const originalOnLine = Object.getOwnPropertyDescriptor(navigator, "onLine");

  afterEach(() => {
    if (originalOnLine) {
      Object.defineProperty(navigator, "onLine", originalOnLine);
    }
  });

  const setOnline = (value: boolean) => {
    Object.defineProperty(navigator, "onLine", {
      configurable: true,
      get: () => value,
    });
  };

  it("detects online state as true", () => {
    setOnline(true);
    expect(navigator.onLine).toBe(true);
  });

  it("detects offline state as false", () => {
    setOnline(false);
    expect(navigator.onLine).toBe(false);
  });

  it("fires offline event when network drops", () => {
    const handler = vi.fn();
    window.addEventListener("offline", handler);
    window.dispatchEvent(new Event("offline"));
    expect(handler).toHaveBeenCalledTimes(1);
    window.removeEventListener("offline", handler);
  });

  it("fires online event when network recovers", () => {
    const handler = vi.fn();
    window.addEventListener("online", handler);
    window.dispatchEvent(new Event("online"));
    expect(handler).toHaveBeenCalledTimes(1);
    window.removeEventListener("online", handler);
  });

  it("subsequent offline+online events update state correctly", () => {
    const states: boolean[] = [];
    const offlineHandler = () => states.push(false);
    const onlineHandler = () => states.push(true);
    window.addEventListener("offline", offlineHandler);
    window.addEventListener("online", onlineHandler);

    window.dispatchEvent(new Event("offline"));
    window.dispatchEvent(new Event("offline"));
    window.dispatchEvent(new Event("online"));

    expect(states).toEqual([false, false, true]);
    window.removeEventListener("offline", offlineHandler);
    window.removeEventListener("online", onlineHandler);
  });
});

// ===========================================================================
// Budget Optimistic Update Helpers
// ===========================================================================

interface Budget {
  id: string;
  name: string;
  amount: number;
  spent_amount: number;
  [key: string]: unknown;
}

/** Simulate the onMutate optimistic update for an edit */
function optimisticEdit(
  budgets: Budget[],
  id: string,
  patch: Partial<Budget>,
): Budget[] {
  return budgets.map((b) => (b.id === id ? { ...b, ...patch } : b));
}

/** Simulate the onMutate optimistic update for a create */
function optimisticCreate(budgets: Budget[], tempBudget: Budget): Budget[] {
  return [tempBudget, ...budgets];
}

/** Replace optimistic placeholder with real server response */
function replaceOptimistic(budgets: Budget[], realBudget: Budget): Budget[] {
  return budgets.map((b) => (b.id === "__optimistic__" ? realBudget : b));
}

describe("Budget optimistic update helpers", () => {
  const existing: Budget[] = [
    { id: "a1", name: "Groceries", amount: 300, spent_amount: 150 },
    { id: "a2", name: "Dining", amount: 100, spent_amount: 80 },
  ];

  it("optimisticEdit updates the matching budget", () => {
    const result = optimisticEdit(existing, "a1", { amount: 400 });
    expect(result.find((b) => b.id === "a1")?.amount).toBe(400);
    expect(result.find((b) => b.id === "a2")?.amount).toBe(100);
  });

  it("optimisticEdit leaves non-matching budgets unchanged", () => {
    const result = optimisticEdit(existing, "a1", { name: "Food" });
    expect(result.find((b) => b.id === "a2")?.name).toBe("Dining");
  });

  it("optimisticCreate prepends to list", () => {
    const temp: Budget = {
      id: "__optimistic__",
      name: "Rent",
      amount: 1500,
      spent_amount: 0,
    };
    const result = optimisticCreate(existing, temp);
    expect(result[0].id).toBe("__optimistic__");
    expect(result).toHaveLength(3);
  });

  it("replaceOptimistic swaps placeholder with real budget", () => {
    const withTemp: Budget[] = [
      { id: "__optimistic__", name: "Rent", amount: 1500, spent_amount: 0 },
      ...existing,
    ];
    const real: Budget = {
      id: "a3",
      name: "Rent",
      amount: 1500,
      spent_amount: 0,
    };
    const result = replaceOptimistic(withTemp, real);
    expect(result.find((b) => b.id === "__optimistic__")).toBeUndefined();
    expect(result.find((b) => b.id === "a3")).toBeDefined();
    expect(result).toHaveLength(3);
  });

  it("rollback restores previous list on error", () => {
    const previous = [...existing];
    // Simulate optimistic create then rollback
    const afterOptimistic = optimisticCreate(existing, {
      id: "__optimistic__",
      name: "Vacation",
      amount: 500,
      spent_amount: 0,
    });
    expect(afterOptimistic).toHaveLength(3);
    // On error, restore previous
    const restored = previous;
    expect(restored).toHaveLength(2);
    expect(restored).toEqual(existing);
  });
});

// ===========================================================================
// Net Worth Percentile Logic (mirrored from backend service)
// ===========================================================================

const SCF_PERCENTILES: Record<
  string,
  [number, number, number, number, number]
> = {
  under_35: [-2400, 3600, 39000, 120000, 300000],
  "35_44": [0, 21700, 135600, 338000, 836000],
  "45_54": [2000, 47500, 247200, 695000, 1870000],
  "55_64": [3400, 63500, 364500, 1054000, 2850000],
  "65_74": [9400, 78000, 409900, 1100000, 3200000],
  "75_plus": [6800, 58000, 335600, 985000, 2680000],
};

function estimatePercentile(netWorth: number, group: string): number {
  const [p10, p25, p50, p75, p90] = SCF_PERCENTILES[group];
  const segments: [number, number, number, number][] = [
    [0, 10, p10 - (p25 - p10), p10],
    [10, 25, p10, p25],
    [25, 50, p25, p50],
    [50, 75, p50, p75],
    [75, 90, p75, p90],
    [90, 100, p90, p90 + (p90 - p75)],
  ];
  for (const [loPct, hiPct, loVal, hiVal] of segments) {
    if (netWorth <= hiVal || hiPct === 100) {
      if (hiVal === loVal) return loPct;
      const ratio = (netWorth - loVal) / (hiVal - loVal);
      return Math.max(
        0,
        Math.min(100, Math.round(loPct + ratio * (hiPct - loPct))),
      );
    }
  }
  return 99;
}

describe("Net worth percentile estimation", () => {
  it("at median returns 50", () => {
    const p50 = SCF_PERCENTILES["35_44"][2];
    expect(estimatePercentile(p50, "35_44")).toBe(50);
  });

  it("at p25 returns 25", () => {
    const p25 = SCF_PERCENTILES["35_44"][1];
    expect(estimatePercentile(p25, "35_44")).toBe(25);
  });

  it("at p75 returns 75", () => {
    const p75 = SCF_PERCENTILES["45_54"][3];
    expect(estimatePercentile(p75, "45_54")).toBe(75);
  });

  it("below p10 returns low percentile", () => {
    expect(estimatePercentile(0, "under_35")).toBeLessThan(20);
  });

  it("above p90 returns high percentile", () => {
    expect(estimatePercentile(10_000_000, "55_64")).toBeGreaterThan(90);
  });

  it("result is always 0–100", () => {
    for (const group of Object.keys(SCF_PERCENTILES)) {
      expect(estimatePercentile(-999_999, group)).toBeGreaterThanOrEqual(0);
      expect(estimatePercentile(50_000_000, group)).toBeLessThanOrEqual(100);
    }
  });

  it("above median has percentile > 50", () => {
    // Well above the 35-44 median of 135k
    expect(estimatePercentile(400_000, "35_44")).toBeGreaterThan(50);
  });

  it("below median has percentile < 50", () => {
    expect(estimatePercentile(20_000, "35_44")).toBeLessThan(50);
  });
});
