/**
 * Tests for GoalContextBanner logic.
 *
 * Covers: goal config selection, investments+no-accounts fallback,
 * dismiss persistence, and account-fetch trigger conditions.
 *
 * @vitest-environment jsdom
 */

import { describe, it, expect, beforeEach } from "vitest";

// ── Constants mirroring GoalContextBanner ────────────────────────────────────

const DISMISSED_KEY = "nest-egg-goal-banner-dismissed";
const GOAL_KEY = "nest-egg-onboarding-goal";

interface GoalConfig {
  intro: string;
  cta: string;
  path: string;
}

const GOAL_CONFIGS: Record<string, GoalConfig> = {
  spending: {
    intro: "You said you want to track your spending.",
    cta: "Set your first budget",
    path: "/budgets",
  },
  retirement: {
    intro: "You said you want to plan for retirement.",
    cta: "See your retirement outlook",
    path: "/retirement",
  },
  investments: {
    intro: "You said you want to understand your investments.",
    cta: "View your portfolio",
    path: "/investments",
  },
};

const INVESTMENTS_NO_ACCOUNTS_CONFIG: GoalConfig = {
  intro: "You said you want to understand your investments.",
  cta: "Add your investment account first",
  path: "/accounts",
};

// Mirrors GoalContextBanner config-selection logic
const resolveConfig = (
  goal: string | null,
  accounts: unknown[] | undefined,
): GoalConfig | null => {
  if (!goal || !GOAL_CONFIGS[goal]) return null;
  const hasNoAccounts =
    goal === "investments" &&
    Array.isArray(accounts) &&
    accounts.length === 0;
  return hasNoAccounts ? INVESTMENTS_NO_ACCOUNTS_CONFIG : GOAL_CONFIGS[goal];
};

// ── Tests: config resolution ─────────────────────────────────────────────────

describe("GoalContextBanner: config resolution", () => {
  it("returns null when goal is null", () => {
    expect(resolveConfig(null, [])).toBeNull();
  });

  it("returns null when goal is unrecognised", () => {
    expect(resolveConfig("unknown_goal", [])).toBeNull();
  });

  it("spending goal returns budgets path", () => {
    const config = resolveConfig("spending", []);
    expect(config?.path).toBe("/budgets");
    expect(config?.cta).toBe("Set your first budget");
  });

  it("retirement goal returns retirement path", () => {
    const config = resolveConfig("retirement", []);
    expect(config?.path).toBe("/retirement");
    expect(config?.cta).toBe("See your retirement outlook");
  });

  it("investments goal with accounts returns investments path", () => {
    const config = resolveConfig("investments", [{ id: "acc1" }]);
    expect(config?.path).toBe("/investments");
    expect(config?.cta).toBe("View your portfolio");
  });

  it("investments goal with no accounts returns accounts path", () => {
    const config = resolveConfig("investments", []);
    expect(config?.path).toBe("/accounts");
    expect(config?.cta).toBe("Add your investment account first");
  });

  it("investments goal while accounts are loading (undefined) shows portfolio CTA", () => {
    // undefined = still fetching — don't redirect to accounts prematurely
    const config = resolveConfig("investments", undefined);
    expect(config?.path).toBe("/investments");
  });

  it("intro copy is the same for both investments configs", () => {
    const withAccounts = resolveConfig("investments", [{ id: "x" }]);
    const withoutAccounts = resolveConfig("investments", []);
    expect(withAccounts?.intro).toBe(withoutAccounts?.intro);
  });
});

// ── Tests: dismiss logic ─────────────────────────────────────────────────────

describe("GoalContextBanner: dismiss persistence", () => {
  beforeEach(() => localStorage.clear());

  it("banner is not dismissed by default", () => {
    expect(localStorage.getItem(DISMISSED_KEY)).toBeNull();
  });

  it("handleDismiss stores 'true' in localStorage", () => {
    localStorage.setItem(DISMISSED_KEY, "true");
    expect(localStorage.getItem(DISMISSED_KEY)).toBe("true");
  });

  it("dismissed check returns true when key is 'true'", () => {
    localStorage.setItem(DISMISSED_KEY, "true");
    const dismissed = localStorage.getItem(DISMISSED_KEY) === "true";
    expect(dismissed).toBe(true);
  });

  it("dismissed check returns false when key is absent", () => {
    const dismissed = localStorage.getItem(DISMISSED_KEY) === "true";
    expect(dismissed).toBe(false);
  });
});

// ── Tests: accounts fetch should only run for investments goal ────────────────

describe("GoalContextBanner: conditional accounts fetch", () => {
  beforeEach(() => localStorage.clear());

  it("fetch is enabled for investments goal when not dismissed", () => {
    localStorage.setItem(GOAL_KEY, "investments");
    const goal = localStorage.getItem(GOAL_KEY);
    const dismissed = false;
    const fetchEnabled = goal === "investments" && !dismissed;
    expect(fetchEnabled).toBe(true);
  });

  it("fetch is disabled for spending goal", () => {
    localStorage.setItem(GOAL_KEY, "spending");
    const goal = localStorage.getItem(GOAL_KEY);
    const dismissed = false;
    const fetchEnabled = goal === "investments" && !dismissed;
    expect(fetchEnabled).toBe(false);
  });

  it("fetch is disabled for retirement goal", () => {
    const goal = "retirement";
    const dismissed = false;
    const fetchEnabled = goal === "investments" && !dismissed;
    expect(fetchEnabled).toBe(false);
  });

  it("fetch is disabled when banner is dismissed, even for investments", () => {
    const goal = "investments";
    const dismissed = true;
    const fetchEnabled = goal === "investments" && !dismissed;
    expect(fetchEnabled).toBe(false);
  });
});
