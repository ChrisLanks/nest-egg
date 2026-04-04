/**
 * Tests that effectiveUserId is exposed by useUserView and used
 * consistently across the app for API calls.
 *
 * effectiveUserId = selectedUserId ?? memberEffectiveUserId ?? null
 *
 * This ensures the member filter checkboxes (partial selection)
 * properly filter API data on ALL pages, not just the sidebar.
 */

import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { resolve } from "path";

const ROOT = resolve(__dirname, "..", "..", "..");

function readSource(relPath: string): string {
  return readFileSync(resolve(ROOT, relPath), "utf-8");
}

describe("effectiveUserId — context definition", () => {
  const contextSource = readSource("src/contexts/UserViewContext.tsx");

  it("useUserView returns effectiveUserId", () => {
    expect(contextSource).toContain("effectiveUserId");
  });

  it("effectiveUserId combines selectedUserId and memberEffectiveUserId", () => {
    expect(contextSource).toContain(
      "selectedUserId ?? memberFilter.memberEffectiveUserId ?? null"
    );
  });
});

describe("effectiveUserId — API calls use effectiveUserId, not selectedUserId", () => {
  // Sample pages that make API calls — verify they pass effectiveUserId
  const pagesToCheck = [
    "src/pages/TaxProjectionPage.tsx",
    "src/pages/TaxBucketsPage.tsx",
    "src/pages/FinancialRatiosTab.tsx",
    "src/pages/CashFlowPage.tsx",
    "src/pages/BudgetsPage.tsx",
    "src/features/dashboard/widgets/YearOverYearWidget.tsx",
    "src/features/dashboard/widgets/NetWorthChartWidget.tsx",
  ];

  for (const file of pagesToCheck) {
    const name = file.split("/").pop()!;

    it(`${name} destructures effectiveUserId from useUserView`, () => {
      const source = readSource(file);
      expect(source).toContain("effectiveUserId");
    });

    it(`${name} uses effectiveUserId (not selectedUserId) in queryKey`, () => {
      const source = readSource(file);
      // queryKey should reference effectiveUserId
      expect(source).toMatch(/queryKey:\s*\[.*effectiveUserId/);
    });
  }
});
