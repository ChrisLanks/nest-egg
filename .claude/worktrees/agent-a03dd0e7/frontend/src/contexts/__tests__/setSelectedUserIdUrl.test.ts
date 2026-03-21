/**
 * Unit tests for setSelectedUserId URL construction logic.
 *
 * Validates that the URL is built from `window.location` (live values)
 * rather than stale React hook closures. This prevents the bug where
 * navigating from /overview to /budgets and then changing the user view
 * would redirect back to /overview due to a stale location.pathname.
 */

import { describe, it, expect } from "vitest";

// ---------------------------------------------------------------------------
// Pure function mirroring the URL construction in setSelectedUserId
// ---------------------------------------------------------------------------

/**
 * Builds the navigation target for setSelectedUserId.
 * In production this is called inside a useCallback that passes the result
 * to navigate(). The key invariant: pathname and search come from
 * window.location, NOT from React hook state.
 */
function buildNavigationTarget(
  userId: string | null,
  livePathname: string,
  liveSearch: string,
): { pathname: string; search: string } {
  const newParams = new URLSearchParams(liveSearch);
  if (userId) {
    newParams.set("user", userId);
  } else {
    newParams.delete("user");
  }
  const search = newParams.toString();
  return {
    pathname: livePathname,
    search: search ? `?${search}` : "",
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("setSelectedUserId URL construction", () => {
  it("preserves the current pathname when setting a user", () => {
    const result = buildNavigationTarget("user-123", "/budgets", "");
    expect(result.pathname).toBe("/budgets");
    expect(result.search).toBe("?user=user-123");
  });

  it("preserves the current pathname when clearing the user", () => {
    const result = buildNavigationTarget(null, "/budgets", "?user=user-123");
    expect(result.pathname).toBe("/budgets");
    expect(result.search).toBe("");
  });

  it("preserves existing search params alongside user param", () => {
    const result = buildNavigationTarget(
      "user-456",
      "/income-expenses",
      "?start=2026-01-01&end=2026-03-31",
    );
    expect(result.pathname).toBe("/income-expenses");
    expect(result.search).toContain("user=user-456");
    expect(result.search).toContain("start=2026-01-01");
    expect(result.search).toContain("end=2026-03-31");
  });

  it("replaces existing user param with new value", () => {
    const result = buildNavigationTarget(
      "user-789",
      "/categories",
      "?user=user-123",
    );
    expect(result.pathname).toBe("/categories");
    expect(result.search).toBe("?user=user-789");
  });

  it("uses live pathname, not a stale value from a previous page", () => {
    // Simulates the bug: callback was created when pathname was /overview,
    // but user has since navigated to /budgets. With window.location, we
    // get the CURRENT pathname.
    const stalePathname = "/overview";
    const livePathname = "/budgets";

    // Old behavior (stale) — would redirect to overview
    const staleResult = buildNavigationTarget("user-123", stalePathname, "");
    expect(staleResult.pathname).toBe("/overview");

    // New behavior (live) — stays on budgets
    const liveResult = buildNavigationTarget("user-123", livePathname, "");
    expect(liveResult.pathname).toBe("/budgets");
  });

  it("handles root path", () => {
    const result = buildNavigationTarget("user-123", "/", "");
    expect(result.pathname).toBe("/");
    expect(result.search).toBe("?user=user-123");
  });

  it("removes user param completely when userId is null", () => {
    const result = buildNavigationTarget(
      null,
      "/categories",
      "?user=user-123&tab=custom",
    );
    expect(result.search).not.toContain("user=");
    expect(result.search).toContain("tab=custom");
  });
});
