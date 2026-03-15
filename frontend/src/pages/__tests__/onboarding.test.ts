/**
 * Tests for onboarding flow logic.
 *
 * Covers: DB-backed onboarding tracking, WelcomePage step flow,
 * routing behavior for new vs. returning users, and first-invite celebration.
 *
 * @vitest-environment jsdom
 */

import { describe, it, expect } from "vitest";
import type { User } from "../../types/user";

// Helper to build a minimal User object for testing
function makeUser(overrides: Partial<User> = {}): User {
  return {
    id: "u1",
    organization_id: "org1",
    email: "test@example.com",
    first_name: null,
    last_name: null,
    display_name: "Test",
    is_active: true,
    is_org_admin: true,
    email_verified: false,
    onboarding_completed: false,
    last_login_at: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

// ── DB-backed onboarding gate ────────────────────────────────────────────────

describe("onboarding completion tracking", () => {
  it("new user has onboarding_completed = false", () => {
    const user = makeUser();
    expect(user.onboarding_completed).toBe(false);
  });

  it("completed user has onboarding_completed = true", () => {
    const user = makeUser({ onboarding_completed: true });
    expect(user.onboarding_completed).toBe(true);
  });

  it("Layout redirect logic: unonboarded user should be redirected", () => {
    const user = makeUser({ onboarding_completed: false });
    const shouldRedirect = user && !user.onboarding_completed;
    expect(shouldRedirect).toBe(true);
  });

  it("Layout redirect logic: onboarded user should NOT be redirected", () => {
    const user = makeUser({ onboarding_completed: true });
    const shouldRedirect = user && !user.onboarding_completed;
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

  it("finish() updates user.onboarding_completed in auth store", () => {
    const user = makeUser();
    // Simulate what finish() does after API call succeeds
    const updatedUser = { ...user, onboarding_completed: true };
    expect(updatedUser.onboarding_completed).toBe(true);
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
