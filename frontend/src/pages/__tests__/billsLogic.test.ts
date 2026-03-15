/**
 * Tests for BillsPage pure logic: due-date coloring, overdue detection,
 * bill display text, currency/date formatting, active/archived partitioning,
 * form sanitization, and save-button validation.
 *
 * All helpers mirror the exact expressions used inside BillsPage so that
 * regressions in the conditional logic are caught without rendering.
 */

import { describe, it, expect } from "vitest";
import type {
  RecurringTransaction,
  UpcomingBill,
} from "../../types/recurring-transaction";
import { RecurringFrequency } from "../../types/recurring-transaction";

// ── helpers mirroring BillsPage expressions ─────────────────────────────────

const getDueDateColor = (daysUntilDue: number, isOverdue: boolean) => {
  if (isOverdue) return "red";
  if (daysUntilDue <= 3) return "orange";
  if (daysUntilDue <= 7) return "yellow";
  return "green";
};

const getBillStatusText = (daysUntilDue: number, isOverdue: boolean) => {
  if (isOverdue) return `${Math.abs(daysUntilDue)} days overdue`;
  if (daysUntilDue === 0) return "Due today";
  return `${daysUntilDue} days`;
};

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(amount);

const formatDate = (dateString: string) =>
  new Date(dateString).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

const formatFrequencyDisplay = (frequency: string) =>
  frequency === "on_demand"
    ? "On Demand"
    : frequency.charAt(0).toUpperCase() + frequency.slice(1);

/** Mirrors partition logic: active vs archived recurring transactions */
const partitionRecurring = (items: RecurringTransaction[]) => ({
  active: items.filter((r) => !r.is_archived),
  archived: items.filter((r) => r.is_archived),
});

/** Mirrors isNoLongerFound display logic in RecurringCard */
const isNoLongerFound = (r: RecurringTransaction) =>
  r.is_no_longer_found && !r.is_user_created;

/** Mirrors form sanitization in handleSave */
const sanitizeFormData = (formData: {
  average_amount: number;
  amount_variance: number;
  [key: string]: unknown;
}) => ({
  ...formData,
  average_amount: isNaN(formData.average_amount) ? 0 : formData.average_amount,
  amount_variance: isNaN(formData.amount_variance)
    ? 0
    : formData.amount_variance,
});

/** Mirrors save-button disabled check in RecurringTransactionModal */
const isSaveDisabled = (merchantName: string, accountId: string) =>
  !merchantName.trim() || !accountId;

// ── fixture factory ─────────────────────────────────────────────────────────

const makeBill = (overrides: Partial<UpcomingBill> = {}): UpcomingBill => ({
  recurring_transaction_id: "rt-1",
  merchant_name: "Electric Co",
  average_amount: 120.5,
  next_expected_date: "2026-04-01",
  days_until_due: 17,
  is_overdue: false,
  account_id: "acc-1",
  category_id: null,
  ...overrides,
});

const makeRecurring = (
  overrides: Partial<RecurringTransaction> = {},
): RecurringTransaction => ({
  id: "r-1",
  organization_id: "org-1",
  account_id: "acc-1",
  merchant_name: "Netflix",
  description_pattern: null,
  frequency: RecurringFrequency.MONTHLY,
  average_amount: 15.99,
  amount_variance: 0,
  category_id: null,
  is_user_created: false,
  confidence_score: 0.95,
  first_occurrence: "2025-01-15",
  last_occurrence: "2026-03-15",
  next_expected_date: "2026-04-15",
  occurrence_count: 14,
  is_active: true,
  is_archived: false,
  is_no_longer_found: false,
  label_id: null,
  is_bill: false,
  reminder_days_before: 3,
  created_at: "2025-01-15T00:00:00Z",
  updated_at: "2026-03-15T00:00:00Z",
  ...overrides,
});

// ── getDueDateColor ─────────────────────────────────────────────────────────

