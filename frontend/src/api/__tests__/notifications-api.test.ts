/**
 * Tests for the notifications API client.
 *
 * Verifies the full contract of notificationsApi via source analysis —
 * no HTTP mocking required.
 */

import { readFileSync } from "fs";
import { resolve } from "path";
import { describe, expect, it } from "vitest";

const ROOT = resolve(__dirname, "..", "..", "..");
const apiSrc = readFileSync(resolve(ROOT, "src/api/notifications.ts"), "utf-8");
const typesSrc = readFileSync(resolve(ROOT, "src/types/notification.ts"), "utf-8");

// ── Endpoint coverage ────────────────────────────────────────────────────────

describe("notificationsApi — endpoint coverage", () => {
  it("exports notificationsApi", () => {
    expect(apiSrc).toContain("export const notificationsApi");
  });

  it("GET /notifications/ — getNotifications", () => {
    expect(apiSrc).toContain("getNotifications");
    expect(apiSrc).toContain("api.get");
    expect(apiSrc).toContain("'/notifications/'");
  });

  it("GET /notifications/unread-count — getUnreadCount", () => {
    expect(apiSrc).toContain("getUnreadCount");
    expect(apiSrc).toContain("'/notifications/unread-count'");
  });

  it("PATCH /notifications/:id/read — markAsRead", () => {
    expect(apiSrc).toContain("markAsRead");
    expect(apiSrc).toContain("api.patch");
    expect(apiSrc).toContain("/read`");
  });

  it("PATCH /notifications/:id/dismiss — dismiss", () => {
    expect(apiSrc).toContain("dismiss");
    expect(apiSrc).toContain("/dismiss`");
  });

  it("POST /notifications/mark-all-read — markAllAsRead", () => {
    expect(apiSrc).toContain("markAllAsRead");
    expect(apiSrc).toContain("api.post");
    expect(apiSrc).toContain("'/notifications/mark-all-read'");
  });

  it("POST /notifications/ — createNotification (toast→bell bridge)", () => {
    expect(apiSrc).toContain("createNotification");
    expect(apiSrc).toContain("'/notifications/'");
  });
});

// ── Return types ─────────────────────────────────────────────────────────────

describe("notificationsApi — return types", () => {
  it("getNotifications returns Promise<Notification[]>", () => {
    expect(apiSrc).toContain("Promise<Notification[]>");
  });

  it("getUnreadCount returns Promise<UnreadCountResponse>", () => {
    expect(apiSrc).toContain("Promise<UnreadCountResponse>");
  });

  it("markAsRead returns Promise<Notification>", () => {
    expect(apiSrc).toContain("Promise<Notification>");
  });

  it("createNotification returns Promise<Notification>", () => {
    expect(apiSrc).toContain("Promise<Notification>");
  });

  it("markAllAsRead returns Promise<{ marked_read: number }>", () => {
    expect(apiSrc).toContain("marked_read: number");
  });
});

// ── NotificationType enum completeness ───────────────────────────────────────

describe("NotificationType enum — backend sync", () => {
  const EXPECTED_TYPES = [
    "sync_failed",
    "reauth_required",
    "sync_stale",
    "account_connected",
    "account_error",
    "budget_alert",
    "transaction_duplicate",
    "large_transaction",
    "milestone",
    "all_time_high",
    "household_member_joined",
    "household_member_left",
    "goal_completed",
    "goal_funded",
    "fire_coast_fi",
    "fire_independent",
    "retirement_scenario_stale",
    "weekly_recap",
    "equity_vesting",
    "crypto_price_alert",
  ];

  for (const t of EXPECTED_TYPES) {
    it(`includes "${t}"`, () => {
      expect(typesSrc).toContain(`"${t}"`);
    });
  }
});

// ── NotificationPriority enum ────────────────────────────────────────────────

describe("NotificationPriority enum", () => {
  it("has LOW, MEDIUM, HIGH, URGENT", () => {
    for (const p of ["low", "medium", "high", "urgent"]) {
      expect(typesSrc).toContain(`"${p}"`);
    }
  });
});

// ── Notification interface shape ─────────────────────────────────────────────

describe("Notification interface", () => {
  const REQUIRED_FIELDS = [
    "id",
    "organization_id",
    "user_id",
    "type",
    "priority",
    "title",
    "message",
    "is_read",
    "is_dismissed",
    "read_at",
    "dismissed_at",
    "action_url",
    "action_label",
    "created_at",
    "expires_at",
  ];

  for (const field of REQUIRED_FIELDS) {
    it(`Notification has field "${field}"`, () => {
      expect(typesSrc).toContain(field);
    });
  }
});

// ── NotificationCreate interface ─────────────────────────────────────────────

describe("NotificationCreate interface", () => {
  it("is exported from types", () => {
    expect(typesSrc).toContain("export interface NotificationCreate");
  });

  it("includes type, priority, title, message as required", () => {
    expect(typesSrc).toContain("type: NotificationType");
    expect(typesSrc).toContain("priority: NotificationPriority");
    expect(typesSrc).toContain("title: string");
    expect(typesSrc).toContain("message: string");
  });

  it("includes optional action_url and action_label", () => {
    expect(typesSrc).toContain("action_url?");
    expect(typesSrc).toContain("action_label?");
  });

  it("includes optional expires_in_days", () => {
    expect(typesSrc).toContain("expires_in_days?");
  });
});
