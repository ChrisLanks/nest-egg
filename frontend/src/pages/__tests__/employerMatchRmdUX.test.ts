/**
 * Tests for Employer Match UX fixes and RMD table empty-state logic.
 */

import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { resolve } from "path";

const readPage = (rel: string) =>
  readFileSync(resolve(__dirname, "..", rel), "utf-8");

const employerMatchSrc = readPage("EmployerMatchTab.tsx");
const rmdSrc = readPage("RmdPlannerTab.tsx");
const investmentToolsSrc = readPage("InvestmentToolsPage.tsx");
const accountDetailSrc = readPage("AccountDetailPage.tsx");
const backdoorRothSrc = readPage("BackdoorRothTab.tsx");

// ── EmployerMatchTab ──────────────────────────────────────────────────────

describe("EmployerMatchTab — alert copy", () => {
  it("does NOT show 'To enable analysis' text (removed)", () => {
    expect(employerMatchSrc).not.toContain("To enable analysis");
  });

  it("shows distinct 'annual salary' path for accounts with match % but no salary", () => {
    expect(employerMatchSrc).toContain("annual salary");
  });

  it("still links to /accounts for both no-match and no-salary cases", () => {
    const linkCount = (employerMatchSrc.match(/to="\/accounts"/g) || []).length;
    expect(linkCount).toBeGreaterThanOrEqual(2);
  });

  it("top-level alert checks for both 'No employer match' and 'annual salary' conditions", () => {
    expect(employerMatchSrc).toContain("annual salary");
    expect(employerMatchSrc).toContain("No employer match");
  });
});

// ── RMD Planner — empty table state ──────────────────────────────────────

describe("RmdPlannerTab — empty table state", () => {
  it("shows an alert when no RMD years fall in the projection window", () => {
    expect(rmdSrc).toContain("No RMDs fall within");
  });

  it("mentions increasing projection years in the empty state message", () => {
    expect(rmdSrc).toContain("Years to Project");
  });

  it("references rmd_start_age in the empty state message", () => {
    expect(rmdSrc).toContain("data.rmd_start_age");
  });

  it("shows table only when RMD rows exist (conditional render)", () => {
    // The table is inside an else branch — check both branches exist
    expect(rmdSrc).toContain("length === 0");
    expect(rmdSrc).toContain("<Table");
  });
});

// ── Planning Tools page subtitle ─────────────────────────────────────────

describe("InvestmentToolsPage — subtitle", () => {
  it("does NOT just list tab names in the subtitle", () => {
    // Old subtitle was a comma-separated list of tab names
    expect(investmentToolsSrc).not.toContain(
      "FIRE progress, loan analysis, HSA strategy, employer match optimization"
    );
  });

  it("new subtitle is value-oriented", () => {
    expect(investmentToolsSrc).toContain("on track to retire early");
  });

  it("subtitle mentions actual account data", () => {
    expect(investmentToolsSrc).toContain("actual account data");
  });
});

// ── AccountDetailPage — Employer Match label inline ───────────────────────

describe("AccountDetailPage — Employer Match FormLabel inline", () => {
  it("uses display='flex' on the Employer Match FormLabel to keep tooltip inline", () => {
    // Find the block around 'Employer Match (%)'
    const idx = accountDetailSrc.indexOf("Employer Match (%)");
    expect(idx).toBeGreaterThan(-1);
    const surrounding = accountDetailSrc.slice(idx - 200, idx + 50);
    expect(surrounding).toContain('display="flex"');
  });

  it("uses alignItems='center' on the Employer Match FormLabel", () => {
    const idx = accountDetailSrc.indexOf("Employer Match (%)");
    const surrounding = accountDetailSrc.slice(idx - 200, idx + 50);
    expect(surrounding).toContain('alignItems="center"');
  });
});

// ── BackdoorRothTab — tooltips ────────────────────────────────────────────

describe("BackdoorRothTab — Contribution Headroom tooltip", () => {
  it("imports Tooltip", () => {
    expect(backdoorRothSrc).toContain("Tooltip");
  });

  it("wraps IRA Contribution Headroom label in a Tooltip", () => {
    const idx = backdoorRothSrc.indexOf("IRA Contribution Headroom");
    expect(idx).toBeGreaterThan(-1);
    // Tooltip opens before the StatLabel — search up to 600 chars back
    const before = backdoorRothSrc.slice(idx - 600, idx);
    expect(before).toContain("<Tooltip");
  });

  it("tooltip for IRA Contribution Headroom mentions IRS limit", () => {
    const idx = backdoorRothSrc.indexOf("IRA Contribution Headroom");
    const surrounding = backdoorRothSrc.slice(idx - 600, idx + 50);
    expect(surrounding).toMatch(/IRS limit|\$7,000|7,000/);
  });

  it("wraps Mega Backdoor Available label in a Tooltip", () => {
    const idx = backdoorRothSrc.indexOf("Mega Backdoor Available");
    expect(idx).toBeGreaterThan(-1);
    const before = backdoorRothSrc.slice(idx - 600, idx);
    expect(before).toContain("<Tooltip");
  });
});

// ── RetirementHubPage — merged SS/RMD/Pension/Variable Income ─────────────────

const retirementHubSrc = readPage("RetirementHubPage.tsx");

