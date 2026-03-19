/**
 * Tests for SS Optimizer age-gating logic.
 *
 * The rule: show /ss-claiming for users aged 50+ or when birth_year is unknown.
 * Hide by default for users under 50.
 */

import { describe, it, expect } from "vitest";

/** Mirrors the showSsOptimizer logic in Layout.tsx */
function computeShowSsOptimizer(
  birthYear: number | null | undefined,
  currentYear: number,
): boolean {
  const userAge = birthYear ? currentYear - birthYear : null;
  return userAge === null || userAge >= 50;
}

describe("SS Optimizer age-gating", () => {
  const CURRENT_YEAR = 2026;

  it("shows for users exactly age 50", () => {
    const birthYear = CURRENT_YEAR - 50; // 1976
    expect(computeShowSsOptimizer(birthYear, CURRENT_YEAR)).toBe(true);
  });

  it("shows for users older than 50", () => {
    const birthYear = CURRENT_YEAR - 65;
    expect(computeShowSsOptimizer(birthYear, CURRENT_YEAR)).toBe(true);
  });

  it("hides for users under 50", () => {
    const birthYear = CURRENT_YEAR - 35;
    expect(computeShowSsOptimizer(birthYear, CURRENT_YEAR)).toBe(false);
  });

  it("hides for users age 49", () => {
    const birthYear = CURRENT_YEAR - 49;
    expect(computeShowSsOptimizer(birthYear, CURRENT_YEAR)).toBe(false);
  });

  it("shows when birth_year is null (unknown age)", () => {
    expect(computeShowSsOptimizer(null, CURRENT_YEAR)).toBe(true);
  });

  it("shows when birth_year is undefined (profile not loaded yet)", () => {
    expect(computeShowSsOptimizer(undefined, CURRENT_YEAR)).toBe(true);
  });

  it("shows for users age 51", () => {
    const birthYear = CURRENT_YEAR - 51;
    expect(computeShowSsOptimizer(birthYear, CURRENT_YEAR)).toBe(true);
  });

  it("hides for users age 25", () => {
    const birthYear = CURRENT_YEAR - 25;
    expect(computeShowSsOptimizer(birthYear, CURRENT_YEAR)).toBe(false);
  });
});
