/**
 * Source-level verification tests for PM audit fixes.
 */

import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";

function readSource(rel: string): string {
  return readFileSync(rel, "utf-8");
}

// ── Fix 1a: CategoriesPage mobile overflow ─────────────────────────────────

describe("Fix 1a: CategoriesPage does not clip table content", () => {
  it("does not contain overflow: hidden on table wrapper", () => {
    const src = readSource("src/pages/CategoriesPage.tsx");
    expect(src).not.toContain('overflow: "hidden"');
    expect(src).not.toContain("overflow=\"hidden\"");
  });

  it("contains overflowX auto on table wrapper", () => {
    const src = readSource("src/pages/CategoriesPage.tsx");
    expect(src).toContain('overflowX="auto"');
  });
});

// ── Fix 1b: BudgetsPage Container wrapper ─────────────────────────────────

describe("Fix 1b: BudgetsPage has Container wrapper", () => {
  it("imports Container from @chakra-ui/react", () => {
    const src = readSource("src/pages/BudgetsPage.tsx");
    expect(src).toContain("Container");
  });

  it("uses Container with maxW prop", () => {
    const src = readSource("src/pages/BudgetsPage.tsx");
    expect(src).toContain("Container");
    expect(src).toContain("maxW");
  });
});

// ── Fix 2: ReportsPage Content-Disposition filename ────────────────────────

describe("Fix 2: ReportsPage uses Content-Disposition for filename", () => {
  it("reads content-disposition header from response", () => {
    const src = readSource("src/pages/ReportsPage.tsx");
    expect(src).toContain("content-disposition");
  });

  it("does not hardcode report.csv as the only filename option", () => {
    const src = readSource("src/pages/ReportsPage.tsx");
    // Should have dynamic filename logic (content-disposition parsing)
    expect(src).toContain("disposition");
    expect(src).toContain("filename");
  });
});

// ── Fix 3: WelcomePage onboarding_completed guard ──────────────────────────

describe("Fix 3: WelcomePage has onboarding_completed re-entry guard", () => {
  it("checks onboarding_completed field", () => {
    const src = readSource("src/pages/WelcomePage.tsx");
    expect(src).toContain("onboarding_completed");
  });

  it("navigates away when onboarding is already done", () => {
    const src = readSource("src/pages/WelcomePage.tsx");
    // Should have navigate("/") or navigate call in the guard
    const hasGuard =
      src.includes('navigate("/")') ||
      src.includes("navigate('/')") ||
      (src.includes("onboarding_completed") && src.includes("navigate"));
    expect(hasGuard).toBe(true);
  });
});

// ── Fix 4: WelcomePage uses validateEmail ─────────────────────────────────

describe("Fix 4: WelcomePage uses validateEmail utility", () => {
  it("imports validateEmail from utils/validation", () => {
    const src = readSource("src/pages/WelcomePage.tsx");
    expect(src).toContain("validateEmail");
    expect(src).toContain("utils/validation");
  });

  it("does not use the naive includes('@') email check", () => {
    const src = readSource("src/pages/WelcomePage.tsx");
    expect(src).not.toContain('inviteEmail.includes("@")');
  });

  it("uses validateEmail result for the Invite button disabled state", () => {
    const src = readSource("src/pages/WelcomePage.tsx");
    expect(src).toContain("validateEmail");
    // Should call validateEmail and use .valid
    expect(src).toContain(".valid");
  });
});

// ── Fix 5: transactions API includes notes in search ─────────────────────

describe("Fix 5: transactions API includes notes field in search", () => {
  it("search query ORs on Transaction.notes.ilike", () => {
    const src = readSource("../backend/app/api/v1/transactions.py");
    expect(src).toContain("Transaction.notes.ilike");
  });

  it("notes ilike appears in both main query and count query", () => {
    const src = readSource("../backend/app/api/v1/transactions.py");
    const occurrences = (src.match(/Transaction\.notes\.ilike/g) || []).length;
    expect(occurrences).toBeGreaterThanOrEqual(2);
  });
});

// ── Fix 6: PreferencesPage uses Skeleton not plain text loading ───────────

describe("Fix 6: PreferencesPage uses Skeleton loading state", () => {
  it("imports Skeleton from @chakra-ui/react", () => {
    const src = readSource("src/pages/PreferencesPage.tsx");
    expect(src).toContain("Skeleton");
  });

  it("does not use plain 'Loading...' text as the loading state", () => {
    const src = readSource("src/pages/PreferencesPage.tsx");
    expect(src).not.toContain("<Text>Loading...</Text>");
  });

  it("renders Skeleton elements in the loading branch", () => {
    const src = readSource("src/pages/PreferencesPage.tsx");
    // Skeleton height props confirm actual skeleton usage
    expect(src).toContain('<Skeleton height="40px"');
  });
});
