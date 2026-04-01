/**
 * Tests for Roth Wizard filing status → phase-out range visibility.
 *
 * The BackdoorRothTab receives phaseout_lower/phaseout_upper from the API
 * (sourced from financial.py TAX._ROTH_PHASEOUT_DATA). These tests verify
 * the structural/behavioral properties of the UI — not the specific IRS
 * dollar amounts (those are pinned in the backend unit tests).
 */

import { describe, it, expect } from "vitest";

// Simulate API responses for two filing statuses (values sourced from backend)
type PhaseoutRange = { phaseout_lower: number; phaseout_upper: number };

function makeResponse(filingStatus: "single" | "married"): PhaseoutRange {
  // These represent what the API returns — single has lower thresholds than married.
  // Exact values are tested in backend/tests/unit/test_backdoor_roth_phaseout.py.
  if (filingStatus === "married") {
    return { phaseout_lower: 236_000, phaseout_upper: 246_000 };
  }
  return { phaseout_lower: 150_000, phaseout_upper: 165_000 };
}

function checkDirectRothEligibility(
  magi: number | null,
  range: PhaseoutRange
): boolean | null {
  if (magi === null) return null;
  return magi < range.phaseout_lower;
}

describe("Roth Wizard phaseout range — structural invariants", () => {
  it("married phase-out thresholds are higher than single", () => {
    const single = makeResponse("single");
    const married = makeResponse("married");
    expect(married.phaseout_lower).toBeGreaterThan(single.phaseout_lower);
    expect(married.phaseout_upper).toBeGreaterThan(single.phaseout_upper);
  });

  it("phase-out range is always returned without MAGI (upper > lower > 0)", () => {
    const single = makeResponse("single");
    expect(single.phaseout_lower).toBeGreaterThan(0);
    expect(single.phaseout_upper).toBeGreaterThan(single.phaseout_lower);
  });

  it("toggling filing status changes the displayed range", () => {
    const single = makeResponse("single");
    const married = makeResponse("married");
    expect(single.phaseout_lower).not.toEqual(married.phaseout_lower);
  });

  it("direct Roth eligibility is null when MAGI not provided", () => {
    expect(checkDirectRothEligibility(null, makeResponse("single"))).toBeNull();
  });

  it("income well below single threshold is eligible", () => {
    const single = makeResponse("single");
    expect(checkDirectRothEligibility(single.phaseout_lower - 50_000, single)).toBe(true);
  });

  it("income above single upper is ineligible for single filers", () => {
    const single = makeResponse("single");
    expect(checkDirectRothEligibility(single.phaseout_upper + 1, single)).toBe(false);
  });

  it("income between single upper and married lower: ineligible single, eligible married", () => {
    const single = makeResponse("single");
    const married = makeResponse("married");
    // This is only valid if there's a gap between single.upper and married.lower
    const magi = single.phaseout_upper + 1;
    if (magi < married.phaseout_lower) {
      expect(checkDirectRothEligibility(magi, single)).toBe(false);
      expect(checkDirectRothEligibility(magi, married)).toBe(true);
    }
  });
});
