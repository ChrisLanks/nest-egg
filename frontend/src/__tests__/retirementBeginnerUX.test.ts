/**
 * Tests for retirement planner beginner UX improvements (M, N, O).
 *
 * M — ScenarioPanel: inline helper text for Return Assumptions defaults
 * N — RetirementPage: dismissable intro banner explaining Monte Carlo
 * O — RetirementPage: color-coded "Is this good?" badge on success rate
 *
 * Tests read source files directly (no DOM rendering needed).
 */

import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const srcRoot = join(__dirname, "..");

function readSrc(rel: string): string {
  return readFileSync(join(srcRoot, rel), "utf-8");
}

const scenarioPanelSrc = readSrc(
  "features/retirement/components/ScenarioPanel.tsx",
);
const retirementPageSrc = readSrc(
  "features/retirement/pages/RetirementPage.tsx",
);

// ── M: ScenarioPanel Return Assumptions helper text ───────────────────────────

describe("ScenarioPanel Return Assumptions helper text (M)", () => {
  it("has a helper text block near the Return Assumptions heading", () => {
    const idx = scenarioPanelSrc.indexOf("Return Assumptions");
    expect(idx).toBeGreaterThan(-1);
    const context = scenarioPanelSrc.slice(idx, idx + 500);
    expect(context).toMatch(/Text/);
  });

  it("mentions the default 7% pre-retirement rate", () => {
    expect(scenarioPanelSrc).toMatch(/7%.*pre.?retirement|pre.?retirement.*7%/i);
  });

  it("mentions the default 5% post-retirement rate", () => {
    expect(scenarioPanelSrc).toMatch(/5%.*post.?retirement|post.?retirement.*5%/i);
  });

  it("mentions the default 15% volatility", () => {
    expect(scenarioPanelSrc).toMatch(/15%.*volatility|volatility.*15%/i);
  });

  it("reassures user they can adjust later", () => {
    expect(scenarioPanelSrc).toMatch(/adjust later|starting point/i);
  });

  it("Volatility tooltip explains what 15% means for a stock-heavy portfolio", () => {
    // Find the Tooltip label text directly — it's a string in the source
    expect(scenarioPanelSrc).toMatch(/15%.*stock-heavy|stock-heavy.*15%/i);
  });

  it("Pre-Retirement Return tooltip explains why 7% (inflation + fees)", () => {
    const preIdx = scenarioPanelSrc.indexOf("Pre-Retirement Return");
    const context = scenarioPanelSrc.slice(Math.max(0, preIdx - 300), preIdx + 200);
    expect(context).toMatch(/inflation|fees/i);
  });
});

// ── N: RetirementPage beginner intro banner ───────────────────────────────────

describe("RetirementPage beginner intro banner (N)", () => {
  it("has a dismissable intro banner", () => {
    expect(retirementPageSrc).toMatch(/introBannerDismissed|retirement-intro-dismissed/i);
  });

  it("explains Monte Carlo in plain language", () => {
    expect(retirementPageSrc).toMatch(/monte carlo|1,000 simulation|random market/i);
  });

  it("tells the user what success rate means", () => {
    expect(retirementPageSrc).toMatch(/success rate.*lasts|money lasts/i);
  });

  it("gives a concrete threshold (80% is solid)", () => {
    expect(retirementPageSrc).toMatch(/80%.*solid|solid.*80%/i);
  });

  it("stores dismissal in localStorage", () => {
    expect(retirementPageSrc).toMatch(/nest-egg-retirement-intro-dismissed/);
  });

  it("has a dismiss button with aria-label", () => {
    expect(retirementPageSrc).toMatch(/aria-label.*[Dd]ismiss.*retirement|aria-label.*[Dd]ismiss/);
  });
});

// ── O: RetirementPage success rate color-coded badge ─────────────────────────

describe("RetirementPage success rate 'Is this good?' badge (O)", () => {
  it("shows a Badge near the success rate value", () => {
    const srIdx = retirementPageSrc.indexOf("Success Rate");
    expect(srIdx).toBeGreaterThan(-1);
    const context = retirementPageSrc.slice(srIdx, srIdx + 800);
    expect(context).toMatch(/Badge/);
  });

  it("uses green colorScheme at 80%+ threshold", () => {
    const srIdx = retirementPageSrc.indexOf("Success Rate");
    const context = retirementPageSrc.slice(srIdx, srIdx + 1000);
    expect(context).toMatch(/green/);
    expect(context).toMatch(/>= 80/);
  });

  it("uses yellow colorScheme for 60-79%", () => {
    const srIdx = retirementPageSrc.indexOf("Success Rate");
    const context = retirementPageSrc.slice(srIdx, srIdx + 1500);
    expect(context).toMatch(/yellow/);
    expect(context).toMatch(/>= 60/);
  });

  it("uses red colorScheme below 60%", () => {
    const srIdx = retirementPageSrc.indexOf("Success Rate");
    const context = retirementPageSrc.slice(srIdx, srIdx + 1500);
    expect(context).toMatch(/red/);
  });

  it("shows 'Good' label for high success rate", () => {
    expect(retirementPageSrc).toMatch(/"Good"/);
  });

  it("shows 'Moderate' label for mid success rate", () => {
    expect(retirementPageSrc).toMatch(/"Moderate"/);
  });

  it("shows 'Needs attention' label for low success rate", () => {
    expect(retirementPageSrc).toMatch(/Needs attention/);
  });

  it("badge has a tooltip explaining the threshold", () => {
    const srIdx = retirementPageSrc.indexOf("Success Rate");
    const context = retirementPageSrc.slice(srIdx, srIdx + 1200);
    expect(context).toMatch(/Tooltip/);
    expect(context).toMatch(/80\+|80%\+|80%.{0,10}solid/i);
  });
});
