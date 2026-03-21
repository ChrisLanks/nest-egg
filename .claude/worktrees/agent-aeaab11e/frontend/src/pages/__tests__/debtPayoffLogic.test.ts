/**
 * Tests for Debt Payoff page logic: strategy prioritization (avalanche vs snowball),
 * payoff timeline calculations, interest savings, monthly payment allocations,
 * progress percentages, sorting, formatting, and card border styling.
 */

import { describe, it, expect } from "vitest";

// ── Types (mirrored from DebtPayoffPage.tsx) ────────────────────────────────

interface DebtAccount {
  account_id: string;
  name: string;
  balance: number;
  interest_rate: number;
  minimum_payment: number;
  account_type: string;
}

interface DebtScheduleEntry {
  name?: string;
  account_type?: string;
  starting_balance?: number;
  interest_rate?: number;
  months_to_payoff?: number;
  total_interest?: number;
  payoff_date?: string;
}

interface StrategyResult {
  strategy: string;
  total_months: number;
  total_interest: number;
  total_paid: number;
  debt_free_date: string | null;
  interest_saved_vs_current?: number;
  months_saved_vs_current?: number;
  debts: DebtScheduleEntry[];
}

interface ComparisonResult {
  snowball: StrategyResult | null;
  avalanche: StrategyResult | null;
  current_pace: StrategyResult | null;
  recommendation: string | null;
}

type StrategyKey = "snowball" | "avalanche" | "current_pace";
type SortField =
  | "name"
  | "account_type"
  | "balance"
  | "interest_rate"
  | "minimum_payment";
type SortDir = "asc" | "desc";

// ── Helper functions (mirrored from DebtPayoffPage.tsx) ─────────────────────

const REC_TO_KEY: Record<string, StrategyKey> = {
  SNOWBALL: "snowball",
  AVALANCHE: "avalanche",
  CURRENT: "current_pace",
};

const KEY_TO_REC: Record<StrategyKey, string> = {
  snowball: "SNOWBALL",
  avalanche: "AVALANCHE",
  current_pace: "CURRENT",
};

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);

const formatDate = (dateStr: string | null) => {
  if (!dateStr) return "N/A";
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    year: "numeric",
  });
};

const handleExtraPaymentValidation = (value: string): boolean =>
  /^\d*\.?\d*$/.test(value);

/** Sorting logic from sortedDebts useMemo */
const sortDebts = (
  debts: DebtAccount[],
  sortField: SortField,
  sortDir: SortDir,
): DebtAccount[] =>
  [...debts].sort((a, b) => {
    const aVal = a[sortField];
    const bVal = b[sortField];
    const cmp =
      typeof aVal === "string" && typeof bVal === "string"
        ? aVal.localeCompare(bVal)
        : (aVal as number) - (bVal as number);
    return sortDir === "asc" ? cmp : -cmp;
  });

/** Card border styling logic from getCardBorderProps */
const getCardBorderProps = (
  key: StrategyKey,
  effectiveStrategyKey: StrategyKey | null,
  recommendation: string | null,
) => {
  const isSel = effectiveStrategyKey === key;
  const isRec = recommendation === KEY_TO_REC[key];
  return {
    borderWidth: isSel || isRec ? 2 : 1,
    borderColor: isSel ? "blue.500" : isRec ? "blue.300" : "border.default",
    bg: isSel ? "bg.info" : undefined,
  };
};

/** Effective strategy key derivation */
const deriveEffectiveStrategyKey = (
  strategyUserInteracted: boolean,
  selectedStrategyKey: StrategyKey | null,
  comparison: ComparisonResult | null,
): StrategyKey | null => {
  if (strategyUserInteracted) return selectedStrategyKey;
  if (!comparison) return null;
  const recKey = comparison.recommendation
    ? REC_TO_KEY[comparison.recommendation]
    : null;
  return recKey && comparison[recKey]
    ? recKey
    : comparison.avalanche
      ? "avalanche"
      : null;
};

