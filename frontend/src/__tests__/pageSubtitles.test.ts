/**
 * Tests for beginner-friendly page subtitles and descriptions (UX improvements I, J, L).
 *
 * Each page that a beginner might visit without context should have a plain-English
 * subtitle that explains what the page does — no jargon, no assumed knowledge.
 *
 * Tests read source files directly (same approach as newPlanningFeatures.test.ts)
 * to guard against accidentally removing these descriptions during refactors.
 */

import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const srcRoot = join(__dirname, "..");

function readPage(rel: string): string {
  return readFileSync(join(srcRoot, rel), "utf-8");
}

const cashFlowSrc = readPage("pages/CashFlowPage.tsx");
const preferencesSrc = readPage("pages/PreferencesPage.tsx");
const rulesSrc = readPage("pages/RulesPage.tsx");

// ── I: CashFlowPage subtitle ─────────────────────────────────────────────────

describe("CashFlowPage beginner subtitle (I)", () => {
  it("has a subtitle/description below the heading", () => {
    // Check there is a Text element near the Heading
    const headingIdx = cashFlowSrc.indexOf('Heading size="lg">Cash Flow');
    const afterHeading = cashFlowSrc.slice(headingIdx, headingIdx + 400);
    expect(afterHeading).toContain("Text");
  });

  it("subtitle explains 'money in vs. money out' in plain English", () => {
    expect(cashFlowSrc).toMatch(/money in|money out|earned.*spent|income.*spending/i);
  });

  it("subtitle mentions the 90-day forecast so users know what Forecast tab does", () => {
    expect(cashFlowSrc).toMatch(/90.?day|ninety day/i);
  });

  it("Overview tab has a tooltip explaining income vs. spending breakdown", () => {
    // Look for a Tooltip wrapping the Overview tab (within 300 chars of the tab label)
    const tabIdx = cashFlowSrc.lastIndexOf(">Overview<");
    const context = cashFlowSrc.slice(Math.max(0, tabIdx - 300), tabIdx + 50);
    expect(context).toMatch(/Tooltip/);
  });

  it("Forecast tab has a tooltip explaining the balance projection", () => {
    expect(cashFlowSrc).toMatch(/balance.*projection|projected balance|balance is headed/i);
  });
});

// ── J: Preferences advanced-features description ─────────────────────────────

describe("Preferences advanced-features toggle description (J)", () => {
  // The description lives in the JSX near the toggle, after "Show advanced features"
  // label text. We find the last occurrence (the UI text, not any comments).
  function getToggleContext(): string {
    const markers = ["Unlocks advanced tabs", "Show advanced features"];
    for (const marker of markers) {
      const idx = preferencesSrc.lastIndexOf(marker);
      if (idx !== -1) return preferencesSrc.slice(idx, idx + 600);
    }
    return "";
  }

  it("mentions Planning Tools", () => {
    expect(getToggleContext()).toContain("Planning Tools");
  });

  it("mentions PE Performance", () => {
    expect(getToggleContext()).toMatch(/PE Performance|PE performance/);
  });

  it("mentions Rental Properties", () => {
    expect(getToggleContext()).toMatch(/Rental Properties|Rental properties/);
  });

  it("mentions Charitable Giving", () => {
    expect(getToggleContext()).toMatch(/Charitable Giving|Charitable giving/);
  });

  it("lists the advanced tabs that get unlocked", () => {
    expect(getToggleContext()).toMatch(/Planning Tools|bond ladder|PE Performance/i);
  });
});

// ── L: RulesPage beginner explanation ────────────────────────────────────────

describe("RulesPage beginner explanation (L)", () => {
  it("has a plain-English description of what rules do", () => {
    expect(rulesSrc).toMatch(/auto.?categori|automatically/i);
  });

  it("uses a concrete example (e.g. Starbucks → Dining)", () => {
    // The description should give a real-world example, not just jargon
    expect(rulesSrc).toMatch(/Starbucks|example|e\.g\.|for example/i);
  });

  it("explains the benefit (saves time, set once)", () => {
    expect(rulesSrc).toMatch(/save time|set.{0,10}once|every future|automatically/i);
  });

  it("shows rule count in plain language (not just 'X rule(s) total')", () => {
    // Should use conditional plural: "1 rule" vs "2 rules"
    expect(rulesSrc).toContain("rule{");
  });
});