describe("RetirementHubPage — structure", () => {
  it("exports RetirementHubPage", () => {
    expect(retirementHubSrc).toContain("export const RetirementHubPage");
  });

  it("includes SS Optimizer tab", () => {
    expect(retirementHubSrc).toContain("SS Optimizer");
  });

  it("includes RMD Planner tab", () => {
    expect(retirementHubSrc).toContain("RMD Planner");
  });

  it("includes Pension tab", () => {
    expect(retirementHubSrc).toContain("Pension");
  });

  it("includes Variable Income tab", () => {
    expect(retirementHubSrc).toContain("Variable Income");
  });

  it("heading is Retirement & Income", () => {
    expect(retirementHubSrc).toContain("Retirement & Income");
  });
});

// ── LifePlanningPage (Estate & Insurance) — simplified ───────────────────────

const estateInsuranceSrc = readPage("LifePlanningPage.tsx");

describe("LifePlanningPage (Estate & Insurance) — structure", () => {
  it("heading is Estate & Insurance", () => {
    expect(estateInsuranceSrc).toContain("Estate & Insurance");
  });

  it("has Estate & Beneficiaries tab", () => {
    expect(estateInsuranceSrc).toContain("Estate");
  });

  it("has Insurance Audit tab", () => {
    expect(estateInsuranceSrc).toContain("Insurance Audit");
  });

  it("does NOT include SS Optimizer (moved to Retirement hub)", () => {
    expect(estateInsuranceSrc).not.toContain("SS Optimizer");
  });

  it("does NOT include RMD Planner (moved to Retirement hub)", () => {
    expect(estateInsuranceSrc).not.toContain("RMD Planner");
  });
});

// ── TaxCenterPage — Roth Conversion tab added ────────────────────────────────

const taxCenterSrc = readPage("TaxCenterPage.tsx");

describe("TaxCenterPage — Roth Conversion tab", () => {
  it("includes Roth Conversion tab", () => {
    expect(taxCenterSrc).toContain("Roth Conversion");
  });

  it("imports RothConversionPage as lazy", () => {
    expect(taxCenterSrc).toContain("RothConversionPage");
  });
});

// ── Layout.tsx — simple/advanced toggle ──────────────────────────────────────

const layoutSrc = readFileSync(
  resolve(__dirname, "..", "..", "components", "Layout.tsx"),
  "utf-8",
);

describe("Layout.tsx — simple/advanced toggle in header", () => {
  it("imports FiSliders icon", () => {
    expect(layoutSrc).toContain("FiSliders");
  });

  it("toggle button shows 'Advanced' or 'Simple' label", () => {
    expect(layoutSrc).toContain("Advanced");
    expect(layoutSrc).toContain("Simple");
  });

  it("toggle writes to nest-egg-show-advanced-nav localStorage key", () => {
    expect(layoutSrc).toContain("nest-egg-show-advanced-nav");
  });
});

// ── ReportsPage — no duplicate Tooltip import ─────────────────────────────

const reportsSrc = readPage("ReportsPage.tsx");

describe("ReportsPage — no duplicate Tooltip import", () => {
  it("aliases recharts Tooltip as RechartsTooltip", () => {
    expect(reportsSrc).toContain("Tooltip as RechartsTooltip");
  });

  it("uses RechartsTooltip in chart JSX", () => {
    expect(reportsSrc).toContain("<RechartsTooltip");
  });

  it("does not have two bare Tooltip imports", () => {
    // Count bare `Tooltip,` lines (not aliased)
    const bareCount = (reportsSrc.match(/^\s+Tooltip,\s*$/gm) ?? []).length;
    expect(bareCount).toBeLessThanOrEqual(1);
  });
});

// ── GoalForm — auto-select checking account for new goals ─────────────────

const goalFormSrc = readFileSync(
  resolve(__dirname, "..", "..", "features", "goals", "components", "GoalForm.tsx"),
  "utf-8",
);

describe("GoalForm — auto-select checking account for new goals", () => {
  it("filters accounts for checking types", () => {
    expect(goalFormSrc).toContain("depository_checking");
    expect(goalFormSrc).toContain("checking");
  });

  it("auto-sets account_id when single checking account found", () => {
    expect(goalFormSrc).toContain("checkingAccounts.length === 1");
    expect(goalFormSrc).toContain("setValue('account_id'");
  });

  it("only auto-selects when not editing an existing goal", () => {
    expect(goalFormSrc).toContain("isEditing");
    // The effect must guard against auto-select when editing
    const effectSrc = goalFormSrc.slice(
      goalFormSrc.indexOf("checkingAccounts"),
      goalFormSrc.indexOf("checkingAccounts") + 300,
    );
    expect(effectSrc).toContain("isEditing");
  });
});

// ── AccountDetailPage — rental property toggle ────────────────────────────

describe("AccountDetailPage — rental property toggle", () => {
  it("imports rentalPropertiesApi", () => {
    expect(accountDetailSrc).toContain("rentalPropertiesApi");
  });

  it("has is_rental_property field in Account interface", () => {
    expect(accountDetailSrc).toContain("is_rental_property");
  });

  it("has rental_monthly_income field in Account interface", () => {
    expect(accountDetailSrc).toContain("rental_monthly_income");
  });

  it("renders a rental property toggle Switch", () => {
    expect(accountDetailSrc).toContain("Rental Property");
    expect(accountDetailSrc).toContain("isRentalProperty");
  });

  it("calls updateRentalFields mutation", () => {
    expect(accountDetailSrc).toContain("updateRentalFieldsMutation");
  });
});
