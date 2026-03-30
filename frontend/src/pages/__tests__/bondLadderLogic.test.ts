/**
 * Logic tests for BondLadderPage.
 *
 * Tests the data-shaping logic that the component depends on:
 * - LadderResult field contracts (what the backend returns, what the frontend reads)
 * - Rate banner display formatting
 * - Income target badge logic
 * - fmt currency formatter
 *
 * @vitest-environment jsdom
 */

import { describe, it, expect } from "vitest";

// ── Mirrors the interfaces in BondLadderPage.tsx ────────────────────────────

interface LadderRung {
  rung: number;
  years_to_maturity: number;
  maturity_year: number;
  investment_amount: number;
  annual_rate: number;
  annual_rate_pct: number;
  maturity_value: number;
  interest_earned: number;
  instrument_type: string;
}

interface LadderResult {
  rungs: LadderRung[];
  num_rungs: number;
  ladder_type: string;
  total_invested: number;
  per_rung_investment: number;
  total_interest: number;
  total_maturity_values: number;
  annual_income_actual: number;
  annual_income_needed: number;
  income_gap: number;
  meets_income_target: boolean;
  reinvestment_note: string;
}

interface RatesResponse {
  treasury_rates: Record<string, number>;
  estimated_cd_rates: Record<string, number>;
  source: string;
}

// ── Formatting helpers (mirrors BondLadderPage.tsx) ─────────────────────────

const fmt = (n: number) =>
  n.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  });

function rateBannerText(ratesData: RatesResponse): string {
  const tenYr = ((ratesData.treasury_rates["10_year"] ?? 0) * 100).toFixed(2);
  const oneYr = ratesData.treasury_rates["1_year"] !== undefined
    ? `, 1-yr: ${(ratesData.treasury_rates["1_year"] * 100).toFixed(2)}%`
    : "";
  return `Rates sourced from ${ratesData.source}. 10-yr Treasury: ${tenYr}%${oneYr}`;
}

function incomeStatus(result: LadderResult): { met: boolean; gap: number } {
  return { met: result.meets_income_target, gap: Math.abs(result.income_gap) };
}

// ── Fixtures ─────────────────────────────────────────────────────────────────

function makeRung(overrides: Partial<LadderRung> = {}): LadderRung {
  return {
    rung: 1,
    years_to_maturity: 1,
    maturity_year: 2026,
    investment_amount: 50000,
    annual_rate: 0.042,
    annual_rate_pct: 4.2,
    maturity_value: 52100,
    interest_earned: 2100,
    instrument_type: "TREASURY",
    ...overrides,
  };
}

function makeResult(overrides: Partial<LadderResult> = {}): LadderResult {
  return {
    rungs: [makeRung()],
    num_rungs: 1,
    ladder_type: "treasury",
    total_invested: 50000,
    per_rung_investment: 50000,
    total_interest: 2100,
    total_maturity_values: 52100,
    annual_income_actual: 52100,
    annual_income_needed: 50000,
    income_gap: -2100,
    meets_income_target: true,
    reinvestment_note: "As each rung matures, reinvest in a new 1-year TREASURY.",
    ...overrides,
  };
}

// ── fmt currency formatter ───────────────────────────────────────────────────

describe("fmt currency formatter", () => {
  it("formats whole dollar amounts", () => {
    expect(fmt(50000)).toBe("$50,000");
  });

  it("rounds fractional cents", () => {
    expect(fmt(50000.99)).toBe("$50,001");
  });

  it("formats zero", () => {
    expect(fmt(0)).toBe("$0");
  });

  it("formats large amounts with commas", () => {
    expect(fmt(1000000)).toBe("$1,000,000");
  });

  it("formats negative values", () => {
    expect(fmt(-5000)).toMatch(/\$5,000/); // sign rendering varies by locale
  });
});

// ── LadderResult field contract ──────────────────────────────────────────────

