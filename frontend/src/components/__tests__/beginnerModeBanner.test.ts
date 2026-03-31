/**
 * Pure-function tests for BeginnerModeBanner logic.
 * Tests the isNewUser predicate and dismiss localStorage key contract
 * without mounting the component.
 */

import { describe, it, expect } from "vitest";

// ── Pure logic extracted from BeginnerModeBanner ─────────────────────────────

const DISMISS_KEY = "nest-egg-beginner-banner-dismissed";

const isNewUser = (loginCount: number | undefined): boolean =>
  !loginCount || loginCount <= 3;

const isDismissed = (store: Record<string, string>): boolean =>
  store[DISMISS_KEY] === "true";

const shouldShowBanner = (
  loginCount: number | undefined,
  store: Record<string, string>,
): boolean => !isDismissed(store) && isNewUser(loginCount);

// ── isNewUser ────────────────────────────────────────────────────────────────

describe("isNewUser", () => {
  it("returns true when loginCount is undefined (brand new registration)", () => {
    expect(isNewUser(undefined)).toBe(true);
  });

  it("returns true when loginCount is 0", () => {
    expect(isNewUser(0)).toBe(true);
  });

  it("returns true when loginCount is 1 (first login)", () => {
    expect(isNewUser(1)).toBe(true);
  });

  it("returns true when loginCount is 3 (within threshold)", () => {
    expect(isNewUser(3)).toBe(true);
  });

  it("returns false when loginCount is 4 (experienced user)", () => {
    expect(isNewUser(4)).toBe(false);
  });

  it("returns false when loginCount is 100", () => {
    expect(isNewUser(100)).toBe(false);
  });
});

// ── isDismissed ──────────────────────────────────────────────────────────────

describe("isDismissed", () => {
  it("returns false when key is absent", () => {
    expect(isDismissed({})).toBe(false);
  });

  it("returns true when key is 'true'", () => {
    expect(isDismissed({ [DISMISS_KEY]: "true" })).toBe(true);
  });

  it("returns false when key is 'false'", () => {
    expect(isDismissed({ [DISMISS_KEY]: "false" })).toBe(false);
  });

  it("returns false for unexpected value", () => {
    expect(isDismissed({ [DISMISS_KEY]: "yes" })).toBe(false);
  });
});

// ── shouldShowBanner ─────────────────────────────────────────────────────────

describe("shouldShowBanner", () => {
  it("shows for new user with no dismiss key", () => {
    expect(shouldShowBanner(1, {})).toBe(true);
  });

  it("shows for undefined loginCount with no dismiss key", () => {
    expect(shouldShowBanner(undefined, {})).toBe(true);
  });

  it("hides when dismissed even for new user", () => {
    expect(shouldShowBanner(1, { [DISMISS_KEY]: "true" })).toBe(false);
  });

  it("hides for experienced user (login_count = 4) even if not dismissed", () => {
    expect(shouldShowBanner(4, {})).toBe(false);
  });

  it("hides for experienced user who also dismissed", () => {
    expect(shouldShowBanner(10, { [DISMISS_KEY]: "true" })).toBe(false);
  });

  it("shows for login_count = 3 with no dismiss key (still within threshold)", () => {
    expect(shouldShowBanner(3, {})).toBe(true);
  });

  it("hides for login_count = 3 after dismiss", () => {
    expect(shouldShowBanner(3, { [DISMISS_KEY]: "true" })).toBe(false);
  });
});

// ── Dismiss key constant ──────────────────────────────────────────────────────

describe("DISMISS_KEY", () => {
  it("has expected value so localStorage key is stable across versions", () => {
    expect(DISMISS_KEY).toBe("nest-egg-beginner-banner-dismissed");
  });
});

// ── Recommendations tab preference ───────────────────────────────────────────
// Mirrors the logic in FinancialHealthPage and PreferencesPage

const RECS_KEY = "nest-egg-show-recommendations-tab";

const getShowRecommendations = (store: Record<string, string>): boolean => {
  const v = store[RECS_KEY];
  return v === null || v === undefined ? true : v === "true";
};

describe("getShowRecommendations (Recommendations tab preference)", () => {
  it("defaults to true when key is absent (on by default)", () => {
    expect(getShowRecommendations({})).toBe(true);
  });

  it("returns true when key is 'true'", () => {
    expect(getShowRecommendations({ [RECS_KEY]: "true" })).toBe(true);
  });

  it("returns false when key is 'false'", () => {
    expect(getShowRecommendations({ [RECS_KEY]: "false" })).toBe(false);
  });

  it("key name is stable", () => {
    expect(RECS_KEY).toBe("nest-egg-show-recommendations-tab");
  });
});
