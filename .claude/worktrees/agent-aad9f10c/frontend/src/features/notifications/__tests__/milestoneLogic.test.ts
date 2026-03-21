/**
 * Tests for milestone celebration logic.
 *
 * Covers: extractThreshold parsing, highest-milestone selection,
 * and batch dismiss behavior.
 *
 * @vitest-environment jsdom
 */

import { describe, it, expect } from "vitest";
import { extractThreshold, getEmoji } from "../../../utils/milestoneUtils";

// ── Highest milestone selection ─────────────────────────────────────────────

interface MilestoneNotification {
  id: string;
  title: string;
  is_read: boolean;
}

function selectHighest(
  notifications: MilestoneNotification[],
  dismissed: Set<string>,
): MilestoneNotification | null {
  const unread = notifications.filter(
    (n) => !n.is_read && !dismissed.has(n.id),
  );
  if (unread.length === 0) return null;
  return unread.reduce((best, current) =>
    extractThreshold(current.title) > extractThreshold(best.title)
      ? current
      : best,
  );
}

// ── Tests ───────────────────────────────────────────────────────────────────

describe("extractThreshold", () => {
  it("parses $10,000 milestone", () => {
    expect(extractThreshold("Milestone reached: $10,000!")).toBe(10_000);
  });

  it("parses $1,000,000 milestone", () => {
    expect(extractThreshold("Milestone reached: $1,000,000!")).toBe(1_000_000);
  });

  it("parses $10,000,000 milestone", () => {
    expect(extractThreshold("Milestone reached: $10,000,000!")).toBe(
      10_000_000,
    );
  });

  it("returns 0 for unrecognized title", () => {
    expect(extractThreshold("Something else happened")).toBe(0);
  });

  it("returns 0 for empty string", () => {
    expect(extractThreshold("")).toBe(0);
  });
});

describe("getEmoji", () => {
  it("returns crown for $1M", () => {
    expect(getEmoji("Milestone reached: $1,000,000!")).toBe("👑");
  });

  it("returns fire for $100K", () => {
    expect(getEmoji("Milestone reached: $100,000!")).toBe("🔥");
  });

  it("returns generic celebration for unknown", () => {
    expect(getEmoji("Unknown milestone")).toBe("🎉");
  });
});

describe("selectHighest", () => {
  const make = (id: string, amount: string): MilestoneNotification => ({
    id,
    title: `Milestone reached: ${amount}!`,
    is_read: false,
  });

  it("picks the highest threshold from multiple notifications", () => {
    const notifications = [
      make("1", "$10,000"),
      make("2", "$50,000"),
      make("3", "$25,000"),
    ];
    const result = selectHighest(notifications, new Set());
    expect(result?.id).toBe("2");
  });

  it("returns null when all are dismissed", () => {
    const notifications = [make("1", "$10,000")];
    const result = selectHighest(notifications, new Set(["1"]));
    expect(result).toBeNull();
  });

  it("returns null for empty list", () => {
    const result = selectHighest([], new Set());
    expect(result).toBeNull();
  });

  it("skips already-read notifications", () => {
    const notifications = [
      { id: "1", title: "Milestone reached: $100,000!", is_read: true },
      make("2", "$10,000"),
    ];
    const result = selectHighest(notifications, new Set());
    expect(result?.id).toBe("2");
  });

  it("returns single notification when only one exists", () => {
    const notifications = [make("1", "$500,000")];
    const result = selectHighest(notifications, new Set());
    expect(result?.id).toBe("1");
  });

  it("handles massive jump — picks $1M over all lower thresholds", () => {
    const notifications = [
      make("1", "$10,000"),
      make("2", "$25,000"),
      make("3", "$50,000"),
      make("4", "$100,000"),
      make("5", "$250,000"),
      make("6", "$500,000"),
      make("7", "$1,000,000"),
    ];
    const result = selectHighest(notifications, new Set());
    expect(result?.id).toBe("7");
    expect(extractThreshold(result!.title)).toBe(1_000_000);
  });
});

describe("batch dismiss", () => {
  it("collects all milestone IDs for batch marking as read", () => {
    const notifications = [
      { id: "a", title: "Milestone reached: $10,000!", is_read: false },
      { id: "b", title: "Milestone reached: $25,000!", is_read: false },
      { id: "c", title: "Milestone reached: $50,000!", is_read: false },
    ];
    const dismissed = new Set<string>();
    const unread = notifications.filter(
      (n) => !n.is_read && !dismissed.has(n.id),
    );

    // All three should be collected for batch dismiss
    const idsToMarkRead = unread.map((n) => n.id);
    expect(idsToMarkRead).toEqual(["a", "b", "c"]);

    // But only the highest is displayed
    const highest = selectHighest(notifications, dismissed);
    expect(highest?.id).toBe("c");
  });
});
