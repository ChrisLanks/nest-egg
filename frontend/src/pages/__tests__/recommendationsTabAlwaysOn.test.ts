import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { resolve } from "path";

const ROOT = resolve(__dirname, "..", "..");

describe("FinancialHealthPage — Recommendations tab always shown", () => {
  const src = readFileSync(resolve(ROOT, "pages/FinancialHealthPage.tsx"), "utf-8");

  it("does not call getShowRecommendations (toggle removed)", () => {
    expect(src).not.toContain("getShowRecommendations");
  });

  it("does not read nest-egg-show-recommendations-tab from localStorage", () => {
    expect(src).not.toContain("nest-egg-show-recommendations-tab");
  });

  it("Recommendations Tab is rendered unconditionally", () => {
    // The tab should appear as a plain Tab, not inside a conditional
    expect(src).toContain("Recommendations");
  });
});

describe("PreferencesPage — Show Recommendations toggle removed", () => {
  const src = readFileSync(resolve(ROOT, "pages/PreferencesPage.tsx"), "utf-8");

  it("does not contain Show Recommendations tab toggle", () => {
    expect(src).not.toContain("showRecommendationsTab");
  });

  it("does not write nest-egg-show-recommendations-tab", () => {
    expect(src).not.toContain("nest-egg-show-recommendations-tab");
  });
});
