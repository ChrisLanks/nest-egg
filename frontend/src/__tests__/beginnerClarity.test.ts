/**
 * Tests for beginner clarity improvements (V, W, X, Y).
 *
 * V — CategoriesPage: plain-English subtitle (no "hierarchical organization" jargon)
 * W — InvestmentsPage: subtitle added + "expense ratios" explained at point of use
 * X — AccountDetailPage: tax treatment options explained inline
 * Y — TaxProjectionPage: AGI, W-2, W-4 acronyms expanded at first use
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

const catSrc = readSrc("pages/CategoriesPage.tsx");
const invSrc = readSrc("pages/InvestmentsPage.tsx");
const acctSrc = readSrc("pages/AccountDetailPage.tsx");
const taxSrc = readSrc("pages/TaxProjectionPage.tsx");

// ── V: CategoriesPage subtitle ────────────────────────────────────────────────

describe("CategoriesPage plain-English subtitle (V)", () => {
  it("does not use 'hierarchical organization' jargon", () => {
    expect(catSrc).not.toMatch(/hierarchical organization/i);
  });

  it("does not use 'max 2 levels' in the visible subtitle text", () => {
    // Only check the subtitle Text block near the heading — comments/code may use this phrase
    const headingIdx = catSrc.indexOf(">Categories<");
    expect(headingIdx).toBeGreaterThan(-1);
    const subtitleArea = catSrc.slice(headingIdx, headingIdx + 400);
    expect(subtitleArea).not.toMatch(/max 2\s+levels/i);
  });

  it("explains categories with a concrete example (parent/sub or e.g.)", () => {
    expect(catSrc).toMatch(/sub.categor|parent.*sub|e\.g\.|example/i);
  });

  it("mentions that categories are different from labels", () => {
    expect(catSrc).toMatch(/different from labels|labels.*free-form|separate.*labels/i);
  });
});

// ── W: InvestmentsPage subtitle + expense ratio ───────────────────────────────

describe("InvestmentsPage subtitle and expense ratio explanation (W)", () => {
  it("has a subtitle near the Investments heading", () => {
    const headingIdx = invSrc.indexOf(">Investments<");
    expect(headingIdx).toBeGreaterThan(-1);
    const after = invSrc.slice(headingIdx, headingIdx + 300);
    expect(after).toMatch(/Text/);
  });

  it("subtitle mentions portfolio value or growth", () => {
    expect(invSrc).toMatch(/portfolio|total value|how much it.s grown/i);
  });

  it("explains expense ratios as annual fees in plain language", () => {
    expect(invSrc).toMatch(/annual fee.*fund|fund.*annual fee|expense ratio.*fee|fee.*expense ratio|quietly charge/i);
  });

  it("empty state no longer uses bare 'expense ratios' without context", () => {
    // The old text was just "expense ratios" — now it adds explanation
    const oldText = "see your portfolio, expense ratios, and how your money is split.";
    expect(invSrc).not.toContain(oldText);
  });
});

// ── X: AccountDetailPage tax treatment explanations ──────────────────────────

describe("AccountDetailPage tax treatment inline explanations (X)", () => {
  it("shows a condensed explanation when no tax treatment is selected", () => {
    expect(acctSrc).toMatch(/Affects how this account is counted/i);
  });

  it("condensed hint covers all four tax treatment types", () => {
    expect(acctSrc).toMatch(/Traditional.*pre-tax|pre-tax.*Traditional/i);
    expect(acctSrc).toMatch(/Roth.*after-tax|after-tax.*Roth/i);
    expect(acctSrc).toMatch(/Taxable.*brokerage|brokerage.*checking/i);
    expect(acctSrc).toMatch(/HSA.*529|529.*HSA/i);
  });

  it("explanation is only shown when tax_treatment is not set (not noisy for power users)", () => {
    // The explanation block should be gated by !account.tax_treatment
    expect(acctSrc).toMatch(/!account\.tax_treatment/);
    // It should NOT show per-value paragraphs after a value is selected
    expect(acctSrc).not.toMatch(/tax_treatment === "pre_tax" && "Traditional/);
    expect(acctSrc).not.toMatch(/tax_treatment === "roth" && "Roth/);
  });

  it("mentions 401k or Traditional IRA as examples", () => {
    expect(acctSrc).toMatch(/Traditional IRA|401k|401\(k\)/i);
  });

  it("mentions tax-free growth for HSA/529", () => {
    expect(acctSrc).toMatch(/tax-free.*growth|tax-free growth/i);
  });
});

// ── Y: TaxProjectionPage acronym expansions ───────────────────────────────────

describe("TaxProjectionPage acronym expansions (Y)", () => {
  it("expands AGI to Adjusted Gross Income at first use", () => {
    expect(taxSrc).toMatch(/AGI.*Adjusted Gross Income|Adjusted Gross Income.*AGI/i);
  });

  it("explains what Adjusted Gross Income means", () => {
    expect(taxSrc).toMatch(/total income minus.*deductions|income minus certain deductions/i);
  });

  it("expands W-2 to explain what it is at first use", () => {
    expect(taxSrc).toMatch(/W-2.*form.*employer|employer.*W-2.*form/i);
  });

  it("explains W-4 as the form that controls withholding", () => {
    expect(taxSrc).toMatch(/W-4.*form.*employer.*withhold|W-4.*set how much tax/i);
  });
});
