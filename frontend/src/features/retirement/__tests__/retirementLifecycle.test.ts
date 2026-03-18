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
  SpendingPhase,
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
      spending_phases: null,
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

  it("'All' view shows all scenarios (personal, selective shared, and include_all_members)", () => {
    // In "All" view, every scenario should be visible regardless of membership type
    const isAllSelected = true;
    const result = allScenarios.filter(() => isAllSelected);
    expect(result.map((s) => s.id)).toEqual([
      "u1-personal",
      "u2-personal",
      "u3-personal",
      "all-members",
      "shared-u1-u2",
      "shared-u1-u3",
    ]);
  });

  it("'All' view includes selective shared plans created by any user", () => {
    const isAllSelected = true;
    const result = allScenarios.filter(() => isAllSelected);
    expect(result.map((s) => s.id)).toContain("shared-u1-u2");
    expect(result.map((s) => s.id)).toContain("shared-u1-u3");
  });

  it("'All' view shows selective plan for non-creator members (e.g., chris creates plan for test+test2)", () => {
    // Scenario: user "chris" creates a plan with members "test" and "test2" (not including chris)
    const scenariosWithCrossPlan = [
      ...allScenarios,
      makeSummary({
        id: "chris-plan-for-others",
        user_id: "chris",
        household_member_ids: ["test", "test2"],
      }),
    ];
    const isAllSelected = true;
    const result = scenariosWithCrossPlan.filter(() => isAllSelected);
    expect(result.map((s) => s.id)).toContain("chris-plan-for-others");
  });

  /**
   * Mirrors the filterForView logic.
   * A plan belongs to its creator (user_id). household_member_ids only
   * controls which accounts are in the simulation, not ownership.
   * include_all_members does NOT change ownership — the plan still
   * belongs to whoever created it. "All" view shows everything separately.
   */
  const scenarioBelongsTo = (userId: string, s: RetirementScenarioSummary) => {
    return s.user_id === userId;
  };

  it("single user view shows their personal and shared plans", () => {
    const userId = "u1";
    const result = allScenarios.filter((s) => scenarioBelongsTo(userId, s));
    // u1 created: u1-personal, all-members, shared-u1-u2, shared-u1-u3
    expect(result.map((s) => s.id)).toEqual([
      "u1-personal",
      "all-members",
      "shared-u1-u2",
      "shared-u1-u3",
    ]);
  });

  it("single user view shows only plans they created", () => {
    const userId = "u2";
    const result = allScenarios.filter((s) => scenarioBelongsTo(userId, s));
    // u2 only owns u2-personal; all-members was created by u1
    expect(result.map((s) => s.id)).toEqual(["u2-personal"]);
  });

  it("single user view: creator sees their shared plan", () => {
    const scenariosWithCrossPlan = [
      ...allScenarios,
      makeSummary({
        id: "chris-plan-for-others",
        user_id: "chris",
        household_member_ids: ["u1", "u2"],
      }),
    ];
    // Chris created the plan, so it shows in chris's view
    const result = scenariosWithCrossPlan.filter((s) =>
      scenarioBelongsTo("chris", s),
    );
    expect(result.map((s) => s.id)).toContain("chris-plan-for-others");
  });

  it("single user view: non-creator member does NOT see someone else's shared plan", () => {
    const scenariosWithCrossPlan = [
      ...allScenarios,
      makeSummary({
        id: "chris-plan-for-others",
        user_id: "chris",
        household_member_ids: ["u1", "u2"],
      }),
    ];
    // u1 is in household_member_ids but chris created it — not u1's plan
    const result = scenariosWithCrossPlan.filter((s) =>
      scenarioBelongsTo("u1", s),
    );
    expect(result.map((s) => s.id)).not.toContain("chris-plan-for-others");
  });

  it("2 users selected shows plans owned by either selected user", () => {
    const selectedIds = new Set(["u1", "u2"]);
    const result = allScenarios.filter((s) =>
      [...selectedIds].some((id) => scenarioBelongsTo(id, s)),
    );
    // u1 owns: u1-personal, all-members, shared-u1-u2, shared-u1-u3
    // u2 owns: u2-personal
    expect(result.map((s) => s.id)).toEqual([
      "u1-personal",
      "u2-personal",
      "all-members",
      "shared-u1-u2",
      "shared-u1-u3",
    ]);
  });

  it("2 users selected does NOT show plan owned by unselected user", () => {
    const scenariosWithCrossPlan = [
      ...allScenarios,
      makeSummary({
        id: "chris-plan-for-u1-u2",
        user_id: "chris",
        household_member_ids: ["u1", "u2"],
      }),
    ];
    // u1 and u2 are selected, but chris (the owner) is not
    const selectedIds = new Set(["u1", "u2"]);
    const result = scenariosWithCrossPlan.filter((s) =>
      [...selectedIds].some((id) => scenarioBelongsTo(id, s)),
    );
    expect(result.map((s) => s.id)).not.toContain("chris-plan-for-u1-u2");
  });

  it("selecting the creator shows their shared plan", () => {
    const scenariosWithCrossPlan = [
      ...allScenarios,
      makeSummary({
        id: "chris-plan-for-u1-u2",
        user_id: "chris",
        household_member_ids: ["u1", "u2"],
      }),
    ];
    // chris is selected — their plan should show
    const selectedIds = new Set(["chris", "u2"]);
    const result = scenariosWithCrossPlan.filter((s) =>
      [...selectedIds].some((id) => scenarioBelongsTo(id, s)),
    );
    expect(result.map((s) => s.id)).toContain("chris-plan-for-u1-u2");
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

// ── Spending phases type tests ──────────────────────────────────────────────

describe("SpendingPhase type shape", () => {
  it("accepts a valid phase with end_age", () => {
    const phase: SpendingPhase = {
      start_age: 65,
      end_age: 75,
      annual_amount: 150000,
    };
    expect(phase.start_age).toBe(65);
    expect(phase.end_age).toBe(75);
    expect(phase.annual_amount).toBe(150000);
  });

  it("accepts a phase with null end_age", () => {
    const phase: SpendingPhase = {
      start_age: 75,
      end_age: null,
      annual_amount: 50000,
    };
    expect(phase.end_age).toBeNull();
  });
});

describe("RetirementScenario spending_phases field", () => {
  it("accepts spending_phases as null", () => {
    const scenario = {
      spending_phases: null,
    } as Partial<RetirementScenario>;
    expect(scenario.spending_phases).toBeNull();
  });

  it("accepts spending_phases as array of phases", () => {
    const phases: SpendingPhase[] = [
      { start_age: 65, end_age: 75, annual_amount: 150000 },
      { start_age: 75, end_age: null, annual_amount: 50000 },
    ];
    const scenario = {
      spending_phases: phases,
    } as Partial<RetirementScenario>;
    expect(scenario.spending_phases).toHaveLength(2);
    expect(scenario.spending_phases![0].annual_amount).toBe(150000);
    expect(scenario.spending_phases![1].end_age).toBeNull();
  });
});

describe("RetirementScenarioCreate spending_phases", () => {
  it("accepts create payload without spending_phases", () => {
    const create: RetirementScenarioCreate = {
      name: "Simple Plan",
      retirement_age: 67,
      annual_spending_retirement: 60000,
    };
    expect(create.spending_phases).toBeUndefined();
  });

  it("accepts create payload with spending_phases", () => {
    const create: RetirementScenarioCreate = {
      name: "Phased Plan",
      retirement_age: 65,
      annual_spending_retirement: 60000,
      spending_phases: [
        { start_age: 65, end_age: 75, annual_amount: 120000 },
        { start_age: 75, end_age: null, annual_amount: 50000 },
      ],
    };
    expect(create.spending_phases).toHaveLength(2);
  });

  it("accepts create payload with spending_phases set to null", () => {
    const create: RetirementScenarioCreate = {
      name: "Cleared Phases",
      retirement_age: 67,
      annual_spending_retirement: 60000,
      spending_phases: null,
    };
    expect(create.spending_phases).toBeNull();
  });
});

// ── Auto-simulate after member change ───────────────────────────────────────

describe("auto-simulate after member change", () => {
  it("should trigger simulation for the edited scenario after saving members", () => {
    // Mirrors the handleSaveMemberEdit flow:
    // 1. Update mutation succeeds
    // 2. Queries invalidated
    // 3. Simulation auto-triggered for the edited scenario ID
    const editingMembersScenarioId = "scenario-123";
    let simulatedId: string | null = null;
    // Mock simulate
    const simulateMutation = {
      mutateAsync: (id: string) => {
        simulatedId = id;
        return Promise.resolve();
      },
    };

    // After successful member save, auto-simulate fires
    if (editingMembersScenarioId) {
      simulateMutation.mutateAsync(editingMembersScenarioId);
    }

    expect(simulatedId).toBe("scenario-123");
  });

  it("should simulate using editingMembersScenarioId, not selectedScenarioId", () => {
    // When the edited scenario differs from the currently viewed one,
    // we should still simulate the correct (edited) scenario
    const editingMembersScenarioId = "edited-scenario";
    const selectedScenarioId = "different-scenario";
    let simulatedId: string | null = null;

    const simulateMutation = {
      mutateAsync: (id: string) => {
        simulatedId = id;
        return Promise.resolve();
      },
    };

    if (editingMembersScenarioId) {
      simulateMutation.mutateAsync(editingMembersScenarioId);
    }

    expect(simulatedId).toBe("edited-scenario");
    expect(simulatedId).not.toBe(selectedScenarioId);
  });

  it("should not simulate when editingMembersScenarioId is null", () => {
    const editingMembersScenarioId: string | null = null;
    let simulateCalled = false;

    const simulateMutation = {
      mutateAsync: (_id: string) => {
        simulateCalled = true;
        return Promise.resolve();
      },
    };

    if (editingMembersScenarioId) {
      simulateMutation.mutateAsync(editingMembersScenarioId);
    }

    expect(simulateCalled).toBe(false);
  });
});

// ── Owner display in household plans ────────────────────────────────────────

describe("scenario owner identification", () => {
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

  /** Mirrors logic for deriving owner label text */
  function getOwnerLabel(
    scenario: RetirementScenarioSummary,
    memberNameMap: Record<string, string>,
  ): string | null {
    const ownerName = memberNameMap[scenario.user_id];
    if (!ownerName) return null;
    // Only show owner label for multi-member scenarios
    if (
      scenario.include_all_members ||
      (scenario.household_member_ids &&
        scenario.household_member_ids.length > 1)
    ) {
      return ownerName;
    }
    return null;
  }

  const nameMap: Record<string, string> = {
    u1: "Chris",
    u2: "Test",
    u3: "Test2",
  };

  it("shows owner name for include_all_members scenario", () => {
    const s = makeSummary({ user_id: "u1", include_all_members: true });
    expect(getOwnerLabel(s, nameMap)).toBe("Chris");
  });

  it("shows owner name for selective shared scenario", () => {
    const s = makeSummary({
      user_id: "u1",
      household_member_ids: ["u2", "u3"],
    });
    expect(getOwnerLabel(s, nameMap)).toBe("Chris");
  });

  it("returns null for personal (single-user) scenario", () => {
    const s = makeSummary({ user_id: "u1" });
    expect(getOwnerLabel(s, nameMap)).toBeNull();
  });

  it("returns null when owner not in name map", () => {
    const s = makeSummary({
      user_id: "unknown",
      include_all_members: true,
    });
    expect(getOwnerLabel(s, nameMap)).toBeNull();
  });
});

// ── Simulation cache invalidation strategy ──────────────────────────────────

describe("simulation cache invalidation strategy", () => {
  /**
   * Mirrors the useRunSimulation onSuccess behavior:
   * - setQueryData writes fresh result into cache
   * - Only non-results queries are invalidated (prevents stale GET /results
   *   from overwriting the fresh setQueryData value)
   */

  it("setQueryData should overwrite existing cache entry", () => {
    // Simulates React Query cache behavior
    const cache: Record<string, unknown> = {};
    const setQueryData = (key: string[], data: unknown) => {
      cache[key.join("|")] = data;
    };

    // Old stale data in cache
    const staleResult = { success_rate: 0, projections: [] };
    setQueryData(["retirement-scenarios", "results", "s1"], staleResult);

    // Simulate returns fresh data
    const freshResult = {
      success_rate: 85.5,
      projections: [{ age: 34, p50: 259000 }],
    };
    setQueryData(["retirement-scenarios", "results", "s1"], freshResult);

    expect(cache["retirement-scenarios|results|s1"]).toBe(freshResult);
    expect(
      (cache["retirement-scenarios|results|s1"] as { success_rate: number })
        .success_rate,
    ).toBe(85.5);
  });

  it("invalidation predicate excludes results queries", () => {
    const QUERY_KEY = "retirement-scenarios";
    const predicate = (queryKey: string[]) =>
      queryKey[0] === QUERY_KEY && !queryKey.includes("results");

    // Scenario list query — should be invalidated
    expect(predicate(["retirement-scenarios"])).toBe(true);
    expect(predicate(["retirement-scenarios", "list"])).toBe(true);

    // Results query — should NOT be invalidated
    expect(predicate(["retirement-scenarios", "results", "s1"])).toBe(false);
    expect(predicate(["retirement-scenarios", "results", "s2"])).toBe(false);

    // Unrelated query — should NOT be invalidated
    expect(predicate(["accounts"])).toBe(false);
  });

  it("member edit handler should not invalidate results queries", () => {
    // Mirrors handleSaveMemberEdit: only invalidate scenario list,
    // auto-simulate handles results via setQueryData
    const QUERY_KEY = "retirement-scenarios";
    const invalidatedKeys: string[][] = [];
    const invalidateQueries = (opts: {
      predicate: (query: { queryKey: string[] }) => boolean;
    }) => {
      const allQueries = [
        { queryKey: [QUERY_KEY] },
        { queryKey: [QUERY_KEY, "results", "s1"] },
        { queryKey: [QUERY_KEY, "results", "s2"] },
        { queryKey: [QUERY_KEY, "scenario", "s1"] },
      ];
      for (const q of allQueries) {
        if (opts.predicate(q)) invalidatedKeys.push(q.queryKey);
      }
    };

    invalidateQueries({
      predicate: (query) =>
        query.queryKey[0] === QUERY_KEY && !query.queryKey.includes("results"),
    });

    // Scenario list and detail queries are invalidated
    expect(invalidatedKeys).toContainEqual([QUERY_KEY]);
    expect(invalidatedKeys).toContainEqual([QUERY_KEY, "scenario", "s1"]);
    // Results queries are NOT invalidated
    expect(invalidatedKeys).not.toContainEqual([QUERY_KEY, "results", "s1"]);
    expect(invalidatedKeys).not.toContainEqual([QUERY_KEY, "results", "s2"]);
  });
});

// ── View filter: ownership-based, not include_all_members bypass ────────────

describe("view filter does not bypass on include_all_members", () => {
  /**
   * Mirrors the filterForView logic in RetirementPage:
   * - isAllSelected → show everything
   * - Otherwise filter by owner (user_id), even for include_all_members plans
   */
  const makeSummary = (
    overrides: Partial<RetirementScenarioSummary>,
  ): RetirementScenarioSummary => ({
    id: "default-id",
    user_id: "chris",
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

  type FilterForView = (s: RetirementScenarioSummary) => boolean;

  /** Build the filter matching RetirementPage logic */
  function buildFilter(opts: {
    isCombinedView: boolean;
    isAllSelected: boolean;
    selectedMemberIds: Set<string>;
  }): FilterForView {
    const { isCombinedView, isAllSelected, selectedMemberIds } = opts;
    return (s: RetirementScenarioSummary): boolean => {
      if (!isCombinedView) return true;
      if (isAllSelected) return true;
      return selectedMemberIds.has(s.user_id);
    };
  }

  it("shows all plans when isAllSelected is true", () => {
    const filter = buildFilter({
      isCombinedView: true,
      isAllSelected: true,
      selectedMemberIds: new Set(["chris", "test1", "test2"]),
    });
    const chrisPlan = makeSummary({
      user_id: "chris",
      include_all_members: true,
    });
    const test1Plan = makeSummary({ user_id: "test1" });
    expect(filter(chrisPlan)).toBe(true);
    expect(filter(test1Plan)).toBe(true);
  });

  it("hides include_all_members plan when owner is not selected", () => {
    const filter = buildFilter({
      isCombinedView: true,
      isAllSelected: false,
      selectedMemberIds: new Set(["test1", "test2"]),
    });
    const chrisPlan = makeSummary({
      user_id: "chris",
      include_all_members: true,
    });
    expect(filter(chrisPlan)).toBe(false);
  });

  it("shows include_all_members plan when owner IS selected", () => {
    const filter = buildFilter({
      isCombinedView: true,
      isAllSelected: false,
      selectedMemberIds: new Set(["chris", "test1"]),
    });
    const chrisPlan = makeSummary({
      user_id: "chris",
      include_all_members: true,
    });
    expect(filter(chrisPlan)).toBe(true);
  });

  it("non-combined view always returns true", () => {
    const filter = buildFilter({
      isCombinedView: false,
      isAllSelected: false,
      selectedMemberIds: new Set(),
    });
    const plan = makeSummary({ user_id: "chris", include_all_members: true });
    expect(filter(plan)).toBe(true);
  });

  it("personal plan hidden when owner not selected", () => {
    const filter = buildFilter({
      isCombinedView: true,
      isAllSelected: false,
      selectedMemberIds: new Set(["test1"]),
    });
    const chrisPersonal = makeSummary({ user_id: "chris" });
    expect(filter(chrisPersonal)).toBe(false);
  });

  it("personal plan visible when owner selected", () => {
    const filter = buildFilter({
      isCombinedView: true,
      isAllSelected: false,
      selectedMemberIds: new Set(["chris"]),
    });
    const chrisPersonal = makeSummary({ user_id: "chris" });
    expect(filter(chrisPersonal)).toBe(true);
  });
});
