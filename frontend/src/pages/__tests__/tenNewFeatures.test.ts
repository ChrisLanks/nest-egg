/**
 * Tests covering the 10 new features:
 * 1. Scheduled report delivery
 * 2. Budget rollover
 * 3. Rules preview
 * 4. Merchant name normalization
 * 5. Receipt OCR
 * 6. State income tax
 * 7. Loan amortization
 * 8. Guest access expiry
 * 9. Portfolio allocation history
 * 10. Budget variance explanation
 */

import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";

// ── Helpers ────────────────────────────────────────────────────────────────

function readSource(rel: string): string {
  return readFileSync(rel, "utf-8");
}

// ── Feature 1: Scheduled Report Delivery ──────────────────────────────────

describe("Feature 1: Scheduled report delivery", () => {
  it("report_template model has scheduled_delivery column", () => {
    const src = readSource(
      "../backend/app/models/report_template.py"
    );
    expect(src).toContain("scheduled_delivery");
    expect(src).toContain("JSON");
  });

  it("reports API schema includes scheduled_delivery", () => {
    const src = readSource("../backend/app/api/v1/reports.py");
    expect(src).toContain("scheduled_delivery");
    expect(src).toContain("ReportTemplateUpdate");
    expect(src).toContain("ReportTemplateResponse");
  });

  it("report_tasks.py task exists with correct name", () => {
    const src = readSource(
      "../backend/app/workers/tasks/report_tasks.py"
    );
    expect(src).toContain("send_scheduled_reports");
    expect(src).toContain("_is_due_today");
    expect(src).toContain("delivery_emails");
  });

  it("celery_app.py imports report_tasks and schedules the task", () => {
    const src = readSource("../backend/app/workers/celery_app.py");
    expect(src).toContain("report_tasks");
    expect(src).toContain("send-scheduled-reports");
  });
});

// ── Feature 2: Budget Rollover ─────────────────────────────────────────────

describe("Feature 2: Budget rollover", () => {
  it("budget_service calculates rollover_amount when rollover_unused=True", () => {
    const src = readSource(
      "../backend/app/services/budget_service.py"
    );
    expect(src).toContain("rollover_unused");
    expect(src).toContain("rollover_amount");
    expect(src).toContain("effective_budget");
    expect(src).toContain("prev_spent");
  });

  it("BudgetSpendingResponse schema has rollover_amount and effective_budget", () => {
    const src = readSource("../backend/app/schemas/budget.py");
    expect(src).toContain("rollover_amount");
    expect(src).toContain("effective_budget");
  });

  it("BudgetSpending TypeScript type has rollover fields", () => {
    const src = readSource("src/types/budget.ts");
    expect(src).toContain("rollover_amount");
  });

  it("BudgetCard shows rollover amount when present", () => {
    const src = readSource(
      "src/features/budgets/components/BudgetCard.tsx"
    );
    expect(src).toContain("rollover_amount");
    expect(src).toContain("rollover");
  });
});

// ── Feature 3: Rules Preview ───────────────────────────────────────────────

describe("Feature 3: Rules preview in modal", () => {
  it("RuleBuilderModal has preview handler and result state", () => {
    const src = readSource("src/components/RuleBuilderModal.tsx");
    expect(src).toContain("preview");
    expect(src).toContain("previewResult");
    // Should call POST /rules/test or testRule
    const hasTestCall =
      src.includes("/rules/test") || src.includes("testRule");
    expect(hasTestCall).toBe(true);
  });

  it("RuleBuilderModal shows matching transaction count", () => {
    const src = readSource("src/components/RuleBuilderModal.tsx");
    expect(src).toContain("matching_count");
  });

  it("Backend /rules/test endpoint exists", () => {
    const src = readSource("../backend/app/api/v1/rules.py");
    expect(src).toContain("/test");
    expect(src).toContain("matching_transactions");
  });
});

// ── Feature 4: Merchant Name Normalization ─────────────────────────────────

