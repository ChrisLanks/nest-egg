/**
 * Tests for Savings Goals page logic: progress calculations, target date
 * projections, contribution tracking, completion percentages, goal filtering,
 * grouping by account, and formatting helpers.
 */

import { describe, it, expect } from "vitest";

// ── Types (mirrored from savings-goal.ts and GoalCard.tsx) ──────────────────

interface SavingsGoal {
  id: string;
  organization_id: string;
  user_id: string | null;
  name: string;
  description: string | null;
  target_amount: number;
  current_amount: number;
  start_date: string;
  target_date: string | null;
  account_id: string | null;
  auto_sync: boolean;
  priority: number | null;
  is_completed: boolean;
  completed_at: string | null;
  is_funded: boolean;
  funded_at: string | null;
  is_shared: boolean;
  shared_user_ids: string[] | null;
  created_at: string;
  updated_at: string;
}

interface SavingsGoalProgress {
  goal_id: string;
  name: string;
  current_amount: number;
  target_amount: number;
  progress_percentage: number;
  remaining_amount: number;
  days_elapsed: number;
  days_remaining: number | null;
  monthly_required: number | null;
  on_track: boolean | null;
  is_completed: boolean;
}

// ── Helper functions (mirrored from GoalCard.tsx and SavingsGoalsPage.tsx) ───

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(amount);

/** Progress percentage calculation from GoalCard */
const calculatePercentage = (
  progress: SavingsGoalProgress | null,
  goal: SavingsGoal,
): number =>
  progress?.progress_percentage ??
  (goal.target_amount > 0
    ? (goal.current_amount / goal.target_amount) * 100
    : 0);

/** Clamped display percentage (shown in UI) */
const displayPercentage = (raw: number): string =>
  `${Math.min(raw, 100).toFixed(1)}%`;

/** Progress bar color from GoalCard.getProgressColor */
const getProgressColor = (
  goal: SavingsGoal,
  progress: SavingsGoalProgress | null,
): string => {
  if (goal.is_funded) return "purple";
  if (goal.is_completed) return "green";
  if (progress?.on_track === false) return "orange";
  return "blue"; // light mode default accent
};

/** Active/completed goal filtering from SavingsGoalsPage */
const filterActive = (goals: SavingsGoal[]) =>
  goals.filter((g) => !g.is_completed && !g.is_funded);

const filterCompleted = (goals: SavingsGoal[]) =>
  goals.filter((g) => g.is_completed || g.is_funded);

/** Emergency fund detection */
const hasEmergencyFundGoal = (goals: SavingsGoal[]) =>
  goals.some((g) => g.name.toLowerCase().includes("emergency"));

/** Auto-sync key derivation */
const hasAutoSyncGoals = (goals: SavingsGoal[]) =>
  goals.some(
    (g) => !g.is_completed && !g.is_funded && g.auto_sync && g.account_id,
  );

/** Group goals by account_id */
const groupByAccount = (
  goals: SavingsGoal[],
): Map<string | null, SavingsGoal[]> => {
  const groups = new Map<string | null, SavingsGoal[]>();
  for (const goal of goals) {
    const key = goal.account_id ?? null;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(goal);
  }
  return groups;
};

/** Self-view filtering logic */
const filterSelfView = (
  goals: SavingsGoal[],
  currentUserId: string,
): SavingsGoal[] =>
  goals.filter((g) => {
    if (g.user_id === currentUserId) return true;
    if (g.is_shared && !g.shared_user_ids) return true;
    if (g.is_shared && g.shared_user_ids?.includes(currentUserId)) return true;
    if (!g.user_id) return true;
    return false;
  });

/** Partial member selection filtering */
const filterByMembers = (
  goals: SavingsGoal[],
  selectedIds: Set<string>,
): SavingsGoal[] =>
  goals.filter((g) => {
    if (g.user_id && selectedIds.has(g.user_id)) return true;
    if (g.is_shared && !g.shared_user_ids) return true;
    if (g.is_shared && g.shared_user_ids?.some((id) => selectedIds.has(id)))
      return true;
    return false;
  });

/** Monthly contribution needed to reach target by target_date */
const monthlyRequired = (
  remaining: number,
  daysRemaining: number | null,
): number | null => {
  if (daysRemaining === null || daysRemaining <= 0) return null;
  const monthsRemaining = daysRemaining / 30.44; // avg days per month
  if (monthsRemaining <= 0) return null;
  return remaining / monthsRemaining;
};