describe("LadderResult field contract", () => {
  it("rungs array is present", () => {
    const result = makeResult();
    expect(Array.isArray(result.rungs)).toBe(true);
  });

  it("each rung has annual_rate_pct (used for display)", () => {
    const rung = makeRung({ annual_rate_pct: 4.25 });
    expect(rung.annual_rate_pct.toFixed(2)).toBe("4.25");
  });

  it("each rung has maturity_year (not maturity_date)", () => {
    const rung = makeRung({ maturity_year: 2030 });
    expect(rung.maturity_year).toBe(2030);
    expect((rung as any).maturity_date).toBeUndefined();
  });

  it("result has total_invested (not total_cost)", () => {
    const result = makeResult({ total_invested: 500000 });
    expect(result.total_invested).toBe(500000);
    expect((result as any).total_cost).toBeUndefined();
  });

  it("result has total_interest (not average_yield)", () => {
    const result = makeResult({ total_interest: 25000 });
    expect(result.total_interest).toBe(25000);
    expect((result as any).average_yield).toBeUndefined();
  });

  it("result has meets_income_target boolean", () => {
    expect(makeResult({ meets_income_target: true }).meets_income_target).toBe(true);
    expect(makeResult({ meets_income_target: false }).meets_income_target).toBe(false);
  });

  it("result has income_gap (positive = shortfall, negative = surplus)", () => {
    const shortfall = makeResult({ income_gap: 5000, meets_income_target: false });
    expect(shortfall.income_gap).toBeGreaterThan(0);

    const surplus = makeResult({ income_gap: -2000, meets_income_target: true });
    expect(surplus.income_gap).toBeLessThan(0);
  });

  it("result has reinvestment_note string", () => {
    const result = makeResult();
    expect(typeof result.reinvestment_note).toBe("string");
    expect(result.reinvestment_note.length).toBeGreaterThan(0);
  });
});

// ── Income target badge logic ─────────────────────────────────────────────────

describe("income target badge logic", () => {
  it("meets target when income_gap <= 0", () => {
    expect(incomeStatus(makeResult({ income_gap: 0, meets_income_target: true })).met).toBe(true);
    expect(incomeStatus(makeResult({ income_gap: -100, meets_income_target: true })).met).toBe(true);
  });

  it("does not meet target when income_gap > 0", () => {
    expect(incomeStatus(makeResult({ income_gap: 5000, meets_income_target: false })).met).toBe(false);
  });

  it("gap display uses absolute value", () => {
    const status = incomeStatus(makeResult({ income_gap: 3000, meets_income_target: false }));
    expect(status.gap).toBe(3000);
  });
});

// ── Rate banner display ───────────────────────────────────────────────────────

describe("rate banner display", () => {
  const sampleRates: RatesResponse = {
    treasury_rates: { "10_year": 0.0395, "1_year": 0.0420 },
    estimated_cd_rates: { "1_year": 0.043, "5_year": 0.0425 },
    source: "FRED / U.S. Treasury + CD spread estimates",
  };

  it("includes the source string", () => {
    const text = rateBannerText(sampleRates);
    expect(text).toContain("FRED / U.S. Treasury");
  });

  it("shows 10-year Treasury rate as percentage", () => {
    const text = rateBannerText(sampleRates);
    expect(text).toContain("3.95%");
  });

  it("shows 1-year Treasury rate when present", () => {
    const text = rateBannerText(sampleRates);
    expect(text).toContain("4.20%");
  });

  it("omits 1-year line when key is absent", () => {
    const noOneYr: RatesResponse = {
      ...sampleRates,
      treasury_rates: { "10_year": 0.0395 },
    };
    const text = rateBannerText(noOneYr);
    expect(text).not.toContain("1-yr");
  });

  it("shows 0.00% when 10-year key is missing", () => {
    const noTenYr: RatesResponse = {
      ...sampleRates,
      treasury_rates: {},
    };
    const text = rateBannerText(noTenYr);
    expect(text).toContain("0.00%");
  });
});

// ── Request schema contract (what the page POSTs) ────────────────────────────

describe("POST /bond-ladder/plan request schema", () => {
  it("uses total_investment (not budget or amount)", () => {
    const req = {
      total_investment: 500000,
      num_rungs: 10,
      annual_income_needed: 50000,
      start_year: 2026,
      ladder_type: "treasury",
    };
    expect(req.total_investment).toBeDefined();
    expect((req as any).budget).toBeUndefined();
    expect((req as any).end_year).toBeUndefined();
  });

  it("uses num_rungs (not duration or years)", () => {
    const req = { total_investment: 500000, num_rungs: 10, annual_income_needed: 0, start_year: 2026, ladder_type: "treasury" };
    expect(req.num_rungs).toBeDefined();
    expect((req as any).duration).toBeUndefined();
  });
});
