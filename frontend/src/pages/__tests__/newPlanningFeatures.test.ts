/**
 * Tests for the 8 new planning feature pages/tabs.
 *
 * Uses source-inspection strategy (readFileSync) consistent with the existing
 * test style in this repo. Checks structural contracts:
 * - Named exports exist
 * - API endpoints called are correct
 * - Key UI elements are present in source
 * - Hub pages include the new tabs
 *
 * @vitest-environment node
 */

import { readFileSync } from "fs";
import { resolve } from "path";
import { describe, expect, it } from "vitest";

const ROOT = resolve(__dirname, "..", "..");  // frontend/src/

function readPage(relPath: string): string {
  return readFileSync(resolve(ROOT, relPath), "utf-8");
}

// ── Source readers ────────────────────────────────────────────────────────────

const forecastSrc = readPage("pages/NetWorthForecastTab.tsx");
const irmaaSrc = readPage("pages/IrmaaMedicareTab.tsx");
const backdoorSrc = readPage("pages/BackdoorRothTab.tsx");
const rmdSrc = readPage("pages/RmdPlannerTab.tsx");
const auditSrc = readPage("pages/BeneficiaryAuditCard.tsx");
const headroomSrc = readPage("pages/ContributionHeadroomTab.tsx");
const yieldSrc = readPage("pages/TaxEquivYieldTab.tsx");
const calendarSrc = readPage("pages/CalendarPage.tsx");

const taxCenterSrc = readPage("pages/TaxCenterPage.tsx");
const lifePlanningsSrc = readPage("pages/LifePlanningPage.tsx");
const investmentToolsSrc = readPage("pages/InvestmentToolsPage.tsx");
const netWorthTimelineSrc = readPage("pages/NetWorthTimelinePage.tsx");
const estateSrc = readPage("pages/EstatePage.tsx");

// ── Feature 1: Net Worth Forecast ─────────────────────────────────────────────

describe("NetWorthForecastTab", () => {
  it("exports NetWorthForecastTab", () => {
    expect(forecastSrc).toContain("export const NetWorthForecastTab");
  });

  it("calls the net-worth-forecast endpoint", () => {
    expect(forecastSrc).toContain("/api/v1/dashboard/net-worth-forecast");
  });

  it("renders three scenario lines (baseline, optimistic, pessimistic)", () => {
    expect(forecastSrc).toContain("baseline");
    expect(forecastSrc).toContain("optimistic");
    expect(forecastSrc).toContain("pessimistic");
  });

  it("shows retirement target and on-track badge", () => {
    expect(forecastSrc).toContain("retirement_target");
    expect(forecastSrc).toContain("on_track");
  });

  it("has retirement age and return rate controls", () => {
    expect(forecastSrc).toContain("retirementAge");
    expect(forecastSrc).toContain("annualReturn");
  });

  it("is embedded in NetWorthTimelinePage as Forecast tab", () => {
    expect(netWorthTimelineSrc).toContain("NetWorthForecastTab");
    expect(netWorthTimelineSrc).toContain("Forecast");
  });
});

// ── Feature 2: IRMAA / Medicare ───────────────────────────────────────────────

describe("IrmaaMedicareTab", () => {
  it("exports IrmaaMedicareTab", () => {
    expect(irmaaSrc).toContain("export const IrmaaMedicareTab");
  });

  it("calls the irmaa-projection endpoint", () => {
    expect(irmaaSrc).toContain("/api/v1/tax/irmaa-projection");
  });

  it("shows IRMAA tier badge", () => {
    expect(irmaaSrc).toContain("irmaa_tier");
    expect(irmaaSrc).toContain("tier_label");
  });

  it("displays lifetime premium estimate", () => {
    expect(irmaaSrc).toContain("lifetime_premium_estimate");
  });

  it("has filing status selector", () => {
    expect(irmaaSrc).toContain("filing_status");
    expect(irmaaSrc).toContain("married");
  });

  it("warns about 2-year IRMAA lookback", () => {
    expect(irmaaSrc).toContain("2 year");
  });

  it("is added as tab in TaxCenterPage", () => {
    expect(taxCenterSrc).toContain("IrmaaMedicareTab");
    expect(taxCenterSrc).toContain("Medicare");
  });
});

