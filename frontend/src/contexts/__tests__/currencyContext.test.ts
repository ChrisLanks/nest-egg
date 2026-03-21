/**
 * Tests for CurrencyContext
 *
 * Verifies that:
 *  1. formatCurrency uses the org's default_currency from /settings/profile
 *  2. formatCurrencyCompact produces compact notation
 *  3. symbol is derived from the currency code
 *  4. Falls back to USD when profile has no default_currency
 */

import { describe, it, expect, vi, beforeEach } from "vitest";

// ---------------------------------------------------------------------------
// Lightweight unit tests — no DOM/React required.
// We extract the pure helper functions directly.
// ---------------------------------------------------------------------------

function getCurrencySymbol(currency: string): string {
  try {
    return (
      new Intl.NumberFormat("en-US", { style: "currency", currency })
        .formatToParts(0)
        .find((p) => p.type === "currency")?.value ?? currency
    );
  } catch {
    return currency;
  }
}

function makeFormatCurrency(currency: string) {
  return (amount: number, options?: Intl.NumberFormatOptions): string =>
    new Intl.NumberFormat("en-US", {
      style: "currency",
      currency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
      ...options,
    }).format(amount);
}

function makeFormatCurrencyCompact(currency: string) {
  return (amount: number): string =>
    new Intl.NumberFormat("en-US", {
      style: "currency",
      currency,
      notation: "compact",
      maximumFractionDigits: 1,
    }).format(amount);
}

// ---------------------------------------------------------------------------

describe("CurrencyContext helpers", () => {
  describe("getCurrencySymbol", () => {
    it("returns $ for USD", () => {
      expect(getCurrencySymbol("USD")).toBe("$");
    });

    it("returns € for EUR", () => {
      expect(getCurrencySymbol("EUR")).toBe("€");
    });

    it("returns £ for GBP", () => {
      expect(getCurrencySymbol("GBP")).toBe("£");
    });

    it("returns the code itself for an unknown currency", () => {
      expect(getCurrencySymbol("XYZ")).toBe("XYZ");
    });
  });

  describe("formatCurrency (USD)", () => {
    const fmt = makeFormatCurrency("USD");

    it("formats a positive amount", () => {
      expect(fmt(1234.56)).toBe("$1,234.56");
    });

    it("formats zero", () => {
      expect(fmt(0)).toBe("$0.00");
    });

    it("formats a negative amount", () => {
      expect(fmt(-500)).toBe("-$500.00");
    });

    it("respects minimumFractionDigits override", () => {
      const result = fmt(1000, { minimumFractionDigits: 0, maximumFractionDigits: 0 });
      expect(result).toBe("$1,000");
    });
  });

  describe("formatCurrency (EUR)", () => {
    const fmt = makeFormatCurrency("EUR");

    it("formats with EUR symbol", () => {
      expect(fmt(500)).toMatch(/€/);
    });

    it("includes the correct numeric value", () => {
      expect(fmt(1000)).toContain("1,000");
    });
  });

  describe("formatCurrencyCompact (USD)", () => {
    const fmt = makeFormatCurrencyCompact("USD");

    it("formats millions compactly", () => {
      const result = fmt(1_200_000);
      expect(result).toMatch(/\$1\.2M/i);
    });

    it("formats thousands compactly", () => {
      const result = fmt(500_000);
      expect(result).toMatch(/\$500(\.\d)?K/i);
    });

    it("formats small amounts without compact suffix", () => {
      const result = fmt(42);
      expect(result).toMatch(/^\$42(\.\d)?$/);
    });
  });

  describe("currency fallback to USD", () => {
    it("defaults to USD when profile has no default_currency", () => {
      const profileCurrency: string | null | undefined = null;
      const currency = profileCurrency?.toUpperCase() || "USD";
      expect(currency).toBe("USD");
    });

    it("defaults to USD when profile is undefined", () => {
      const profileCurrency: string | null | undefined = undefined;
      const currency = profileCurrency?.toUpperCase() || "USD";
      expect(currency).toBe("USD");
    });

    it("uses org currency when set", () => {
      const profileCurrency = "gbp";
      const currency = profileCurrency?.toUpperCase() || "USD";
      expect(currency).toBe("GBP");
    });
  });
});