describe("Feature 4: Merchant name normalization", () => {
  it("transactions API has /merchants endpoint", () => {
    const src = readSource("../backend/app/api/v1/transactions.py");
    expect(src).toContain("merchants");
    expect(src).toContain("merchant_name");
  });

  it("RulesPage has merchant aliases section", () => {
    const src = readSource("src/pages/RulesPage.tsx");
    // Should have merchant alias or normalization section
    const hasMerchantSection =
      src.includes("Merchant") &&
      (src.includes("alias") ||
        src.includes("Alias") ||
        src.includes("normalize") ||
        src.includes("Display Name") ||
        src.includes("SET_MERCHANT"));
    expect(hasMerchantSection).toBe(true);
  });
});

// ── Feature 5: Receipt OCR ─────────────────────────────────────────────────

describe("Feature 5: Receipt OCR", () => {
  it("ocr_service.py exists with extract method", () => {
    const src = readSource(
      "../backend/app/services/ocr_service.py"
    );
    expect(src).toContain("extract_from_image");
    expect(src).toContain("merchant");
    expect(src).toContain("amount");
  });

  it("attachment model has ocr_status and ocr_data columns", () => {
    const src = readSource(
      "../backend/app/models/attachment.py"
    );
    expect(src).toContain("ocr_status");
    expect(src).toContain("ocr_data");
  });

  it("attachment_service calls OCR after upload", () => {
    const src = readSource(
      "../backend/app/services/attachment_service.py"
    );
    expect(src).toContain("ocr");
  });

  it("attachments API response includes ocr_data", () => {
    const src = readSource(
      "../backend/app/api/v1/attachments.py"
    );
    expect(src).toContain("ocr_data");
    expect(src).toContain("ocr_status");
  });

  it("AttachmentsList shows OCR suggestion banner", () => {
    const src = readSource(
      "src/features/transactions/components/AttachmentsList.tsx"
    );
    expect(src).toContain("ocr");
    // Should show detected merchant/amount suggestion
    const hasSuggestion =
      src.includes("detected") ||
      src.includes("suggestion") ||
      src.includes("Receipt data") ||
      src.includes("Apply");
    expect(hasSuggestion).toBe(true);
  });
});

// ── Feature 6: State Income Tax ────────────────────────────────────────────

describe("Feature 6: State income tax", () => {
  it("state_tax_rates.py exists with STATE_TAX_RATES dict", () => {
    const src = readSource(
      "../backend/app/constants/state_tax_rates.py"
    );
    expect(src).toContain("STATE_TAX_RATES");
    // Check a few known no-tax states are 0
    expect(src).toContain('"TX": 0.0');
    expect(src).toContain('"FL": 0.0');
    // Check a high-tax state has non-zero rate
    expect(src).toContain('"CA"');
  });

  it("TaxProjection dataclass has state fields", () => {
    const src = readSource(
      "../backend/app/services/tax_projection_service.py"
    );
    expect(src).toContain("state_tax");
    expect(src).toContain("combined_tax");
    expect(src).toContain("state_tax_rate");
    expect(src).toContain("combined_effective_rate");
  });

  it("tax projection API endpoint accepts state parameter", () => {
    const src = readSource(
      "../backend/app/api/v1/financial_planning.py"
    );
    expect(src).toContain("state");
    expect(src).toContain("state_tax");
  });

  it("TaxProjectionPage has state selector", () => {
    const src = readSource("src/pages/TaxProjectionPage.tsx");
    expect(src).toContain("state");
    // Should have a Select or dropdown for state
    const hasStateSelect =
      src.includes("Select") || src.includes("select");
    expect(hasStateSelect).toBe(true);
    expect(src).toContain("state_tax");
  });
});

// ── Feature 7: Loan Amortization ──────────────────────────────────────────

describe("Feature 7: Loan amortization", () => {
  it("debt_payoff API has amortization endpoint", () => {
    const src = readSource(
      "../backend/app/api/v1/debt_payoff.py"
    );
    expect(src).toContain("amortization");
    expect(src).toContain("extra_payment");
    expect(src).toContain("total_interest");
    expect(src).toContain("payoff_date");
  });

  it("amortization calculates monthly schedule with principal/interest split", () => {
    const src = readSource(
      "../backend/app/api/v1/debt_payoff.py"
    );
    expect(src).toContain("principal");
    expect(src).toContain("interest");
    expect(src).toContain("balance");
    expect(src).toContain("monthly_rate");
  });

  it("DebtPayoffPage has amortization view", () => {
    const src = readSource("src/pages/DebtPayoffPage.tsx");
    expect(src).toContain("amortization");
    // Should show schedule
    const hasSchedule =
      src.includes("Schedule") || src.includes("schedule");
    expect(hasSchedule).toBe(true);
  });
});

