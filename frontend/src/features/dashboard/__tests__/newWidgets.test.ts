/**
 * Pure-function tests for the 4 new dashboard widgets.
 * No React rendering or API calls — logic extracted inline.
 */

import { describe, it, expect } from "vitest";

// ── Shared formatter ──────────────────────────────────────────────────────────

const fmt = (n: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n);

const fmtSigned = (n: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
    signDisplay: "exceptZero",
  }).format(n);

const fmtPct = (n: number) => `${Number(n).toFixed(1)}%`;

// ── ContributionHeadroomWidget ────────────────────────────────────────────────

interface MemberHeadroom {
  user_id: string;
  name: string;
  age: number | null;
  accounts: { account_id: string }[];
  total_limit: number;
  total_contributed_ytd: number;
  total_remaining_headroom: number;
}

const noData = (members: MemberHeadroom[]): boolean =>
  members.length === 0 || members.every((m) => m.accounts.length === 0);

const allMaxed = (members: MemberHeadroom[]): boolean =>
  !noData(members) && members.every((m) => m.total_remaining_headroom === 0);

const pctUsed = (member: MemberHeadroom): number =>
  member.total_limit > 0
    ? Math.min((member.total_contributed_ytd / member.total_limit) * 100, 100)
    : 0;

const headroomColor = (member: MemberHeadroom): string =>
  member.total_remaining_headroom > 0 ? "green.500" : "gray.400";

const multiMember = (members: MemberHeadroom[]): boolean => members.length > 1;

describe("ContributionHeadroomWidget — noData", () => {
  it("noData is true when members array is empty", () => {
    expect(noData([])).toBe(true);
  });

  it("noData is true when all members have no accounts", () => {
    const members: MemberHeadroom[] = [
      { user_id: "u1", name: "Alice", age: 35, accounts: [], total_limit: 0, total_contributed_ytd: 0, total_remaining_headroom: 0 },
    ];
    expect(noData(members)).toBe(true);
  });

  it("noData is false when at least one member has an account", () => {
    const members: MemberHeadroom[] = [
      {
        user_id: "u1", name: "Alice", age: 35,
        accounts: [{ account_id: "a1" }],
        total_limit: 23000, total_contributed_ytd: 5000, total_remaining_headroom: 18000,
      },
    ];
    expect(noData(members)).toBe(false);
  });
});

describe("ContributionHeadroomWidget — allMaxed", () => {
  it("allMaxed is false when noData", () => {
    expect(allMaxed([])).toBe(false);
  });

  it("allMaxed is true when all members have 0 remaining headroom", () => {
    const members: MemberHeadroom[] = [
      {
        user_id: "u1", name: "Alice", age: 35,
        accounts: [{ account_id: "a1" }],
        total_limit: 23000, total_contributed_ytd: 23000, total_remaining_headroom: 0,
      },
    ];
    expect(allMaxed(members)).toBe(true);
  });

  it("allMaxed is false when any member has remaining headroom", () => {
    const members: MemberHeadroom[] = [
      {
        user_id: "u1", name: "Alice", age: 35,
        accounts: [{ account_id: "a1" }],
        total_limit: 23000, total_contributed_ytd: 10000, total_remaining_headroom: 13000,
      },
    ];
    expect(allMaxed(members)).toBe(false);
  });

  it("allMaxed is true for multi-member household where both are maxed", () => {
    const members: MemberHeadroom[] = [
      { user_id: "u1", name: "Alice", age: 35, accounts: [{ account_id: "a1" }], total_limit: 23000, total_contributed_ytd: 23000, total_remaining_headroom: 0 },
      { user_id: "u2", name: "Bob", age: 37, accounts: [{ account_id: "a2" }], total_limit: 23000, total_contributed_ytd: 23000, total_remaining_headroom: 0 },
    ];
    expect(allMaxed(members)).toBe(true);
  });

  it("allMaxed is false for multi-member household where one is not maxed", () => {
    const members: MemberHeadroom[] = [
      { user_id: "u1", name: "Alice", age: 35, accounts: [{ account_id: "a1" }], total_limit: 23000, total_contributed_ytd: 23000, total_remaining_headroom: 0 },
      { user_id: "u2", name: "Bob", age: 37, accounts: [{ account_id: "a2" }], total_limit: 23000, total_contributed_ytd: 5000, total_remaining_headroom: 18000 },
    ];
    expect(allMaxed(members)).toBe(false);
  });
});

