/**
 * Tests for:
 * 1. Goal template picker visibility (SavingsGoalsPage)
 *    - Which templates are shown vs hidden based on existing goal names
 *    - All 4 templates visible when user has no goals
 *    - Individual cards hidden when matching goal already exists
 *
 * 2. Budget suggestions visibility gate (BudgetsPage)
 *    - Starter budgets shown when no spending history (empty API response)
 *    - History-based suggestions shown when API returns data
 *    - Suggestions shown in combined view (selectedUserId = null)
 *    - Suggestions not shown when canEdit = false
 *
 * 3. BudgetSuggestions isHistoryBased flag
 *    - Derives correctly from whether API returned results
 *
 * @vitest-environment jsdom
 */

import { describe, it, expect } from "vitest";
import type { BudgetSuggestion } from "../../../types/budget";

// ── Goal template visibility (mirrors SavingsGoalsPage.tsx) ──────────────────

type GoalTemplateKey =
  | "emergency_fund"
  | "vacation_fund"
  | "home_down_payment"
  | "debt_payoff_reserve";

interface GoalTemplate {
  key: GoalTemplateKey;
  label: string;
  hidden: boolean;
}

/** Mirrors the hidden-detection logic in SavingsGoalsPage.tsx */
function buildVisibleTemplates(goalNames: string[]): GoalTemplate[] {
  const lower = goalNames.map((n) => n.toLowerCase());

  const hasEmergencyFund = lower.some((n) => n.includes("emergency"));
  const hasVacation = lower.some(
    (n) => n.includes("vacation") || n.includes("travel"),
  );
  const hasDownPayment = lower.some(
    (n) => n.includes("down payment") || n.includes("home"),
  );
  const hasDebtPayoff = lower.some(
    (n) => n.includes("debt") || n.includes("payoff"),
  );

  const templates: GoalTemplate[] = [
    {
      key: "emergency_fund",
      label: "Emergency Fund",
      hidden: hasEmergencyFund,
    },
    { key: "vacation_fund", label: "Vacation Fund", hidden: hasVacation },
    {
      key: "home_down_payment",
      label: "Home Down Payment",
      hidden: hasDownPayment,
    },
    {
      key: "debt_payoff_reserve",
      label: "Debt Payoff Reserve",
      hidden: hasDebtPayoff,
    },
  ];

  return templates.filter((t) => !t.hidden);
}

// ── Budget suggestions visibility (mirrors BudgetsPage.tsx) ──────────────────

function shouldShowSuggestions(opts: {
  canEdit: boolean;
  isSelfView: boolean;
  selectedUserId: string | null;
}): boolean {
  const { canEdit, isSelfView, selectedUserId } = opts;
  return canEdit && (isSelfView || !selectedUserId);
}

// ── STARTER_BUDGETS (mirrors BudgetSuggestions.tsx) ───────────────────────────

const STARTER_BUDGETS: BudgetSuggestion[] = [
  {
    category_name: "Groceries",
    category_id: null,
    suggested_amount: 400,
    suggested_period: "monthly",
    avg_monthly_spend: 0,
    total_spend: 0,
    month_count: 0,
    transaction_count: 0,
  },
  {
    category_name: "Dining Out",
    category_id: null,
    suggested_amount: 200,
    suggested_period: "monthly",
    avg_monthly_spend: 0,
    total_spend: 0,
    month_count: 0,
    transaction_count: 0,
  },
  {
    category_name: "Gas & Transportation",
    category_id: null,
    suggested_amount: 150,
    suggested_period: "monthly",
    avg_monthly_spend: 0,
    total_spend: 0,
    month_count: 0,
    transaction_count: 0,
  },
  {
    category_name: "Entertainment",
    category_id: null,
    suggested_amount: 100,
    suggested_period: "monthly",
    avg_monthly_spend: 0,
    total_spend: 0,
    month_count: 0,
    transaction_count: 0,
  },
  {
    category_name: "Shopping",
    category_id: null,
    suggested_amount: 200,
    suggested_period: "monthly",
    avg_monthly_spend: 0,
    total_spend: 0,
    month_count: 0,
    transaction_count: 0,
  },
  {
    category_name: "Subscriptions",
    category_id: null,
    suggested_amount: 50,
    suggested_period: "monthly",
    avg_monthly_spend: 0,
    total_spend: 0,
    month_count: 0,
    transaction_count: 0,
  },
];

/** Mirrors BudgetSuggestions.tsx: use starter budgets if API returns nothing */
function resolveSuggestions(historySuggestions: BudgetSuggestion[]): {
  suggestions: BudgetSuggestion[];
  isHistoryBased: boolean;
} {
  const isHistoryBased = historySuggestions.length > 0;
  return {
    suggestions: isHistoryBased ? historySuggestions : STARTER_BUDGETS,
    isHistoryBased,
  };
}