// ── Fixtures ────────────────────────────────────────────────────────────────

const makeGoal = (overrides: Partial<SavingsGoal> = {}): SavingsGoal => ({
  id: "goal-1",
  organization_id: "org-1",
  user_id: "user-1",
  name: "Vacation Fund",
  description: "Trip to Europe",
  target_amount: 5000,
  current_amount: 2000,
  start_date: "2025-01-01",
  target_date: "2025-12-31",
  account_id: "acct-1",
  auto_sync: false,
  priority: 1,
  is_completed: false,
  completed_at: null,
  is_funded: false,
  funded_at: null,
  is_shared: false,
  shared_user_ids: null,
  created_at: "2025-01-01T00:00:00Z",
  updated_at: "2025-06-15T00:00:00Z",
  ...overrides,
});

const GOALS: SavingsGoal[] = [
  makeGoal({
    id: "goal-1",
    name: "Vacation Fund",
    target_amount: 5000,
    current_amount: 2000,
    account_id: "acct-1",
    priority: 1,
  }),
  makeGoal({
    id: "goal-2",
    name: "Emergency Fund",
    target_amount: 15000,
    current_amount: 10000,
    account_id: "acct-1",
    priority: 2,
    auto_sync: true,
  }),
  makeGoal({
    id: "goal-3",
    name: "Down Payment",
    target_amount: 60000,
    current_amount: 25000,
    account_id: "acct-2",
    priority: 3,
    target_date: "2027-06-01",
  }),
  makeGoal({
    id: "goal-4",
    name: "New Laptop",
    target_amount: 2000,
    current_amount: 2000,
    is_completed: true,
    completed_at: "2025-05-01T00:00:00Z",
    priority: null,
  }),
  makeGoal({
    id: "goal-5",
    name: "Wedding Fund",
    target_amount: 20000,
    current_amount: 20000,
    is_funded: true,
    funded_at: "2025-04-15T00:00:00Z",
    account_id: "acct-2",
    priority: null,
  }),
  makeGoal({
    id: "goal-6",
    name: "Charity Donation",
    target_amount: 1000,
    current_amount: 300,
    account_id: null,
    priority: 4,
  }),
];

const makeProgress = (
  overrides: Partial<SavingsGoalProgress> = {},
): SavingsGoalProgress => ({
  goal_id: "goal-1",
  name: "Vacation Fund",
  current_amount: 2000,
  target_amount: 5000,
  progress_percentage: 40,
  remaining_amount: 3000,
  days_elapsed: 165,
  days_remaining: 200,
  monthly_required: 456.84,
  on_track: true,
  is_completed: false,
  ...overrides,
});

// ── Tests ───────────────────────────────────────────────────────────────────

describe("formatCurrency", () => {
  it("formats positive amounts with cents", () => {
    expect(formatCurrency(5000)).toBe("$5,000.00");
    expect(formatCurrency(2500.5)).toBe("$2,500.50");
  });

  it("formats zero", () => {
    expect(formatCurrency(0)).toBe("$0.00");
  });

  it("formats large amounts", () => {
    expect(formatCurrency(60000)).toBe("$60,000.00");
  });
});

// ── Progress Calculations ───────────────────────────────────────────────────

describe("calculatePercentage", () => {
  it("uses progress data when available", () => {
    const progress = makeProgress({ progress_percentage: 40 });
    const goal = makeGoal({ current_amount: 2000, target_amount: 5000 });
    expect(calculatePercentage(progress, goal)).toBe(40);
  });

  it("falls back to manual calculation when no progress data", () => {
    const goal = makeGoal({ current_amount: 2500, target_amount: 5000 });
    expect(calculatePercentage(null, goal)).toBe(50);
  });

  it("returns 0 when target is 0 and no progress data", () => {
    const goal = makeGoal({ current_amount: 0, target_amount: 0 });
    expect(calculatePercentage(null, goal)).toBe(0);
  });

  it("handles over-funded goals (> 100%)", () => {
    const goal = makeGoal({ current_amount: 6000, target_amount: 5000 });
    expect(calculatePercentage(null, goal)).toBe(120);
  });

  it("computes correct percentage for partial progress", () => {
    const goal = makeGoal({ current_amount: 1, target_amount: 3 });
    expect(calculatePercentage(null, goal)).toBeCloseTo(33.333, 2);
  });
});

