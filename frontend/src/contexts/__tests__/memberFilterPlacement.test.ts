/**
 * Tests that MemberFilterProvider is placed correctly in the component tree.
 *
 * Bug context: MemberFilterProvider was originally placed in App.tsx wrapping
 * ALL routes (including /login). Because it calls useHouseholdMembers() which
 * hits an authenticated API endpoint, unauthenticated users on /login triggered:
 *   API 401 → logout + window.location.href = '/login' → full reload → repeat
 *
 * Fix: MemberFilterProvider lives inside Layout.tsx, which only renders within
 * ProtectedRoute (authenticated users only).
 *
 * These tests read the source files as strings to enforce the structural
 * invariant without needing to render React components.
 */

import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { resolve } from "path";

const ROOT = resolve(__dirname, "..", "..", "..");

function readSource(relPath: string): string {
  return readFileSync(resolve(ROOT, relPath), "utf-8");
}

describe("MemberFilterProvider placement — prevents login refresh loop", () => {
  it("App.tsx does NOT import MemberFilterProvider", () => {
    const appSource = readSource("src/App.tsx");
    expect(appSource).not.toContain("MemberFilterProvider");
    expect(appSource).not.toContain("MemberFilterContext");
  });

  it("App.tsx does NOT import useHouseholdMembers", () => {
    const appSource = readSource("src/App.tsx");
    expect(appSource).not.toContain("useHouseholdMembers");
  });

  it("Layout.tsx imports and uses MemberFilterProvider", () => {
    const layoutSource = readSource("src/components/Layout.tsx");
    expect(layoutSource).toContain("import { MemberFilterProvider }");
    expect(layoutSource).toContain("<MemberFilterProvider>");
    expect(layoutSource).toContain("</MemberFilterProvider>");
  });

  it("Layout.tsx is only rendered inside ProtectedRoute (verified via App.tsx)", () => {
    const appSource = readSource("src/App.tsx");

    // Find where ProtectedRoute and Layout appear
    const protectedRouteIndex = appSource.indexOf("<ProtectedRoute");
    const layoutIndex = appSource.indexOf("<Layout");

    // Layout must come AFTER ProtectedRoute in the JSX tree
    expect(protectedRouteIndex).toBeGreaterThan(-1);
    expect(layoutIndex).toBeGreaterThan(-1);
    expect(layoutIndex).toBeGreaterThan(protectedRouteIndex);

    // Layout should NOT appear in the public routes section
    const publicRoutesComment = appSource.indexOf("{/* Public routes */}");
    const protectedRoutesComment = appSource.indexOf("{/* Protected routes");
    expect(publicRoutesComment).toBeGreaterThan(-1);
    expect(protectedRoutesComment).toBeGreaterThan(-1);

    // Layout reference must be after the protected routes comment
    expect(layoutIndex).toBeGreaterThan(protectedRoutesComment);
  });

  it("public routes (/login, /register, etc.) are NOT inside Layout", () => {
    const appSource = readSource("src/App.tsx");

    // Extract the section between "Public routes" comment and "Protected routes" comment
    const publicStart = appSource.indexOf("{/* Public routes */}");
    const protectedStart = appSource.indexOf("{/* Protected routes");
    const publicSection = appSource.slice(publicStart, protectedStart);

    // The public section should not reference Layout or MemberFilterProvider
    expect(publicSection).not.toContain("Layout");
    expect(publicSection).not.toContain("MemberFilterProvider");
    expect(publicSection).not.toContain("useHouseholdMembers");
  });
});

describe("MemberFilterContext — context guard", () => {
  it("useMemberFilterContext throws when used outside provider", () => {
    const contextSource = readSource("src/contexts/MemberFilterContext.tsx");

    // Verify the guard exists — must throw when context is undefined
    expect(contextSource).toContain("if (!ctx)");
    expect(contextSource).toContain("throw new Error");
    expect(contextSource).toContain("must be used within MemberFilterProvider");
  });

  it("MemberFilterProvider calls useHouseholdMembers (the authenticated hook)", () => {
    // This confirms that placing the provider on public routes WOULD cause
    // the 401 loop — reinforcing the need for the structural invariant above
    const contextSource = readSource("src/contexts/MemberFilterContext.tsx");
    expect(contextSource).toContain("useHouseholdMembers");
  });
});