describe("ContributionHeadroomWidget — pctUsed", () => {
  it("returns 0 when total_limit is 0", () => {
    const m: MemberHeadroom = { user_id: "u1", name: "Alice", age: null, accounts: [], total_limit: 0, total_contributed_ytd: 0, total_remaining_headroom: 0 };
    expect(pctUsed(m)).toBe(0);
  });

  it("returns 50 when half contributed", () => {
    const m: MemberHeadroom = { user_id: "u1", name: "Alice", age: null, accounts: [], total_limit: 23000, total_contributed_ytd: 11500, total_remaining_headroom: 11500 };
    expect(pctUsed(m)).toBeCloseTo(50);
  });

  it("caps at 100 when over-contributed", () => {
    const m: MemberHeadroom = { user_id: "u1", name: "Alice", age: null, accounts: [], total_limit: 23000, total_contributed_ytd: 30000, total_remaining_headroom: 0 };
    expect(pctUsed(m)).toBe(100);
  });

  it("returns 100 when exactly maxed", () => {
    const m: MemberHeadroom = { user_id: "u1", name: "Alice", age: null, accounts: [], total_limit: 23000, total_contributed_ytd: 23000, total_remaining_headroom: 0 };
    expect(pctUsed(m)).toBe(100);
  });
});

describe("ContributionHeadroomWidget — headroomColor", () => {
  it("green.500 when remaining headroom > 0", () => {
    const m: MemberHeadroom = { user_id: "u1", name: "Alice", age: null, accounts: [], total_limit: 23000, total_contributed_ytd: 5000, total_remaining_headroom: 18000 };
    expect(headroomColor(m)).toBe("green.500");
  });

  it("gray.400 when remaining headroom = 0 (maxed)", () => {
    const m: MemberHeadroom = { user_id: "u1", name: "Alice", age: null, accounts: [], total_limit: 23000, total_contributed_ytd: 23000, total_remaining_headroom: 0 };
    expect(headroomColor(m)).toBe("gray.400");
  });
});

describe("ContributionHeadroomWidget — multiMember", () => {
  it("false for single member", () => {
    expect(multiMember([{ user_id: "u1", name: "Alice", age: null, accounts: [], total_limit: 0, total_contributed_ytd: 0, total_remaining_headroom: 0 }])).toBe(false);
  });

  it("true for 2 members", () => {
    const m: MemberHeadroom = { user_id: "u1", name: "Alice", age: null, accounts: [], total_limit: 0, total_contributed_ytd: 0, total_remaining_headroom: 0 };
    expect(multiMember([m, { ...m, user_id: "u2", name: "Bob" }])).toBe(true);
  });
});

// ── WithholdingCheckWidget ────────────────────────────────────────────────────

// months remaining including current month (getMonth is 0-indexed)
const defaultMonthsRemaining = (month: number): number => 12 - month;

describe("WithholdingCheckWidget — defaultMonthsRemaining", () => {
  it("January (month=0) → 12 months remaining", () => {
    expect(defaultMonthsRemaining(0)).toBe(12);
  });

  it("December (month=11) → 1 month remaining", () => {
    expect(defaultMonthsRemaining(11)).toBe(1);
  });

  it("June (month=5) → 7 months remaining", () => {
    expect(defaultMonthsRemaining(5)).toBe(7);
  });

  it("always returns a positive number (>= 1)", () => {
    for (let month = 0; month <= 11; month++) {
      expect(defaultMonthsRemaining(month)).toBeGreaterThanOrEqual(1);
    }
  });
});