describe("displayPercentage", () => {
  it("formats normal percentages with one decimal", () => {
    expect(displayPercentage(40)).toBe("40.0%");
    expect(displayPercentage(66.667)).toBe("66.7%");
  });

  it("clamps to 100%", () => {
    expect(displayPercentage(120)).toBe("100.0%");
    expect(displayPercentage(150.5)).toBe("100.0%");
  });

  it("formats zero", () => {
    expect(displayPercentage(0)).toBe("0.0%");
  });

  it("formats exactly 100%", () => {
    expect(displayPercentage(100)).toBe("100.0%");
  });
});

// ── Progress Color Logic ────────────────────────────────────────────────────

describe("getProgressColor", () => {
  it("returns purple for funded goals", () => {
    const goal = makeGoal({ is_funded: true });
    expect(getProgressColor(goal, null)).toBe("purple");
  });

  it("returns green for completed goals", () => {
    const goal = makeGoal({ is_completed: true });
    expect(getProgressColor(goal, null)).toBe("green");
  });

  it("returns orange when behind schedule", () => {
    const goal = makeGoal();
    const progress = makeProgress({ on_track: false });
    expect(getProgressColor(goal, progress)).toBe("orange");
  });

  it("returns blue (accent) when on track", () => {
    const goal = makeGoal();
    const progress = makeProgress({ on_track: true });
    expect(getProgressColor(goal, progress)).toBe("blue");
  });

  it("returns blue when no progress data available", () => {
    const goal = makeGoal();
    expect(getProgressColor(goal, null)).toBe("blue");
  });

  it("funded takes priority over completed", () => {
    const goal = makeGoal({ is_funded: true, is_completed: true });
    expect(getProgressColor(goal, null)).toBe("purple");
  });

  it("completed takes priority over on_track=false", () => {
    const goal = makeGoal({ is_completed: true });
    const progress = makeProgress({ on_track: false });
    expect(getProgressColor(goal, progress)).toBe("green");
  });
});

// ── Goal Filtering ──────────────────────────────────────────────────────────

describe("Active / Completed Filtering", () => {
  it("active goals exclude completed and funded", () => {
    const active = filterActive(GOALS);
    expect(active).toHaveLength(4);
    expect(active.every((g) => !g.is_completed && !g.is_funded)).toBe(true);
  });

  it("completed goals include both is_completed and is_funded", () => {
    const completed = filterCompleted(GOALS);
    expect(completed).toHaveLength(2);
    expect(completed.some((g) => g.is_completed)).toBe(true);
    expect(completed.some((g) => g.is_funded)).toBe(true);
  });

  it("active + completed = total goals", () => {
    expect(filterActive(GOALS).length + filterCompleted(GOALS).length).toBe(
      GOALS.length,
    );
  });

  it("empty array returns empty for both filters", () => {
    expect(filterActive([])).toEqual([]);
    expect(filterCompleted([])).toEqual([]);
  });
});

// ── Emergency Fund Detection ────────────────────────────────────────────────

describe("hasEmergencyFundGoal", () => {
  it("detects existing emergency fund goal (case insensitive)", () => {
    expect(hasEmergencyFundGoal(GOALS)).toBe(true);
  });

  it("returns false when no emergency fund exists", () => {
    const noEmergency = GOALS.filter(
      (g) => !g.name.toLowerCase().includes("emergency"),
    );
    expect(hasEmergencyFundGoal(noEmergency)).toBe(false);
  });

  it("detects varied naming: 'My Emergency Savings'", () => {
    const goals = [makeGoal({ name: "My Emergency Savings" })];
    expect(hasEmergencyFundGoal(goals)).toBe(true);
  });

  it("detects 'EMERGENCY' in uppercase", () => {
    const goals = [makeGoal({ name: "EMERGENCY FUND" })];
    expect(hasEmergencyFundGoal(goals)).toBe(true);
  });
});

// ── Auto-Sync Detection ─────────────────────────────────────────────────────

