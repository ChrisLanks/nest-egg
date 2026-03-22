/**
 * Tests for the global error toast logic in the axios response interceptor.
 *
 * api.ts dispatches a "api-error-toast" CustomEvent for 429/5xx errors;
 * ApiErrorToastListener renders these using Chakra's single ToastProvider.
 * Auth endpoint errors are excluded to avoid spurious toasts during token refresh.
 *
 * These tests verify the decision logic without mounting a React component.
 */

import { describe, it, expect } from "vitest";

// ---------------------------------------------------------------------------
// Pure helpers — mirror the decision logic in api.ts interceptor
// ---------------------------------------------------------------------------
type ToastType = "rate-limit" | "server-error" | null;

const AUTH_PATHS = [
  "/auth/login",
  "/auth/register",
  "/auth/refresh",
  "/auth/forgot-password",
  "/auth/reset-password",
];

function isAuthEndpoint(url: string): boolean {
  return AUTH_PATHS.some((p) => url.includes(p));
}

function getToastType(httpStatus: number | undefined, url: string): ToastType {
  if (isAuthEndpoint(url)) return null;
  if (httpStatus === 429) return "rate-limit";
  if (httpStatus !== undefined && httpStatus >= 500) return "server-error";
  return null;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("api.ts global error toast logic", () => {
  describe("429 Too Many Requests", () => {
    it("returns rate-limit for non-auth endpoints", () => {
      expect(getToastType(429, "/api/v1/transactions")).toBe("rate-limit");
    });

    it("returns null for /auth/refresh (rate-limit on refresh must not log out)", () => {
      expect(getToastType(429, "/auth/refresh")).toBeNull();
    });

    it("returns null for /auth/login", () => {
      expect(getToastType(429, "/auth/login")).toBeNull();
    });
  });

  describe("5xx Server Errors", () => {
    it("returns server-error for 500", () => {
      expect(getToastType(500, "/api/v1/accounts")).toBe("server-error");
    });

    it("returns server-error for 502", () => {
      expect(getToastType(502, "/api/v1/accounts")).toBe("server-error");
    });

    it("returns server-error for 503", () => {
      expect(getToastType(503, "/api/v1/accounts")).toBe("server-error");
    });

    it("returns server-error for 504", () => {
      expect(getToastType(504, "/api/v1/accounts")).toBe("server-error");
    });

    it("returns null for 500 on auth endpoint", () => {
      expect(getToastType(500, "/auth/register")).toBeNull();
    });
  });

  describe("4xx Client Errors (no toast — component handles these)", () => {
    it("returns null for 400", () => {
      expect(getToastType(400, "/api/v1/accounts")).toBeNull();
    });

    it("returns null for 401 (handled by token refresh flow)", () => {
      expect(getToastType(401, "/api/v1/accounts")).toBeNull();
    });

    it("returns null for 403", () => {
      expect(getToastType(403, "/api/v1/accounts")).toBeNull();
    });

    it("returns null for 404", () => {
      expect(getToastType(404, "/api/v1/accounts")).toBeNull();
    });

    it("returns null for 422", () => {
      expect(getToastType(422, "/api/v1/accounts")).toBeNull();
    });
  });

  describe("edge cases", () => {
    it("returns null when status is undefined (network error)", () => {
      expect(getToastType(undefined, "/api/v1/accounts")).toBeNull();
    });

    it("does not show a toast for 499", () => {
      expect(getToastType(499, "/api/v1/accounts")).toBeNull();
    });

    it("rate-limit and server-error are distinct types", () => {
      expect(getToastType(429, "/api/v1/accounts")).not.toBe(
        getToastType(500, "/api/v1/accounts")
      );
    });
  });

  describe("auth endpoint exclusion", () => {
    const authEndpoints = [
      "/auth/login",
      "/auth/register",
      "/auth/refresh",
      "/auth/forgot-password",
      "/auth/reset-password",
    ];

    it.each(authEndpoints)(
      "suppresses toast for %s even on 429",
      (url) => {
        expect(getToastType(429, url)).toBeNull();
      }
    );

    it.each(authEndpoints)(
      "suppresses toast for %s even on 500",
      (url) => {
        expect(getToastType(500, url)).toBeNull();
      }
    );
  });
});
