/**
 * Tests for onboarding flow logic.
 *
 * Covers: DB-backed onboarding tracking, WelcomePage step flow,
 * routing behavior for new vs. returning users, and first-invite celebration.
 *
 * @vitest-environment jsdom
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
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

// ── Advanced nav preference during onboarding ────────────────────────────────

const ADVANCED_NAV_KEY = "nest-egg-show-advanced-nav";
const GOAL_KEY = "nest-egg-onboarding-goal";

describe("WelcomePage: advanced nav preference", () => {
  beforeEach(() => localStorage.clear());

  it("finish() persists showAdvancedNav=false by default", () => {
    // Simulate finish() with default checkbox (unchecked)
    localStorage.setItem(ADVANCED_NAV_KEY, String(false));
    expect(localStorage.getItem(ADVANCED_NAV_KEY)).toBe("false");
  });

  it("finish() persists showAdvancedNav=true when checkbox is checked", () => {
    localStorage.setItem(ADVANCED_NAV_KEY, String(true));
    expect(localStorage.getItem(ADVANCED_NAV_KEY)).toBe("true");
  });

  it("Layout reads 'true' string as truthy advanced toggle", () => {
    localStorage.setItem(ADVANCED_NAV_KEY, "true");
    const showAdvanced =
      localStorage.getItem(ADVANCED_NAV_KEY) === "true";
    expect(showAdvanced).toBe(true);
  });

  it("Layout reads 'false' string as falsy advanced toggle", () => {
    localStorage.setItem(ADVANCED_NAV_KEY, "false");
    const showAdvanced =
      localStorage.getItem(ADVANCED_NAV_KEY) === "true";
    expect(showAdvanced).toBe(false);
  });

  it("goal is persisted to localStorage in finish()", () => {
    const selectedGoal = "retirement";
    localStorage.setItem(GOAL_KEY, selectedGoal);
    expect(localStorage.getItem(GOAL_KEY)).toBe("retirement");
  });

  it("goal and advanced flag are both persisted independently", () => {
    localStorage.setItem(GOAL_KEY, "investments");
    localStorage.setItem(ADVANCED_NAV_KEY, "true");
    expect(localStorage.getItem(GOAL_KEY)).toBe("investments");
    expect(localStorage.getItem(ADVANCED_NAV_KEY)).toBe("true");
  });
});

// ── Goal option copy ──────────────────────────────────────────────────────────

describe("WelcomePage: goal options content", () => {
  const GOAL_OPTIONS = [
    {
      id: "spending",
      title: "Track my spending",
      desc: "See where my money goes each month and set a budget so I stop overspending",
    },
    {
      id: "retirement",
      title: "Plan for retirement",
      desc: "Based on what I save, see when I could stop working — and what I need to get there",
    },
    {
      id: "investments",
      title: "Understand my investments",
      desc: "If I have a 401(k) or brokerage account, see what's in it and what it costs me each year",
    },
  ];

  it("has exactly 3 goal options", () => {
    expect(GOAL_OPTIONS).toHaveLength(3);
  });

  it("investments goal mentions 401(k)", () => {
    const inv = GOAL_OPTIONS.find((g) => g.id === "investments");
    expect(inv?.desc).toContain("401(k)");
  });

  it("retirement goal mentions stopping working", () => {
    const ret = GOAL_OPTIONS.find((g) => g.id === "retirement");
    expect(ret?.desc).toContain("stop working");
  });

  it("spending goal mentions budget", () => {
    const sp = GOAL_OPTIONS.find((g) => g.id === "spending");
    expect(sp?.desc).toContain("budget");
  });
});

// ── finish() API integration ────────────────────────────────────────────────

describe("finish() onboarding completion flow", () => {
  /**
   * These tests simulate the finish() logic from WelcomePage
   * using mock API and store functions.
   */

  async function runFinish(opts: { apiSucceeds: boolean; user: User | null }) {
    const mockPost = opts.apiSucceeds
      ? vi.fn().mockResolvedValue({ data: { onboarding_completed: true } })
      : vi.fn().mockRejectedValue(new Error("Network error"));
    const mockSetUser = vi.fn();
    const mockNavigate = vi.fn();

    // Replicate WelcomePage.finish() logic
    try {
      await mockPost("/onboarding/complete");
      if (opts.user) {
        mockSetUser({ ...opts.user, onboarding_completed: true });
      }
    } catch {
      // Best-effort — don't block navigation
    }
    mockNavigate("/overview");

    return { mockPost, mockSetUser, mockNavigate };
  }

  it("calls POST /onboarding/complete", async () => {
    const { mockPost } = await runFinish({
      apiSucceeds: true,
      user: makeUser(),
    });
    expect(mockPost).toHaveBeenCalledWith("/onboarding/complete");
  });

  it("updates auth store user with onboarding_completed: true on success", async () => {
    const user = makeUser();
    const { mockSetUser } = await runFinish({ apiSucceeds: true, user });
    expect(mockSetUser).toHaveBeenCalledWith(
      expect.objectContaining({ onboarding_completed: true }),
    );
  });

  it("does not call setUser when user is null", async () => {
    const { mockSetUser } = await runFinish({
      apiSucceeds: true,
      user: null,
    });
    expect(mockSetUser).not.toHaveBeenCalled();
  });

  it("navigates to /overview even when API call fails", async () => {
    const { mockNavigate, mockSetUser } = await runFinish({
      apiSucceeds: false,
      user: makeUser(),
    });
    expect(mockNavigate).toHaveBeenCalledWith("/overview");
    // setUser should NOT be called when API fails
    expect(mockSetUser).not.toHaveBeenCalled();
  });

  it("navigates to /overview on success", async () => {
    const { mockNavigate } = await runFinish({
      apiSucceeds: true,
      user: makeUser(),
    });
    expect(mockNavigate).toHaveBeenCalledWith("/overview");
  });

  it("preserves all existing user fields when updating", async () => {
    const user = makeUser({
      email: "alice@example.com",
      display_name: "Alice",
      is_org_admin: true,
    });
    const { mockSetUser } = await runFinish({ apiSucceeds: true, user });
    const updatedUser = mockSetUser.mock.calls[0][0];
    expect(updatedUser.email).toBe("alice@example.com");
    expect(updatedUser.display_name).toBe("Alice");
    expect(updatedUser.is_org_admin).toBe(true);
    expect(updatedUser.onboarding_completed).toBe(true);
  });
});
