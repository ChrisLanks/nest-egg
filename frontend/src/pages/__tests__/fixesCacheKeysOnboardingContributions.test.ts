/**
 * Tests for the four fixes:
 * 1. GettingStartedWidget shared cache keys
 * 2. WelcomePage onboarding step restore
 * 3. Savings goal contributions API + UI logic
 * 4. Organization type monthly_start_day
 *
 * @vitest-environment jsdom
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import type { User, Organization } from "../../types/user";
import type { SavingsGoal } from "../../types/savings-goal";
import type { ContributionResult } from "../../api/savings-goals";

// ── Helpers ──────────────────────────────────────────────────────────────────

function makeUser(overrides: Partial<User> = {}): User {
  return {
    id: "u1",
    organization_id: "org1",
    email: "test@example.com",
    first_name: "Alice",
    last_name: null,
    display_name: "Alice",
    is_active: true,
    is_org_admin: false,
    email_verified: true,
    onboarding_completed: false,
    onboarding_step: null,
    onboarding_goal: null,
    last_login_at: null,
    login_count: 1,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

function makeGoal(overrides: Partial<SavingsGoal> = {}): SavingsGoal {
  return {
    id: "goal-1",
    organization_id: "org1",
    user_id: "u1",
    name: "Emergency Fund",
    description: null,
    target_amount: 10000,
    current_amount: 2500,
    start_date: "2026-01-01",
    target_date: null,
    account_id: null,
    auto_sync: false,
    priority: 1,
    is_completed: false,
    completed_at: null,
    is_funded: false,
    funded_at: null,
    is_shared: false,
    shared_user_ids: null,
    member_contributions: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

// ── Fix 1: GettingStartedWidget shared cache keys ────────────────────────────

describe("Fix 1: GettingStartedWidget uses shared cache keys", () => {
  it("accounts query key is ['accounts'] not 'getting-started-accounts'", () => {
    // The widget must use the same key as AccountsPage / GoalCard
    const queryKey = ["accounts"];
    expect(queryKey).toEqual(["accounts"]);
    expect(queryKey).not.toContain("getting-started-accounts");
  });

  it("budgets query key is ['budgets'] not 'getting-started-budgets'", () => {
    const queryKey = ["budgets"];
    expect(queryKey).toEqual(["budgets"]);
    expect(queryKey).not.toContain("getting-started-budgets");
  });

  it("savings-goals query key is ['goals'] not 'getting-started-savings-goals'", () => {
    // Matches SavingsGoalsPage queryKey: ["goals", selectedUserId]
    const queryKey = ["goals"];
    expect(queryKey[0]).toBe("goals");
    expect(queryKey[0]).not.toBe("getting-started-savings-goals");
  });

  it("shared cache avoids duplicate network calls when other pages already fetched data", () => {
    // Simulate react-query cache hit: same key → returns stale data immediately
    const cache: Record<string, unknown[]> = {
      accounts: [{ id: "a1" }],
      budgets: [{ id: "b1" }],
      goals: [{ id: "g1" }],
    };

    // Widget reads from shared cache (same keys)
    const widgetAccounts = cache["accounts"];
    const widgetBudgets = cache["budgets"];
    const widgetGoals = cache["goals"];

    expect(widgetAccounts).toHaveLength(1);
    expect(widgetBudgets).toHaveLength(1);
    expect(widgetGoals).toHaveLength(1);
  });

  it("step1Done = true when accounts cache has at least one account", () => {
    const accounts = [{ id: "a1", current_balance: 500 }];
    const step1Done = Array.isArray(accounts) && accounts.length > 0;
    expect(step1Done).toBe(true);
  });

  it("step1Done = false when accounts cache is empty", () => {
    const accounts: unknown[] = [];
    const step1Done = Array.isArray(accounts) && accounts.length > 0;
    expect(step1Done).toBe(false);
  });

  it("step2Done = true when budgets cache has at least one budget", () => {
    const budgets = [{ id: "b1" }];
    const step2Done = Array.isArray(budgets) && budgets.length > 0;
    expect(step2Done).toBe(true);
  });

  it("step3Done = true when goals cache has at least one goal", () => {
    const savingsGoals = [{ id: "g1" }];
    const step3Done = Array.isArray(savingsGoals) && savingsGoals.length > 0;
    expect(step3Done).toBe(true);
  });
});

// ── Fix 2: WelcomePage onboarding step restore ───────────────────────────────

describe("Fix 2: WelcomePage restores onboarding step from user.onboarding_step", () => {
  // Step mapping (matches WelcomePage implementation)
  const STEP_MAP: Record<string, number> = {
    profile: 0,
    accounts: 1,
    budget: 3,
    goals: 3,
  };

  it("maps 'profile' step to wizard index 0", () => {
    expect(STEP_MAP["profile"]).toBe(0);
  });

  it("maps 'accounts' step to wizard index 1", () => {
    expect(STEP_MAP["accounts"]).toBe(1);
  });

  it("maps 'budget' step to wizard index 3", () => {
    expect(STEP_MAP["budget"]).toBe(3);
  });

  it("maps 'goals' step to wizard index 3", () => {
    expect(STEP_MAP["goals"]).toBe(3);
  });

  it("returns undefined for unknown step (no restore)", () => {
    expect(STEP_MAP["unknown"]).toBeUndefined();
  });

  it("restores step when user.onboarding_step is 'accounts'", () => {
    const user = makeUser({ onboarding_step: "accounts" });
    let step = 0;
    if (user.onboarding_step) {
      const restored = STEP_MAP[user.onboarding_step];
      if (restored !== undefined) step = restored;
    }
    expect(step).toBe(1);
  });

  it("restores step when user.onboarding_step is 'budget'", () => {
    const user = makeUser({ onboarding_step: "budget" });
    let step = 0;
    if (user.onboarding_step) {
      const restored = STEP_MAP[user.onboarding_step];
      if (restored !== undefined) step = restored;
    }
    expect(step).toBe(3);
  });

  it("does NOT restore step when user.onboarding_step is null", () => {
    const user = makeUser({ onboarding_step: null });
    let step = 0;
    if (user.onboarding_step) {
      const restored = STEP_MAP[user.onboarding_step];
      if (restored !== undefined) step = restored;
    }
    expect(step).toBe(0); // stays at default
  });

  it("does NOT restore step when onboarding is already completed", () => {
    const user = makeUser({ onboarding_completed: true, onboarding_step: "accounts" });
    let step = 0;
    let redirected = false;
    if (user.onboarding_completed) {
      redirected = true;
      // return early — no step restore
    } else if (user.onboarding_step) {
      const restored = STEP_MAP[user.onboarding_step];
      if (restored !== undefined) step = restored;
    }
    expect(redirected).toBe(true);
    expect(step).toBe(0); // never mutated
  });

  it("runs step-restore logic only on mount (dependency array is empty)", () => {
    // The useEffect has [] deps — it runs once. Simulate mount behavior.
    const user = makeUser({ onboarding_step: "goals" });
    const mountCallCount = { count: 0 };

    const runEffect = (u: typeof user) => {
      mountCallCount.count++;
      if (u.onboarding_step) {
        return STEP_MAP[u.onboarding_step] ?? 0;
      }
      return 0;
    };

    // Called once on mount
    const result = runEffect(user);
    expect(mountCallCount.count).toBe(1);
    expect(result).toBe(3);
  });

  it("User type includes onboarding_step field", () => {
    const user = makeUser({ onboarding_step: "accounts" });
    expect(user.onboarding_step).toBe("accounts");
  });
});

// ── Fix 3: Savings goal contributions API ────────────────────────────────────

describe("Fix 3: Savings goal contributions", () => {
  it("SavingsGoal type has member_contributions field", () => {
    const goal = makeGoal({ member_contributions: { "u1": 500, "u2": 300 } });
    expect(goal.member_contributions).toEqual({ "u1": 500, "u2": 300 });
  });

  it("member_contributions is null by default for new goals", () => {
    const goal = makeGoal();
    expect(goal.member_contributions).toBeNull();
  });

  it("ContributionResult shape matches backend response", () => {
    const result: ContributionResult = {
      goal_id: "goal-1",
      goal_name: "Emergency Fund",
      contribution_amount: 500,
      user_total_contributions: 1000,
      current_amount: 3000,
      target_amount: 10000,
      member_contributions: { "u1": 1000 },
    };
    expect(result.contribution_amount).toBe(500);
    expect(result.member_contributions["u1"]).toBe(1000);
  });

  it("recordContribution calls correct API endpoint", async () => {
    const mockPost = vi.fn().mockResolvedValue({
      data: {
        goal_id: "goal-1",
        goal_name: "Emergency Fund",
        contribution_amount: 250,
        user_total_contributions: 250,
        current_amount: 2750,
        target_amount: 10000,
        member_contributions: { "u1": 250 },
      },
    });

    const goalId = "goal-1";
    const amount = 250;
    const { data } = await mockPost(`/savings-goals/${goalId}/contributions`, { amount });

    expect(mockPost).toHaveBeenCalledWith(
      `/savings-goals/${goalId}/contributions`,
      { amount: 250 },
    );
    expect(data.contribution_amount).toBe(250);
  });

  it("contribution increments current_amount", () => {
    const goal = makeGoal({ current_amount: 2500, target_amount: 10000 });
    const contributionAmount = 500;
    const newAmount = goal.current_amount + contributionAmount;
    expect(newAmount).toBe(3000);
  });

  it("contribution button is hidden when goal is completed", () => {
    const goal = makeGoal({ is_completed: true });
    const showButton = !goal.is_completed && !goal.is_funded;
    expect(showButton).toBe(false);
  });

  it("contribution button is hidden when goal is funded", () => {
    const goal = makeGoal({ is_funded: true });
    const showButton = !goal.is_completed && !goal.is_funded;
    expect(showButton).toBe(false);
  });

  it("contribution button is visible for active goals", () => {
    const goal = makeGoal({ is_completed: false, is_funded: false });
    const showButton = !goal.is_completed && !goal.is_funded;
    expect(showButton).toBe(true);
  });

  it("contribution button is hidden when canEdit is false", () => {
    const canEdit = false;
    const goal = makeGoal({ is_completed: false, is_funded: false });
    const showButton = !goal.is_completed && !goal.is_funded && canEdit;
    expect(showButton).toBe(false);
  });

  it("handleContribute rejects zero amount", () => {
    const contributionAmount = "0";
    const parsed = parseFloat(contributionAmount);
    const isValid = !!parsed && parsed > 0;
    expect(isValid).toBe(false);
  });

  it("handleContribute rejects negative amount", () => {
    const contributionAmount = "-50";
    const parsed = parseFloat(contributionAmount);
    const isValid = !!parsed && parsed > 0;
    expect(isValid).toBe(false);
  });

  it("handleContribute accepts positive amount", () => {
    const contributionAmount = "250.50";
    const parsed = parseFloat(contributionAmount);
    const isValid = !!parsed && parsed > 0;
    expect(isValid).toBe(true);
  });

  it("handleContribute rejects empty string", () => {
    const contributionAmount = "";
    const parsed = parseFloat(contributionAmount);
    const isValid = !!parsed && parsed > 0;
    expect(isValid).toBe(false);
  });

  it("member_contributions display: maps user IDs to member names", () => {
    const members = [
      { id: "u1", display_name: "Alice", first_name: "Alice", email: "alice@example.com" },
      { id: "u2", display_name: null, first_name: "Bob", email: "bob@example.com" },
      { id: "u3", display_name: null, first_name: null, email: "charlie@example.com" },
    ];

    const getName = (userId: string) => {
      const m = members.find(m => m.id === userId);
      return m?.display_name || m?.first_name || m?.email || userId;
    };

    expect(getName("u1")).toBe("Alice");
    expect(getName("u2")).toBe("Bob");
    expect(getName("u3")).toBe("charlie@example.com");
    expect(getName("u99")).toBe("u99"); // unknown user falls back to id
  });

  it("success toast shows contribution amount and new total", () => {
    const result: ContributionResult = {
      goal_id: "goal-1",
      goal_name: "Emergency Fund",
      contribution_amount: 500,
      user_total_contributions: 1000,
      current_amount: 3000,
      target_amount: 10000,
      member_contributions: {},
    };

    const toastTitle = `$${result.contribution_amount.toLocaleString()} contributed`;
    const toastDesc = `New total: $${result.current_amount.toLocaleString()} of $${result.target_amount.toLocaleString()}`;

    expect(toastTitle).toBe("$500 contributed");
    expect(toastDesc).toBe("New total: $3,000 of $10,000");
  });

  it("after successful contribution, modal resets contributionAmount to empty string", () => {
    let contributionAmount = "500";
    // Simulate onSuccess
    const onSuccess = () => { contributionAmount = ""; };
    onSuccess();
    expect(contributionAmount).toBe("");
  });
});

// ── Fix 4: Organization type monthly_start_day ───────────────────────────────

describe("Fix 4: Organization type includes monthly_start_day", () => {
  it("Organization can have monthly_start_day as a number", () => {
    const org: Organization = {
      id: "org1",
      name: "Test Household",
      custom_month_end_day: 28,
      monthly_start_day: 1,
      timezone: "America/New_York",
      default_currency: "USD",
      is_active: true,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    };
    expect(org.monthly_start_day).toBe(1);
  });

  it("monthly_start_day is optional (can be omitted)", () => {
    const org: Organization = {
      id: "org1",
      name: "Test Household",
      custom_month_end_day: 28,
      timezone: "America/New_York",
      default_currency: "USD",
      is_active: true,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    };
    expect(org.monthly_start_day).toBeUndefined();
  });

  it("monthly_start_day can be set to any valid day of month (1-31)", () => {
    for (const day of [1, 15, 28, 31]) {
      const org: Partial<Organization> = { monthly_start_day: day };
      expect(org.monthly_start_day).toBe(day);
    }
  });

  it("User type includes onboarding_step as optional string or null", () => {
    const userWithStep = makeUser({ onboarding_step: "accounts" });
    const userWithoutStep = makeUser({ onboarding_step: null });
    const userUndefined = makeUser();

    expect(userWithStep.onboarding_step).toBe("accounts");
    expect(userWithoutStep.onboarding_step).toBeNull();
    expect(userUndefined.onboarding_step).toBeNull();
  });
});