/** Default sort direction for a field */
const defaultSortDirForField = (field: SortField): SortDir =>
  field === "balance" ||
  field === "interest_rate" ||
  field === "minimum_payment"
    ? "desc"
    : "asc";

// ── Fixtures ────────────────────────────────────────────────────────────────

const DEBTS: DebtAccount[] = [
  {
    account_id: "cc-1",
    name: "Chase Sapphire",
    balance: 5000,
    interest_rate: 24.99,
    minimum_payment: 150,
    account_type: "credit_card",
  },
  {
    account_id: "cc-2",
    name: "Amex Gold",
    balance: 2000,
    interest_rate: 19.99,
    minimum_payment: 50,
    account_type: "credit_card",
  },
  {
    account_id: "loan-1",
    name: "Auto Loan",
    balance: 15000,
    interest_rate: 6.5,
    minimum_payment: 350,
    account_type: "auto_loan",
  },
  {
    account_id: "loan-2",
    name: "Student Loan",
    balance: 30000,
    interest_rate: 5.0,
    minimum_payment: 300,
    account_type: "student_loan",
  },
];

const SNOWBALL_RESULT: StrategyResult = {
  strategy: "SNOWBALL",
  total_months: 48,
  total_interest: 8500,
  total_paid: 60500,
  debt_free_date: "2030-03-01",
  interest_saved_vs_current: 3200,
  months_saved_vs_current: 18,
  debts: [
    {
      name: "Amex Gold",
      account_type: "credit_card",
      starting_balance: 2000,
      interest_rate: 19.99,
      months_to_payoff: 8,
      total_interest: 180,
      payoff_date: "2026-11-01",
    },
    {
      name: "Chase Sapphire",
      account_type: "credit_card",
      starting_balance: 5000,
      interest_rate: 24.99,
      months_to_payoff: 18,
      total_interest: 1200,
      payoff_date: "2027-09-01",
    },
    {
      name: "Auto Loan",
      account_type: "auto_loan",
      starting_balance: 15000,
      interest_rate: 6.5,
      months_to_payoff: 36,
      total_interest: 2100,
      payoff_date: "2029-03-01",
    },
    {
      name: "Student Loan",
      account_type: "student_loan",
      starting_balance: 30000,
      interest_rate: 5.0,
      months_to_payoff: 48,
      total_interest: 5020,
      payoff_date: "2030-03-01",
    },
  ],
};

const AVALANCHE_RESULT: StrategyResult = {
  strategy: "AVALANCHE",
  total_months: 45,
  total_interest: 7200,
  total_paid: 59200,
  debt_free_date: "2029-12-01",
  interest_saved_vs_current: 4500,
  months_saved_vs_current: 21,
  debts: [
    {
      name: "Chase Sapphire",
      account_type: "credit_card",
      starting_balance: 5000,
      interest_rate: 24.99,
      months_to_payoff: 14,
      total_interest: 850,
      payoff_date: "2027-05-01",
    },
    {
      name: "Amex Gold",
      account_type: "credit_card",
      starting_balance: 2000,
      interest_rate: 19.99,
      months_to_payoff: 20,
      total_interest: 300,
      payoff_date: "2027-11-01",
    },
    {
      name: "Auto Loan",
      account_type: "auto_loan",
      starting_balance: 15000,
      interest_rate: 6.5,
      months_to_payoff: 36,
      total_interest: 2050,
      payoff_date: "2029-03-01",
    },
    {
      name: "Student Loan",
      account_type: "student_loan",
      starting_balance: 30000,
      interest_rate: 5.0,
      months_to_payoff: 45,
      total_interest: 4000,
      payoff_date: "2029-12-01",
    },
  ],
};

const CURRENT_PACE_RESULT: StrategyResult = {
  strategy: "CURRENT",
  total_months: 66,
  total_interest: 11700,
  total_paid: 63700,
  debt_free_date: "2031-09-01",
  debts: [],
};

const COMPARISON: ComparisonResult = {
  snowball: SNOWBALL_RESULT,
  avalanche: AVALANCHE_RESULT,
  current_pace: CURRENT_PACE_RESULT,
  recommendation: "AVALANCHE",
};