// ── Feature 3: Backdoor Roth ──────────────────────────────────────────────────

describe("BackdoorRothTab", () => {
  it("exports BackdoorRothTab", () => {
    expect(backdoorSrc).toContain("export const BackdoorRothTab");
  });

  it("calls the backdoor-roth-analysis endpoint", () => {
    expect(backdoorSrc).toContain("/api/v1/tax/backdoor-roth-analysis");
  });

  it("shows pro-rata warning", () => {
    expect(backdoorSrc).toContain("pro_rata_warning");
    expect(backdoorSrc).toContain("Pro-Rata");
  });

  it("shows mega backdoor section", () => {
    expect(backdoorSrc).toContain("mega_backdoor");
    expect(backdoorSrc).toContain("Mega Backdoor");
  });

  it("shows action steps", () => {
    expect(backdoorSrc).toContain("steps");
  });

  it("has direct Roth eligibility check", () => {
    expect(backdoorSrc).toContain("direct_roth_eligible");
  });

  it("is added as Roth Wizard tab in TaxCenterPage", () => {
    expect(taxCenterSrc).toContain("BackdoorRothTab");
    expect(taxCenterSrc).toContain("Roth Wizard");
  });
});

// ── Feature 4: RMD Planner ────────────────────────────────────────────────────

describe("RmdPlannerTab", () => {
  it("exports RmdPlannerTab", () => {
    expect(rmdSrc).toContain("export const RmdPlannerTab");
  });

  it("calls the rmd-planner endpoint", () => {
    expect(rmdSrc).toContain("/api/v1/rmd/rmd-planner");
  });

  it("shows years until RMD", () => {
    expect(rmdSrc).toContain("years_until_rmd");
  });

  it("shows total lifetime RMD estimate", () => {
    expect(rmdSrc).toContain("total_lifetime_rmd_estimate");
  });

  it("renders a chart for RMD over time", () => {
    expect(rmdSrc).toContain("LineChart");
  });

  it("shows estimated tax on RMD", () => {
    expect(rmdSrc).toContain("estimated_tax_on_rmd");
  });

  it("is added as RMD Planner tab in LifePlanningPage", () => {
    expect(lifePlanningsSrc).toContain("RmdPlannerTab");
    expect(lifePlanningsSrc).toContain("RMD Planner");
  });
});

// ── Feature 5: Beneficiary Audit ─────────────────────────────────────────────

describe("BeneficiaryAuditCard", () => {
  it("exports BeneficiaryAuditCard", () => {
    expect(auditSrc).toContain("export const BeneficiaryAuditCard");
  });

  it("calls the beneficiary-audit endpoint", () => {
    expect(auditSrc).toContain("/api/v1/estate/beneficiary-audit");
  });

  it("shows overall score", () => {
    expect(auditSrc).toContain("overall_score");
  });

  it("shows severity colors (critical/warning/ok)", () => {
    expect(auditSrc).toContain("critical");
    expect(auditSrc).toContain("warning");
    expect(auditSrc).toContain("ok");
  });

  it("shows missing_primary issue label", () => {
    expect(auditSrc).toContain("missing_primary");
  });

  it("is embedded in EstatePage", () => {
    expect(estateSrc).toContain("BeneficiaryAuditCard");
  });
});

// ── Feature 6: Contribution Headroom ─────────────────────────────────────────

