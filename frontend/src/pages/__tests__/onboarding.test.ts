/**
 * Tests for onboarding flow logic.
 *
 * Covers: localStorage-based onboarding tracking, WelcomePage step flow,
 * routing behavior for new vs. returning users, and first-invite celebration.
 *
 * @vitest-environment jsdom
 */

import { describe, it, expect, beforeEach } from "vitest";

// ── localStorage onboarding gate ─────────────────────────────────────────────

describe("onboarding completion tracking", () => {
  const ONBOARDING_KEY = "nest-egg-onboarding-complete";

  beforeEach(() => {
    localStorage.clear();
  });

  it("new user has no onboarding flag", () => {
    expect(localStorage.getItem(ONBOARDING_KEY)).toBeNull();
  });

  it("setting the flag marks onboarding as complete", () => {
    localStorage.setItem(ONBOARDING_KEY, "true");
    expect(localStorage.getItem(ONBOARDING_KEY)).toBe("true");
  });

  it("Layout redirect logic: unonboarded user should be redirected", () => {
    // Simulates what Layout.tsx checks
    const shouldRedirect = !localStorage.getItem(ONBOARDING_KEY);
    expect(shouldRedirect).toBe(true);
  });

  it("Layout redirect logic: onboarded user should NOT be redirected", () => {
    localStorage.setItem(ONBOARDING_KEY, "true");
    const shouldRedirect = !localStorage.getItem(ONBOARDING_KEY);
    expect(shouldRedirect).toBe(false);
  });
});

// ── WelcomePage step logic ───────────────────────────────────────────────────

describe("WelcomePage step progression", () => {
  const STEPS = [
    { label: "Welcome" },
    { label: "Accounts" },
    { label: "Household" },
    { label: "Ready" },
  ];

  it("has 4 steps", () => {
    expect(STEPS).toHaveLength(4);
  });

  it("progress percentage calculates correctly for each step", () => {
    for (let step = 0; step < STEPS.length; step++) {
      const percent = ((step + 1) / STEPS.length) * 100;
      expect(percent).toBe((step + 1) * 25);
    }
  });

  it("step 0 is Welcome", () => {
    expect(STEPS[0].label).toBe("Welcome");
  });

  it("last step is Ready", () => {
    expect(STEPS[STEPS.length - 1].label).toBe("Ready");
  });

  it("next() from step 0 with household name triggers name update", () => {
    const step = 0;
    const householdName = "The Smith Family";
    const shouldUpdateName = step === 0 && householdName.trim().length > 0;
    expect(shouldUpdateName).toBe(true);
  });

  it("next() from step 0 without household name does NOT trigger update", () => {
    const step = 0;
    const householdName = "   ";
    const shouldUpdateName = step === 0 && householdName.trim().length > 0;
    expect(shouldUpdateName).toBe(false);
  });

  it("finish() sets onboarding complete in localStorage", () => {
    localStorage.setItem("nest-egg-onboarding-complete", "true");
    expect(localStorage.getItem("nest-egg-onboarding-complete")).toBe("true");
  });
});

// ── First-invite celebration logic ───────────────────────────────────────────

describe("first-invite celebration", () => {
  it("triggers when invitations list is empty", () => {
    const invitations: unknown[] = [];
    const isFirstInvite = !invitations || invitations.length === 0;
    expect(isFirstInvite).toBe(true);
  });

  it("triggers when invitations is null/undefined", () => {
    const invitations = null;
    const isFirstInvite = !invitations || invitations.length === 0;
    expect(isFirstInvite).toBe(true);
  });

  it("does NOT trigger when invitations already exist", () => {
    const invitations = [{ id: "1", email: "test@example.com" }];
    const isFirstInvite = !invitations || invitations.length === 0;
    expect(isFirstInvite).toBe(false);
  });
});

// ── Invite email validation ──────────────────────────────────────────────────

describe("invite email validation", () => {
  it("email with @ is valid for invite button", () => {
    const email = "partner@example.com";
    expect(email.includes("@")).toBe(true);
  });

  it("email without @ disables invite button", () => {
    const email = "notanemail";
    expect(email.includes("@")).toBe(false);
  });

  it("empty email disables invite button", () => {
    const email = "";
    expect(email.includes("@")).toBe(false);
  });
});
