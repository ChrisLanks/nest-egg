/**
 * Tests for template logic: grouping, ID parsing, display state.
 */

import { describe, it, expect } from "vitest";
import type { TemplateInfo } from "../../../../api/financial-templates";

// ---------------------------------------------------------------------------
// Template ID parsing (mirrors QuickSetupPanel grouping)
// ---------------------------------------------------------------------------

function parseTemplateId(id: string): { category: string; name: string } {
  const [category, ...rest] = id.split(":");
  return { category, name: rest.join(":") };
}

describe("parseTemplateId", () => {
  it.each([
    ["goal:emergency_fund", "goal", "emergency_fund"],
    ["rule:coffee_shops", "rule", "coffee_shops"],
    ["retirement:default", "retirement", "default"],
    ["budget:suggestions", "budget", "suggestions"],
  ])(
    'parses "%s" into category=%s name=%s',
    (id, expectedCat, expectedName) => {
      const { category, name } = parseTemplateId(id);
      expect(category).toBe(expectedCat);
      expect(name).toBe(expectedName);
    },
  );
});

// ---------------------------------------------------------------------------
// Template grouping by category
// ---------------------------------------------------------------------------

function groupByCategory(
  templates: TemplateInfo[],
): Record<string, TemplateInfo[]> {
  const grouped: Record<string, TemplateInfo[]> = {};
  for (const t of templates) {
    if (!grouped[t.category]) grouped[t.category] = [];
    grouped[t.category].push(t);
  }
  return grouped;
}

const makeTemplate = (overrides: Partial<TemplateInfo>): TemplateInfo => ({
  id: "goal:test",
  category: "goal",
  name: "Test",
  description: "A test template",
  is_activated: false,
  ...overrides,
});

describe("groupByCategory", () => {
  it("groups templates correctly", () => {
    const templates: TemplateInfo[] = [
      makeTemplate({ id: "goal:a", category: "goal", name: "A" }),
      makeTemplate({ id: "goal:b", category: "goal", name: "B" }),
      makeTemplate({ id: "rule:c", category: "rule", name: "C" }),
    ];
    const grouped = groupByCategory(templates);

    expect(Object.keys(grouped)).toEqual(["goal", "rule"]);
    expect(grouped.goal).toHaveLength(2);
    expect(grouped.rule).toHaveLength(1);
  });

  it("returns empty object for empty input", () => {
    expect(groupByCategory([])).toEqual({});
  });
});

// ---------------------------------------------------------------------------
// Activation state display logic
// ---------------------------------------------------------------------------

function shouldShowSetupPanel(templates: TemplateInfo[]): boolean {
  if (templates.length === 0) return false;
  return !templates.every((t) => t.is_activated);
}

describe("shouldShowSetupPanel", () => {
  it("shows when some templates are not activated", () => {
    const templates = [
      makeTemplate({ is_activated: true }),
      makeTemplate({ is_activated: false }),
    ];
    expect(shouldShowSetupPanel(templates)).toBe(true);
  });

  it("hides when all templates are activated", () => {
    const templates = [
      makeTemplate({ is_activated: true }),
      makeTemplate({ is_activated: true }),
    ];
    expect(shouldShowSetupPanel(templates)).toBe(false);
  });

  it("hides when no templates exist", () => {
    expect(shouldShowSetupPanel([])).toBe(false);
  });

  it("shows when no templates are activated", () => {
    const templates = [
      makeTemplate({ is_activated: false }),
      makeTemplate({ is_activated: false }),
    ];
    expect(shouldShowSetupPanel(templates)).toBe(true);
  });
});