// ── Tests: goal template picker ───────────────────────────────────────────────

describe("Goal template picker: visibility", () => {
  it("shows all 4 templates when user has no goals", () => {
    const visible = buildVisibleTemplates([]);
    expect(visible).toHaveLength(4);
    expect(visible.map((t) => t.key)).toEqual([
      "emergency_fund",
      "vacation_fund",
      "home_down_payment",
      "debt_payoff_reserve",
    ]);
  });

  it("hides Emergency Fund when a goal named 'Emergency Fund' exists", () => {
    const visible = buildVisibleTemplates(["Emergency Fund"]);
    expect(visible.find((t) => t.key === "emergency_fund")).toBeUndefined();
    expect(visible).toHaveLength(3);
  });

  it("hides Emergency Fund for case-insensitive match ('my emergency savings')", () => {
    const visible = buildVisibleTemplates(["My Emergency Savings"]);
    expect(visible.find((t) => t.key === "emergency_fund")).toBeUndefined();
  });

  it("hides Vacation Fund when goal includes 'vacation'", () => {
    const visible = buildVisibleTemplates(["Europe Vacation 2026"]);
    expect(visible.find((t) => t.key === "vacation_fund")).toBeUndefined();
  });

  it("hides Vacation Fund when goal includes 'travel'", () => {
    const visible = buildVisibleTemplates(["Travel Fund"]);
    expect(visible.find((t) => t.key === "vacation_fund")).toBeUndefined();
  });

  it("hides Home Down Payment when goal includes 'down payment'", () => {
    const visible = buildVisibleTemplates(["House Down Payment"]);
    expect(visible.find((t) => t.key === "home_down_payment")).toBeUndefined();
  });

  it("hides Home Down Payment when goal includes 'home'", () => {
    const visible = buildVisibleTemplates(["New Home Fund"]);
    expect(visible.find((t) => t.key === "home_down_payment")).toBeUndefined();
  });

  it("hides Debt Payoff Reserve when goal includes 'debt'", () => {
    const visible = buildVisibleTemplates(["Credit Card Debt"]);
    expect(
      visible.find((t) => t.key === "debt_payoff_reserve"),
    ).toBeUndefined();
  });

  it("hides Debt Payoff Reserve when goal includes 'payoff'", () => {
    const visible = buildVisibleTemplates(["Loan Payoff"]);
    expect(
      visible.find((t) => t.key === "debt_payoff_reserve"),
    ).toBeUndefined();
  });

  it("hides only the matching template — others still visible", () => {
    const visible = buildVisibleTemplates(["Emergency Fund"]);
    expect(visible.map((t) => t.key)).toContain("vacation_fund");
    expect(visible.map((t) => t.key)).toContain("home_down_payment");
    expect(visible.map((t) => t.key)).toContain("debt_payoff_reserve");
  });

  it("shows no templates when all 4 matching goals exist", () => {
    const visible = buildVisibleTemplates([
      "Emergency Fund",
      "Vacation Savings",
      "Home Down Payment",
      "Debt Payoff",
    ]);
    expect(visible).toHaveLength(0);
  });

  it("unrelated goal names don't hide any templates", () => {
    const visible = buildVisibleTemplates([
      "Wedding Fund",
      "New Car",
      "College Tuition",
    ]);
    expect(visible).toHaveLength(4);
  });

  it("multiple matching names still hides only one template (dedup)", () => {
    const visible = buildVisibleTemplates([
      "Emergency Fund",
      "Emergency Savings",
    ]);
    // Both match 'emergency' but it's the same template key
    const emergencyCount = visible.filter(
      (t) => t.key === "emergency_fund",
    ).length;
    expect(emergencyCount).toBe(0);
    expect(visible).toHaveLength(3);
  });
});

// ── Tests: budget suggestions visibility gate ─────────────────────────────────

describe("Budget suggestions visibility gate", () => {
  it("shows suggestions in combined view (selectedUserId = null, canEdit)", () => {
    expect(
      shouldShowSuggestions({
        canEdit: true,
        isSelfView: false,
        selectedUserId: null,
      }),
    ).toBe(true);
  });

  it("shows suggestions in self view", () => {
    expect(
      shouldShowSuggestions({
        canEdit: true,
        isSelfView: true,
        selectedUserId: "user-1",
      }),
    ).toBe(true);
  });

  it("hides suggestions when canEdit is false (read-only view)", () => {
    expect(
      shouldShowSuggestions({
        canEdit: false,
        isSelfView: true,
        selectedUserId: "user-1",
      }),
    ).toBe(false);
    expect(
      shouldShowSuggestions({
        canEdit: false,
        isSelfView: false,
        selectedUserId: null,
      }),
    ).toBe(false);
  });

  it("hides suggestions when viewing another user (not self, not combined)", () => {
    expect(
      shouldShowSuggestions({
        canEdit: true,
        isSelfView: false,
        selectedUserId: "other-user",
      }),
    ).toBe(false);
  });

  it("shows suggestions when isSelfView even if selectedUserId is set", () => {
    // User clicked their own name in household selector
    expect(
      shouldShowSuggestions({
        canEdit: true,
        isSelfView: true,
        selectedUserId: "user-1",
      }),
    ).toBe(true);
  });
});

