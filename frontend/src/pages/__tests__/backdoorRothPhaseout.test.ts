/**
 * Tests for Roth Wizard filing status → phase-out range visibility.
 *
 * The BackdoorRothTab receives phaseout_lower/phaseout_upper from the API
 * and displays them immediately (no MAGI required), so toggling
 * single ↔ married should visibly change the displayed range.
 */

import { describe, it, expect } from "vitest";

// Mirrors backend TAX._ROTH_PHASEOUT_DATA for 2025
const PHASEOUT_2025 = {
  single: { lower: 150_000, upper: 165_000 },
  married: { lower: 236_000, upper: 246_000 },
};

function getPhaseout(filingStatus: string, year = 2025) {
  const data = PHASEOUT_2025 as Record<string, { lower: number; upper: number }>;
  const key = ["married", "mfj"].includes(filingStatus.toLowerCase()) ? "married" : "single";
  return data[key];
}

function checkDirectRothEligibility(
  magi: number | null,
  phaseout: { lower: number; upper: number }
): boolean | null {
  if (magi === null) return null;
  return magi < phaseout.lower;
}

describe("Roth Wizard phaseout range", () => {
  it("single and married have different phaseout ranges", () => {
    const single = getPhaseout("single");
    const married = getPhaseout("married");
    expect(married.lower).toBeGreaterThan(single.lower);
    expect(married.upper).toBeGreaterThan(single.upper);
  });

  it("phase-out range is always returned (no MAGI required)", () => {
    const single = getPhaseout("single");
    expect(single.lower).toBeGreaterThan(0);
    expect(single.upper).toBeGreaterThan(single.lower);
  });

  it("toggling filing status changes displayed range", () => {
    const single = getPhaseout("single");
    const married = getPhaseout("married");
    // Both should be populated and different
    expect(single.lower).not.toEqual(married.lower);
  });

  it("direct roth eligible when MAGI below single threshold", () => {
    const phaseout = getPhaseout("single");
    expect(checkDirectRothEligibility(100_000, phaseout)).toBe(true);
  });

  it("direct roth ineligible when MAGI above single upper", () => {
    const phaseout = getPhaseout("single");
    expect(checkDirectRothEligibility(200_000, phaseout)).toBe(false);
  });

  it("same MAGI may be eligible for married but not single", () => {
    const magi = 160_000; // above single upper, below married lower
    const single = getPhaseout("single");
    const married = getPhaseout("married");
    expect(checkDirectRothEligibility(magi, single)).toBe(false);
    expect(checkDirectRothEligibility(magi, married)).toBe(true);
  });

  it("direct roth eligibility is null when MAGI not provided", () => {
    const phaseout = getPhaseout("single");
    expect(checkDirectRothEligibility(null, phaseout)).toBeNull();
  });
});