describe("ContributionHeadroomTab", () => {
  it("exports ContributionHeadroomTab", () => {
    expect(headroomSrc).toContain("export const ContributionHeadroomTab");
  });

  it("calls the contribution-headroom endpoint", () => {
    expect(headroomSrc).toContain("/api/v1/tax/contribution-headroom");
  });

  it("shows remaining headroom", () => {
    expect(headroomSrc).toContain("remaining_headroom");
  });

  it("shows progress bars for each account", () => {
    expect(headroomSrc).toContain("Progress");
    expect(headroomSrc).toContain("pct_used");
  });

  it("shows catch-up badge", () => {
    expect(headroomSrc).toContain("catch_up_eligible");
    expect(headroomSrc).toContain("Catch-up");
  });

  it("has year selector", () => {
    expect(headroomSrc).toContain("taxYear");
  });

  it("is added as Contribution Headroom tab in TaxCenterPage", () => {
    expect(taxCenterSrc).toContain("ContributionHeadroomTab");
    expect(taxCenterSrc).toContain("Contribution Headroom");
  });
});

// ── Feature 7: Tax-Equivalent Yield ──────────────────────────────────────────

describe("TaxEquivYieldTab", () => {
  it("exports TaxEquivYieldTab", () => {
    expect(yieldSrc).toContain("export const TaxEquivYieldTab");
  });

  it("calls the tax-equivalent-yield endpoint", () => {
    expect(yieldSrc).toContain("/api/v1/holdings/tax-equivalent-yield");
  });

  it("shows nominal and tax-equivalent yield columns", () => {
    expect(yieldSrc).toContain("nominal_yield_pct");
    expect(yieldSrc).toContain("tax_equivalent_yield_pct");
  });

  it("shows blended portfolio yields", () => {
    expect(yieldSrc).toContain("portfolio_blended_nominal_yield_pct");
    expect(yieldSrc).toContain("portfolio_blended_tax_equiv_yield_pct");
  });

  it("allows federal and state rate overrides", () => {
    expect(yieldSrc).toContain("federalRate");
    expect(yieldSrc).toContain("stateRate");
  });

  it("is added as Tax-Equiv Yield tab in InvestmentToolsPage", () => {
    expect(investmentToolsSrc).toContain("TaxEquivYieldTab");
    expect(investmentToolsSrc).toContain("Tax-Equiv Yield");
  });
});

// ── Feature 8: Cash Flow Calendar Weekly View ─────────────────────────────────

describe("CalendarPage weekly view", () => {
  it("has viewMode state with monthly/weekly options", () => {
    expect(calendarSrc).toContain("viewMode");
    expect(calendarSrc).toContain("monthly");
    expect(calendarSrc).toContain("weekly");
  });

  it("has weekStart state", () => {
    expect(calendarSrc).toContain("weekStart");
  });

  it("has prev/next week navigation", () => {
    expect(calendarSrc).toContain("7 * 86400000");
  });

  it("shows weekly inflow/outflow totals", () => {
    expect(calendarSrc).toContain("totalInflow");
    expect(calendarSrc).toContain("totalOutflow");
  });

  it("shows daily net in weekly view", () => {
    expect(calendarSrc).toContain("dayNet");
  });

  it("has This Week button", () => {
    expect(calendarSrc).toContain("This Week");
  });

  it("shows 7-column grid for weekly view", () => {
    expect(calendarSrc).toContain("weekDays");
    expect(calendarSrc).toContain("length: 7");
  });
});

// ── Hub page integration ──────────────────────────────────────────────────────

describe("Hub page tab counts", () => {
  it("TaxCenterPage has 6 tabs", () => {
    const tabMatches = taxCenterSrc.match(/<Tab\s/g) ?? [];
    expect(tabMatches.length).toBeGreaterThanOrEqual(6);
  });

  it("LifePlanningPage has 4 tabs", () => {
    const tabMatches = lifePlanningsSrc.match(/<Tab\s/g) ?? [];
    expect(tabMatches.length).toBeGreaterThanOrEqual(4);
  });

  it("InvestmentToolsPage has 5 tabs", () => {
    const tabMatches = investmentToolsSrc.match(/<Tab\s/g) ?? [];
    expect(tabMatches.length).toBeGreaterThanOrEqual(5);
  });

  it("NetWorthTimelinePage has Historical and Forecast tabs", () => {
    expect(netWorthTimelineSrc).toContain("Historical");
    expect(netWorthTimelineSrc).toContain("Forecast");
  });
});