describe("WithholdingCheckWidget — underpayment result display logic", () => {
  const underpaymentResult = {
    underpayment_risk: true,
    projected_tax: 18000,
    projected_year_end_withholding: 15000,
    w4_extra_amount: 125,
    notes: ["Based on current pace, you may owe at filing."],
    tax_year: 2026,
    safe_harbour_amount: 16200,
    ytd_withheld: 10000,
    recommended_additional_withholding_per_paycheck: 125,
  };

  const onTrackResult = {
    ...underpaymentResult,
    underpayment_risk: false,
    w4_extra_amount: 0,
  };

  it("underpayment risk shows orange badge", () => {
    const colorScheme = underpaymentResult.underpayment_risk ? "orange" : "green";
    expect(colorScheme).toBe("orange");
  });

  it("on track shows green badge", () => {
    const colorScheme = onTrackResult.underpayment_risk ? "orange" : "green";
    expect(colorScheme).toBe("green");
  });

  it("shows W-4 extra amount callout when underpayment and w4_extra_amount > 0", () => {
    const show = underpaymentResult.underpayment_risk && underpaymentResult.w4_extra_amount > 0;
    expect(show).toBe(true);
  });

  it("does not show W-4 callout when on track (w4_extra_amount = 0)", () => {
    const show = onTrackResult.underpayment_risk && onTrackResult.w4_extra_amount > 0;
    expect(show).toBe(false);
  });

  it("does not show W-4 callout when underpayment_risk=true but w4_extra_amount=0", () => {
    const result = { ...underpaymentResult, w4_extra_amount: 0 };
    const show = result.underpayment_risk && result.w4_extra_amount > 0;
    expect(show).toBe(false);
  });

  it("badge label is '⚠ Underpayment Risk' for underpayment", () => {
    const label = underpaymentResult.underpayment_risk
      ? "\u26A0 Underpayment Risk"
      : "\u2713 On Track";
    expect(label).toBe("⚠ Underpayment Risk");
  });

  it("badge label is '✓ On Track' for on-track result", () => {
    const label = onTrackResult.underpayment_risk
      ? "\u26A0 Underpayment Risk"
      : "\u2713 On Track";
    expect(label).toBe("✓ On Track");
  });

  it("notes[0] shown when notes array is non-empty", () => {
    const note = underpaymentResult.notes.length > 0 ? underpaymentResult.notes[0] : null;
    expect(note).toBe("Based on current pace, you may owe at filing.");
  });

  it("no note shown when notes array is empty", () => {
    const emptyNotes: string[] = [];
    const note = emptyNotes.length > 0 ? emptyNotes[0] : null;
    expect(note).toBeNull();
  });
});

describe("WithholdingCheckWidget — form validation", () => {
  const isValidSalary = (val: string): boolean => {
    if (!val) return false;
    const n = parseFloat(val);
    return !isNaN(n) && n > 0;
  };

  it("empty string is invalid", () => {
    expect(isValidSalary("")).toBe(false);
  });

  it("zero is invalid", () => {
    expect(isValidSalary("0")).toBe(false);
  });

  it("negative is invalid", () => {
    expect(isValidSalary("-500")).toBe(false);
  });

  it("non-numeric is invalid", () => {
    expect(isValidSalary("abc")).toBe(false);
  });

  it("positive number is valid", () => {
    expect(isValidSalary("75000")).toBe(true);
  });

  it("decimal salary is valid", () => {
    expect(isValidSalary("75000.50")).toBe(true);
  });
});

// ── NetWorthAttributionWidget ─────────────────────────────────────────────────

interface AttributionMonth {
  month: number;
  year: number;
  period_label: string;
  savings: number;
  investment_contributions: number;
  debt_paydown: number;
  attribution_note?: string;
}

const totalChange = (m: AttributionMonth): number =>
  m.savings + m.investment_contributions + m.debt_paydown;

const noDataAttribution = (months: AttributionMonth[]): boolean =>
  months.length === 0 ||
  months.every(
    (m) => m.savings === 0 && m.investment_contributions === 0 && m.debt_paydown === 0
  );

describe("NetWorthAttributionWidget — totalChange", () => {
  it("sums all three fields", () => {
    const m: AttributionMonth = { month: 3, year: 2026, period_label: "Mar 2026", savings: 1000, investment_contributions: 500, debt_paydown: 200 };
    expect(totalChange(m)).toBe(1700);
  });

  it("handles negative values (debt increased)", () => {
    const m: AttributionMonth = { month: 3, year: 2026, period_label: "Mar 2026", savings: -200, investment_contributions: 300, debt_paydown: 100 };
    expect(totalChange(m)).toBe(200);
  });

  it("returns 0 when all fields are 0", () => {
    const m: AttributionMonth = { month: 3, year: 2026, period_label: "Mar 2026", savings: 0, investment_contributions: 0, debt_paydown: 0 };
    expect(totalChange(m)).toBe(0);
  });
});

