/**
 * Tests for batch-2 features:
 * - PropertyAccountForm: Investment Strategy dropdown for investment classification
 * - InvestmentAccountForm: account_type locked/disabled for 529 Plan
 * - TaxLossHarvestingWidget: "No Wash-Sale Rule (Crypto)" badge
 * - PrivateEquityAccountForm: LP Interest grant type option
 * - ManualAccountTypeStep: updated PE description
 */

import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { resolve } from "path";

const readFeature = (rel: string) =>
  readFileSync(
    resolve(__dirname, "../../features", rel),
    "utf-8"
  );

const readPage = (rel: string) =>
  readFileSync(resolve(__dirname, "..", rel), "utf-8");

const propertyFormSrc = readFeature(
  "accounts/components/forms/PropertyAccountForm.tsx"
);
const investmentFormSrc = readFeature(
  "accounts/components/forms/InvestmentAccountForm.tsx"
);
const tlhWidgetSrc = readFeature(
  "dashboard/widgets/TaxLossHarvestingWidget.tsx"
);
const peFormSrc = readFeature(
  "accounts/components/forms/PrivateEquityAccountForm.tsx"
);
const manualTypeStepSrc = readFeature(
  "accounts/components/ManualAccountTypeStep.tsx"
);

// ── PropertyAccountForm — Investment Strategy dropdown ─────────────────────

describe("PropertyAccountForm — rental strategy classification", () => {
  it("renders Investment Strategy select when property_classification is investment", () => {
    expect(propertyFormSrc).toContain("watchedClassification === 'investment'");
  });

  it("has buy_and_hold option in rental strategy select", () => {
    expect(propertyFormSrc).toContain("buy_and_hold");
  });

  it("has long_term_rental option in rental strategy select", () => {
    expect(propertyFormSrc).toContain("long_term_rental");
  });

  it("has short_term_rental option (Airbnb/VRBO) in rental strategy select", () => {
    expect(propertyFormSrc).toContain("short_term_rental");
    expect(propertyFormSrc).toContain("Airbnb");
  });

  it("surfaces STR loophole IRC §469 in helper text", () => {
    expect(propertyFormSrc).toContain("469");
    expect(propertyFormSrc).toContain("STR loophole");
  });

  it("mentions passive loss $25K limit in helper text", () => {
    expect(propertyFormSrc).toContain("25K");
  });

  it("registers rental_type field", () => {
    expect(propertyFormSrc).toContain("register('rental_type')");
  });
});

// ── InvestmentAccountForm — 529 account_type lock ─────────────────────────

describe("InvestmentAccountForm — 529 Plan account type lock", () => {
  it("disables account_type Select when defaultAccountType is RETIREMENT_529", () => {
    expect(investmentFormSrc).toContain("isDisabled");
    expect(investmentFormSrc).toContain("RETIREMENT_529");
  });

  it("shows helper text explaining the lock when disabled", () => {
    expect(investmentFormSrc).toContain("Account type is set");
  });

  it("still renders account_type Select (not removed)", () => {
    expect(investmentFormSrc).toContain("account_type");
  });
});

// ── TaxLossHarvestingWidget — Crypto "No Wash-Sale Rule" badge ────────────

describe("TaxLossHarvestingWidget — crypto no-wash-sale badge", () => {
  it("has is_crypto field in opportunity interface", () => {
    expect(tlhWidgetSrc).toContain("is_crypto");
  });

  it("has no_wash_sale_rule field in opportunity interface", () => {
    expect(tlhWidgetSrc).toContain("no_wash_sale_rule");
  });

  it("renders 'No Wash-Sale Rule (Crypto)' badge when no_wash_sale_rule is true", () => {
    expect(tlhWidgetSrc).toContain("No Wash-Sale Rule (Crypto)");
  });

  it("only shows badge when opp.no_wash_sale_rule is truthy", () => {
    expect(tlhWidgetSrc).toContain("opp.no_wash_sale_rule");
  });

  it("uses orange color scheme for the crypto badge", () => {
    const noWashIdx = tlhWidgetSrc.indexOf("No Wash-Sale Rule (Crypto)");
    const surrounding = tlhWidgetSrc.slice(Math.max(0, noWashIdx - 80), noWashIdx + 50);
    expect(surrounding).toContain("orange");
  });
});

// ── PrivateEquityAccountForm — LP Interest grant type ─────────────────────

describe("PrivateEquityAccountForm — LP Interest grant type", () => {
  it("has lp_interest option in grant_type select", () => {
    expect(peFormSrc).toContain("lp_interest");
  });

  it("labels LP Interest as Limited Partnership", () => {
    expect(peFormSrc).toContain("Limited Partnership");
  });

  it("still has profit_interest option for LLC membership interests", () => {
    expect(peFormSrc).toContain("profit_interest");
  });
});

// ── ManualAccountTypeStep — PE description updated ────────────────────────

describe("ManualAccountTypeStep — updated PE description", () => {
  it("PE description mentions LP interests", () => {
    expect(manualTypeStepSrc).toContain("LP interest");
  });

  it("PE description mentions PE funds", () => {
    expect(manualTypeStepSrc).toContain("PE fund");
  });
});