// ── Tests ───────────────────────────────────────────────────────────────────

describe("formatCurrency", () => {
  it("formats typical debt amounts", () => {
    expect(formatCurrency(5000)).toBe("$5,000");
    expect(formatCurrency(15000)).toBe("$15,000");
    expect(formatCurrency(150)).toBe("$150");
  });

  it("formats zero", () => {
    expect(formatCurrency(0)).toBe("$0");
  });

  it("rounds to whole dollars", () => {
    expect(formatCurrency(1234.56)).toBe("$1,235");
    expect(formatCurrency(99.49)).toBe("$99");
  });

  it("formats large amounts with commas", () => {
    expect(formatCurrency(1000000)).toBe("$1,000,000");
  });
});

describe("formatDate", () => {
  it("formats ISO date strings to month/year", () => {
    // Use mid-month dates to avoid UTC/local timezone boundary issues
    expect(formatDate("2030-03-15")).toBe("Mar 2030");
    expect(formatDate("2029-12-15")).toBe("Dec 2029");
  });

  it('returns "N/A" for null', () => {
    expect(formatDate(null)).toBe("N/A");
  });

  it("handles first and last months of the year", () => {
    expect(formatDate("2025-01-15")).toBe("Jan 2025");
    expect(formatDate("2025-12-31")).toBe("Dec 2025");
  });
});

describe("extraPayment input validation", () => {
  it("accepts whole numbers", () => {
    expect(handleExtraPaymentValidation("500")).toBe(true);
    expect(handleExtraPaymentValidation("0")).toBe(true);
    expect(handleExtraPaymentValidation("1000")).toBe(true);
  });

  it("accepts decimal numbers", () => {
    expect(handleExtraPaymentValidation("500.50")).toBe(true);
    expect(handleExtraPaymentValidation("0.99")).toBe(true);
    expect(handleExtraPaymentValidation(".5")).toBe(true);
  });

  it("accepts empty string", () => {
    expect(handleExtraPaymentValidation("")).toBe(true);
  });

  it("rejects non-numeric input", () => {
    expect(handleExtraPaymentValidation("abc")).toBe(false);
    expect(handleExtraPaymentValidation("$500")).toBe(false);
    expect(handleExtraPaymentValidation("-100")).toBe(false);
    expect(handleExtraPaymentValidation("12.34.56")).toBe(false);
  });
});

// ── Debt Prioritization (Avalanche vs Snowball) ─────────────────────────────

describe("Snowball Strategy — smallest balance first", () => {
  it("orders debts from smallest to largest balance", () => {
    const sorted = [...DEBTS].sort((a, b) => a.balance - b.balance);
    expect(sorted[0].name).toBe("Amex Gold"); // $2,000
    expect(sorted[1].name).toBe("Chase Sapphire"); // $5,000
    expect(sorted[2].name).toBe("Auto Loan"); // $15,000
    expect(sorted[3].name).toBe("Student Loan"); // $30,000
  });

  it("snowball payoff order matches smallest-first", () => {
    const names = SNOWBALL_RESULT.debts.map((d) => d.name);
    expect(names).toEqual([
      "Amex Gold",
      "Chase Sapphire",
      "Auto Loan",
      "Student Loan",
    ]);
  });
});

describe("Avalanche Strategy — highest interest first", () => {
  it("orders debts from highest to lowest interest rate", () => {
    const sorted = [...DEBTS].sort((a, b) => b.interest_rate - a.interest_rate);
    expect(sorted[0].name).toBe("Chase Sapphire"); // 24.99%
    expect(sorted[1].name).toBe("Amex Gold"); // 19.99%
    expect(sorted[2].name).toBe("Auto Loan"); // 6.5%
    expect(sorted[3].name).toBe("Student Loan"); // 5.0%
  });

  it("avalanche payoff order matches highest-interest-first", () => {
    const names = AVALANCHE_RESULT.debts.map((d) => d.name);
    expect(names).toEqual([
      "Chase Sapphire",
      "Amex Gold",
      "Auto Loan",
      "Student Loan",
    ]);
  });
});