// ── Tests: starter budget fallback ───────────────────────────────────────────

describe("Budget suggestions: starter fallback", () => {
  it("returns starter budgets when API returns empty array", () => {
    const { suggestions, isHistoryBased } = resolveSuggestions([]);
    expect(isHistoryBased).toBe(false);
    expect(suggestions).toHaveLength(6);
    expect(suggestions).toBe(STARTER_BUDGETS);
  });

  it("returns history-based suggestions when API returns results", () => {
    const historySuggestions: BudgetSuggestion[] = [
      {
        category_name: "Groceries",
        category_id: "cat-1",
        suggested_amount: 350,
        suggested_period: "monthly",
        avg_monthly_spend: 320,
        total_spend: 1920,
        month_count: 6,
        transaction_count: 48,
      },
    ];
    const { suggestions, isHistoryBased } =
      resolveSuggestions(historySuggestions);
    expect(isHistoryBased).toBe(true);
    expect(suggestions).toBe(historySuggestions);
    expect(suggestions).toHaveLength(1);
  });

  it("starter budgets all have monthly period", () => {
    const { suggestions } = resolveSuggestions([]);
    expect(suggestions.every((s) => s.suggested_period === "monthly")).toBe(
      true,
    );
  });

  it("starter budgets all have null category_id (not mapped to custom category)", () => {
    const { suggestions } = resolveSuggestions([]);
    expect(suggestions.every((s) => s.category_id === null)).toBe(true);
  });

  it("starter budget amounts are positive and reasonable", () => {
    const { suggestions } = resolveSuggestions([]);
    expect(suggestions.every((s) => s.suggested_amount > 0)).toBe(true);
    expect(suggestions.every((s) => s.suggested_amount <= 500)).toBe(true);
  });

  it("starter budgets cover the 6 expected categories", () => {
    const { suggestions } = resolveSuggestions([]);
    const names = suggestions.map((s) => s.category_name);
    expect(names).toContain("Groceries");
    expect(names).toContain("Dining Out");
    expect(names).toContain("Gas & Transportation");
    expect(names).toContain("Entertainment");
    expect(names).toContain("Shopping");
    expect(names).toContain("Subscriptions");
  });

  it("history-based flag is false when API returns empty", () => {
    const { isHistoryBased } = resolveSuggestions([]);
    expect(isHistoryBased).toBe(false);
  });

  it("history-based flag is true when API returns any results", () => {
    const apiResult: BudgetSuggestion[] = [
      {
        category_name: "Dining",
        category_id: null,
        suggested_amount: 200,
        suggested_period: "monthly",
        avg_monthly_spend: 180,
        total_spend: 1080,
        month_count: 6,
        transaction_count: 24,
      },
    ];
    const { isHistoryBased } = resolveSuggestions(apiResult);
    expect(isHistoryBased).toBe(true);
  });
});

// ── Tests: notification preference category ───────────────────────────────────

describe("Notification preference categories", () => {
  // Mirrors NOTIFICATION_CATEGORIES in PreferencesPage.tsx
  const NOTIFICATION_CATEGORIES = [
    { key: "account_syncs" },
    { key: "account_activity" },
    { key: "budget_alerts" },
    { key: "goal_alerts" },
    { key: "milestones" },
    { key: "household" },
    { key: "weekly_recap" },
    { key: "equity_alerts" },
    { key: "crypto_alerts" },
  ];

  it("goal_alerts category exists in notification preferences", () => {
    const keys = NOTIFICATION_CATEGORIES.map((c) => c.key);
    expect(keys).toContain("goal_alerts");
  });

  it("goal_alerts appears after budget_alerts", () => {
    const keys = NOTIFICATION_CATEGORIES.map((c) => c.key);
    const budgetIdx = keys.indexOf("budget_alerts");
    const goalIdx = keys.indexOf("goal_alerts");
    expect(budgetIdx).toBeGreaterThanOrEqual(0);
    expect(goalIdx).toBe(budgetIdx + 1);
  });

  it("all preference categories are unique keys", () => {
    const keys = NOTIFICATION_CATEGORIES.map((c) => c.key);
    expect(new Set(keys).size).toBe(keys.length);
  });
});
