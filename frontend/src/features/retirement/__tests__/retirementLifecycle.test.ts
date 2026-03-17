/**
 * Tests for retirement scenario archival lifecycle types and filtering logic.
 *
 * Covers:
 * - Archive/unarchive fields in types
 * - member_ids in create type
 * - Scenario filtering (active vs archived)
 * - Multi-member scenario detection
 */

import { describe, it, expect } from "vitest";
import type {
  RetirementScenario,
  RetirementScenarioCreate,
  RetirementScenarioSummary,
} from "../types/retirement";

// ── Type shape tests ─────────────────────────────────────────────────────────

describe("RetirementScenario archival fields", () => {
  it("includes is_archived, archived_at, archived_reason", () => {
    const scenario: RetirementScenario = {
      id: "test-id",
      organization_id: "org-1",
      user_id: "user-1",
      name: "Test",
      description: null,
      is_default: false,
      retirement_age: 65,
      life_expectancy: 90,
      current_annual_income: null,
      annual_spending_retirement: 50000,
      pre_retirement_return: 0.07,
      post_retirement_return: 0.05,
      volatility: 0.15,
      inflation_rate: 0.03,
      medical_inflation_rate: 0.05,
      social_security_monthly: null,
      social_security_start_age: null,
      use_estimated_pia: false,
      spouse_social_security_monthly: null,
      spouse_social_security_start_age: null,
      withdrawal_strategy: "simple_rate",
      withdrawal_rate: 0.04,
      federal_tax_rate: 0.22,
      state_tax_rate: 0.05,
      capital_gains_rate: 0.15,
      healthcare_pre65_override: null,
      healthcare_medicare_override: null,
      healthcare_ltc_override: null,
      num_simulations: 1000,
      is_shared: false,
      include_all_members: false,
      is_stale: false,
      household_member_ids: null,
      is_archived: true,
      archived_at: "2026-03-17T00:00:00Z",
      archived_reason: "Member left household",
      life_events: [],
      created_at: "2026-01-01",
      updated_at: "2026-03-17",
    };

    expect(scenario.is_archived).toBe(true);
    expect(scenario.archived_at).toBe("2026-03-17T00:00:00Z");
    expect(scenario.archived_reason).toBe("Member left household");
  });
});

describe("RetirementScenarioSummary archival fields", () => {
  it("includes is_archived and household_member_ids", () => {
    const summary: RetirementScenarioSummary = {
      id: "test-id",
      name: "Test Plan",
      retirement_age: 65,
      is_default: false,
      is_stale: false,
      include_all_members: false,
      is_archived: true,
      household_member_ids: ["user-1", "user-2"],
      readiness_score: 75,
      success_rate: 82.5,
      updated_at: "2026-03-17",
    };

    expect(summary.is_archived).toBe(true);
    expect(summary.household_member_ids).toEqual(["user-1", "user-2"]);
  });
});

describe("RetirementScenarioCreate member_ids", () => {
  it("accepts member_ids for selective multi-user plan", () => {
    const create: RetirementScenarioCreate = {
      name: "Joint Plan",
      retirement_age: 65,
      annual_spending_retirement: 60000,
      member_ids: ["user-1", "user-2", "user-3"],
    };

    expect(create.member_ids).toHaveLength(3);
  });

  it("works without member_ids (single-user)", () => {
    const create: RetirementScenarioCreate = {
      name: "Solo Plan",
      retirement_age: 67,
      annual_spending_retirement: 50000,
    };

    expect(create.member_ids).toBeUndefined();
  });
});

// ── Filtering logic ──────────────────────────────────────────────────────────

describe("scenario filtering", () => {
  const makeSummary = (
    overrides: Partial<RetirementScenarioSummary>,
  ): RetirementScenarioSummary => ({
    id: "default-id",
    name: "Default",
    retirement_age: 65,
    is_default: false,
    is_stale: false,
    include_all_members: false,
    is_archived: false,
    household_member_ids: null,
    readiness_score: null,
    success_rate: null,
    updated_at: "2026-01-01",
    ...overrides,
  });

  it("splits active and archived scenarios", () => {
    const all = [
      makeSummary({ id: "1", is_archived: false }),
      makeSummary({ id: "2", is_archived: true }),
      makeSummary({ id: "3", is_archived: false }),
      makeSummary({ id: "4", is_archived: true }),
    ];

    const active = all.filter((s) => !s.is_archived);
    const archived = all.filter((s) => s.is_archived);

    expect(active).toHaveLength(2);
    expect(archived).toHaveLength(2);
    expect(active.map((s) => s.id)).toEqual(["1", "3"]);
    expect(archived.map((s) => s.id)).toEqual(["2", "4"]);
  });

  it("identifies multi-member scenarios", () => {
    const all = [
      makeSummary({ id: "single", household_member_ids: null }),
      makeSummary({
        id: "selective",
        household_member_ids: ["u1", "u2"],
      }),
      makeSummary({ id: "all", include_all_members: true }),
    ];

    const multiMember = all.filter(
      (s) =>
        s.include_all_members ||
        (s.household_member_ids && s.household_member_ids.length > 1),
    );

    expect(multiMember).toHaveLength(2);
    expect(multiMember.map((s) => s.id)).toEqual(["selective", "all"]);
  });

  it("filters combined view to only multi-member scenarios", () => {
    const all = [
      makeSummary({ id: "solo" }),
      makeSummary({
        id: "joint",
        household_member_ids: ["u1", "u2", "u3"],
      }),
      makeSummary({
        id: "archived-joint",
        is_archived: true,
        household_member_ids: ["u1", "u2"],
      }),
    ];

    const activeMulti = all.filter(
      (s) =>
        !s.is_archived &&
        (s.include_all_members ||
          (s.household_member_ids && s.household_member_ids.length > 1)),
    );
    const archivedMulti = all.filter(
      (s) =>
        s.is_archived &&
        (s.include_all_members ||
          (s.household_member_ids && s.household_member_ids.length > 1)),
    );

    expect(activeMulti).toHaveLength(1);
    expect(activeMulti[0].id).toBe("joint");
    expect(archivedMulti).toHaveLength(1);
    expect(archivedMulti[0].id).toBe("archived-joint");
  });
});
