/**
 * Pure-function tests verifying the UserMenu Preferences badge logic.
 * The "Setup" badge appears for new users (loginCount <= 5) to guide them
 * to Preferences for initial configuration.
 */
import { describe, it, expect } from "vitest";

// Replicate the badge logic from Layout.tsx UserMenu
function getPreferencesBadge(loginCount: number | undefined): string | undefined {
  return (loginCount ?? 0) <= 5 ? "Setup" : undefined;
}

describe("UserMenu Preferences badge", () => {
  it("login count = 1 → badge shown", () => {
    expect(getPreferencesBadge(1)).toBe("Setup");
  });

  it("login count = 5 → badge shown (boundary)", () => {
    expect(getPreferencesBadge(5)).toBe("Setup");
  });

  it("login count = 6 → badge hidden", () => {
    expect(getPreferencesBadge(6)).toBeUndefined();
  });

  it("login count = 100 → badge hidden", () => {
    expect(getPreferencesBadge(100)).toBeUndefined();
  });

  it("login count = 0 → badge shown (first visit before increment)", () => {
    expect(getPreferencesBadge(0)).toBe("Setup");
  });

  it("undefined loginCount → badge shown (new user)", () => {
    expect(getPreferencesBadge(undefined)).toBe("Setup");
  });
});
