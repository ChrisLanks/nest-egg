/**
 * Verify that pages fetching user-specific financial data pass
 * selectedUserId to their API calls via useUserView.
 *
 * Pages that are pure calculators (no user-specific GET queries),
 * auth flows, or settings pages are intentionally excluded.
 */

import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { resolve } from "path";

const ROOT = resolve(__dirname, "..", "..", "..");

function readSource(relPath: string): string {
  return readFileSync(resolve(ROOT, relPath), "utf-8");
}

const PAGES_REQUIRING_USER_VIEW = [
  "src/pages/FinancialRatiosTab.tsx",
  "src/pages/LiquidityDashboardTab.tsx",
  "src/pages/CharitableGivingPage.tsx",
  "src/pages/LoanModelerPage.tsx",
  "src/pages/EstatePage.tsx",
  "src/pages/NetWorthPercentileTab.tsx",
  "src/pages/ContributionHeadroomTab.tsx",
  "src/pages/DividendCalendarTab.tsx",
  "src/pages/EmployerMatchTab.tsx",
  "src/pages/CostBasisAgingTab.tsx",
  "src/pages/PensionModelerTab.tsx",
  "src/pages/IrmaaMedicareTab.tsx",
  "src/pages/InsuranceAuditTab.tsx",
  "src/pages/PePerformancePage.tsx",
];

describe("All financial pages respect user view selection", () => {
  for (const file of PAGES_REQUIRING_USER_VIEW) {
    const name = file.split("/").pop()!;

    it(`${name} imports useUserView`, () => {
      const source = readSource(file);
      expect(source).toContain("useUserView");
    });

    it(`${name} extracts selectedUserId`, () => {
      const source = readSource(file);
      expect(source).toContain("selectedUserId");
    });

    it(`${name} includes effectiveUserId in at least one queryKey`, () => {
      const source = readSource(file);
      // queryKey arrays should reference effectiveUserId (not selectedUserId)
      expect(source).toMatch(/queryKey:\s*\[.*effectiveUserId/);
    });
  }
});
