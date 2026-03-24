/**
 * Tests for useNotificationToast hook.
 *
 * The vitest environment is "node" (no DOM / no React renderer), so we verify
 * correctness by reading the source and checking structural contracts.
 */

import { readFileSync } from "fs";
import { resolve } from "path";
import { describe, expect, it } from "vitest";

const ROOT = resolve(__dirname, "..", "..", "..");

function readSource(relPath: string): string {
  return readFileSync(resolve(ROOT, relPath), "utf-8");
}

const HOOK_PATH = "src/hooks/useNotificationToast.ts";
const API_PATH = "src/api/notifications.ts";
const TYPES_PATH = "src/types/notification.ts";

const hookSrc = readSource(HOOK_PATH);
const apiSrc = readSource(API_PATH);
const typesSrc = readSource(TYPES_PATH);

// ── Source structure ─────────────────────────────────────────────────────────

describe("useNotificationToast source structure", () => {
  it("exports useNotificationToast as a named export", () => {
    expect(hookSrc).toContain("export function useNotificationToast");
  });

  it("exports NotificationToastOptions interface", () => {
    expect(hookSrc).toContain("export interface NotificationToastOptions");
  });

  it("extends UseToastOptions from Chakra", () => {
    expect(hookSrc).toContain("extends UseToastOptions");
  });

  it("shows the Chakra toast before persisting (toast called first)", () => {
    // toast() call must appear before the guard that exits early when no
    // notification descriptor is supplied.
    const toastCallIdx = hookSrc.indexOf("toast(options)");
    const guardIdx = hookSrc.indexOf("if (!options.notification)");
    expect(toastCallIdx).toBeGreaterThan(-1);
    expect(guardIdx).toBeGreaterThan(-1);
    expect(toastCallIdx).toBeLessThan(guardIdx);
  });

  it("calls createNotification on the notificationsApi", () => {
    expect(hookSrc).toContain("notificationsApi");
    expect(hookSrc).toContain("createNotification(payload)");
  });

  it("invalidates the notifications query on success", () => {
    expect(hookSrc).toContain('queryKey: ["notifications"]');
    expect(hookSrc).toContain("queryClient.invalidateQueries");
  });

  it("catches errors silently (fire-and-forget) without re-throwing", () => {
    expect(hookSrc).toContain(".catch(");
    // Must not re-throw inside catch
    const catchBlock = hookSrc.slice(hookSrc.indexOf(".catch("));
    expect(catchBlock).not.toContain("throw ");
  });

  it("wraps the return in useCallback for stable reference", () => {
    expect(hookSrc).toContain("useCallback");
  });

  it("uses useQueryClient from react-query", () => {
    expect(hookSrc).toContain("useQueryClient");
  });
});

// ── Bell API integration ─────────────────────────────────────────────────────

describe("notificationsApi.createNotification", () => {
  it("is defined in the API client", () => {
    expect(apiSrc).toContain("createNotification");
  });

  it("posts to /notifications/ endpoint", () => {
    expect(apiSrc).toContain("api.post");
    expect(apiSrc).toContain("'/notifications/'");
  });

  it("returns a Notification object", () => {
    expect(apiSrc).toContain("Promise<Notification>");
  });
});

// ── Type completeness ────────────────────────────────────────────────────────

describe("NotificationType enum completeness", () => {
  it("includes WEEKLY_RECAP (backend type added in this feature)", () => {
    expect(typesSrc).toContain("WEEKLY_RECAP");
  });

  it("includes EQUITY_VESTING", () => {
    expect(typesSrc).toContain("EQUITY_VESTING");
  });

  it("includes CRYPTO_PRICE_ALERT", () => {
    expect(typesSrc).toContain("CRYPTO_PRICE_ALERT");
  });
});

// ── Contract: notification field is optional ─────────────────────────────────

describe("NotificationToastOptions.notification is optional", () => {
  it("marks the notification field as optional (?) in the interface", () => {
    // The interface must have `notification?:` so callers can omit it for
    // transient toasts (e.g. rate-limit warnings) that should not clutter the bell.
    expect(hookSrc).toMatch(/notification\?:/);
  });
});

// ── Default expires_in_days ───────────────────────────────────────────────────

describe("default expires_in_days", () => {
  it("defaults to 30 days when not specified by the caller", () => {
    expect(hookSrc).toContain("expires_in_days: notification.expires_in_days ?? 30");
  });
});