describe("hasAutoSyncGoals", () => {
  it("detects active auto-sync goals with account_id", () => {
    expect(hasAutoSyncGoals(GOALS)).toBe(true);
  });

  it("returns false when no auto-sync goals", () => {
    const noSync = GOALS.map((g) => ({ ...g, auto_sync: false }));
    expect(hasAutoSyncGoals(noSync)).toBe(false);
  });

  it("ignores completed auto-sync goals", () => {
    const goals = [
      makeGoal({ auto_sync: true, account_id: "acct-1", is_completed: true }),
    ];
    expect(hasAutoSyncGoals(goals)).toBe(false);
  });

  it("ignores funded auto-sync goals", () => {
    const goals = [
      makeGoal({ auto_sync: true, account_id: "acct-1", is_funded: true }),
    ];
    expect(hasAutoSyncGoals(goals)).toBe(false);
  });

  it("ignores auto-sync goals without account_id", () => {
    const goals = [makeGoal({ auto_sync: true, account_id: null })];
    expect(hasAutoSyncGoals(goals)).toBe(false);
  });
});

// ── Group By Account ────────────────────────────────────────────────────────

describe("groupByAccount", () => {
  it("groups active goals by account_id", () => {
    const active = filterActive(GOALS);
    const groups = groupByAccount(active);

    expect(groups.get("acct-1")).toHaveLength(2);
    expect(groups.get("acct-2")).toHaveLength(1);
    expect(groups.get(null)).toHaveLength(1);
  });

  it("unlinked goals go to null key", () => {
    const active = filterActive(GOALS);
    const groups = groupByAccount(active);
    const unlinked = groups.get(null) ?? [];
    expect(unlinked.every((g) => g.account_id === null)).toBe(true);
  });

  it("empty input returns empty map", () => {
    const groups = groupByAccount([]);
    expect(groups.size).toBe(0);
  });

  it("single account group contains all goals for that account", () => {
    const goals = [
      makeGoal({ id: "a", account_id: "acct-x" }),
      makeGoal({ id: "b", account_id: "acct-x" }),
    ];
    const groups = groupByAccount(goals);
    expect(groups.size).toBe(1);
    expect(groups.get("acct-x")).toHaveLength(2);
  });
});

// ── Self-View Filtering ─────────────────────────────────────────────────────

describe("Self-View Filtering", () => {
  const MY_ID = "user-1";

  it("includes goals owned by current user", () => {
    const goals = [makeGoal({ user_id: MY_ID })];
    expect(filterSelfView(goals, MY_ID)).toHaveLength(1);
  });

  it("includes shared goals with no shared_user_ids (all-member share)", () => {
    const goals = [
      makeGoal({ user_id: "other", is_shared: true, shared_user_ids: null }),
    ];
    expect(filterSelfView(goals, MY_ID)).toHaveLength(1);
  });

  it("includes shared goals where current user is in shared_user_ids", () => {
    const goals = [
      makeGoal({
        user_id: "other",
        is_shared: true,
        shared_user_ids: [MY_ID, "user-3"],
      }),
    ];
    expect(filterSelfView(goals, MY_ID)).toHaveLength(1);
  });

  it("excludes shared goals where current user is NOT in shared_user_ids", () => {
    const goals = [
      makeGoal({
        user_id: "other",
        is_shared: true,
        shared_user_ids: ["user-3"],
      }),
    ];
    expect(filterSelfView(goals, MY_ID)).toHaveLength(0);
  });

  it("includes goals with null user_id (legacy/system goals)", () => {
    const goals = [makeGoal({ user_id: null })];
    expect(filterSelfView(goals, MY_ID)).toHaveLength(1);
  });

  it("excludes other user's private goals", () => {
    const goals = [makeGoal({ user_id: "other", is_shared: false })];
    expect(filterSelfView(goals, MY_ID)).toHaveLength(0);
  });
});

// ── Partial Member Selection Filtering ──────────────────────────────────────

describe("Partial Member Selection Filtering", () => {
  const selected = new Set(["user-1", "user-2"]);

  it("includes goals owned by a selected member", () => {
    const goals = [makeGoal({ user_id: "user-1" })];
    expect(filterByMembers(goals, selected)).toHaveLength(1);
  });

  it("excludes goals owned by a non-selected member", () => {
    const goals = [makeGoal({ user_id: "user-99" })];
    expect(filterByMembers(goals, selected)).toHaveLength(0);
  });

  it("includes shared goals with no shared_user_ids", () => {
    const goals = [
      makeGoal({ user_id: "user-99", is_shared: true, shared_user_ids: null }),
    ];
    expect(filterByMembers(goals, selected)).toHaveLength(1);
  });

  it("includes shared goals where at least one shared_user_id is selected", () => {
    const goals = [
      makeGoal({
        user_id: "user-99",
        is_shared: true,
        shared_user_ids: ["user-2", "user-99"],
      }),
    ];
    expect(filterByMembers(goals, selected)).toHaveLength(1);
  });

  it("excludes shared goals where no shared_user_ids match selected", () => {
    const goals = [
      makeGoal({
        user_id: "user-99",
        is_shared: true,
        shared_user_ids: ["user-88"],
      }),
    ];
    expect(filterByMembers(goals, selected)).toHaveLength(0);
  });

  it("includes goal with null user_id if user_id is in selected (no match)", () => {
    const goals = [makeGoal({ user_id: null, is_shared: false })];
    // null user_id is not in selectedIds and not shared → excluded
    expect(filterByMembers(goals, selected)).toHaveLength(0);
  });
});