// ── Interest Savings Comparison ─────────────────────────────────────────────

describe("Interest Savings vs Current Pace", () => {
  it("avalanche saves more interest than snowball", () => {
    expect(AVALANCHE_RESULT.interest_saved_vs_current!).toBeGreaterThan(
      SNOWBALL_RESULT.interest_saved_vs_current!,
    );
  });

  it("avalanche pays less total interest than snowball", () => {
    expect(AVALANCHE_RESULT.total_interest).toBeLessThan(
      SNOWBALL_RESULT.total_interest,
    );
  });

  it("both strategies save interest vs current pace", () => {
    expect(SNOWBALL_RESULT.total_interest).toBeLessThan(
      CURRENT_PACE_RESULT.total_interest,
    );
    expect(AVALANCHE_RESULT.total_interest).toBeLessThan(
      CURRENT_PACE_RESULT.total_interest,
    );
  });

  it("interest saved + strategy interest = current pace interest", () => {
    // Avalanche: 7200 + 4500 = 11700
    expect(
      AVALANCHE_RESULT.total_interest +
        AVALANCHE_RESULT.interest_saved_vs_current!,
    ).toBe(CURRENT_PACE_RESULT.total_interest);

    // Snowball: 8500 + 3200 = 11700
    expect(
      SNOWBALL_RESULT.total_interest +
        SNOWBALL_RESULT.interest_saved_vs_current!,
    ).toBe(CURRENT_PACE_RESULT.total_interest);
  });
});

// ── Payoff Timeline Calculations ────────────────────────────────────────────

describe("Payoff Timeline", () => {
  it("avalanche finishes faster than snowball", () => {
    expect(AVALANCHE_RESULT.total_months).toBeLessThan(
      SNOWBALL_RESULT.total_months,
    );
  });

  it("both strategies finish faster than current pace", () => {
    expect(SNOWBALL_RESULT.total_months).toBeLessThan(
      CURRENT_PACE_RESULT.total_months,
    );
    expect(AVALANCHE_RESULT.total_months).toBeLessThan(
      CURRENT_PACE_RESULT.total_months,
    );
  });

  it("months saved is correct vs current pace", () => {
    expect(
      CURRENT_PACE_RESULT.total_months - SNOWBALL_RESULT.total_months,
    ).toBe(SNOWBALL_RESULT.months_saved_vs_current);
    expect(
      CURRENT_PACE_RESULT.total_months - AVALANCHE_RESULT.total_months,
    ).toBe(AVALANCHE_RESULT.months_saved_vs_current);
  });

  it("current pace has no months_saved_vs_current (baseline)", () => {
    expect(CURRENT_PACE_RESULT.months_saved_vs_current).toBeUndefined();
  });
});

// ── Monthly Payment Allocations ─────────────────────────────────────────────

describe("Monthly Payment Allocations", () => {
  it("total minimum payments sum correctly", () => {
    const totalMin = DEBTS.reduce((sum, d) => sum + d.minimum_payment, 0);
    expect(totalMin).toBe(850); // 150 + 50 + 350 + 300
  });

  it("total paid = principal + interest", () => {
    const totalPrincipal = DEBTS.reduce((sum, d) => sum + d.balance, 0);
    expect(SNOWBALL_RESULT.total_paid).toBe(
      totalPrincipal + SNOWBALL_RESULT.total_interest,
    );
    expect(AVALANCHE_RESULT.total_paid).toBe(
      totalPrincipal + AVALANCHE_RESULT.total_interest,
    );
  });

  it("each debt has a non-negative payoff duration", () => {
    for (const debt of SNOWBALL_RESULT.debts) {
      expect(debt.months_to_payoff).toBeGreaterThan(0);
    }
    for (const debt of AVALANCHE_RESULT.debts) {
      expect(debt.months_to_payoff).toBeGreaterThan(0);
    }
  });
});