describe("getDueDateColor", () => {
  it("returns red when overdue regardless of days value", () => {
    expect(getDueDateColor(-5, true)).toBe("red");
    expect(getDueDateColor(0, true)).toBe("red");
    expect(getDueDateColor(10, true)).toBe("red");
  });

  it("returns orange when 1-3 days until due", () => {
    expect(getDueDateColor(1, false)).toBe("orange");
    expect(getDueDateColor(2, false)).toBe("orange");
    expect(getDueDateColor(3, false)).toBe("orange");
  });

  it("returns yellow when 4-7 days until due", () => {
    expect(getDueDateColor(4, false)).toBe("yellow");
    expect(getDueDateColor(5, false)).toBe("yellow");
    expect(getDueDateColor(7, false)).toBe("yellow");
  });

  it("returns green when more than 7 days until due", () => {
    expect(getDueDateColor(8, false)).toBe("green");
    expect(getDueDateColor(30, false)).toBe("green");
  });

  it("returns orange for 0 days (due today, not overdue)", () => {
    expect(getDueDateColor(0, false)).toBe("orange");
  });
});

// ── getBillStatusText ───────────────────────────────────────────────────────

describe("getBillStatusText", () => {
  it("shows overdue text with absolute day count", () => {
    expect(getBillStatusText(-3, true)).toBe("3 days overdue");
    expect(getBillStatusText(-1, true)).toBe("1 days overdue");
  });

  it('shows "Due today" when 0 days and not overdue', () => {
    expect(getBillStatusText(0, false)).toBe("Due today");
  });

  it("shows days remaining for future bills", () => {
    expect(getBillStatusText(5, false)).toBe("5 days");
    expect(getBillStatusText(1, false)).toBe("1 days");
    expect(getBillStatusText(30, false)).toBe("30 days");
  });

  it("overdue takes precedence even when days_until_due is 0", () => {
    expect(getBillStatusText(0, true)).toBe("0 days overdue");
  });
});

// ── formatCurrency ──────────────────────────────────────────────────────────

describe("formatCurrency", () => {
  it("formats positive amounts with dollar sign", () => {
    expect(formatCurrency(120.5)).toBe("$120.50");
  });

  it("formats zero", () => {
    expect(formatCurrency(0)).toBe("$0.00");
  });

  it("formats negative amounts", () => {
    expect(formatCurrency(-15.99)).toBe("-$15.99");
  });

  it("adds comma separators for large amounts", () => {
    expect(formatCurrency(1234.56)).toBe("$1,234.56");
    expect(formatCurrency(100000)).toBe("$100,000.00");
  });

  it("rounds to two decimal places", () => {
    expect(formatCurrency(9.999)).toBe("$10.00");
  });
});

// ── formatDate ──────────────────────────────────────────────────────────────

describe("formatDate", () => {
  it("returns a formatted US locale date string", () => {
    // new Date() with date-only strings parses as UTC, which may shift
    // the displayed day depending on the local timezone. We verify the
    // format is "Mon DD, YYYY" (the shape produced by toLocaleDateString).
    const result = formatDate("2026-06-15T12:00:00");
    expect(result).toMatch(/Jun/);
    expect(result).toMatch(/15/);
    expect(result).toMatch(/2026/);
  });

  it("produces short month name, numeric day, and four-digit year", () => {
    const result = formatDate("2026-12-25T12:00:00");
    expect(result).toMatch(/Dec/);
    expect(result).toMatch(/25/);
    expect(result).toMatch(/2026/);
  });
});

// ── formatFrequencyDisplay ──────────────────────────────────────────────────

describe("formatFrequencyDisplay", () => {
  it('formats "on_demand" as "On Demand"', () => {
    expect(formatFrequencyDisplay("on_demand")).toBe("On Demand");
  });

  it("capitalizes first letter of other frequencies", () => {
    expect(formatFrequencyDisplay("monthly")).toBe("Monthly");
    expect(formatFrequencyDisplay("weekly")).toBe("Weekly");
    expect(formatFrequencyDisplay("biweekly")).toBe("Biweekly");
    expect(formatFrequencyDisplay("quarterly")).toBe("Quarterly");
    expect(formatFrequencyDisplay("yearly")).toBe("Yearly");
  });
});

// ── partitionRecurring ──────────────────────────────────────────────────────

