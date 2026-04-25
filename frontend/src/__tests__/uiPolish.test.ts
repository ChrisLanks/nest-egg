/**
 * Tests for UI polish improvements:
 * 1. Modal focus management (initialFocusRef)
 * 2. ScrollableTable component (mobile scroll hints)
 * 3. Contextual error messages
 */
import { describe, expect, it } from "vitest";
import * as fs from "fs";
import * as path from "path";

const root = path.resolve(__dirname, "../..");

function readFile(relPath: string): string {
  return fs.readFileSync(path.join(root, relPath), "utf-8");
}

// ---------------------------------------------------------------------------
// 1. Modal focus management — all form modals must have initialFocusRef
// ---------------------------------------------------------------------------
describe("Modal initialFocusRef", () => {
  const modalFiles = [
    "src/features/budgets/components/BudgetForm.tsx",
    "src/features/goals/components/GoalForm.tsx",
    "src/features/accounts/components/AddTransactionModal.tsx",
    "src/features/accounts/components/AddHoldingModal.tsx",
    "src/features/permissions/components/GrantModal.tsx",
    "src/features/retirement/components/LifeEventEditor.tsx",
    "src/features/rules/components/RuleBuilder.tsx",
  ];

  modalFiles.forEach((file) => {
    const name = path.basename(file, ".tsx");

    it(`${name} imports useRef`, () => {
      const src = readFile(file);
      expect(src).toMatch(/useRef/);
    });

    it(`${name} creates initialFocusRef`, () => {
      const src = readFile(file);
      expect(src).toMatch(/const initialFocusRef = useRef/);
    });

    it(`${name} passes initialFocusRef to Modal`, () => {
      const src = readFile(file);
      expect(src).toMatch(/initialFocusRef={initialFocusRef}/);
    });

    it(`${name} attaches ref to first input`, () => {
      const src = readFile(file);
      // Either ref={initialFocusRef} or ref={(el) => { ... initialFocusRef.current = el; }}
      expect(src).toMatch(/ref={initialFocusRef}|initialFocusRef\.current\s*=\s*el/);
    });
  });
});

// ---------------------------------------------------------------------------
// 2. ScrollableTable component
// ---------------------------------------------------------------------------
describe("ScrollableTable component", () => {
  it("exists and exports ScrollableTable", () => {
    const src = readFile("src/components/ScrollableTable.tsx");
    expect(src).toContain("export const ScrollableTable");
  });

  it("renders with role='region' and aria-label for accessibility", () => {
    const src = readFile("src/components/ScrollableTable.tsx");
    expect(src).toContain('role="region"');
    expect(src).toContain('aria-label="Scrollable table"');
  });

  it("shows gradient hint only on mobile via useBreakpointValue", () => {
    const src = readFile("src/components/ScrollableTable.tsx");
    expect(src).toContain("useBreakpointValue");
    expect(src).toContain("isMobile && showHint");
  });

  it("tracks scroll position to hide hint when fully scrolled", () => {
    const src = readFile("src/components/ScrollableTable.tsx");
    expect(src).toContain("onScroll={checkOverflow}");
    expect(src).toContain("scrollWidth");
  });

  it("is used on InvestmentsPage", () => {
    const src = readFile("src/pages/InvestmentsPage.tsx");
    expect(src).toContain("ScrollableTable");
    expect(src).toContain('from "../components/ScrollableTable"');
  });
});

// ---------------------------------------------------------------------------
// 3. Contextual error messages
// ---------------------------------------------------------------------------
describe("Contextual error messages", () => {
  it("InvestmentsPage shows contextual error for 503 (service unavailable)", () => {
    const src = readFile("src/pages/InvestmentsPage.tsx");
    expect(src).toContain("503");
    expect(src).toMatch(/market data service|temporarily unavailable/i);
  });

  it("InvestmentsPage shows contextual error for 401 (auth expired)", () => {
    const src = readFile("src/pages/InvestmentsPage.tsx");
    expect(src).toContain("401");
    expect(src).toMatch(/session.*expired|log in again/i);
  });

  it("TransactionsPage shows contextual error for 422 (validation)", () => {
    const src = readFile("src/pages/TransactionsPage.tsx");
    expect(src).toContain("422");
    expect(src).toMatch(/invalid.*range|filter|criteria/i);
  });

  it("BudgetsPage shows contextual error for 401", () => {
    const src = readFile("src/pages/BudgetsPage.tsx");
    expect(src).toContain("401");
    expect(src).toMatch(/session.*expired|log in again/i);
  });

  it("No generic 'An error occurred' without context on key pages", () => {
    const investSrc = readFile("src/pages/InvestmentsPage.tsx");
    const txnSrc = readFile("src/pages/TransactionsPage.tsx");
    // These should NOT have the bare generic message in error display
    expect(investSrc).not.toMatch(/Unable to load portfolio data\. Please try again\./);
    expect(txnSrc).not.toMatch(/Failed to load transactions\. Please refresh and try again\./);
  });
});
