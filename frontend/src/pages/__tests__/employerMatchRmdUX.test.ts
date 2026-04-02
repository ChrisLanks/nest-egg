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

// ── Calculators page subtitle ─────────────────────────────────────────────

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
