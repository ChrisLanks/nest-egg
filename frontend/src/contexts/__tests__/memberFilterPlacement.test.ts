/**
 * Tests that authenticated API calls (useHouseholdMembers) are only made
 * inside ProtectedRoute — never on public routes like /login.
 *
 * Bug context: An earlier version called useHouseholdMembers from a provider
 * wrapping ALL routes (including /login). Unauthenticated users triggered:
 *   API 401 → logout + window.location.href = '/login' → full reload → repeat
 *
 * Architecture after unification:
 *   - UserViewContext lives in App.tsx but does NOT call useHouseholdMembers
 *   - UserViewToggle (inside Layout.tsx, inside ProtectedRoute) calls
 *     useHouseholdMembers and registers members into the context
 *   - MemberFilterContext is removed — member filter state lives in UserViewContext
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

describe("Authenticated API call placement — prevents login refresh loop", () => {
  it("App.tsx does NOT import useHouseholdMembers", () => {
    const appSource = readSource("src/App.tsx");
    expect(appSource).not.toContain("useHouseholdMembers");
  });

  it("UserViewContext does NOT call useHouseholdMembers (only type import)", () => {
    const contextSource = readSource("src/contexts/UserViewContext.tsx");
    // Type imports are erased at compile time and don't trigger API calls.
    // Verify there is no runtime call: useHouseholdMembers() with parens.
    expect(contextSource).not.toContain("useHouseholdMembers()");
    // Also ensure no runtime import (only type import is allowed)
    expect(contextSource).not.toMatch(/import\s+\{[^}]*useHouseholdMembers/);
  });

  it("UserViewContext holds member filter state (selectedMemberIds)", () => {
    const contextSource = readSource("src/contexts/UserViewContext.tsx");
    expect(contextSource).toContain("selectedMemberIds");
    expect(contextSource).toContain("_registerHouseholdMembers");
  });

  it("UserViewToggle calls useHouseholdMembers and registers members", () => {
    const toggleSource = readSource("src/components/UserViewToggle.tsx");
    expect(toggleSource).toContain("useHouseholdMembers");
    expect(toggleSource).toContain("_registerHouseholdMembers");
  });

  it("Layout.tsx renders UserViewToggle (which loads members)", () => {
    const layoutSource = readSource("src/components/Layout.tsx");
    expect(layoutSource).toContain("<UserViewToggle");
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

    // The public section should not reference Layout or useHouseholdMembers
    expect(publicSection).not.toContain("Layout");
    expect(publicSection).not.toContain("useHouseholdMembers");
  });

  it("MemberFilterContext no longer exists (merged into UserViewContext)", () => {
    // The old MemberFilterContext.tsx should not be imported by any component
    const appSource = readSource("src/App.tsx");
    const layoutSource = readSource("src/components/Layout.tsx");
    expect(appSource).not.toContain("MemberFilterContext");
    expect(appSource).not.toContain("MemberFilterProvider");
    expect(layoutSource).not.toContain("MemberFilterContext");
    expect(layoutSource).not.toContain("MemberFilterProvider");
  });
});

describe("UserViewContext — context guard", () => {
  it("useUserView throws when used outside provider", () => {
    const contextSource = readSource("src/contexts/UserViewContext.tsx");
    expect(contextSource).toContain("throw new Error");
    expect(contextSource).toContain("must be used within UserViewProvider");
  });
});

describe("Unified view control — no per-page MemberMultiSelect", () => {
  const pageFiles = [
    "src/pages/BudgetsPage.tsx",
    "src/pages/TrendsPage.tsx",
    "src/pages/FireMetricsPage.tsx",
    "src/pages/AccountsPage.tsx",
    "src/pages/InvestmentsPage.tsx",
    "src/pages/SavingsGoalsPage.tsx",
    "src/features/retirement/pages/RetirementPage.tsx",
    "src/features/income-expenses/pages/IncomeExpensesPage.tsx",
  ];

  for (const file of pageFiles) {
    const name = file.split("/").pop()!;
    it(`${name} does NOT import MemberMultiSelect`, () => {
      const source = readSource(file);
      expect(source).not.toContain("MemberMultiSelect");
    });

    it(`${name} does NOT import useMultiMemberFilter`, () => {
      const source = readSource(file);
      expect(source).not.toContain("useMultiMemberFilter");
    });
  }
});