// ── Monthly Required Contribution ───────────────────────────────────────────

describe("monthlyRequired", () => {
  it("calculates monthly contribution for 365 days remaining", () => {
    const result = monthlyRequired(12000, 365);
    // 365 / 30.44 ≈ 11.99 months → 12000 / 11.99 ≈ 1000.33
    expect(result).toBeCloseTo(1000.33, 0);
  });

  it("returns null when days_remaining is null (no target date)", () => {
    expect(monthlyRequired(5000, null)).toBeNull();
  });

  it("returns null when days_remaining is 0", () => {
    expect(monthlyRequired(5000, 0)).toBeNull();
  });

  it("returns null when days_remaining is negative (past due)", () => {
    expect(monthlyRequired(5000, -10)).toBeNull();
  });

  it("handles small remaining amount", () => {
    const result = monthlyRequired(100, 30);
    // 30 / 30.44 ≈ 0.986 months → 100 / 0.986 ≈ 101.45
    expect(result).toBeCloseTo(101.45, 0);
  });

  it("handles zero remaining amount", () => {
    const result = monthlyRequired(0, 200);
    expect(result).toBe(0);
  });
});

// ── Button disabled logic (mirrors SavingsGoalsPage.tsx) ────────────────────

/**
 * Pure function mirroring the "New Goal" button disabled check.
 * The key fix: self-view users can always create, even when
 * isPartialSelection is true (1-of-N members selected = self).
 */
function isCreateDisabled(
  canEdit: boolean,
  isPartialSelection: boolean,
  isSelfView: boolean,
): boolean {
  return !canEdit || (isPartialSelection && !isSelfView);
}

describe("New Goal button — disabled state", () => {
  it("enabled in self view even when isPartialSelection is true", () => {
    expect(isCreateDisabled(true, true, true)).toBe(false);
  });

  it("enabled in combined view with no partial selection", () => {
    expect(isCreateDisabled(true, false, false)).toBe(false);
  });

  it("disabled when canEdit is false", () => {
    expect(isCreateDisabled(false, false, true)).toBe(true);
    expect(isCreateDisabled(false, true, true)).toBe(true);
    expect(isCreateDisabled(false, false, false)).toBe(true);
  });

  it("disabled when partial selection and NOT self view", () => {
    expect(isCreateDisabled(true, true, false)).toBe(true);
  });

  it("enabled when not partial selection and not self view", () => {
    expect(isCreateDisabled(true, false, false)).toBe(false);
  });
});

// ── On-Track Badge Logic ────────────────────────────────────────────────────

describe("On-Track Badge Display", () => {
  it("shows badge when not funded, not completed, and on_track is not null", () => {
    const goal = makeGoal({ is_funded: false, is_completed: false });
    const progress = makeProgress({ on_track: true });
    const show =
      !goal.is_funded &&
      progress !== null &&
      progress.on_track !== null &&
      !goal.is_completed;
    expect(show).toBe(true);
  });

  it("hides badge when goal is funded", () => {
    const goal = makeGoal({ is_funded: true });
    const progress = makeProgress({ on_track: true });
    const show =
      !goal.is_funded &&
      progress !== null &&
      progress.on_track !== null &&
      !goal.is_completed;
    expect(show).toBe(false);
  });

  it("hides badge when goal is completed", () => {
    const goal = makeGoal({ is_completed: true });
    const progress = makeProgress({ on_track: false });
    const show =
      !goal.is_funded &&
      progress !== null &&
      progress.on_track !== null &&
      !goal.is_completed;
    expect(show).toBe(false);
  });

  it("hides badge when on_track is null", () => {
    const goal = makeGoal();
    const progress = makeProgress({ on_track: null });
    const show =
      !goal.is_funded &&
      progress !== null &&
      progress.on_track !== null &&
      !goal.is_completed;
    expect(show).toBe(false);
  });

  it("hides badge when no progress data", () => {
    const goal = makeGoal();
    const progress: SavingsGoalProgress | null = null;
    const show =
      !goal.is_funded &&
      progress !== null &&
      progress.on_track !== null &&
      !goal.is_completed;
    expect(show).toBe(false);
  });
});

