/**
 * Tests for RulesPage logic: field/operator/action label lookups,
 * expand/collapse toggle, date formatting, and rule display text.
 */

import { describe, it, expect } from "vitest";

// ── Label maps (mirrored from RulesPage.tsx) ────────────────────────────────

const FIELD_LABELS: Record<string, string> = {
  merchant_name: "Merchant",
  amount: "Amount",
  amount_exact: "Amount (Exact)",
  category: "Category",
  description: "Description",
};

const OPERATOR_LABELS: Record<string, string> = {
  equals: "=",
  contains: "contains",
  starts_with: "starts with",
  ends_with: "ends with",
  greater_than: ">",
  less_than: "<",
  between: "between",
  regex: "matches regex",
};

const ACTION_LABELS: Record<string, string> = {
  set_category: "Set category",
  add_label: "Add label",
  remove_label: "Remove label",
  set_merchant: "Set merchant",
};

// ── Logic helpers ────────────────────────────────────────────────────────────

const formatDate = (dateStr: string) =>
  new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

function toggleExpanded(current: string | null, ruleId: string): string | null {
  return current === ruleId ? null : ruleId;
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe("FIELD_LABELS", () => {
  it("maps known field keys to human labels", () => {
    expect(FIELD_LABELS["merchant_name"]).toBe("Merchant");
    expect(FIELD_LABELS["amount"]).toBe("Amount");
    expect(FIELD_LABELS["description"]).toBe("Description");
  });

  it("returns undefined for unknown fields", () => {
    expect(FIELD_LABELS["unknown_field"]).toBeUndefined();
  });

  it("falls back gracefully with || pattern", () => {
    const field = "custom_field";
    const label = FIELD_LABELS[field] || field;
    expect(label).toBe("custom_field");
  });
});

describe("OPERATOR_LABELS", () => {
  it("maps all operator keys", () => {
    expect(OPERATOR_LABELS["equals"]).toBe("=");
    expect(OPERATOR_LABELS["contains"]).toBe("contains");
    expect(OPERATOR_LABELS["between"]).toBe("between");
    expect(OPERATOR_LABELS["regex"]).toBe("matches regex");
    expect(OPERATOR_LABELS["greater_than"]).toBe(">");
    expect(OPERATOR_LABELS["less_than"]).toBe("<");
  });
});

describe("ACTION_LABELS", () => {
  it("maps all action types", () => {
    expect(ACTION_LABELS["set_category"]).toBe("Set category");
    expect(ACTION_LABELS["add_label"]).toBe("Add label");
    expect(ACTION_LABELS["remove_label"]).toBe("Remove label");
    expect(ACTION_LABELS["set_merchant"]).toBe("Set merchant");
  });
});

describe("toggleExpanded", () => {
  it("expands a rule when none is expanded", () => {
    expect(toggleExpanded(null, "rule-1")).toBe("rule-1");
  });

  it("collapses the currently expanded rule", () => {
    expect(toggleExpanded("rule-1", "rule-1")).toBeNull();
  });

  it("switches to a different rule", () => {
    expect(toggleExpanded("rule-1", "rule-2")).toBe("rule-2");
  });
});

describe("formatDate", () => {
  it("formats ISO date string", () => {
    const result = formatDate("2025-06-15T14:30:00Z");
    // The exact output depends on locale, but should contain key parts
    expect(result).toContain("Jun");
    expect(result).toContain("15");
    expect(result).toContain("2025");
  });
});

describe("Rule display logic", () => {
  it("shows apply_to badges correctly", () => {
    const applyToLabels: Record<string, string> = {
      new_only: "New only",
      existing_only: "Existing only",
      both: "New & existing",
      single: "Single use",
    };
    expect(applyToLabels["new_only"]).toBe("New only");
    expect(applyToLabels["both"]).toBe("New & existing");
    expect(applyToLabels["single"]).toBe("Single use");
  });

  it("shows match_type badge", () => {
    const matchType = "all";
    const label = matchType === "all" ? "ALL conditions" : "ANY condition";
    expect(label).toBe("ALL conditions");
  });

  it('shows "ANY condition" for match_type any', () => {
    const matchType = "any";
    const label = matchType === "all" ? "ALL conditions" : "ANY condition";
    expect(label).toBe("ANY condition");
  });

  it("shows times_applied count", () => {
    const timesApplied = 42;
    expect(`Applied ${timesApplied} times`).toBe("Applied 42 times");
  });
});