// ── Strategy Key Mapping ────────────────────────────────────────────────────

describe("Strategy Key Mapping", () => {
  it("REC_TO_KEY maps recommendation strings to keys", () => {
    expect(REC_TO_KEY["SNOWBALL"]).toBe("snowball");
    expect(REC_TO_KEY["AVALANCHE"]).toBe("avalanche");
    expect(REC_TO_KEY["CURRENT"]).toBe("current_pace");
  });

  it("KEY_TO_REC is the reverse mapping", () => {
    expect(KEY_TO_REC["snowball"]).toBe("SNOWBALL");
    expect(KEY_TO_REC["avalanche"]).toBe("AVALANCHE");
    expect(KEY_TO_REC["current_pace"]).toBe("CURRENT");
  });

  it("round-trips correctly", () => {
    for (const key of [
      "snowball",
      "avalanche",
      "current_pace",
    ] as StrategyKey[]) {
      expect(REC_TO_KEY[KEY_TO_REC[key]]).toBe(key);
    }
  });
});

// ── Effective Strategy Key Derivation ───────────────────────────────────────

describe("deriveEffectiveStrategyKey", () => {
  it("returns user selection when user has interacted", () => {
    expect(deriveEffectiveStrategyKey(true, "snowball", COMPARISON)).toBe(
      "snowball",
    );
  });

  it("returns null when user interacted and deselected", () => {
    expect(deriveEffectiveStrategyKey(true, null, COMPARISON)).toBeNull();
  });

  it("returns null when no comparison data and no interaction", () => {
    expect(deriveEffectiveStrategyKey(false, null, null)).toBeNull();
  });

  it("auto-selects recommendation when user has not interacted", () => {
    expect(deriveEffectiveStrategyKey(false, null, COMPARISON)).toBe(
      "avalanche",
    );
  });

  it("falls back to avalanche when recommendation is missing but avalanche exists", () => {
    const comp: ComparisonResult = {
      ...COMPARISON,
      recommendation: null,
    };
    expect(deriveEffectiveStrategyKey(false, null, comp)).toBe("avalanche");
  });

  it("returns null when no recommendation and no avalanche data", () => {
    const comp: ComparisonResult = {
      snowball: SNOWBALL_RESULT,
      avalanche: null,
      current_pace: CURRENT_PACE_RESULT,
      recommendation: null,
    };
    expect(deriveEffectiveStrategyKey(false, null, comp)).toBeNull();
  });

  it("auto-selects snowball when that is the recommendation", () => {
    const comp: ComparisonResult = {
      ...COMPARISON,
      recommendation: "SNOWBALL",
    };
    expect(deriveEffectiveStrategyKey(false, null, comp)).toBe("snowball");
  });
});

// ── Card Border Styling ─────────────────────────────────────────────────────

describe("getCardBorderProps", () => {
  it("selected card gets blue.500 border and bg.info", () => {
    const props = getCardBorderProps("avalanche", "avalanche", "AVALANCHE");
    expect(props.borderWidth).toBe(2);
    expect(props.borderColor).toBe("blue.500");
    expect(props.bg).toBe("bg.info");
  });

  it("recommended but unselected card gets blue.300 border", () => {
    const props = getCardBorderProps("avalanche", "snowball", "AVALANCHE");
    expect(props.borderWidth).toBe(2);
    expect(props.borderColor).toBe("blue.300");
    expect(props.bg).toBeUndefined();
  });

  it("neither selected nor recommended card gets default border", () => {
    const props = getCardBorderProps("current_pace", "avalanche", "AVALANCHE");
    expect(props.borderWidth).toBe(1);
    expect(props.borderColor).toBe("border.default");
    expect(props.bg).toBeUndefined();
  });

  it("no strategy selected, recommended card still highlighted", () => {
    const props = getCardBorderProps("avalanche", null, "AVALANCHE");
    expect(props.borderWidth).toBe(2);
    expect(props.borderColor).toBe("blue.300");
  });
});

