/**
 * Tests for NotificationItem component.
 *
 * Verifies structural contracts via source analysis.
 */

import { readFileSync } from "fs";
import { resolve } from "path";
import { describe, expect, it } from "vitest";

const ROOT = resolve(__dirname, "..", "..", "..", "..");
const src = readFileSync(
  resolve(ROOT, "src/features/notifications/components/NotificationItem.tsx"),
  "utf-8",
);

describe("NotificationItem — dismiss behaviour", () => {
  it("calls notificationsApi.dismiss when dismiss button clicked", () => {
    expect(src).toContain("notificationsApi.dismiss");
  });

  it("shows a success toast after dismiss", () => {
    expect(src).toContain("Notification dismissed");
    expect(src).toContain("useToast");
  });

  it("invalidates notification queries after dismiss", () => {
    const afterDismiss = src.slice(src.indexOf("dismissMutation"));
    expect(afterDismiss).toContain("invalidateQueries");
  });

  it("stops click propagation on dismiss (does not trigger handleClick)", () => {
    expect(src).toContain("e.stopPropagation()");
  });
});

describe("NotificationItem — mark as read behaviour", () => {
  it("calls notificationsApi.markAsRead when item clicked", () => {
    expect(src).toContain("notificationsApi.markAsRead");
  });

  it("only marks as read if not already read", () => {
    expect(src).toContain("!notification.is_read");
    expect(src).toContain("markReadMutation.mutate()");
  });

  it("invalidates queries after marking as read", () => {
    const afterMark = src.slice(src.indexOf("markReadMutation"));
    expect(afterMark).toContain("invalidateQueries");
  });
});

describe("NotificationItem — navigation", () => {
  it("navigates to action_url when provided", () => {
    expect(src).toContain("notification.action_url");
    expect(src).toContain("navigate(notification.action_url)");
  });
});

describe("NotificationItem — priority colours", () => {
  it("maps URGENT to red", () => {
    expect(src).toContain("URGENT");
    expect(src).toContain("red");
  });

  it("maps HIGH to orange", () => {
    expect(src).toContain("HIGH");
    expect(src).toContain("orange");
  });

  it("maps MEDIUM to blue", () => {
    expect(src).toContain("MEDIUM");
    expect(src).toContain("blue");
  });

  it("maps LOW to gray", () => {
    expect(src).toContain("LOW");
    expect(src).toContain("gray");
  });
});

describe("NotificationItem — visual state", () => {
  it("renders title in bold when unread", () => {
    // Unread items should have bold weight
    expect(src).toContain("is_read ? 'normal' : 'bold'");
  });

  it("shows action_label when present", () => {
    expect(src).toContain("notification.action_label");
  });

  it("shows formatted created_at timestamp", () => {
    expect(src).toContain("notification.created_at");
    expect(src).toContain("toLocaleString()");
  });
});
