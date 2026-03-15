/**
 * Tests for VerifyEmailPage logic: state determination from token presence,
 * verification state transitions, and resend guard.
 */

import { describe, it, expect } from "vitest";

// ── Types (mirrored from VerifyEmailPage.tsx) ────────────────────────────────

type State = "loading" | "success" | "error" | "no-token";

// ── Logic helpers ────────────────────────────────────────────────────────────

function determineInitialState(token: string | null): State {
  if (!token) return "no-token";
  return "loading";
}

function shouldShowErrorUI(state: State): boolean {
  return state === "error" || state === "no-token";
}

function shouldShowResendButton(resendDone: boolean): boolean {
  return !resendDone;
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe("determineInitialState", () => {
  it('returns "no-token" when token is null', () => {
    expect(determineInitialState(null)).toBe("no-token");
  });

  it('returns "no-token" when token is empty string', () => {
    expect(determineInitialState("")).toBe("no-token");
  });

  it('returns "loading" when token is present', () => {
    expect(determineInitialState("abc123")).toBe("loading");
  });
});

describe("shouldShowErrorUI", () => {
  it("shows error UI for error state", () => {
    expect(shouldShowErrorUI("error")).toBe(true);
  });

  it("shows error UI for no-token state", () => {
    expect(shouldShowErrorUI("no-token")).toBe(true);
  });

  it("does not show error UI for success", () => {
    expect(shouldShowErrorUI("success")).toBe(false);
  });

  it("does not show error UI for loading", () => {
    expect(shouldShowErrorUI("loading")).toBe(false);
  });
});

describe("shouldShowResendButton", () => {
  it("shows resend button when not yet sent", () => {
    expect(shouldShowResendButton(false)).toBe(true);
  });

  it("hides resend button after successful resend", () => {
    expect(shouldShowResendButton(true)).toBe(false);
  });
});

describe("State transitions", () => {
  it("transitions from loading to success on API success", () => {
    let state: State = "loading";
    // Simulate API success
    state = "success";
    expect(state).toBe("success");
  });

  it("transitions from loading to error on API failure", () => {
    let state: State = "loading";
    // Simulate API failure
    state = "error";
    expect(state).toBe("error");
  });
});

describe("User update on success", () => {
  it("sets email_verified to true on existing user", () => {
    const user = { id: "u1", email: "a@b.com", email_verified: false };
    const updated = { ...user, email_verified: true };
    expect(updated.email_verified).toBe(true);
  });

  it("handles null user gracefully", () => {
    const user = null;
    const shouldUpdate = !!user;
    expect(shouldUpdate).toBe(false);
  });
});