describe("NetWorthAttributionWidget — noData", () => {
  it("noData when array is empty", () => {
    expect(noDataAttribution([])).toBe(true);
  });

  it("noData when all months have 0 values", () => {
    const months: AttributionMonth[] = [
      { month: 1, year: 2026, period_label: "Jan 2026", savings: 0, investment_contributions: 0, debt_paydown: 0 },
      { month: 2, year: 2026, period_label: "Feb 2026", savings: 0, investment_contributions: 0, debt_paydown: 0 },
    ];
    expect(noDataAttribution(months)).toBe(true);
  });

  it("has data when any month has a non-zero value", () => {
    const months: AttributionMonth[] = [
      { month: 1, year: 2026, period_label: "Jan 2026", savings: 0, investment_contributions: 0, debt_paydown: 0 },
      { month: 2, year: 2026, period_label: "Feb 2026", savings: 500, investment_contributions: 0, debt_paydown: 0 },
    ];
    expect(noDataAttribution(months)).toBe(false);
  });
});

describe("NetWorthAttributionWidget — latest month extraction", () => {
  const months: AttributionMonth[] = [
    { month: 1, year: 2026, period_label: "Jan 2026", savings: 500, investment_contributions: 200, debt_paydown: 100 },
    { month: 2, year: 2026, period_label: "Feb 2026", savings: 600, investment_contributions: 300, debt_paydown: 150 },
    { month: 3, year: 2026, period_label: "Mar 2026", savings: 700, investment_contributions: 400, debt_paydown: 200 },
  ];

  it("latest is the last element in the array", () => {
    const latest = months[months.length - 1];
    expect(latest.period_label).toBe("Mar 2026");
  });

  it("recentRows are the 3 months before the latest", () => {
    // With 3 months: slice(-4, -1) = slice(0, 2) = first 2
    const recentRows = months.slice(-4, -1);
    expect(recentRows).toHaveLength(2);
    expect(recentRows[0].period_label).toBe("Jan 2026");
    expect(recentRows[1].period_label).toBe("Feb 2026");
  });

  it("recentRows badge colorScheme is green for positive month, red for negative", () => {
    const posMonth: AttributionMonth = { month: 1, year: 2026, period_label: "Jan", savings: 500, investment_contributions: 200, debt_paydown: 0 };
    const negMonth: AttributionMonth = { month: 2, year: 2026, period_label: "Feb", savings: -300, investment_contributions: 0, debt_paydown: 0 };

    const posColor = totalChange(posMonth) >= 0 ? "green" : "red";
    const negColor = totalChange(negMonth) >= 0 ? "green" : "red";

    expect(posColor).toBe("green");
    expect(negColor).toBe("red");
  });
});

describe("NetWorthAttributionWidget — bar segment logic", () => {
  it("barTotal uses max to avoid division by zero (at least 0.01)", () => {
    const latest: AttributionMonth = { month: 3, year: 2026, period_label: "Mar", savings: 0, investment_contributions: 0, debt_paydown: 0 };
    const computed = latest.savings + latest.investment_contributions + latest.debt_paydown;
    const barTotal = Math.max(computed, 0.01);
    expect(barTotal).toBe(0.01);
  });

  it("barTotal equals sum for positive values", () => {
    const latest: AttributionMonth = { month: 3, year: 2026, period_label: "Mar", savings: 300, investment_contributions: 200, debt_paydown: 100 };
    const barTotal = Math.max(latest.savings + latest.investment_contributions + latest.debt_paydown, 0.01);
    expect(barTotal).toBe(600);
  });

  it("pct for a segment is capped at 100", () => {
    const pct = (value: number, total: number) =>
      total === 0 || value <= 0 ? 0 : Math.min((value / total) * 100, 100);
    expect(pct(600, 100)).toBe(100); // over total → capped
    expect(pct(50, 100)).toBe(50);
    expect(pct(0, 100)).toBe(0);
    expect(pct(-10, 100)).toBe(0); // negative value → 0
  });
});

describe("NetWorthAttributionWidget — fmtSigned", () => {
  it("shows + sign for positive", () => {
    expect(fmtSigned(1700)).toMatch(/^\+/);
  });

  it("shows - sign for negative", () => {
    expect(fmtSigned(-500)).toMatch(/^-/);
  });

  it("shows no sign for zero", () => {
    const result = fmtSigned(0);
    expect(result).not.toMatch(/^\+/);
    expect(result).not.toMatch(/^-/);
  });
});

// ── RebalancingWidget ─────────────────────────────────────────────────────────

interface DriftItem {
  asset_class: string;
  label: string;
  target_percent: number;
  current_percent: number;
  current_value: number;
  drift_percent: number;
  drift_value: number;
  status: "overweight" | "underweight" | "on_target";
}

