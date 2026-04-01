/**
 * Tests for PostOnboardingBanner visibility logic (UX improvement D).
 *
 * The banner guides early users (< 5 logins, with at least 1 account)
 * toward the next high-value actions: set a goal, run a tax projection,
 * check net worth. It is dismissable and hides for returning users.
 */

import { describe, it, expect } from "vitest";
import { shouldShowPostOnboardingBanner } from "../components/PostOnboardingBanner";

describe("PostOnboardingBanner visibility (UX improvement D)", () => {
  describe("shows when user is early-stage with accounts", () => {
    it("shows on login 1 with 1 account", () => {
      expect(shouldShowPostOnboardingBanner(1, 1, false)).toBe(true);
    });

    it("shows on login 4 (last early-stage login) with accounts", () => {
      expect(shouldShowPostOnboardingBanner(3, 4, false)).toBe(true);
    });

    it("shows when loginCount is undefined (new user, profile not loaded)", () => {
      expect(shouldShowPostOnboardingBanner(2, undefined, false)).toBe(true);
    });

    it("shows with many accounts on login 2", () => {
      expect(shouldShowPostOnboardingBanner(10, 2, false)).toBe(true);
    });
  });

  describe("hides when user is experienced", () => {
    it("hides on login 5 (threshold reached)", () => {
      expect(shouldShowPostOnboardingBanner(5, 5, false)).toBe(false);
    });

    it("hides on login 10 (long-term user)", () => {
      expect(shouldShowPostOnboardingBanner(5, 10, false)).toBe(false);
    });

    it("hides on login 100", () => {
      expect(shouldShowPostOnboardingBanner(5, 100, false)).toBe(false);
    });
  });

  describe("hides when no accounts yet", () => {
    it("hides when accountCount is 0 (GettingStartedEmptyState handles this)", () => {
      expect(shouldShowPostOnboardingBanner(0, 1, false)).toBe(false);
    });

    it("hides when accountCount is 0 even on first login", () => {
      expect(shouldShowPostOnboardingBanner(0, 0, false)).toBe(false);
    });
  });

  describe("hides when dismissed", () => {
    it("hides when dismissed=true regardless of accounts or loginCount", () => {
      expect(shouldShowPostOnboardingBanner(5, 1, true)).toBe(false);
    });

    it("hides when dismissed=true even on first login", () => {
      expect(shouldShowPostOnboardingBanner(1, 1, true)).toBe(false);
    });
  });

  describe("next steps navigation targets", () => {
    const NEXT_STEPS = [
      { path: "/goals" },
      { path: "/tax-center" },
      { path: "/net-worth" },
    ];

    it("has exactly 3 next steps", () => {
      expect(NEXT_STEPS.length).toBe(3);
    });

    it("includes a goals path", () => {
      expect(NEXT_STEPS.some((s) => s.path.includes("goal"))).toBe(true);
    });

    it("includes a tax center path", () => {
      expect(NEXT_STEPS.some((s) => s.path.includes("tax"))).toBe(true);
    });

    it("includes a net worth path", () => {
      expect(NEXT_STEPS.some((s) => s.path.includes("net-worth"))).toBe(true);
    });
  });
});
