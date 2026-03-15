/**
 * Tests for bank provider auto-selection logic.
 *
 * When exactly one bank sync provider is enabled, the SourceSelectionStep
 * should auto-select it (skipping the provider selection UI).
 */

import { describe, it, expect } from "vitest";

type AccountSource = "plaid" | "teller" | "mx";

interface ProviderAvailability {
  plaid: boolean;
  teller: boolean;
  mx: boolean;
}

/**
 * Mirrors the auto-selection logic from SourceSelectionStep.tsx
 */
function getAutoSelectProvider(
  availability: ProviderAvailability | undefined,
  isLoading: boolean,
  skipAutoSelect: boolean,
): AccountSource | null {
  if (skipAutoSelect || isLoading || !availability) return null;

  const enabled: AccountSource[] = [];
  if (availability.plaid) enabled.push("plaid");
  if (availability.teller) enabled.push("teller");
  if (availability.mx) enabled.push("mx");

  if (enabled.length === 1) return enabled[0];
  return null;
}

// ── Auto-selection ───────────────────────────────────────────────────────────

describe("provider auto-selection", () => {
  it("auto-selects plaid when only plaid is enabled", () => {
    const result = getAutoSelectProvider(
      { plaid: true, teller: false, mx: false },
      false,
      false,
    );
    expect(result).toBe("plaid");
  });

  it("auto-selects teller when only teller is enabled", () => {
    const result = getAutoSelectProvider(
      { plaid: false, teller: true, mx: false },
      false,
      false,
    );
    expect(result).toBe("teller");
  });

  it("auto-selects mx when only mx is enabled", () => {
    const result = getAutoSelectProvider(
      { plaid: false, teller: false, mx: true },
      false,
      false,
    );
    expect(result).toBe("mx");
  });

  it("does NOT auto-select when multiple providers are enabled", () => {
    const result = getAutoSelectProvider(
      { plaid: true, teller: true, mx: false },
      false,
      false,
    );
    expect(result).toBeNull();
  });

  it("does NOT auto-select when all three providers are enabled", () => {
    const result = getAutoSelectProvider(
      { plaid: true, teller: true, mx: true },
      false,
      false,
    );
    expect(result).toBeNull();
  });

  it("does NOT auto-select when no providers are enabled", () => {
    const result = getAutoSelectProvider(
      { plaid: false, teller: false, mx: false },
      false,
      false,
    );
    expect(result).toBeNull();
  });

  it("does NOT auto-select while loading", () => {
    const result = getAutoSelectProvider(
      { plaid: true, teller: false, mx: false },
      true,
      false,
    );
    expect(result).toBeNull();
  });

  it("does NOT auto-select when availability is undefined", () => {
    const result = getAutoSelectProvider(undefined, false, false);
    expect(result).toBeNull();
  });

  it("does NOT auto-select when skipAutoSelect is true", () => {
    const result = getAutoSelectProvider(
      { plaid: true, teller: false, mx: false },
      false,
      true,
    );
    expect(result).toBeNull();
  });
});

// ── Back-navigation guard ────────────────────────────────────────────────────

describe("skipAutoSelect (back-navigation guard)", () => {
  it("prevents re-triggering when user navigates back to source selection", () => {
    // Simulates: user was auto-selected to plaid, then navigated back.
    // The AddAccountModal sets userNavigatedBack=true which becomes skipAutoSelect=true
    const skipAutoSelect = true;
    const result = getAutoSelectProvider(
      { plaid: true, teller: false, mx: false },
      false,
      skipAutoSelect,
    );
    expect(result).toBeNull();
  });

  it("allows auto-select on fresh modal open (skipAutoSelect=false)", () => {
    const skipAutoSelect = false;
    const result = getAutoSelectProvider(
      { plaid: true, teller: false, mx: false },
      false,
      skipAutoSelect,
    );
    expect(result).toBe("plaid");
  });
});
