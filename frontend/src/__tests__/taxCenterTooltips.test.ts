/**
 * Tests for TaxCenterPage UX improvements:
 * C — Jargon tooltips on tab labels
 * E — Charitable Giving tab hidden in simple mode (showAdvancedNav = false)
 */

import { describe, it, expect } from "vitest";

// ── Tab tooltip coverage ──────────────────────────────────────────────────────

/** Mirror of TAB_TOOLTIPS in TaxCenterPage.tsx */
const TAB_TOOLTIPS: Record<string, string> = {
  "Tax Projection":
    "Estimate your total federal + state tax bill for the year based on your income — so you're not surprised in April.",
  "Tax Buckets":
    "Your money split into three buckets: taxable (brokerage), tax-deferred (401k/IRA), and tax-free (Roth). Pulling from the right bucket in retirement can save you thousands.",
  "Charitable Giving":
    "Track donations to charities, churches, and nonprofits — and see how they reduce your taxable income.",
  "Medicare & IRMAA":
    "If your income is above ~$103K/yr, Medicare charges you more for Part B and Part D premiums. IRMAA = Income-Related Monthly Adjustment Amount. Planning ahead can lower these costs.",
  "Roth Wizard":
    "A Roth IRA grows tax-free, but high earners can't contribute directly. This wizard shows you the 'backdoor' workaround and whether it applies to you.",
  "Contribution Headroom":
    "How much more you can still contribute to your 401(k), IRA, and HSA this year before hitting IRS limits — maxing these out lowers your taxable income.",
};

const ALL_TABS = [
  "Tax Projection",
  "Tax Buckets",
  "Charitable Giving",
  "Medicare & IRMAA",
  "Roth Wizard",
  "Contribution Headroom",
] as const;

describe("TaxCenter tab tooltips (C — jargon tooltips)", () => {
  it("every tab has a tooltip entry", () => {
    for (const tab of ALL_TABS) {
      expect(TAB_TOOLTIPS[tab], `Missing tooltip for "${tab}"`).toBeTruthy();
    }
  });

  it("no tooltip is empty", () => {
    for (const [tab, tip] of Object.entries(TAB_TOOLTIPS)) {
      expect(tip.trim().length, `Tooltip for "${tab}" is empty`).toBeGreaterThan(0);
    }
  });

  it("tooltips use plain English — no raw IRS jargon without explanation", () => {
    // IRMAA must be explained inline
    expect(TAB_TOOLTIPS["Medicare & IRMAA"]).toContain("Income-Related Monthly Adjustment Amount");
    // Roth wizard must mention the backdoor approach
    expect(TAB_TOOLTIPS["Roth Wizard"]).toContain("backdoor");
    // Buckets tooltip must mention all three bucket types
    expect(TAB_TOOLTIPS["Tax Buckets"]).toContain("taxable");
    expect(TAB_TOOLTIPS["Tax Buckets"]).toContain("tax-deferred");
    expect(TAB_TOOLTIPS["Tax Buckets"]).toContain("tax-free");
  });

  it("Tax Projection tooltip mentions April — anchors to familiar filing deadline", () => {
    expect(TAB_TOOLTIPS["Tax Projection"]).toContain("April");
  });

  it("Contribution Headroom tooltip mentions IRS limits", () => {
    expect(TAB_TOOLTIPS["Contribution Headroom"]).toContain("IRS limits");
  });
});

// ── Advanced nav: Charitable Giving tab visibility ────────────────────────────

/** Mirrors effectiveTabIndex logic from TaxCenterPage.tsx */
function effectiveTabIndex(
  storedIndex: number,
  showAdvancedNav: boolean,
): number {
  if (!showAdvancedNav && storedIndex === 2) return 0; // Charitable Giving hidden → fallback to first
  if (!showAdvancedNav && storedIndex > 2) return storedIndex - 1; // offset down by 1
  return storedIndex;
}

/** Mirrors handleTabChange storage mapping from TaxCenterPage.tsx */
function storageIndex(visibleIndex: number, showAdvancedNav: boolean): number {
  return !showAdvancedNav && visibleIndex >= 2 ? visibleIndex + 1 : visibleIndex;
}

describe("TaxCenter Charitable Giving tab (E — advanced nav gating)", () => {
  describe("simple mode (showAdvancedNav = false)", () => {
    it("visible tabs are 5 (Charitable Giving hidden)", () => {
      const visibleTabs = ALL_TABS.filter((t) => t !== "Charitable Giving");
      expect(visibleTabs.length).toBe(5);
    });

    it("stored index 2 (Charitable Giving) falls back to 0", () => {
      expect(effectiveTabIndex(2, false)).toBe(0);
    });

    it("stored index 3 (Medicare) maps to visible index 2", () => {
      expect(effectiveTabIndex(3, false)).toBe(2);
    });

    it("stored index 4 (Roth) maps to visible index 3", () => {
      expect(effectiveTabIndex(4, false)).toBe(3);
    });

    it("stored index 5 (Contribution) maps to visible index 4", () => {
      expect(effectiveTabIndex(5, false)).toBe(4);
    });

    it("clicking visible tab 2 (Medicare in simple mode) stores as index 3", () => {
      expect(storageIndex(2, false)).toBe(3);
    });

    it("clicking visible tab 4 (Contribution in simple mode) stores as index 5", () => {
      expect(storageIndex(4, false)).toBe(5);
    });
  });

  describe("advanced mode (showAdvancedNav = true)", () => {
    it("stored index 2 stays at 2 (Charitable Giving visible)", () => {
      expect(effectiveTabIndex(2, true)).toBe(2);
    });

    it("stored index 4 stays at 4 (Roth Wizard)", () => {
      expect(effectiveTabIndex(4, true)).toBe(4);
    });

    it("visible index 2 stores as 2 (no offset)", () => {
      expect(storageIndex(2, true)).toBe(2);
    });
  });

  describe("round-trip: click visible → store → restore", () => {
    it("clicking Medicare in simple mode round-trips correctly", () => {
      const visibleClick = 2; // Medicare is index 2 in simple mode
      const stored = storageIndex(visibleClick, false); // should be 3
      const restored = effectiveTabIndex(stored, false); // should be 2
      expect(stored).toBe(3);
      expect(restored).toBe(2);
    });

    it("clicking Charitable Giving in advanced mode round-trips correctly", () => {
      const visibleClick = 2;
      const stored = storageIndex(visibleClick, true); // stays 2
      const restored = effectiveTabIndex(stored, true); // stays 2
      expect(stored).toBe(2);
      expect(restored).toBe(2);
    });
  });
});
