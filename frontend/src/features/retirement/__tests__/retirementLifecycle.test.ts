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
      user_id: "user-1",
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
    user_id: "user-1",
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

// ── View-specific filtering ──────────────────────────────────────────────────

describe("view-specific scenario filtering", () => {
  const makeSummary = (
    overrides: Partial<RetirementScenarioSummary>,
  ): RetirementScenarioSummary => ({
    id: "default-id",
    user_id: "u1",
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

  const allScenarios = [
    makeSummary({ id: "u1-personal", user_id: "u1" }),
    makeSummary({ id: "u2-personal", user_id: "u2" }),
    makeSummary({ id: "u3-personal", user_id: "u3" }),
    makeSummary({
      id: "all-members",
      user_id: "u1",
      include_all_members: true,
    }),
    makeSummary({
      id: "shared-u1-u2",
      user_id: "u1",
      household_member_ids: ["u1", "u2"],
    }),
    makeSummary({
      id: "shared-u1-u3",
      user_id: "u1",
      household_member_ids: ["u1", "u3"],
    }),
  ];

  const isPersonal = (s: RetirementScenarioSummary) =>
    !s.include_all_members &&
    (!s.household_member_ids || s.household_member_ids.length <= 1);

  it("'All' view shows include_all_members scenarios + all personal plans", () => {
    const result = allScenarios.filter(
      (s) => s.include_all_members || isPersonal(s),
    );
    expect(result.map((s) => s.id)).toEqual([
      "u1-personal",
      "u2-personal",
      "u3-personal",
      "all-members",
    ]);
  });

  it("'All' view excludes selective shared plans", () => {
    const result = allScenarios.filter(
      (s) => s.include_all_members || isPersonal(s),
    );
    expect(result.map((s) => s.id)).not.toContain("shared-u1-u2");
    expect(result.map((s) => s.id)).not.toContain("shared-u1-u3");
  });

  it("single user view shows only their personal plans", () => {
    const userId = "u2";
    const result = allScenarios.filter(
      (s) => s.user_id === userId && isPersonal(s),
    );
    expect(result.map((s) => s.id)).toEqual(["u2-personal"]);
  });

  it("2 users selected shows their personal plans + exact-match shared plans", () => {
    const selectedIds = new Set(["u1", "u2"]);
    const selectedArray = [...selectedIds];
    const result = allScenarios.filter((s) => {
      if (s.include_all_members) return false;
      if (s.household_member_ids && s.household_member_ids.length > 1) {
        const scenarioMembers = new Set(s.household_member_ids);
        return (
          scenarioMembers.size === selectedIds.size &&
          selectedArray.every((id) => scenarioMembers.has(id))
        );
      }
      return selectedIds.has(s.user_id);
    });
    expect(result.map((s) => s.id)).toEqual([
      "u1-personal",
      "u2-personal",
      "shared-u1-u2",
    ]);
  });

  it("2 users selected does NOT show shared plans for different sets", () => {
    const selectedIds = new Set(["u1", "u2"]);
    const selectedArray = [...selectedIds];
    const result = allScenarios.filter((s) => {
      if (s.include_all_members) return false;
      if (s.household_member_ids && s.household_member_ids.length > 1) {
        const scenarioMembers = new Set(s.household_member_ids);
        return (
          scenarioMembers.size === selectedIds.size &&
          selectedArray.every((id) => scenarioMembers.has(id))
        );
      }
      return selectedIds.has(s.user_id);
    });
    // shared-u1-u3 should NOT appear since u3 is not selected
    expect(result.map((s) => s.id)).not.toContain("shared-u1-u3");
  });
});

// ── Member edit update payload ──────────────────────────────────────────────

describe("member edit update payload construction", () => {
  type EditMode = "just_me" | "select" | "all";

  /** Mirrors the logic in handleSaveMemberEdit */
  function buildMemberUpdate(
    mode: EditMode,
    editMemberIds: Set<string>,
  ): Record<string, unknown> {
    const updates: Record<string, unknown> = {};
    if (mode === "all") {
      updates.include_all_members = true;
      updates.member_ids = null;
    } else if (mode === "select" && editMemberIds.size >= 2) {
      updates.include_all_members = false;
      updates.member_ids = [...editMemberIds];
    } else {
      updates.include_all_members = false;
      updates.member_ids = [];
    }
    return updates;
  }

  it("switching to 'all' sets include_all_members and clears member_ids", () => {
    const updates = buildMemberUpdate("all", new Set());
    expect(updates.include_all_members).toBe(true);
    expect(updates.member_ids).toBeNull();
  });

  it("selecting specific members sets member_ids and disables include_all_members", () => {
    const updates = buildMemberUpdate("select", new Set(["u1", "u2"]));
    expect(updates.include_all_members).toBe(false);
    expect(updates.member_ids).toEqual(expect.arrayContaining(["u1", "u2"]));
    expect((updates.member_ids as string[]).length).toBe(2);
  });

  it("switching to 'just_me' sends empty member_ids to revert to personal", () => {
    const updates = buildMemberUpdate("just_me", new Set());
    expect(updates.include_all_members).toBe(false);
    expect(updates.member_ids).toEqual([]);
  });

  it("select mode with <2 members falls back to personal", () => {
    const updates = buildMemberUpdate("select", new Set(["u1"]));
    expect(updates.include_all_members).toBe(false);
    expect(updates.member_ids).toEqual([]);
  });

  it("selecting all household members promotes to 'all' mode", () => {
    const allHouseholdIds = ["u1", "u2", "u3"];

    function buildWithAllCheck(
      mode: EditMode,
      editIds: Set<string>,
      householdIds: string[],
    ): Record<string, unknown> {
      const allSelected =
        mode === "select" &&
        householdIds.length > 0 &&
        editIds.size >= householdIds.length &&
        householdIds.every((id) => editIds.has(id));

      const updates: Record<string, unknown> = {};
      if (mode === "all" || allSelected) {
        updates.include_all_members = true;
        updates.member_ids = null;
      } else if (mode === "select" && editIds.size >= 2) {
        updates.include_all_members = false;
        updates.member_ids = [...editIds];
      } else {
        updates.include_all_members = false;
        updates.member_ids = [];
      }
      return updates;
    }

    // All 3 selected → promoted to "all"
    const all = buildWithAllCheck(
      "select",
      new Set(allHouseholdIds),
      allHouseholdIds,
    );
    expect(all.include_all_members).toBe(true);
    expect(all.member_ids).toBeNull();

    // Only 2 of 3 → stays selective
    const partial = buildWithAllCheck(
      "select",
      new Set(["u1", "u2"]),
      allHouseholdIds,
    );
    expect(partial.include_all_members).toBe(false);
    expect(partial.member_ids).toEqual(expect.arrayContaining(["u1", "u2"]));
  });
});

// ── Badge classification ────────────────────────────────────────────────────

describe("scenario badge classification", () => {
  const makeSummary = (
    overrides: Partial<RetirementScenarioSummary>,
  ): RetirementScenarioSummary => ({
    id: "default-id",
    user_id: "u1",
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

  type BadgeType = "all" | "shared" | null;

  /** Mirrors the badge IIFE logic in RetirementPage tab rendering */
  function classifyBadge(
    s: RetirementScenarioSummary,
    householdMemberIds: string[],
  ): BadgeType {
    const isEffectivelyAll =
      s.include_all_members ||
      (s.household_member_ids &&
        householdMemberIds.length > 0 &&
        s.household_member_ids.length >= householdMemberIds.length &&
        householdMemberIds.every((id) => s.household_member_ids!.includes(id)));
    if (isEffectivelyAll) return "all";
    if (s.household_member_ids && s.household_member_ids.length > 1)
      return "shared";
    return null;
  }

  const household = ["u1", "u2", "u3"];

  it("include_all_members → 'all' badge", () => {
    const s = makeSummary({ include_all_members: true });
    expect(classifyBadge(s, household)).toBe("all");
  });

  it("selective plan with subset of household → 'shared' badge", () => {
    const s = makeSummary({ household_member_ids: ["u1", "u2"] });
    expect(classifyBadge(s, household)).toBe("shared");
  });

  it("selective plan with ALL household members → 'all' badge (not 'shared')", () => {
    const s = makeSummary({ household_member_ids: ["u1", "u2", "u3"] });
    expect(classifyBadge(s, household)).toBe("all");
  });

  it("personal plan (no household_member_ids) → null badge", () => {
    const s = makeSummary({});
    expect(classifyBadge(s, household)).toBeNull();
  });

  it("single member in household_member_ids → null badge", () => {
    const s = makeSummary({ household_member_ids: ["u1"] });
    expect(classifyBadge(s, household)).toBeNull();
  });

  it("all members selected but household is empty → 'shared' badge (no false positive)", () => {
    const s = makeSummary({ household_member_ids: ["u1", "u2"] });
    expect(classifyBadge(s, [])).toBe("shared");
  });
});

// ── Modal pre-population ────────────────────────────────────────────────────

describe("member editor modal pre-population", () => {
  const makeSummary = (
    overrides: Partial<RetirementScenarioSummary>,
  ): RetirementScenarioSummary => ({
    id: "s1",
    user_id: "u1",
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

  type EditMode = "just_me" | "select" | "all";

  /** Mirrors handleOpenMemberEditor logic */
  function deriveEditState(s: RetirementScenarioSummary): {
    mode: EditMode;
    ids: Set<string>;
  } {
    if (s.include_all_members) {
      return { mode: "all", ids: new Set() };
    }
    if (s.household_member_ids && s.household_member_ids.length > 1) {
      return { mode: "select", ids: new Set(s.household_member_ids) };
    }
    return { mode: "just_me", ids: new Set() };
  }

  it("include_all_members scenario opens in 'all' mode with empty ids", () => {
    const s = makeSummary({ include_all_members: true });
    const { mode, ids } = deriveEditState(s);
    expect(mode).toBe("all");
    expect(ids.size).toBe(0);
  });

  it("selective shared scenario opens in 'select' mode with correct ids", () => {
    const s = makeSummary({ household_member_ids: ["u1", "u2"] });
    const { mode, ids } = deriveEditState(s);
    expect(mode).toBe("select");
    expect(ids).toEqual(new Set(["u1", "u2"]));
  });

  it("personal scenario opens in 'just_me' mode", () => {
    const s = makeSummary({});
    const { mode, ids } = deriveEditState(s);
    expect(mode).toBe("just_me");
    expect(ids.size).toBe(0);
  });

  it("single-member household_member_ids opens in 'just_me' mode", () => {
    const s = makeSummary({ household_member_ids: ["u1"] });
    const { mode, ids } = deriveEditState(s);
    expect(mode).toBe("just_me");
    expect(ids.size).toBe(0);
  });
});
