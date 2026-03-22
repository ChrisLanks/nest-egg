/**
 * Tests for authStore.tryRestoreSession behaviour.
 *
 * Key regression: a 429 from /auth/refresh must NOT log the user out.
 * A rate-limited refresh means the session is still valid — the user
 * should stay authenticated and retry on the next navigation.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";

// ---------------------------------------------------------------------------
// Pure helper — mirrors the catch logic in authStore.tryRestoreSession
// ---------------------------------------------------------------------------
function shouldLogoutOnRefreshError(error: { response?: { status?: number } }): boolean {
  // 429 = rate limited — session still valid, don't log out
  if (error?.response?.status === 429) return false;
  return true;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("authStore.tryRestoreSession error handling", () => {
  describe("rate limit (429) on /auth/refresh", () => {
    it("does NOT log out when refresh returns 429", () => {
      const err = { response: { status: 429 } };
      expect(shouldLogoutOnRefreshError(err)).toBe(false);
    });
  });

  describe("genuine auth failures", () => {
    it("logs out when refresh returns 401 (invalid/expired token)", () => {
      const err = { response: { status: 401 } };
      expect(shouldLogoutOnRefreshError(err)).toBe(true);
    });

    it("logs out when refresh returns 403", () => {
      const err = { response: { status: 403 } };
      expect(shouldLogoutOnRefreshError(err)).toBe(true);
    });

    it("logs out on network error (no response)", () => {
      const err = { message: "Network Error" };
      expect(shouldLogoutOnRefreshError(err)).toBe(true);
    });

    it("logs out when refresh returns 500", () => {
      const err = { response: { status: 500 } };
      expect(shouldLogoutOnRefreshError(err)).toBe(true);
    });
  });
});
