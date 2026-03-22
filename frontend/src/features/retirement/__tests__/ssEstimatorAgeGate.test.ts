/**
 * Tests for Social Security estimator age-gating in RetirementPage.
 *
 * Rule: show the SS estimator when the user is >= 55 OR when birthdate is
 * unknown (null/undefined). Hide it for users under 55.
 *
 * Age is derived from a full ISO birthdate string (e.g. "1990-07-15"),
 * not a birth_year integer — this is different from the nav-level SS
 * optimizer gating which uses birth_year.
 */

import { describe, it, expect } from "vitest";

const SS_SHOW_AGE = 55;

/**
 * Mirrors the exact logic in RetirementPage:
 *   const currentUserAge = useMemo(() => {
 *     if (!userProfile?.birthdate) return null;
 *     const birth = new Date(userProfile.birthdate);
 *     const today = new Date();
 *     let age = today.getFullYear() - birth.getFullYear();
 *     const m = today.getMonth() - birth.getMonth();
 *     if (m < 0 || (m === 0 && today.getDate() < birth.getDate())) age--;
 *     return age;
 *   }, [userProfile?.birthdate]);
 *   const showSocialSecurity = currentUserAge === null || currentUserAge >= SS_SHOW_AGE;
 */
function computeAge(birthdate: string, today: Date): number {
  const birth = new Date(birthdate);
  let age = today.getFullYear() - birth.getFullYear();
  const m = today.getMonth() - birth.getMonth();
  if (m < 0 || (m === 0 && today.getDate() < birth.getDate())) age--;
  return age;
}

function shouldShowSsEstimator(
  birthdate: string | null | undefined,
  today: Date,
): boolean {
  if (!birthdate) return true; // unknown age → show by default
  const age = computeAge(birthdate, today);
  return age >= SS_SHOW_AGE;
}

// Fix a reference date so tests don't drift over time
const TODAY = new Date("2026-03-22");

function birthdateForAge(age: number): string {
  // Birthday falls on Jan 1 so there's no month-boundary ambiguity
  const year = TODAY.getFullYear() - age;
  return `${year}-01-01`;
}

describe("SS estimator age gate — computeAge", () => {
  it("returns correct age for a birthday earlier in the year", () => {
    expect(computeAge("1971-01-01", TODAY)).toBe(55);
  });

  it("returns correct age for a birthday later in the year (not yet had birthday)", () => {
    // Born Dec 1971 — hasn't had birthday yet in March 2026
    expect(computeAge("1971-12-01", TODAY)).toBe(54);
  });

  it("returns correct age on the exact birthday", () => {
    expect(computeAge("1971-03-22", TODAY)).toBe(55);
  });

  it("returns correct age for day before birthday (still 54)", () => {
    expect(computeAge("1971-03-23", TODAY)).toBe(54);
  });
});

describe("SS estimator age gate — shouldShowSsEstimator", () => {
  it("shows when birthdate is null", () => {
    expect(shouldShowSsEstimator(null, TODAY)).toBe(true);
  });

  it("shows when birthdate is undefined", () => {
    expect(shouldShowSsEstimator(undefined, TODAY)).toBe(true);
  });

  it("shows when birthdate is empty string", () => {
    expect(shouldShowSsEstimator("", TODAY)).toBe(true);
  });

  it("shows for user exactly age 55", () => {
    expect(shouldShowSsEstimator(birthdateForAge(55), TODAY)).toBe(true);
  });

  it("shows for user age 60", () => {
    expect(shouldShowSsEstimator(birthdateForAge(60), TODAY)).toBe(true);
  });

  it("shows for user age 70", () => {
    expect(shouldShowSsEstimator(birthdateForAge(70), TODAY)).toBe(true);
  });

  it("hides for user age 54", () => {
    expect(shouldShowSsEstimator(birthdateForAge(54), TODAY)).toBe(false);
  });

  it("hides for user age 30", () => {
    expect(shouldShowSsEstimator(birthdateForAge(30), TODAY)).toBe(false);
  });

  it("hides for user age 0", () => {
    expect(shouldShowSsEstimator(birthdateForAge(0), TODAY)).toBe(false);
  });

  it("threshold is 55, not 50 (retirement page vs nav)", () => {
    // Age 52 should be hidden on the retirement page estimator
    expect(shouldShowSsEstimator(birthdateForAge(52), TODAY)).toBe(false);
    // Age 55 should be shown
    expect(shouldShowSsEstimator(birthdateForAge(55), TODAY)).toBe(true);
  });
});