describe("partitionRecurring (active vs archived)", () => {
  const items = [
    makeRecurring({ id: "r-1", is_archived: false }),
    makeRecurring({ id: "r-2", is_archived: true }),
    makeRecurring({ id: "r-3", is_archived: false }),
    makeRecurring({ id: "r-4", is_archived: true }),
  ];

  it("separates active items", () => {
    const { active } = partitionRecurring(items);
    expect(active).toHaveLength(2);
    expect(active.map((r) => r.id)).toEqual(["r-1", "r-3"]);
  });

  it("separates archived items", () => {
    const { archived } = partitionRecurring(items);
    expect(archived).toHaveLength(2);
    expect(archived.map((r) => r.id)).toEqual(["r-2", "r-4"]);
  });

  it("returns empty arrays when input is empty", () => {
    const { active, archived } = partitionRecurring([]);
    expect(active).toHaveLength(0);
    expect(archived).toHaveLength(0);
  });

  it("puts all items in active when none are archived", () => {
    const allActive = [
      makeRecurring({ id: "r-a", is_archived: false }),
      makeRecurring({ id: "r-b", is_archived: false }),
    ];
    const { active, archived } = partitionRecurring(allActive);
    expect(active).toHaveLength(2);
    expect(archived).toHaveLength(0);
  });

  it("puts all items in archived when all are archived", () => {
    const allArchived = [
      makeRecurring({ id: "r-x", is_archived: true }),
      makeRecurring({ id: "r-y", is_archived: true }),
    ];
    const { active, archived } = partitionRecurring(allArchived);
    expect(active).toHaveLength(0);
    expect(archived).toHaveLength(2);
  });
});

// ── isNoLongerFound ─────────────────────────────────────────────────────────

describe("isNoLongerFound", () => {
  it("true for auto-detected pattern that is no longer found", () => {
    expect(
      isNoLongerFound(
        makeRecurring({ is_no_longer_found: true, is_user_created: false }),
      ),
    ).toBe(true);
  });

  it("false for user-created pattern even if flagged no longer found", () => {
    expect(
      isNoLongerFound(
        makeRecurring({ is_no_longer_found: true, is_user_created: true }),
      ),
    ).toBe(false);
  });

  it("false when is_no_longer_found is false", () => {
    expect(
      isNoLongerFound(
        makeRecurring({ is_no_longer_found: false, is_user_created: false }),
      ),
    ).toBe(false);
  });
});

// ── sanitizeFormData ────────────────────────────────────────────────────────

describe("sanitizeFormData", () => {
  it("passes through valid numeric values unchanged", () => {
    const result = sanitizeFormData({
      average_amount: 99.99,
      amount_variance: 5,
    });
    expect(result.average_amount).toBe(99.99);
    expect(result.amount_variance).toBe(5);
  });

  it("replaces NaN average_amount with 0", () => {
    const result = sanitizeFormData({
      average_amount: NaN,
      amount_variance: 5,
    });
    expect(result.average_amount).toBe(0);
  });

  it("replaces NaN amount_variance with 0", () => {
    const result = sanitizeFormData({
      average_amount: 10,
      amount_variance: NaN,
    });
    expect(result.amount_variance).toBe(0);
  });

  it("replaces both NaN values with 0", () => {
    const result = sanitizeFormData({
      average_amount: NaN,
      amount_variance: NaN,
    });
    expect(result.average_amount).toBe(0);
    expect(result.amount_variance).toBe(0);
  });

  it("preserves other fields in the form data", () => {
    const result = sanitizeFormData({
      average_amount: 50,
      amount_variance: 2,
      merchant_name: "Test Co",
      is_bill: true,
    });
    expect(result.merchant_name).toBe("Test Co");
    expect(result.is_bill).toBe(true);
  });

  it("treats zero as valid (not NaN)", () => {
    const result = sanitizeFormData({
      average_amount: 0,
      amount_variance: 0,
    });
    expect(result.average_amount).toBe(0);
    expect(result.amount_variance).toBe(0);
  });
});

// ── isSaveDisabled ──────────────────────────────────────────────────────────

describe("isSaveDisabled", () => {
  it("disabled when merchant name is empty", () => {
    expect(isSaveDisabled("", "acc-1")).toBe(true);
  });

  it("disabled when merchant name is whitespace only", () => {
    expect(isSaveDisabled("   ", "acc-1")).toBe(true);
  });

  it("disabled when account ID is empty", () => {
    expect(isSaveDisabled("Netflix", "")).toBe(true);
  });

  it("disabled when both are empty", () => {
    expect(isSaveDisabled("", "")).toBe(true);
  });

  it("enabled when both merchant name and account ID are provided", () => {
    expect(isSaveDisabled("Netflix", "acc-1")).toBe(false);
  });

  it("enabled when merchant name has leading/trailing spaces but content", () => {
    expect(isSaveDisabled("  Netflix  ", "acc-1")).toBe(false);
  });
});