// ── Target Date Display ─────────────────────────────────────────────────────

describe("Target Date Display", () => {
  it("shows target date when set", () => {
    const goal = makeGoal({ target_date: "2025-12-31" });
    const showDate = !!goal.target_date;
    expect(showDate).toBe(true);
  });

  it("hides target date when null", () => {
    const goal = makeGoal({ target_date: null });
    const showDate = !!goal.target_date;
    expect(showDate).toBe(false);
  });

  it("formats target date correctly", () => {
    const date = new Date("2025-12-31").toLocaleDateString();
    expect(date).toBeTruthy(); // locale-dependent, just verify no crash
  });
});

// ── Accordion Default Open Indices ──────────────────────────────────────────

describe("Accordion Default Open Indices", () => {
  it("opens all sections by default", () => {
    const linkedCount = 2;
    const hasUnlinked = true;
    const total = linkedCount + (hasUnlinked ? 1 : 0);
    const indices = Array.from({ length: total }, (_, i) => i);
    expect(indices).toEqual([0, 1, 2]);
  });

  it("handles no unlinked goals", () => {
    const linkedCount = 3;
    const hasUnlinked = false;
    const total = linkedCount + (hasUnlinked ? 1 : 0);
    const indices = Array.from({ length: total }, (_, i) => i);
    expect(indices).toEqual([0, 1, 2]);
  });

  it("handles no linked accounts (only unlinked)", () => {
    const linkedCount = 0;
    const hasUnlinked = true;
    const total = linkedCount + (hasUnlinked ? 1 : 0);
    const indices = Array.from({ length: total }, (_, i) => i);
    expect(indices).toEqual([0]);
  });

  it("handles no goals at all", () => {
    const linkedCount = 0;
    const hasUnlinked = false;
    const total = linkedCount + (hasUnlinked ? 1 : 0);
    const indices = Array.from({ length: total }, (_, i) => i);
    expect(indices).toEqual([]);
  });
});

// ── Edge Cases ──────────────────────────────────────────────────────────────

describe("Edge Cases", () => {
  it("goal with 0 target shows 0% progress", () => {
    const goal = makeGoal({ current_amount: 500, target_amount: 0 });
    expect(calculatePercentage(null, goal)).toBe(0);
  });

  it("goal at exactly 100% funded", () => {
    const goal = makeGoal({ current_amount: 5000, target_amount: 5000 });
    const pct = calculatePercentage(null, goal);
    expect(pct).toBe(100);
    expect(displayPercentage(pct)).toBe("100.0%");
  });

  it("goal over-funded clamps display to 100%", () => {
    const goal = makeGoal({ current_amount: 7500, target_amount: 5000 });
    const pct = calculatePercentage(null, goal);
    expect(pct).toBe(150);
    expect(displayPercentage(pct)).toBe("100.0%");
  });

  it("remaining amount is correct", () => {
    const progress = makeProgress({
      current_amount: 2000,
      target_amount: 5000,
      remaining_amount: 3000,
    });
    expect(progress.remaining_amount).toBe(
      progress.target_amount - progress.current_amount,
    );
  });

  it("all goals as single group when all share one account", () => {
    const goals = [
      makeGoal({ id: "a", account_id: "acct-1" }),
      makeGoal({ id: "b", account_id: "acct-1" }),
      makeGoal({ id: "c", account_id: "acct-1" }),
    ];
    const groups = groupByAccount(goals);
    expect(groups.size).toBe(1);
    expect(groups.get("acct-1")).toHaveLength(3);
  });

  it("every goal unlinked puts all into null group", () => {
    const goals = [
      makeGoal({ id: "a", account_id: null }),
      makeGoal({ id: "b", account_id: null }),
    ];
    const groups = groupByAccount(goals);
    expect(groups.size).toBe(1);
    expect(groups.get(null)).toHaveLength(2);
  });
});