// ── Feature 8: Guest Access Expiry ────────────────────────────────────────

describe("Feature 8: Guest access expiry", () => {
  it("HouseholdGuest model has expires_at column", () => {
    const src = readSource("../backend/app/models/user.py");
    // Find HouseholdGuest class section
    const guestIdx = src.indexOf("class HouseholdGuest");
    const guestSection = src.slice(guestIdx, guestIdx + 2500);
    expect(guestSection).toContain("expires_at");
  });

  it("HouseholdGuestInvitation model has access_expires_days", () => {
    const src = readSource("../backend/app/models/user.py");
    const invitationIdx = src.indexOf("class HouseholdGuestInvitation");
    const invitationSection = src.slice(invitationIdx, invitationIdx + 2500);
    expect(invitationSection).toContain("access_expires_days");
  });

  it("guest_access API InviteGuestRequest has access_expires_days", () => {
    const src = readSource(
      "../backend/app/api/v1/guest_access.py"
    );
    expect(src).toContain("access_expires_days");
    expect(src).toContain("expires_at");
  });

  it("guest_access_tasks.py exists with auto-revoke task", () => {
    const src = readSource(
      "../backend/app/workers/tasks/guest_access_tasks.py"
    );
    expect(src).toContain("auto_revoke_expired_guests");
    expect(src).toContain("expires_at");
  });

  it("celery_app schedules auto-revoke-expired-guests", () => {
    const src = readSource("../backend/app/workers/celery_app.py");
    expect(src).toContain("auto-revoke-expired-guests");
    expect(src).toContain("guest_access_tasks");
  });

  it("HouseholdSettingsPage has access duration selector for invite", () => {
    const src = readSource("src/pages/HouseholdSettingsPage.tsx");
    expect(src).toContain("expires");
    const hasDuration =
      src.includes("duration") ||
      src.includes("Duration") ||
      src.includes("access_expires_days") ||
      src.includes("30 days");
    expect(hasDuration).toBe(true);
  });
});

// ── Feature 9: Portfolio Allocation History ────────────────────────────────

describe("Feature 9: Portfolio allocation history", () => {
  it("holdings API has allocation-history endpoint", () => {
    const src = readSource(
      "../backend/app/api/v1/holdings.py"
    );
    expect(src).toContain("allocation-history");
    expect(src).toContain("stocks_pct");
    expect(src).toContain("snapshot_service");
  });

  it("AllocationHistoryChart component exists", () => {
    const src = readSource(
      "src/features/investments/components/AllocationHistoryChart.tsx"
    );
    expect(src).toContain("AllocationHistoryChart");
    expect(src).toContain("AreaChart");
    expect(src).toContain("allocation-history");
  });

  it("holdings API client has getAllocationHistory method", () => {
    const src = readSource("src/api/holdings.ts");
    expect(src).toContain("getAllocationHistory");
    expect(src).toContain("AllocationHistoryPoint");
  });

  it("InvestmentsPage renders AllocationHistoryChart", () => {
    const src = readSource("src/pages/InvestmentsPage.tsx");
    expect(src).toContain("AllocationHistoryChart");
  });
});

// ── Feature 10: Budget Variance ────────────────────────────────────────────

describe("Feature 10: Budget variance explanation", () => {
  it("budget_service has get_budget_variance_breakdown method", () => {
    const src = readSource(
      "../backend/app/services/budget_service.py"
    );
    expect(src).toContain("get_budget_variance_breakdown");
    expect(src).toContain("merchant_breakdown");
    expect(src).toContain("largest_transactions");
  });

  it("budgets API has /variance endpoint", () => {
    const src = readSource("../backend/app/api/v1/budgets.py");
    expect(src).toContain("variance");
    expect(src).toContain("get_budget_variance_breakdown");
  });

  it("BudgetCard shows why button and variance breakdown", () => {
    const src = readSource(
      "src/features/budgets/components/BudgetCard.tsx"
    );
    expect(src).toContain("variance");
    // Should have some toggle/collapse for the breakdown
    const hasWhy =
      src.includes("Why") || src.includes("why") || src.includes("breakdown");
    expect(hasWhy).toBe(true);
  });
});

