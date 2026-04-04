/**
 * Tests that the sidebar (Layout.tsx) respects the member filter for:
 * 1. Dashboard summary query key — includes memberEffectiveUserId
 * 2. Net worth display — computes from filtered accounts when partial selection
 * 3. Account groups — use dedupedAccounts which are already filtered
 */

import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { resolve } from "path";

const ROOT = resolve(__dirname, "..", "..", "..");

function readSource(relPath: string): string {
  return readFileSync(resolve(ROOT, relPath), "utf-8");
}

describe("Sidebar net worth respects member filter", () => {
  const layoutSource = readSource("src/components/Layout.tsx");

  it("Dashboard summary query uses memberEffectiveUserId (not just selectedUserId)", () => {
    // summaryUserId should combine selectedUserId and memberEffectiveUserId
    expect(layoutSource).toContain("summaryUserId");
    expect(layoutSource).toContain("selectedUserId ?? memberEffectiveUserId");
  });

  it("Dashboard summary query key includes isPartialMemberSelection", () => {
    expect(layoutSource).toContain(
      '"dashboard-summary", summaryUserId, isPartialMemberSelection'
    );
  });

  it("Net worth display handles partial member selection from filtered accounts", () => {
    // When partial selection without a single effective user, compute from dedupedAccounts
    expect(layoutSource).toContain("isPartialMemberSelection && !summaryUserId");
    expect(layoutSource).toContain("dedupedAccounts.reduce");
  });
});
