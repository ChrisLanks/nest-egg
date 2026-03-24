/**
 * Tests for NotificationBell component.
 *
 * Verifies structural contracts via source analysis — no DOM renderer required.
 */

import { readFileSync } from "fs";
import { resolve } from "path";
import { describe, expect, it } from "vitest";

const ROOT = resolve(__dirname, "..", "..", "..", "..");
const src = readFileSync(
  resolve(ROOT, "src/features/notifications/components/NotificationBell.tsx"),
  "utf-8",
);

describe("NotificationBell — polling behaviour", () => {
  it("polls unread count every 2 minutes", () => {
    expect(src).toContain("refetchInterval: 120_000");
  });

  it("pauses polling when tab is not focused", () => {
    expect(src).toContain("refetchIntervalInBackground: false");
  });

  it("invalidates all notification queries when popover opens", () => {
    expect(src).toContain('queryKey: ["notifications"]');
    expect(src).toContain("queryClient.invalidateQueries");
    expect(src).toContain("onOpen={onPopoverOpen}");
  });
});

describe("NotificationBell — unread badge", () => {
  it("renders a badge with unread count", () => {
    expect(src).toContain("unreadCount?.count");
    expect(src).toContain("Badge");
  });

  it("caps the badge display at 99+", () => {
    expect(src).toContain('"99+"');
  });

  it("uses the unread-count query key", () => {
    expect(src).toContain('"unread-count"');
  });
});

describe("NotificationBell — mark all read", () => {
  it("calls markAllAsRead API", () => {
    expect(src).toContain("notificationsApi.markAllAsRead");
  });

  it("shows a success toast after marking all read", () => {
    expect(src).toContain("All notifications marked as read");
    expect(src).toContain("useToast");
  });

  it("invalidates notification queries after marking all read", () => {
    // onSuccess must invalidate queries
    const onSuccessBlock = src.slice(src.indexOf("onSuccess"));
    expect(onSuccessBlock).toContain("invalidateQueries");
  });
});

describe("NotificationBell — expand / show all", () => {
  it("defaults to showing unread only (limit 10)", () => {
    expect(src).toContain("include_read: false");
    expect(src).toContain("limit: 10");
  });

  it("can expand to show all notifications", () => {
    expect(src).toContain("include_read: true");
    expect(src).toContain("View all notifications");
  });

  it("resets to unread-only view when popover reopens", () => {
    expect(src).toContain("setShowAll(false)");
  });
});

describe("NotificationBell — empty state", () => {
  it("shows a no-notifications message when list is empty", () => {
    expect(src).toContain("No notifications");
  });
});

describe("NotificationBell — renders NotificationItem for each notification", () => {
  it("imports and uses NotificationItem", () => {
    expect(src).toContain("NotificationItem");
  });
});