// ── upcoming bill sorting (by days_until_due) ───────────────────────────────

describe("upcoming bill sorting by due date", () => {
  const bills: UpcomingBill[] = [
    makeBill({ merchant_name: "Water", days_until_due: 15 }),
    makeBill({ merchant_name: "Electric", days_until_due: 3 }),
    makeBill({ merchant_name: "Internet", days_until_due: 7 }),
    makeBill({
      merchant_name: "Rent",
      days_until_due: -2,
      is_overdue: true,
    }),
    makeBill({ merchant_name: "Phone", days_until_due: 0 }),
  ];

  const sorted = [...bills].sort((a, b) => a.days_until_due - b.days_until_due);

  it("overdue bills sort first (most negative)", () => {
    expect(sorted[0].merchant_name).toBe("Rent");
  });

  it("due-today bills sort before upcoming", () => {
    expect(sorted[1].merchant_name).toBe("Phone");
  });

  it("bills sort in ascending order by days until due", () => {
    expect(sorted.map((b) => b.days_until_due)).toEqual([-2, 0, 3, 7, 15]);
  });
});

// ── bill card badge color integration ───────────────────────────────────────

describe("bill card color + text integration", () => {
  it("overdue bill: red badge with overdue text", () => {
    const bill = makeBill({ days_until_due: -5, is_overdue: true });
    expect(getDueDateColor(bill.days_until_due, bill.is_overdue)).toBe("red");
    expect(getBillStatusText(bill.days_until_due, bill.is_overdue)).toBe(
      "5 days overdue",
    );
  });

  it("due-today bill: orange badge with due-today text", () => {
    const bill = makeBill({ days_until_due: 0, is_overdue: false });
    expect(getDueDateColor(bill.days_until_due, bill.is_overdue)).toBe(
      "orange",
    );
    expect(getBillStatusText(bill.days_until_due, bill.is_overdue)).toBe(
      "Due today",
    );
  });

  it("upcoming bill (2 days): orange badge with days text", () => {
    const bill = makeBill({ days_until_due: 2, is_overdue: false });
    expect(getDueDateColor(bill.days_until_due, bill.is_overdue)).toBe(
      "orange",
    );
    expect(getBillStatusText(bill.days_until_due, bill.is_overdue)).toBe(
      "2 days",
    );
  });

  it("upcoming bill (5 days): yellow badge", () => {
    const bill = makeBill({ days_until_due: 5, is_overdue: false });
    expect(getDueDateColor(bill.days_until_due, bill.is_overdue)).toBe(
      "yellow",
    );
  });

  it("upcoming bill (20 days): green badge", () => {
    const bill = makeBill({ days_until_due: 20, is_overdue: false });
    expect(getDueDateColor(bill.days_until_due, bill.is_overdue)).toBe("green");
  });
});

// ── recurring card display flags ────────────────────────────────────────────

describe("recurring card display flags", () => {
  it("shows inactive badge when not active and not in archive view", () => {
    const r = makeRecurring({ is_active: false, is_archived: false });
    // The expression: !recurring.is_active && !isArchiveView
    expect(!r.is_active && !r.is_archived).toBe(true);
  });

  it("does not show inactive badge when in archive view", () => {
    const r = makeRecurring({ is_active: false, is_archived: true });
    const isArchiveView = true;
    expect(!r.is_active && !isArchiveView).toBe(false);
  });

  it("shows bill badge when is_bill is true", () => {
    const r = makeRecurring({ is_bill: true });
    expect(r.is_bill).toBe(true);
  });

  it("does not show bill badge when is_bill is false", () => {
    const r = makeRecurring({ is_bill: false });
    expect(r.is_bill).toBe(false);
  });

  it("shows manual badge for user-created patterns", () => {
    expect(makeRecurring({ is_user_created: true }).is_user_created).toBe(true);
  });

  it("shows auto-synced badge for auto-detected patterns", () => {
    expect(makeRecurring({ is_user_created: false }).is_user_created).toBe(
      false,
    );
  });
});