// ── Debt Sorting ────────────────────────────────────────────────────────────

describe("Debt Sorting", () => {
  it("sorts by balance descending (default)", () => {
    const sorted = sortDebts(DEBTS, "balance", "desc");
    expect(sorted[0].name).toBe("Student Loan"); // 30000
    expect(sorted[1].name).toBe("Auto Loan"); // 15000
    expect(sorted[2].name).toBe("Chase Sapphire"); // 5000
    expect(sorted[3].name).toBe("Amex Gold"); // 2000
  });

  it("sorts by balance ascending", () => {
    const sorted = sortDebts(DEBTS, "balance", "asc");
    expect(sorted[0].name).toBe("Amex Gold"); // 2000
    expect(sorted[3].name).toBe("Student Loan"); // 30000
  });

  it("sorts by interest_rate descending", () => {
    const sorted = sortDebts(DEBTS, "interest_rate", "desc");
    expect(sorted[0].name).toBe("Chase Sapphire"); // 24.99
    expect(sorted[1].name).toBe("Amex Gold"); // 19.99
  });

  it("sorts by name ascending (alphabetical)", () => {
    const sorted = sortDebts(DEBTS, "name", "asc");
    expect(sorted[0].name).toBe("Amex Gold");
    expect(sorted[1].name).toBe("Auto Loan");
    expect(sorted[2].name).toBe("Chase Sapphire");
    expect(sorted[3].name).toBe("Student Loan");
  });

  it("sorts by name descending (reverse alphabetical)", () => {
    const sorted = sortDebts(DEBTS, "name", "desc");
    expect(sorted[0].name).toBe("Student Loan");
    expect(sorted[3].name).toBe("Amex Gold");
  });

  it("sorts by minimum_payment descending", () => {
    const sorted = sortDebts(DEBTS, "minimum_payment", "desc");
    expect(sorted[0].name).toBe("Auto Loan"); // 350
    expect(sorted[1].name).toBe("Student Loan"); // 300
  });

  it("does not mutate original array", () => {
    const original = [...DEBTS];
    sortDebts(DEBTS, "balance", "asc");
    expect(DEBTS).toEqual(original);
  });
});

describe("Default Sort Direction", () => {
  it("numeric fields default to descending", () => {
    expect(defaultSortDirForField("balance")).toBe("desc");
    expect(defaultSortDirForField("interest_rate")).toBe("desc");
    expect(defaultSortDirForField("minimum_payment")).toBe("desc");
  });

  it("text fields default to ascending", () => {
    expect(defaultSortDirForField("name")).toBe("asc");
    expect(defaultSortDirForField("account_type")).toBe("asc");
  });
});

// ── Account Selection Logic ─────────────────────────────────────────────────

describe("Account Selection Logic", () => {
  it("effectiveSelectedAccounts defaults to all accounts when nothing selected", () => {
    const selectedAccounts = new Set<string>();
    const allIds = DEBTS.map((d) => d.account_id);
    const effective =
      selectedAccounts.size > 0 ? selectedAccounts : new Set(allIds);
    expect(effective.size).toBe(4);
    for (const debt of DEBTS) {
      expect(effective.has(debt.account_id)).toBe(true);
    }
  });

  it("uses explicit selection when accounts are selected", () => {
    const selectedAccounts = new Set(["cc-1", "loan-1"]);
    const allIds = DEBTS.map((d) => d.account_id);
    const effective =
      selectedAccounts.size > 0 ? selectedAccounts : new Set(allIds);
    expect(effective.size).toBe(2);
    expect(effective.has("cc-1")).toBe(true);
    expect(effective.has("loan-1")).toBe(true);
    expect(effective.has("cc-2")).toBe(false);
  });

  it("toggle adds account when not present", () => {
    const effective = new Set(["cc-1", "loan-1"]);
    const accountId = "cc-2";
    if (effective.has(accountId)) {
      effective.delete(accountId);
    } else {
      effective.add(accountId);
    }
    expect(effective.has("cc-2")).toBe(true);
    expect(effective.size).toBe(3);
  });

  it("toggle removes account when already present", () => {
    const effective = new Set(["cc-1", "cc-2", "loan-1"]);
    const accountId = "cc-2";
    if (effective.has(accountId)) {
      effective.delete(accountId);
    } else {
      effective.add(accountId);
    }
    expect(effective.has("cc-2")).toBe(false);
    expect(effective.size).toBe(2);
  });
});

