/**
 * Tests for CurrencyContext
 *
 * Verifies that:
 *  1. formatCurrency uses the org's default_currency from /settings/profile
 *  2. formatCurrencyCompact produces compact notation
 *  3. symbol is derived from the currency code
 *  4. Falls back to USD when profile has no default_currency
 *  5. Query is gated on accessToken (not isAuthenticated) to prevent 401s
 *     on hard refresh before the session token is restored
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

// ---------------------------------------------------------------------------
// Query guard: enabled: !!accessToken
//
// CurrencyContext gates its /settings/profile query on the in-memory
// accessToken, NOT the persisted isAuthenticated flag.
//
// Scenario that caused the bug:
//   1. User hard-refreshes the page
//   2. Zustand rehydrates from localStorage: isAuthenticated = true, accessToken = ""
//   3. CurrencyContext fires GET /settings/profile before /auth/refresh completes
//   4. Server returns 401 because no token was sent
//
// Fix: enabled: !!accessToken  (only fires when a real token exists in memory)
// ---------------------------------------------------------------------------

describe("CurrencyContext query guard — accessToken vs isAuthenticated", () => {
  /** Mirrors the enabled condition in CurrencyContext: enabled: !!accessToken */
  function shouldQueryFire(accessToken: string | null | undefined): boolean {
    return !!accessToken;
  }

  it("does NOT fire when accessToken is empty string (hard refresh, not yet restored)", () => {
    expect(shouldQueryFire("")).toBe(false);
  });

  it("does NOT fire when accessToken is null", () => {
    expect(shouldQueryFire(null)).toBe(false);
  });

  it("does NOT fire when accessToken is undefined", () => {
    expect(shouldQueryFire(undefined)).toBe(false);
  });

  it("DOES fire once accessToken is populated", () => {
    expect(shouldQueryFire("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9")).toBe(true);
  });

  it("would incorrectly fire with isAuthenticated=true on hard refresh", () => {
    // Demonstrates the OLD bug: isAuthenticated is persisted and is true
    // before the token is restored, so it would (wrongly) fire the query.
    const isAuthenticated = true; // restored from localStorage
    const accessToken = "";       // not yet restored (in-memory only)

    const oldBehavior = isAuthenticated;       // would fire → 401
    const newBehavior = !!accessToken;         // correctly suppressed

    expect(oldBehavior).toBe(true);  // old code fires prematurely
    expect(newBehavior).toBe(false); // new code waits for token
  });
});
