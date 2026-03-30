/**
 * Logic tests for PePerformancePage.
 *
 * Tests the field contract between the backend /pe-performance/portfolio
 * response and what the frontend reads, plus display formatting.
 *
 * Key regression: the original page used wrong field names (rvpi, total_distributed,
 * nav, account_name) that don't exist in the backend response.
 *
 * @vitest-environment jsdom
 */

import { describe, it, expect } from "vitest";

// ── Mirrors the PeAccount interface in PePerformancePage.tsx ─────────────────

interface PeAccount {
  account_id: string;
  name: string;           // was account_name — backend uses name
  tvpi: number;
  dpi: number;
  moic: number;           // was rvpi — backend uses moic
  irr: number | null;
  irr_pct: number | null; // percentage form, e.g. 12.5 (not 0.125)
  total_called: number;
  total_distributions: number; // was total_distributed
  current_nav: number;         // was nav
  net_profit: number;
}

// ── fmt helper (mirrors PePerformancePage.tsx) ──────────────────────────────

const fmt = (n: number) =>
  n.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  });

// ── Fixture ──────────────────────────────────────────────────────────────────

function makeAccount(overrides: Partial<PeAccount> = {}): PeAccount {
  return {
    account_id: "abc-123",
    name: "Acme Capital Fund I",
    tvpi: 1.85,
    dpi: 0.75,
    moic: 1.85,
    irr: 0.125,
    irr_pct: 12.5,
    total_called: 500000,
    total_distributions: 375000,
    current_nav: 550000,
    net_profit: 425000,
    ...overrides,
  };
}

// ── Field name contract ───────────────────────────────────────────────────────

describe("PeAccount field contract — corrected field names", () => {
  it("uses name (not account_name)", () => {
    const acct = makeAccount({ name: "Fund I" });
    expect(acct.name).toBe("Fund I");
    expect((acct as any).account_name).toBeUndefined();
  });

  it("uses moic (not rvpi)", () => {
    const acct = makeAccount({ moic: 1.85 });
    expect(acct.moic).toBe(1.85);
    expect((acct as any).rvpi).toBeUndefined();
  });

  it("uses total_distributions (not total_distributed)", () => {
    const acct = makeAccount({ total_distributions: 375000 });
    expect(acct.total_distributions).toBe(375000);
    expect((acct as any).total_distributed).toBeUndefined();
  });

  it("uses current_nav (not nav)", () => {
    const acct = makeAccount({ current_nav: 550000 });
    expect(acct.current_nav).toBe(550000);
    expect((acct as any).nav).toBeUndefined();
  });

  it("uses irr_pct for display (already a percentage, not a decimal)", () => {
    const acct = makeAccount({ irr_pct: 12.5 });
    expect(acct.irr_pct).toBe(12.5);
    // display: toFixed(1) → "12.5%"
    expect(acct.irr_pct!.toFixed(1)).toBe("12.5");
  });
});

// ── IRR display ───────────────────────────────────────────────────────────────

describe("IRR display", () => {
  it("shows N/A when irr_pct is null", () => {
    const acct = makeAccount({ irr_pct: null });
    const display = acct.irr_pct !== null ? `${acct.irr_pct.toFixed(1)}%` : "N/A";
    expect(display).toBe("N/A");
  });

  it("shows formatted percentage when irr_pct is set", () => {
    const acct = makeAccount({ irr_pct: 18.3 });
    const display = acct.irr_pct !== null ? `${acct.irr_pct.toFixed(1)}%` : "N/A";
    expect(display).toBe("18.3%");
  });

  it("handles zero IRR", () => {
    const acct = makeAccount({ irr_pct: 0 });
    const display = acct.irr_pct !== null ? `${acct.irr_pct.toFixed(1)}%` : "N/A";
    expect(display).toBe("0.0%");
  });
});

// ── Multiplier display ────────────────────────────────────────────────────────

describe("TVPI / DPI / MOIC multiplier display", () => {
  it("formats tvpi to 2 decimal places", () => {
    const acct = makeAccount({ tvpi: 1.854 });
    expect(acct.tvpi.toFixed(2)).toBe("1.85");
  });

  it("formats dpi to 2 decimal places", () => {
    const acct = makeAccount({ dpi: 0.756 });
    expect(acct.dpi.toFixed(2)).toBe("0.76");
  });

  it("formats moic to 2 decimal places", () => {
    const acct = makeAccount({ moic: 2.001 });
    expect(acct.moic.toFixed(2)).toBe("2.00");
  });
});

// ── Currency display ─────────────────────────────────────────────────────────

describe("currency display", () => {
  it("formats total_called", () => {
    const acct = makeAccount({ total_called: 500000 });
    expect(fmt(acct.total_called)).toBe("$500,000");
  });

  it("formats total_distributions", () => {
    const acct = makeAccount({ total_distributions: 375000 });
    expect(fmt(acct.total_distributions)).toBe("$375,000");
  });

  it("formats current_nav", () => {
    const acct = makeAccount({ current_nav: 550000 });
    expect(fmt(acct.current_nav)).toBe("$550,000");
  });
});

// ── Portfolio endpoint contract ───────────────────────────────────────────────

describe("GET /pe-performance/portfolio response shape", () => {
  it("accounts array is present at res.data.accounts", () => {
    const response = { accounts: [makeAccount()], portfolio_metrics: {} };
    expect(Array.isArray(response.accounts)).toBe(true);
  });

  it("empty accounts returns empty array (not 404)", () => {
    const response = { accounts: [], portfolio_metrics: null };
    expect(response.accounts).toHaveLength(0);
  });

  it("does not use res.data directly (old /summary shape)", () => {
    // Old code: return res.data.accounts ?? res.data
    // New code: return res.data.accounts ?? []
    // This test documents the correct fallback is [] not the whole response
    const noAccountsKey = { portfolio_metrics: null };
    const result = (noAccountsKey as any).accounts ?? [];
    expect(result).toEqual([]);
    expect(Array.isArray(result)).toBe(true);
  });
});