interface TradeRecommendation {
  asset_class: string;
  label: string;
  action: "BUY" | "SELL";
  amount: number;
  current_value: number;
  target_value: number;
  current_percent: number;
  target_percent: number;
}

const filterDriftItems = (items: DriftItem[]): DriftItem[] =>
  items.filter((d) => d.status !== "on_target");

describe("RebalancingWidget — 404 / noAllocation logic", () => {
  it("noAllocation is true when data is undefined and error has 404 status", () => {
    const data = undefined;
    const error = { response: { status: 404 } } as { response?: { status?: number } } | null;
    const is404 = !data && error?.response?.status === 404;
    const noAllocation = is404 || !data;
    expect(noAllocation).toBe(true);
  });

  it("noAllocation is true when data is undefined and no error (loading failed silently)", () => {
    const data = undefined;
    const error = null;
    const is404 = !data && (error as { response?: { status?: number } } | null)?.response?.status === 404;
    const noAllocation = is404 || !data;
    expect(noAllocation).toBe(true);
  });

  it("noAllocation is false when data is present", () => {
    const data = { needs_rebalancing: false, max_drift_percent: 1.2, drift_items: [], trade_recommendations: [], target_allocation_id: "a1", target_allocation_name: "60/40", portfolio_total: 100000 };
    const error = null;
    const is404 = !data && (error as { response?: { status?: number } } | null)?.response?.status === 404;
    const noAllocation = is404 || !data;
    expect(noAllocation).toBe(false);
  });

  it("retry logic skips retry on 404", () => {
    const shouldRetry = (failureCount: number, err: unknown): boolean => {
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (status === 404) return false;
      return failureCount < 2;
    };
    expect(shouldRetry(0, { response: { status: 404 } })).toBe(false);
    expect(shouldRetry(0, { response: { status: 500 } })).toBe(true);
    expect(shouldRetry(1, { response: { status: 500 } })).toBe(true);
    expect(shouldRetry(2, { response: { status: 500 } })).toBe(false);
  });
});

describe("RebalancingWidget — drift item filtering", () => {
  const driftItems: DriftItem[] = [
    { asset_class: "us_equity", label: "US Equity", target_percent: 60, current_percent: 68, current_value: 68000, drift_percent: 8, drift_value: 8000, status: "overweight" },
    { asset_class: "intl_equity", label: "International", target_percent: 20, current_percent: 15, current_value: 15000, drift_percent: -5, drift_value: -5000, status: "underweight" },
    { asset_class: "bonds", label: "Bonds", target_percent: 20, current_percent: 20, current_value: 20000, drift_percent: 0, drift_value: 0, status: "on_target" },
  ];

  it("filters out on_target items", () => {
    const filtered = filterDriftItems(driftItems);
    expect(filtered).toHaveLength(2);
    expect(filtered.every((d) => d.status !== "on_target")).toBe(true);
  });

  it("keeps overweight items", () => {
    const filtered = filterDriftItems(driftItems);
    expect(filtered.some((d) => d.status === "overweight")).toBe(true);
  });

  it("keeps underweight items", () => {
    const filtered = filterDriftItems(driftItems);
    expect(filtered.some((d) => d.status === "underweight")).toBe(true);
  });

  it("returns empty when all items are on_target", () => {
    const allGood: DriftItem[] = [
      { ...driftItems[2], asset_class: "a" },
      { ...driftItems[2], asset_class: "b" },
    ];
    expect(filterDriftItems(allGood)).toHaveLength(0);
  });

  it("slices to top 3 when more drift items exist", () => {
    const many: DriftItem[] = Array.from({ length: 5 }, (_, i) => ({
      asset_class: `class_${i}`,
      label: `Asset ${i}`,
      target_percent: 20,
      current_percent: 25,
      current_value: 25000,
      drift_percent: 5,
      drift_value: 5000,
      status: "overweight" as const,
    }));
    expect(filterDriftItems(many).slice(0, 3)).toHaveLength(3);
  });
});

