/**
 * Pure-function tests for Dashboard simple mode behaviour.
 * Tests the logic for showing/hiding the Customize button and hint text.
 */
import { describe, it, expect } from "vitest";

// Replicate the logic from DashboardPage.tsx
function shouldShowCustomize(showAdvancedNav: boolean, isEditing: boolean): boolean {
  return showAdvancedNav || isEditing;
}

function shouldShowHint(showAdvancedNav: boolean, isEditing: boolean): boolean {
  return !showAdvancedNav && !isEditing;
}

describe("Dashboard simple mode — Customize button visibility", () => {
  it("showAdvancedNav=false and not editing → Customize button is hidden", () => {
    expect(shouldShowCustomize(false, false)).toBe(false);
  });

  it("showAdvancedNav=true → Customize button is visible", () => {
    expect(shouldShowCustomize(true, false)).toBe(true);
  });

  it("showAdvancedNav=true and editing → Customize button is visible", () => {
    expect(shouldShowCustomize(true, true)).toBe(true);
  });

  it("isEditing overrides simple mode — even in simple mode the button appears if already editing", () => {
    expect(shouldShowCustomize(false, true)).toBe(true);
  });
});

describe("Dashboard simple mode — hint text visibility", () => {
  it("hint text appears when showAdvancedNav=false and not editing", () => {
    expect(shouldShowHint(false, false)).toBe(true);
  });

  it("hint text is hidden when showAdvancedNav=true", () => {
    expect(shouldShowHint(true, false)).toBe(false);
  });

  it("hint text is hidden when isEditing=true (regardless of advanced nav)", () => {
    expect(shouldShowHint(false, true)).toBe(false);
    expect(shouldShowHint(true, true)).toBe(false);
  });
});