// ── Query Enablement Guard ──────────────────────────────────────────────────

describe("Comparison Query Enablement", () => {
  it("is enabled when debts exist and accounts are selected", () => {
    const debts = DEBTS;
    const effectiveSelected = new Set(DEBTS.map((d) => d.account_id));
    const enabled = !!debts && debts.length > 0 && effectiveSelected.size > 0;
    expect(enabled).toBe(true);
  });

  it("is disabled when no debts exist", () => {
    const debts: DebtAccount[] = [];
    const effectiveSelected = new Set<string>();
    const enabled = !!debts && debts.length > 0 && effectiveSelected.size > 0;
    expect(enabled).toBe(false);
  });

  it("is disabled when debts is undefined", () => {
    const debts: DebtAccount[] | undefined = undefined;
    const effectiveSelected = new Set(["cc-1"]);
    const enabled = !!debts && debts.length > 0 && effectiveSelected.size > 0;
    expect(enabled).toBe(false);
  });

  it("is disabled when no accounts selected", () => {
    const debts = DEBTS;
    const effectiveSelected = new Set<string>();
    const enabled = !!debts && debts.length > 0 && effectiveSelected.size > 0;
    expect(enabled).toBe(false);
  });
});

// ── Strategy Toggle (click handler) ─────────────────────────────────────────

describe("Strategy Toggle Behavior", () => {
  it("clicking a non-selected strategy selects it", () => {
    const effectiveKey: StrategyKey | null = "avalanche";
    const clickedKey: StrategyKey = "snowball";
    const newKey = effectiveKey === clickedKey ? null : clickedKey;
    expect(newKey).toBe("snowball");
  });

  it("clicking the already-selected strategy deselects it", () => {
    const effectiveKey: StrategyKey | null = "snowball";
    const clickedKey: StrategyKey = "snowball";
    const newKey = effectiveKey === clickedKey ? null : clickedKey;
    expect(newKey).toBeNull();
  });

  it("clicking when nothing is selected, selects the clicked strategy", () => {
    const effectiveKey: StrategyKey | null = null;
    const clickedKey: StrategyKey = "current_pace";
    const newKey = effectiveKey === clickedKey ? null : clickedKey;
    expect(newKey).toBe("current_pace");
  });
});

// ── Boundary: Empty / Single Debt ───────────────────────────────────────────

describe("Edge Cases", () => {
  it("sorting an empty debt array returns empty", () => {
    expect(sortDebts([], "balance", "desc")).toEqual([]);
  });

  it("sorting a single debt returns the same debt", () => {
    const single = [DEBTS[0]];
    const sorted = sortDebts(single, "balance", "desc");
    expect(sorted).toHaveLength(1);
    expect(sorted[0].name).toBe("Chase Sapphire");
  });

  it("formatCurrency handles negative amounts (overpayment)", () => {
    const result = formatCurrency(-500);
    expect(result).toBe("-$500");
  });

  it("debts with zero balance are valid", () => {
    const zeroed: DebtAccount = {
      ...DEBTS[0],
      balance: 0,
    };
    const sorted = sortDebts([zeroed, DEBTS[1]], "balance", "asc");
    expect(sorted[0].balance).toBe(0);
  });

  it("debts with zero interest rate sort correctly", () => {
    const noInterest: DebtAccount = {
      ...DEBTS[0],
      interest_rate: 0,
    };
    const sorted = sortDebts([noInterest, DEBTS[1]], "interest_rate", "desc");
    expect(sorted[0].interest_rate).toBe(19.99);
    expect(sorted[1].interest_rate).toBe(0);
  });
});