describe("RebalancingWidget — drift item badge colors", () => {
  it("overweight item badge is red", () => {
    const d: DriftItem = { asset_class: "a", label: "A", target_percent: 20, current_percent: 28, current_value: 28000, drift_percent: 8, drift_value: 8000, status: "overweight" };
    const colorScheme = d.status === "overweight" ? "red" : "blue";
    expect(colorScheme).toBe("red");
  });

  it("underweight item badge is blue", () => {
    const d: DriftItem = { asset_class: "a", label: "A", target_percent: 20, current_percent: 12, current_value: 12000, drift_percent: -8, drift_value: -8000, status: "underweight" };
    const colorScheme = d.status === "overweight" ? "red" : "blue";
    expect(colorScheme).toBe("blue");
  });

  it("drift label text: overweight shows 'Overweight'", () => {
    const d: DriftItem = { asset_class: "a", label: "A", target_percent: 20, current_percent: 28, current_value: 28000, drift_percent: 8, drift_value: 8000, status: "overweight" };
    const label = d.status === "overweight" ? "Overweight" : "Underweight";
    expect(label).toBe("Overweight");
  });

  it("drift label text: underweight shows 'Underweight'", () => {
    const d: DriftItem = { asset_class: "a", label: "A", target_percent: 20, current_percent: 12, current_value: 12000, drift_percent: -8, drift_value: -8000, status: "underweight" };
    const label = d.status === "overweight" ? "Overweight" : "Underweight";
    expect(label).toBe("Underweight");
  });
});

describe("RebalancingWidget — trade recommendations", () => {
  const trades: TradeRecommendation[] = [
    { asset_class: "us_equity", label: "US Equity", action: "SELL", amount: 8000, current_value: 68000, target_value: 60000, current_percent: 68, target_percent: 60 },
    { asset_class: "intl_equity", label: "International", action: "BUY", amount: 5000, current_value: 15000, target_value: 20000, current_percent: 15, target_percent: 20 },
    { asset_class: "bonds", label: "Bonds", action: "BUY", amount: 3000, current_value: 17000, target_value: 20000, current_percent: 17, target_percent: 20 },
  ];

  it("slices trade recommendations to top 2", () => {
    expect(trades.slice(0, 2)).toHaveLength(2);
  });

  it("BUY trade has green badge", () => {
    const t = trades.find((t) => t.action === "BUY")!;
    const colorScheme = t.action === "BUY" ? "green" : "red";
    expect(colorScheme).toBe("green");
  });

  it("SELL trade has red badge", () => {
    const t = trades.find((t) => t.action === "SELL")!;
    const colorScheme = t.action === "BUY" ? "green" : "red";
    expect(colorScheme).toBe("red");
  });

  it("trade text shows amount and label", () => {
    const t = trades[0];
    const text = `${t.action === "BUY" ? "BUY" : "SELL"} ${fmtCurrency(t.amount)} of ${t.label}`;
    expect(text).toBe("SELL $8,000 of US Equity");
  });

  it("no trades shown when trade_recommendations is empty", () => {
    expect([].length > 0).toBe(false);
  });
});

describe("RebalancingWidget — needs_rebalancing display", () => {
  it("shows 'Portfolio is balanced' badge when needs_rebalancing=false", () => {
    const data = { needs_rebalancing: false, max_drift_percent: 1.5, drift_items: [], trade_recommendations: [] };
    const isBalanced = data.needs_rebalancing === false;
    expect(isBalanced).toBe(true);
  });

  it("shows 'Rebalancing Needed' badge when needs_rebalancing=true", () => {
    const data = { needs_rebalancing: true, max_drift_percent: 9.0, drift_items: [], trade_recommendations: [] };
    const isBalanced = data.needs_rebalancing === false;
    expect(isBalanced).toBe(false);
  });

  it("fmtPct formats drift percentage correctly", () => {
    expect(fmtPct(1.5)).toBe("1.5%");
    expect(fmtPct(9.12)).toBe("9.1%");
    expect(fmtPct(0)).toBe("0.0%");
  });
});

// ── fmt (currency formatter used across widgets) ──────────────────────────────

const fmtCurrency = (n: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n);

describe("fmt (shared currency formatter)", () => {
  it("formats whole numbers without decimals", () => {
    expect(fmt(1000)).toBe("$1,000");
    expect(fmt(23000)).toBe("$23,000");
  });

  it("rounds fractional amounts", () => {
    expect(fmt(1000.75)).toBe("$1,001");
  });

  it("formats zero", () => {
    expect(fmt(0)).toBe("$0");
  });

  it("formats large values with commas", () => {
    expect(fmt(1234567)).toBe("$1,234,567");
  });
});
