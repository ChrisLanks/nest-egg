/**
 * Tests for the 9 new advanced planning feature pages/tabs.
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

const assetLocationSrc = readPage("pages/AssetLocationTab.tsx");
const insuranceAuditSrc = readPage("pages/InsuranceAuditTab.tsx");
const pensionModelerSrc = readPage("pages/PensionModelerTab.tsx");
const financialRatiosSrc = readPage("pages/FinancialRatiosTab.tsx");
const employerMatchSrc = readPage("pages/EmployerMatchTab.tsx");
const dividendCalendarSrc = readPage("pages/DividendCalendarTab.tsx");
const costBasisAgingSrc = readPage("pages/CostBasisAgingTab.tsx");
const liquidityDashboardSrc = readPage("pages/LiquidityDashboardTab.tsx");
const netWorthPercentileSrc = readPage("pages/NetWorthPercentileTab.tsx");
const financialHealthPageSrc = readPage("pages/FinancialHealthPage.tsx");

const investmentToolsSrc = readPage("pages/InvestmentToolsPage.tsx");
const lifePlanningSrc = readPage("pages/LifePlanningPage.tsx");
const netWorthTimelineSrc = readPage("pages/NetWorthTimelinePage.tsx");
const appSrc = readPage("App.tsx");
const calendarSrc = readPage("pages/CalendarPage.tsx");
const rmdSrc = readPage("pages/RmdPlannerTab.tsx");
const estateSrc = readPage("pages/EstatePage.tsx");

// ── Nav consolidation source readers ─────────────────────────────────────────
const layoutSrc = readFileSync(resolve(ROOT, "components/Layout.tsx"), "utf-8");
const appTsxSrc = readPage("App.tsx");
const retirementPageSrc = readFileSync(resolve(ROOT, "features/retirement/pages/RetirementPage.tsx"), "utf-8");
const useNavDefaultsSrc = readFileSync(resolve(ROOT, "hooks/useNavDefaults.ts"), "utf-8");

// ── Feature 1: Asset Location ─────────────────────────────────────────────────

describe("AssetLocationTab", () => {
  it("exports AssetLocationTab", () => {
    expect(assetLocationSrc).toContain("export const AssetLocationTab");
  });

  it("calls the asset-location endpoint", () => {
    expect(assetLocationSrc).toContain("/holdings/asset-location");
  });

  it("shows optimization_score with CircularProgress", () => {
    expect(assetLocationSrc).toContain("optimization_score");
    expect(assetLocationSrc).toContain("CircularProgress");
  });

  it("shows is_optimal status badges", () => {
    expect(assetLocationSrc).toContain("is_optimal");
    expect(assetLocationSrc).toContain("Optimal");
    expect(assetLocationSrc).toContain("Suboptimal");
  });

  it("shows optimal_count and suboptimal_count stats", () => {
    expect(assetLocationSrc).toContain("optimal_count");
    expect(assetLocationSrc).toContain("suboptimal_count");
  });

  it("renders recommended_location and tax_treatment columns", () => {
    expect(assetLocationSrc).toContain("recommended_location");
    expect(assetLocationSrc).toContain("tax_treatment");
  });

  it("is embedded in InvestmentToolsPage as Asset Location tab", () => {
    expect(investmentToolsSrc).toContain("AssetLocationTab");
    expect(investmentToolsSrc).toContain("Asset Location");
  });
});

// ── Feature 2: Insurance Audit ────────────────────────────────────────────────

describe("InsuranceAuditTab", () => {
  it("exports InsuranceAuditTab", () => {
    expect(insuranceAuditSrc).toContain("export const InsuranceAuditTab");
  });

  it("calls the insurance-audit endpoint", () => {
    expect(insuranceAuditSrc).toContain("/estate/insurance-audit");
  });

  it("shows coverage_score stat", () => {
    expect(insuranceAuditSrc).toContain("coverage_score");
  });

  it("shows critical_gaps badge", () => {
    expect(insuranceAuditSrc).toContain("critical_gaps");
    expect(insuranceAuditSrc).toContain("critical");
  });

  it("shows has_coverage status and priority badge", () => {
    expect(insuranceAuditSrc).toContain("has_coverage");
    expect(insuranceAuditSrc).toContain("priority");
  });

  it("shows coverage_items list with tips", () => {
    expect(insuranceAuditSrc).toContain("coverage_items");
    expect(insuranceAuditSrc).toContain("tips");
  });

  it("is embedded in LifePlanningPage as Insurance Audit tab", () => {
    expect(lifePlanningSrc).toContain("InsuranceAuditTab");
    expect(lifePlanningSrc).toContain("Insurance Audit");
  });
});

// ── Feature 3: Pension Modeler ────────────────────────────────────────────────

describe("PensionModelerTab", () => {
  it("exports PensionModelerTab", () => {
    expect(pensionModelerSrc).toContain("export const PensionModelerTab");
  });

  it("calls the pension-model endpoint", () => {
    expect(pensionModelerSrc).toContain("/retirement/pension-model");
  });

  it("shows break_even_years with label", () => {
    expect(pensionModelerSrc).toContain("break_even_years");
    expect(pensionModelerSrc).toContain("Break-Even");
    expect(pensionModelerSrc).toContain("Take annuity");
    expect(pensionModelerSrc).toContain("Consider lump sum");
  });

  it("shows lifetime_value_20yr and lifetime_value_25yr", () => {
    expect(pensionModelerSrc).toContain("lifetime_value_20yr");
    expect(pensionModelerSrc).toContain("lifetime_value_25yr");
  });

  it("shows has_cola_protection badge", () => {
    expect(pensionModelerSrc).toContain("has_cola_protection");
    expect(pensionModelerSrc).toContain("COLA Protection");
  });

  it("shows survivor_monthly and recommendation", () => {
    expect(pensionModelerSrc).toContain("survivor_monthly");
    expect(pensionModelerSrc).toContain("recommendation");
  });

  it("is embedded in RetirementHubPage as Pension tab", () => {
    const retirementHubSrc = readPage("pages/RetirementHubPage.tsx");
    expect(retirementHubSrc).toContain("PensionModelerTab");
    expect(retirementHubSrc).toContain("Pension");
  });
});

// ── Feature 4: Financial Ratios ────────────────────────────────────────────────

describe("FinancialRatiosTab", () => {
  it("exports FinancialRatiosTab", () => {
    expect(financialRatiosSrc).toContain("export const FinancialRatiosTab");
  });

  it("calls the financial-ratios endpoint", () => {
    expect(financialRatiosSrc).toContain("/dashboard/financial-ratios");
  });

  it("shows overall_grade and overall_score with progress bar", () => {
    expect(financialRatiosSrc).toContain("overall_grade");
    expect(financialRatiosSrc).toContain("overall_score");
    expect(financialRatiosSrc).toContain("Progress");
  });

  it("has monthly income and spending inputs", () => {
    expect(financialRatiosSrc).toContain("monthlyIncome");
    expect(financialRatiosSrc).toContain("monthlySpending");
  });

  it("shows grade badges on each metric", () => {
    expect(financialRatiosSrc).toContain("metric.grade");
    expect(financialRatiosSrc).toContain("metric.formatted");
  });

  it("shows net_worth, liquid_assets, total_debt context", () => {
    expect(financialRatiosSrc).toContain("net_worth");
    expect(financialRatiosSrc).toContain("liquid_assets");
    expect(financialRatiosSrc).toContain("total_debt");
  });

  it("is embedded in FinancialHealthPage as Financial Ratios tab", () => {
    expect(financialHealthPageSrc).toContain("FinancialRatiosTab");
    expect(financialHealthPageSrc).toContain("Financial Ratios");
  });

  it("has tooltips on monthly income and spending inputs", () => {
    expect(financialRatiosSrc).toContain("Tooltip");
    expect(financialRatiosSrc).toContain("gross monthly income");
    expect(financialRatiosSrc).toContain("monthly essential");
  });

  it("auto-populates income and spending from dashboard summary on load", () => {
    // useEffect watches estimatedIncome/estimatedSpending and sets fields if not user-edited
    expect(financialRatiosSrc).toContain("useEffect");
    expect(financialRatiosSrc).toContain("incomeUserEdited");
    expect(financialRatiosSrc).toContain("spendingUserEdited");
    expect(financialRatiosSrc).toContain("setMonthlyIncome(Math.round(estimatedIncome))");
    expect(financialRatiosSrc).toContain("setMonthlySpending(Math.round(estimatedSpending))");
  });

  it("marks fields as user-edited on manual change to prevent auto-overwrite", () => {
    expect(financialRatiosSrc).toContain("setIncomeUserEdited(true)");
    expect(financialRatiosSrc).toContain("setSpendingUserEdited(true)");
  });

  it("shows pre-filled hint when auto-populated from transactions", () => {
    expect(financialRatiosSrc).toContain("Pre-filled from your recent transactions");
  });
});

// ── Feature 5: Employer Match ─────────────────────────────────────────────────

describe("EmployerMatchTab", () => {
  it("exports EmployerMatchTab", () => {
    expect(employerMatchSrc).toContain("export const EmployerMatchTab");
  });

  it("calls the employer-match endpoint", () => {
    expect(employerMatchSrc).toContain("/retirement/employer-match");
  });

  it("shows annual_match_value and estimated_left_on_table", () => {
    expect(employerMatchSrc).toContain("annual_match_value");
    expect(employerMatchSrc).toContain("estimated_left_on_table");
  });

  it("shows is_capturing_full_match badge (Full Match / Match Gap)", () => {
    expect(employerMatchSrc).toContain("is_capturing_full_match");
    expect(employerMatchSrc).toContain("Full Match");
    expect(employerMatchSrc).toContain("Match Gap");
  });

  it("shows summary stats: total_potential_match and total_left_on_table", () => {
    expect(employerMatchSrc).toContain("total_potential_match");
    expect(employerMatchSrc).toContain("total_left_on_table");
  });

  it("shows fully_optimized badge and action alert", () => {
    expect(employerMatchSrc).toContain("fully_optimized");
    expect(employerMatchSrc).toContain("account.action");
  });

  it("is embedded in InvestmentToolsPage as Employer Match tab", () => {
    expect(investmentToolsSrc).toContain("EmployerMatchTab");
    expect(investmentToolsSrc).toContain("Employer Match");
  });
});

// ── Feature 6: Dividend Calendar ──────────────────────────────────────────────

describe("DividendCalendarTab", () => {
  it("exports DividendCalendarTab", () => {
    expect(dividendCalendarSrc).toContain("export const DividendCalendarTab");
  });

  it("calls the dividend-calendar endpoint with year param", () => {
    expect(dividendCalendarSrc).toContain("/holdings/dividend-calendar?year=");
  });

  it("shows annual_total and avg_monthly stats", () => {
    expect(dividendCalendarSrc).toContain("annual_total");
    expect(dividendCalendarSrc).toContain("avg_monthly");
  });

  it("shows best_month highlight", () => {
    expect(dividendCalendarSrc).toContain("best_month");
    expect(dividendCalendarSrc).toContain("Best Month");
  });

  it("has year selector with prev/current/next year options", () => {
    expect(dividendCalendarSrc).toContain("currentYear - 1");
    expect(dividendCalendarSrc).toContain("currentYear + 1");
    expect(dividendCalendarSrc).toContain("setYear");
  });

  it("renders 12-month grid and by_ticker table", () => {
    expect(dividendCalendarSrc).toContain("months.map");
    expect(dividendCalendarSrc).toContain("by_ticker");
    expect(dividendCalendarSrc).toContain("event_count");
  });

  it("DividendCalendarTab is integrated into CalendarPage (not InvestmentToolsPage)", () => {
    // Dividend Calendar moved to the main Calendar page as a toggleable category
    expect(calendarSrc).toContain("dividend");
    expect(investmentToolsSrc).not.toContain("DividendCalendarTab");
  });
});

// ── Feature 7: Cost Basis Aging ───────────────────────────────────────────────

describe("CostBasisAgingTab", () => {
  it("exports CostBasisAgingTab", () => {
    expect(costBasisAgingSrc).toContain("export const CostBasisAgingTab");
  });

  it("calls the cost-basis-aging endpoint", () => {
    expect(costBasisAgingSrc).toContain("/holdings/cost-basis-aging");
  });

  it("shows approaching_count badge and summary_tip", () => {
    expect(costBasisAgingSrc).toContain("approaching_count");
    expect(costBasisAgingSrc).toContain("summary_tip");
  });

  it("shows short-term and long-term gain/loss stats", () => {
    expect(costBasisAgingSrc).toContain("short_term_gain");
    expect(costBasisAgingSrc).toContain("long_term_gain");
    expect(costBasisAgingSrc).toContain("short_term_loss");
  });

  it("filters lots by bucket (approaching, short_term, long_term)", () => {
    expect(costBasisAgingSrc).toContain(`l.bucket === "approaching"`);
    expect(costBasisAgingSrc).toContain(`l.bucket === "short_term"`);
    expect(costBasisAgingSrc).toContain(`l.bucket === "long_term"`);
  });

  it("shows days_held and days_to_long_term columns", () => {
    expect(costBasisAgingSrc).toContain("days_held");
    expect(costBasisAgingSrc).toContain("days_to_long_term");
  });

  it("is embedded in InvestmentToolsPage as Cost Basis tab", () => {
    expect(investmentToolsSrc).toContain("CostBasisAgingTab");
    expect(investmentToolsSrc).toContain("Cost Basis");
  });
});

// ── Feature 8: Liquidity Dashboard ────────────────────────────────────────────

describe("LiquidityDashboardTab", () => {
  it("exports LiquidityDashboardTab", () => {
    expect(liquidityDashboardSrc).toContain("export const LiquidityDashboardTab");
  });

  it("calls the liquidity endpoint", () => {
    expect(liquidityDashboardSrc).toContain("/dashboard/liquidity");
  });

  it("shows emergency_months_immediate with grade badge", () => {
    expect(liquidityDashboardSrc).toContain("emergency_months_immediate");
    expect(liquidityDashboardSrc).toContain("data.grade");
  });

  it("shows coverage_gap and target_months", () => {
    expect(liquidityDashboardSrc).toContain("coverage_gap");
    expect(liquidityDashboardSrc).toContain("target_months");
  });

  it("shows is_accessible column in account table", () => {
    expect(liquidityDashboardSrc).toContain("is_accessible");
    expect(liquidityDashboardSrc).toContain("Accessible");
    expect(liquidityDashboardSrc).toContain("Locked");
  });

  it("has optional monthly_spending override input", () => {
    expect(liquidityDashboardSrc).toContain("monthlySpending");
    expect(liquidityDashboardSrc).toContain("spending_is_estimated");
  });

  it("is embedded in FinancialHealthPage as Liquidity tab", () => {
    expect(financialHealthPageSrc).toContain("LiquidityDashboardTab");
    expect(financialHealthPageSrc).toContain("Liquidity");
  });

  it("has tooltips on stat labels and spending input", () => {
    expect(liquidityDashboardSrc).toContain("Tooltip");
    expect(liquidityDashboardSrc).toContain("Immediately Accessible");
    expect(liquidityDashboardSrc).toContain("Total Liquid");
    expect(liquidityDashboardSrc).toContain("Monthly Spending Used");
  });
});

// ── Feature 9: Net Worth Percentile ───────────────────────────────────────────

describe("NetWorthPercentileTab", () => {
  it("exports NetWorthPercentileTab", () => {
    expect(netWorthPercentileSrc).toContain("export const NetWorthPercentileTab");
  });

  it("calls the net-worth-percentile endpoint", () => {
    expect(netWorthPercentileSrc).toContain("/dashboard/net-worth-percentile");
  });

  it("shows estimated_percentile with CircularProgress", () => {
    expect(netWorthPercentileSrc).toContain("estimated_percentile");
    expect(netWorthPercentileSrc).toContain("CircularProgress");
  });

  it("shows percentile_label and age_bucket badge", () => {
    expect(netWorthPercentileSrc).toContain("percentile_label");
    expect(netWorthPercentileSrc).toContain("age_bucket");
  });

  it("shows benchmarks table with is_above status", () => {
    expect(netWorthPercentileSrc).toContain("benchmarks");
    expect(netWorthPercentileSrc).toContain("is_above");
    expect(netWorthPercentileSrc).toContain("Above");
    expect(netWorthPercentileSrc).toContain("Below");
  });

  it("shows encouragement alert and fidelity target", () => {
    expect(netWorthPercentileSrc).toContain("encouragement");
    expect(netWorthPercentileSrc).toContain("fidelity_target_multiplier");
  });

  it("has optional age override input", () => {
    expect(netWorthPercentileSrc).toContain("ageOverride");
    expect(netWorthPercentileSrc).toContain("Age Override");
  });

  it("is embedded in NetWorthTimelinePage as Percentile tab", () => {
    expect(netWorthTimelineSrc).toContain("NetWorthPercentileTab");
    expect(netWorthTimelineSrc).toContain("Percentile");
  });
});

// ── Financial Health Page ─────────────────────────────────────────────────────

describe("FinancialHealthPage", () => {
  it("exports FinancialHealthPage", () => {
    expect(financialHealthPageSrc).toContain("export const FinancialHealthPage");
  });

  it("lazy-imports FinancialRatiosTab", () => {
    expect(financialHealthPageSrc).toContain("import(\"./FinancialRatiosTab\")");
  });

  it("lazy-imports LiquidityDashboardTab", () => {
    expect(financialHealthPageSrc).toContain("import(\"./LiquidityDashboardTab\")");
  });

  it("has Financial Ratios tab label", () => {
    expect(financialHealthPageSrc).toContain("Financial Ratios");
  });

  it("has Liquidity & Emergency Fund tab label", () => {
    expect(financialHealthPageSrc).toContain("Liquidity");
    expect(financialHealthPageSrc).toContain("Emergency Fund");
  });

  it("has 2 Tab elements", () => {
    const tabMatches = financialHealthPageSrc.match(/<Tab\s/g) ?? [];
    expect(tabMatches.length).toBeGreaterThanOrEqual(2);
  });

  it("wraps each tab in a Tooltip", () => {
    expect(financialHealthPageSrc).toContain("Tooltip");
    // All four tabs should have tooltip wrappers
    const tooltipMatches = financialHealthPageSrc.match(/<Tooltip/g) ?? [];
    expect(tooltipMatches.length).toBeGreaterThanOrEqual(4);
  });

  it("includes descriptive tooltip text for each tab", () => {
    expect(financialHealthPageSrc).toContain("savings rate");
    expect(financialHealthPageSrc).toContain("emergency fund");
    expect(financialHealthPageSrc).toContain("credit score");
    expect(financialHealthPageSrc).toContain("recommendations");
  });
});

// ── App.tsx routing ────────────────────────────────────────────────────────────

describe("App.tsx routing", () => {
  it("has /financial-health route", () => {
    expect(appSrc).toContain("/financial-health");
  });

  it("imports FinancialHealthPage", () => {
    expect(appSrc).toContain("FinancialHealthPage");
    expect(appSrc).toContain("import(\"./pages/FinancialHealthPage\")");
  });

  it("has /investment-tools route", () => {
    expect(appSrc).toContain("/investment-tools");
  });

  it("has /estate-insurance route", () => {
    expect(appSrc).toContain("/estate-insurance");
  });

  it("has /net-worth-timeline route", () => {
    expect(appSrc).toContain("/net-worth-timeline");
  });
});

// ── Hub page integration ───────────────────────────────────────────────────────

describe("Hub page tab counts", () => {
  it("InvestmentToolsPage has 8 tabs (Dividend Calendar moved to CalendarPage)", () => {
    const tabMatches = investmentToolsSrc.match(/<Tab\s/g) ?? [];
    expect(tabMatches.length).toBeGreaterThanOrEqual(8);
  });

  it("LifePlanningPage (Estate & Insurance) has 2 tabs: Estate & Beneficiaries and Insurance Audit", () => {
    const tabMatches = lifePlanningSrc.match(/<Tab\s/g) ?? [];
    expect(tabMatches.length).toBeGreaterThanOrEqual(2);
    expect(lifePlanningSrc).toContain("Insurance Audit");
    expect(lifePlanningSrc).toContain("Estate");
  });

  it("NetWorthTimelinePage has Historical, Forecast, and Percentile tabs", () => {
    expect(netWorthTimelineSrc).toContain("Historical");
    expect(netWorthTimelineSrc).toContain("Forecast");
    expect(netWorthTimelineSrc).toContain("Percentile");
  });

  it("InvestmentToolsPage includes advanced tabs (Dividend Calendar tab removed — moved to Calendar)", () => {
    expect(investmentToolsSrc).toContain("Asset Location");
    expect(investmentToolsSrc).toContain("Employer Match");
    // The tab label is gone (comment reference allowed), but the lazy import and Tab component are removed
    expect(investmentToolsSrc).not.toContain("DividendCalendarTab");
    expect(investmentToolsSrc).toContain("Cost Basis");
  });
});

// ── Tab persistence ───────────────────────────────────────────────────────────

const taxCenterSrc = readPage("pages/TaxCenterPage.tsx");
const financialHealthPageSrc2 = readPage("pages/FinancialHealthPage.tsx");

describe("Tab persistence on all hub pages", () => {
  it("TaxCenterPage persists active tab to localStorage", () => {
    expect(taxCenterSrc).toContain("nest-egg-tab-tax-center");
    expect(taxCenterSrc).toContain("localStorage");
    expect(taxCenterSrc).toContain("handleTabChange");
  });

  it("LifePlanningPage (Estate & Insurance) persists active tab to localStorage", () => {
    expect(lifePlanningSrc).toContain("nest-egg-tab-life-planning");
    expect(lifePlanningSrc).toContain("localStorage");
  });

  it("InvestmentToolsPage persists active tab to localStorage", () => {
    expect(investmentToolsSrc).toContain("nest-egg-tab-investment-tools");
    expect(investmentToolsSrc).toContain("localStorage");
  });

  it("FinancialHealthPage persists active tab to localStorage", () => {
    expect(financialHealthPageSrc2).toContain("nest-egg-tab-financial-health");
    expect(financialHealthPageSrc2).toContain("localStorage");
  });

  it("NetWorthTimelinePage persists active tab to localStorage", () => {
    expect(netWorthTimelineSrc).toContain("nest-egg-tab-net-worth");
    expect(netWorthTimelineSrc).toContain("localStorage");
  });
});

// ── Insurance Audit dismissal ─────────────────────────────────────────────────

describe("InsuranceAuditTab dismissal", () => {
  it("has dismissed state backed by localStorage", () => {
    expect(insuranceAuditSrc).toContain("dismissed");
    expect(insuranceAuditSrc).toContain("insurance-audit-dismissed");
  });

  it("has onDismiss prop on InsuranceCard", () => {
    expect(insuranceAuditSrc).toContain("onDismiss");
  });

  it("has restore functionality for dismissed items", () => {
    expect(insuranceAuditSrc).toContain("Restore");
  });

  it("shows dismissed items in collapsible section", () => {
    expect(insuranceAuditSrc).toContain("Dismissed");
  });
});

// ── Asset location tooltips and why-explanation ───────────────────────────────

describe("AssetLocationTab tooltips and explanation", () => {
  it("shows why asset location matters explanation", () => {
    expect(assetLocationSrc).toContain("Why asset location");
  });

  it("has tooltips on table column headers", () => {
    expect(assetLocationSrc).toContain("Tooltip");
  });

  it("shows item.reason in tooltip on status cell", () => {
    expect(assetLocationSrc).toContain("reason");
  });
});

// ── Employer match tooltips ───────────────────────────────────────────────────

describe("EmployerMatchTab tooltips", () => {
  it("has Tooltip on summary stat labels", () => {
    expect(employerMatchSrc).toContain("Tooltip");
  });

  it("explains match percent concept", () => {
    expect(employerMatchSrc).toContain("match");
  });
});

// ── Cost basis aging explanation and tooltips ─────────────────────────────────

describe("CostBasisAgingTab explanation", () => {
  it("shows long-term capital gains rate explanation", () => {
    expect(costBasisAgingSrc).toContain("long-term capital gains");
  });

  it("has tooltip on Days to LT column", () => {
    expect(costBasisAgingSrc).toContain("Tooltip");
  });
});

// ── Financial Ratios auto-populate ───────────────────────────────────────────

describe("FinancialRatiosTab auto-populate from account data", () => {
  it("fetches an estimate for pre-filling income/spending inputs", () => {
    // Either dashboard/summary or savings-rate endpoint used for estimates
    const hasEstimateSource =
      financialRatiosSrc.includes("/dashboard/summary") ||
      financialRatiosSrc.includes("/financial-planning/savings-rate");
    expect(hasEstimateSource).toBe(true);
  });

  it("provides a way to use estimated values", () => {
    const hasUseEstimate =
      financialRatiosSrc.includes("Use this") ||
      financialRatiosSrc.includes("use this") ||
      financialRatiosSrc.includes("estimated") ||
      financialRatiosSrc.includes("Estimated");
    expect(hasUseEstimate).toBe(true);
  });
});

// ── Goals widget on dashboard ─────────────────────────────────────────────────

const dashboardSrc = readPage("pages/DashboardPage.tsx");

describe("Goals widget on dashboard", () => {
  it("loads savings-goals data for the widget", () => {
    expect(dashboardSrc).toContain("savings-goals");
  });

  it("renders a life goals section", () => {
    const hasGoals =
      dashboardSrc.includes("Life Goals") ||
      dashboardSrc.includes("GoalsWidget") ||
      dashboardSrc.includes("goals");
    expect(hasGoals).toBe(true);
  });

  it("has navigation link to /goals", () => {
    expect(dashboardSrc).toContain("/goals");
  });
});

// ── CalendarPage dividend integration ─────────────────────────────────────────

describe("CalendarPage dividend integration", () => {
  it("has showDividends toggle in CalendarPrefs interface", () => {
    expect(calendarSrc).toContain("showDividends");
  });
  it("fetches dividend-calendar endpoint when toggle enabled", () => {
    expect(calendarSrc).toContain("/holdings/dividend-calendar");
  });
  it("handles dividend event type with teal color", () => {
    expect(calendarSrc).toContain('"dividend"');
    expect(calendarSrc).toContain("teal");
  });
});

// ── RmdPlannerTab filing status ───────────────────────────────────────────────

describe("RmdPlannerTab filing status", () => {
  it("has filing status selector", () => {
    expect(rmdSrc).toContain("filingStatus");
  });
  it("does NOT send unused federal_rate_pct to API", () => {
    expect(rmdSrc).not.toContain("federal_rate_pct");
  });
});

// ── EstatePage legal disclaimer ───────────────────────────────────────────────

describe("EstatePage legal disclaimer", () => {
  it("has legal disclaimer warning", () => {
    expect(estateSrc).toContain("not legal or financial advice");
  });
  it("recommends licensed estate attorney", () => {
    expect(estateSrc).toContain("licensed estate attorney");
  });
});

// ── Nav consolidation audit ───────────────────────────────────────────────────

describe("Nav consolidation: Investments nav item", () => {
  it('Layout top nav shows "Investments" label', () => {
    expect(layoutSrc).toContain('"Investments"');
  });

  it("Investments navigates to /investments route", () => {
    expect(layoutSrc).toContain('"/investments"');
  });

  it("/portfolio redirect exists in App.tsx", () => {
    expect(appTsxSrc).toContain('"/portfolio"');
    expect(appTsxSrc).toContain('"/investments"');
  });
});

describe("Nav consolidation: Planning Tools rename", () => {
  it('InvestmentToolsPage heading is "Planning Tools"', () => {
    expect(investmentToolsSrc).toContain("Planning Tools");
  });

  it('Layout allPlanningItems has "Planning Tools" label', () => {
    expect(layoutSrc).toContain('"Planning Tools"');
  });

  it("Planning Tools still routes to /investment-tools", () => {
    expect(layoutSrc).toContain('"/investment-tools"');
  });
});

describe("Nav consolidation: Smart Insights and Financial Health in Analytics", () => {
  it("PE Performance is in allAnalyticsItems in Layout (moved from Planning)", () => {
    // PE Performance should appear in the analytics section
    const analyticsSection = layoutSrc.slice(
      layoutSrc.indexOf("allAnalyticsItems"),
      layoutSrc.indexOf("allPlanningItems")
    );
    expect(analyticsSection).toContain("PE Performance");
  });

  it("Financial Checkup (formerly Financial Health) is in allAnalyticsItems in Layout", () => {
    const analyticsSection = layoutSrc.slice(
      layoutSrc.indexOf("allAnalyticsItems"),
      layoutSrc.indexOf("allPlanningItems")
    );
    expect(analyticsSection).toContain("Financial Checkup");
  });

  it("Smart Insights is NOT in allPlanningItems", () => {
    const planningSection = layoutSrc.slice(
      layoutSrc.indexOf("allPlanningItems")
    );
    expect(planningSection).not.toContain('"Smart Insights"');
  });

  it("Financial Checkup is NOT in allPlanningItems", () => {
    const planningSection = layoutSrc.slice(
      layoutSrc.indexOf("allPlanningItems")
    );
    expect(planningSection).not.toContain('"Financial Checkup"');
  });
});

describe("Nav consolidation: NAV_SECTIONS matches Layout structure", () => {
  it("Planning Tools appears in NAV_SECTIONS Planning group", () => {
    expect(useNavDefaultsSrc).toContain("Planning Tools");
  });

  it("PE Performance appears in NAV_SECTIONS Analytics group (moved from Planning)", () => {
    const analyticsGroup = useNavDefaultsSrc.slice(
      useNavDefaultsSrc.indexOf('group: "Analytics"'),
      useNavDefaultsSrc.indexOf('group: "Planning"')
    );
    expect(analyticsGroup).toContain("PE Performance");
  });

  it("Financial Checkup appears in NAV_SECTIONS Analytics group (formerly Financial Health)", () => {
    const analyticsGroup = useNavDefaultsSrc.slice(
      useNavDefaultsSrc.indexOf('group: "Analytics"'),
      useNavDefaultsSrc.indexOf('group: "Planning"')
    );
    expect(analyticsGroup).toContain("Financial Checkup");
  });
});

describe("Nav consolidation: Retirement multi-user banner", () => {
  it("RetirementPage handles combined view with multiple members", () => {
    expect(retirementPageSrc).toContain("isCombinedView");
    // Retirement is per-person; multi-member view handled via member selection
    expect(retirementPageSrc).toContain("selectedIds");
  });

  it("RetirementPage uses Alert for the multi-member notice", () => {
    expect(retirementPageSrc).toContain('status="info"');
  });
});