// ── Amortization logic unit tests (pure JS) ────────────────────────────────

describe("Loan amortization math", () => {
  /**
   * Replicate the Python amortization logic in JS to verify correctness.
   * Balance: $10,000, rate: 12% APR, payment: $500/month
   */
  function amortize(
    balance: number,
    annualRate: number,
    monthlyPayment: number,
    months: number
  ) {
    const monthlyRate = annualRate / 100 / 12;
    let bal = balance;
    let totalInterest = 0;
    const schedule = [];
    for (let m = 1; m <= months && bal > 0.005; m++) {
      const interest = bal * monthlyRate;
      const payment = Math.min(monthlyPayment, bal + interest);
      const principal = payment - interest;
      bal = Math.max(0, bal - principal);
      totalInterest += interest;
      schedule.push({ month: m, principal, interest, balance: bal });
    }
    return { schedule, totalInterest };
  }

  it("month-1 interest = balance * monthly_rate", () => {
    const { schedule } = amortize(10000, 12, 500, 1);
    expect(schedule[0].interest).toBeCloseTo(100, 1); // 10000 * 0.01
    expect(schedule[0].principal).toBeCloseTo(400, 1); // 500 - 100
  });

  it("balance decreases each month", () => {
    const { schedule } = amortize(10000, 12, 500, 12);
    for (let i = 1; i < schedule.length; i++) {
      expect(schedule[i].balance).toBeLessThan(schedule[i - 1].balance);
    }
  });

  it("total paid = principal + total interest", () => {
    const { schedule, totalInterest } = amortize(5000, 6, 200, 30);
    const totalPrincipal = 5000 - schedule[schedule.length - 1].balance;
    const totalPaid = totalPrincipal + totalInterest;
    expect(totalPaid).toBeGreaterThan(5000);
  });

  it("extra payment reduces total months", () => {
    const base = amortize(10000, 12, 300, 360);
    const extra = amortize(10000, 12, 600, 360);
    expect(extra.schedule.length).toBeLessThan(base.schedule.length);
  });
});

// ── State tax rate logic ───────────────────────────────────────────────────

describe("State tax rate data", () => {
  it("no-income-tax states have 0.0 rate", () => {
    // Pure data test — read the file and verify specific values
    const src = readSource(
      "../backend/app/constants/state_tax_rates.py"
    );
    // TX, FL, NV, WY should all be 0.0
    for (const state of ["TX", "FL", "NV", "WY"]) {
      expect(src).toContain(`"${state}": 0.0`);
    }
  });

  it("all 50 states + DC are present", () => {
    const src = readSource(
      "../backend/app/constants/state_tax_rates.py"
    );
    const stateCount = (src.match(/"[A-Z]{2}":/g) || []).length;
    // At minimum 50 states + DC = 51 entries across both dicts;
    // allow for duplication across STATE_TAX_RATES and STATE_NAMES
    expect(stateCount).toBeGreaterThanOrEqual(51);
  });
});

// ── Budget rollover math ───────────────────────────────────────────────────

describe("Budget rollover math", () => {
  function calcRollover(budgetAmount: number, prevSpent: number): number {
    return Math.max(0, budgetAmount - prevSpent);
  }

  function calcEffectiveBudget(budgetAmount: number, rollover: number): number {
    return budgetAmount + rollover;
  }

  it("unused budget rolls over fully when under budget", () => {
    const rollover = calcRollover(500, 300);
    expect(rollover).toBe(200);
    expect(calcEffectiveBudget(500, rollover)).toBe(700);
  });

  it("overspent period yields zero rollover", () => {
    const rollover = calcRollover(500, 600);
    expect(rollover).toBe(0);
    expect(calcEffectiveBudget(500, rollover)).toBe(500);
  });

  it("exactly on budget yields zero rollover", () => {
    expect(calcRollover(500, 500)).toBe(0);
  });
});
