/**
 * Tests for EducationPlanningPage logic: funding percentage colors,
 * progress bar capping, college type labels, and totals aggregation.
 */

import { describe, it, expect } from "vitest";

// ── Logic helpers (mirrored from EducationPlanningPage.tsx) ──────────────────

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);

const COLLEGE_TYPE_LABELS: Record<string, string> = {
  public_in_state: "Public (In-State)",
  public_out_of_state: "Public (Out-of-State)",
  private: "Private",
};

function progressColor(fundingPct: number): string {
  if (fundingPct >= 100) return "green";
  if (fundingPct >= 60) return "yellow";
  return "red";
}

function progressValue(fundingPct: number): number {
  return Math.min(fundingPct, 100);
}

function hasStripe(fundingPct: number): boolean {
  return fundingPct < 100;
}

function annualReturnToDecimal(annualReturn: number): number {
  return annualReturn / 100;
}

// ── Types ────────────────────────────────────────────────────────────────────

interface Plan {
  account_id: string;
  account_name: string;
  current_balance: number;
  monthly_contribution: number;
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe("progressColor", () => {
  it("returns green when fully funded (>= 100%)", () => {
    expect(progressColor(100)).toBe("green");
    expect(progressColor(150)).toBe("green");
  });

  it("returns yellow when between 60-99%", () => {
    expect(progressColor(60)).toBe("yellow");
    expect(progressColor(80)).toBe("yellow");
    expect(progressColor(99.9)).toBe("yellow");
  });

  it("returns red when under 60%", () => {
    expect(progressColor(0)).toBe("red");
    expect(progressColor(30)).toBe("red");
    expect(progressColor(59.9)).toBe("red");
  });
});

describe("progressValue", () => {
  it("caps at 100 for overfunded plans", () => {
    expect(progressValue(150)).toBe(100);
    expect(progressValue(200)).toBe(100);
  });

  it("passes through values under 100", () => {
    expect(progressValue(50)).toBe(50);
    expect(progressValue(0)).toBe(0);
  });

  it("returns exactly 100 at boundary", () => {
    expect(progressValue(100)).toBe(100);
  });
});

describe("hasStripe", () => {
  it("shows stripe animation when not fully funded", () => {
    expect(hasStripe(50)).toBe(true);
    expect(hasStripe(99)).toBe(true);
  });

  it("no stripe when fully funded", () => {
    expect(hasStripe(100)).toBe(false);
    expect(hasStripe(120)).toBe(false);
  });
});

describe("COLLEGE_TYPE_LABELS", () => {
  it("maps all college type keys", () => {
    expect(COLLEGE_TYPE_LABELS["public_in_state"]).toBe("Public (In-State)");
    expect(COLLEGE_TYPE_LABELS["public_out_of_state"]).toBe(
      "Public (Out-of-State)",
    );
    expect(COLLEGE_TYPE_LABELS["private"]).toBe("Private");
  });

  it("has exactly 3 college types", () => {
    expect(Object.keys(COLLEGE_TYPE_LABELS)).toHaveLength(3);
  });
});

describe("annualReturnToDecimal", () => {
  it("converts UI percentage to API decimal", () => {
    expect(annualReturnToDecimal(6)).toBeCloseTo(0.06);
    expect(annualReturnToDecimal(7.5)).toBeCloseTo(0.075);
  });

  it("handles zero", () => {
    expect(annualReturnToDecimal(0)).toBe(0);
  });
});

describe("Total savings aggregation", () => {
  const plans: Plan[] = [
    {
      account_id: "a1",
      account_name: "Child 1",
      current_balance: 25000,
      monthly_contribution: 200,
    },
    {
      account_id: "a2",
      account_name: "Child 2",
      current_balance: 15000,
      monthly_contribution: 300,
    },
  ];

  it("sums total monthly contributions", () => {
    const total = plans.reduce((sum, p) => sum + p.monthly_contribution, 0);
    expect(total).toBe(500);
  });

  it("handles empty plans array", () => {
    const total = ([] as Plan[]).reduce(
      (sum, p) => sum + p.monthly_contribution,
      0,
    );
    expect(total).toBe(0);
  });
});

describe("Account count label", () => {
  it("uses singular for 1 account", () => {
    const count = 1;
    const label = count === 1 ? "account" : "accounts";
    expect(label).toBe("account");
  });

  it("uses plural for multiple accounts", () => {
    const count = 3;
    const label = count === 1 ? "account" : "accounts";
    expect(label).toBe("accounts");
  });
});

describe("Funding gap vs surplus display", () => {
  it("shows gap when funding_gap > 0", () => {
    const projection = { funding_gap: 20000, funding_surplus: 0 };
    const showGap = projection.funding_gap > 0;
    expect(showGap).toBe(true);
  });

  it("shows surplus when funding_gap is 0", () => {
    const projection = { funding_gap: 0, funding_surplus: 15000 };
    const showGap = projection.funding_gap > 0;
    expect(showGap).toBe(false);
  });
});

describe("formatCurrency", () => {
  it("formats education costs", () => {
    expect(formatCurrency(120000)).toBe("$120,000");
    expect(formatCurrency(0)).toBe("$0");
  });
});

describe("Query enabled guard", () => {
  it("disables query when yearsUntilCollege < 1", () => {
    const yearsUntilCollege = 0;
    expect(yearsUntilCollege >= 1).toBe(false);
  });

  it("enables query when yearsUntilCollege >= 1", () => {
    const yearsUntilCollege = 1;
    expect(yearsUntilCollege >= 1).toBe(true);
  });
});
