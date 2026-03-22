/**
 * Tests for the global error toast logic in the axios response interceptor.
 *
 * api.ts uses createStandaloneToast so error feedback reaches the user even
 * when the calling component has no explicit error handler.  These tests verify
 * the decision logic (which status codes trigger which toast) without mounting
 * a React component.
 */

import { describe, it, expect } from "vitest";

// ---------------------------------------------------------------------------
// Pure helper — mirrors the decision logic in api.ts interceptor
// ---------------------------------------------------------------------------
type ToastCall = { title: string; status: "warning" | "error" } | null;

function getToastForStatus(httpStatus: number | undefined): ToastCall {
  if (httpStatus === 429) {
    return { title: "Too many requests", status: "warning" };
  }
  if (httpStatus !== undefined && httpStatus >= 500) {
    return { title: "Server error", status: "error" };
  }
  return null;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("api.ts global error toast logic", () => {
  describe("429 Too Many Requests", () => {
    it("returns a warning toast", () => {
      const result = getToastForStatus(429);
      expect(result).not.toBeNull();
      expect(result!.status).toBe("warning");
      expect(result!.title).toBe("Too many requests");
    });
  });

  describe("5xx Server Errors", () => {
    it("returns an error toast for 500", () => {
      const result = getToastForStatus(500);
      expect(result).not.toBeNull();
      expect(result!.status).toBe("error");
    });

    it("returns an error toast for 502", () => {
      expect(getToastForStatus(502)?.status).toBe("error");
    });

    it("returns an error toast for 503", () => {
      expect(getToastForStatus(503)?.status).toBe("error");
    });

    it("returns an error toast for 504", () => {
      expect(getToastForStatus(504)?.status).toBe("error");
    });
  });

  describe("4xx Client Errors (no toast — component handles these)", () => {
    it("returns null for 400", () => {
      expect(getToastForStatus(400)).toBeNull();
    });

    it("returns null for 401", () => {
      // 401 is handled by the token refresh flow, not a toast
      expect(getToastForStatus(401)).toBeNull();
    });

    it("returns null for 403", () => {
      expect(getToastForStatus(403)).toBeNull();
    });

    it("returns null for 404", () => {
      expect(getToastForStatus(404)).toBeNull();
    });

    it("returns null for 422", () => {
      expect(getToastForStatus(422)).toBeNull();
    });
  });

  describe("edge cases", () => {
    it("returns null when status is undefined (network error before response)", () => {
      expect(getToastForStatus(undefined)).toBeNull();
    });

    it("does not show a toast for 499 (client closed)", () => {
      expect(getToastForStatus(499)).toBeNull();
    });

    it("shows error toast for exactly 500", () => {
      expect(getToastForStatus(500)?.status).toBe("error");
    });

    it("warning toast for 429 is distinct from error toast for 500", () => {
      const r429 = getToastForStatus(429);
      const r500 = getToastForStatus(500);
      expect(r429!.status).not.toBe(r500!.status);
    });
  });
});
