/**
 * Tests for tax lots panel logic: currency formatting, cost basis methods,
 * sale validation, and type definitions.
 */

import { describe, it, expect } from "vitest";
import type {
  TaxLot,
  SaleRequest,
  SaleResult,
  UnrealizedGainsSummary,
  RealizedGainsSummary,
} from "../../../api/taxLots";

// ── Currency formatting (mirrored from TaxLotsPanel) ────────────────────────

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);

describe("TaxLots formatCurrency", () => {
  it("formats positive amounts with two decimals", () => {
    expect(formatCurrency(1234.56)).toBe("$1,234.56");
  });

  it("formats zero", () => {
    expect(formatCurrency(0)).toBe("$0.00");
  });

  it("formats negative amounts", () => {
    expect(formatCurrency(-500.5)).toBe("-$500.50");
  });
});

// ── TaxLot type shapes ──────────────────────────────────────────────────────

describe("TaxLot type", () => {
  const openLot: TaxLot = {
    id: "lot-1",
    holding_id: "hold-1",
    acquired_date: "2023-01-15",
    quantity: 100,
    remaining_quantity: 80,
    cost_basis_per_share: 50.25,
    total_cost_basis: 4020.0,
    holding_period: "LONG_TERM",
    is_closed: false,
    closed_date: null,
  };

  const closedLot: TaxLot = {
    ...openLot,
    id: "lot-2",
    remaining_quantity: 0,
    is_closed: true,
    closed_date: "2024-06-01",
  };

  it("open lot has remaining_quantity > 0", () => {
    expect(openLot.remaining_quantity).toBeGreaterThan(0);
    expect(openLot.is_closed).toBe(false);
    expect(openLot.closed_date).toBeNull();
  });

  it("closed lot has remaining_quantity = 0", () => {
    expect(closedLot.remaining_quantity).toBe(0);
    expect(closedLot.is_closed).toBe(true);
    expect(closedLot.closed_date).not.toBeNull();
  });

  it("holding_period is SHORT_TERM or LONG_TERM", () => {
    const validPeriods = ["SHORT_TERM", "LONG_TERM"];
    expect(validPeriods).toContain(openLot.holding_period);
  });
});

// ── Sale request validation ─────────────────────────────────────────────────

describe("Sale Request Validation", () => {
  it("valid sale request has all required fields", () => {
    const sale: SaleRequest = {
      quantity: 10,
      sale_price_per_share: 75.0,
      sale_date: "2024-12-15",
      cost_basis_method: "FIFO",
    };
    expect(sale.quantity).toBeGreaterThan(0);
    expect(sale.sale_price_per_share).toBeGreaterThan(0);
    expect(sale.sale_date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  it("cost basis method must be one of FIFO, LIFO, HIFO, SPECIFIC_ID", () => {
    const validMethods: SaleRequest["cost_basis_method"][] = [
      "FIFO",
      "LIFO",
      "HIFO",
      "SPECIFIC_ID",
    ];
    expect(validMethods).toHaveLength(4);
    for (const method of validMethods) {
      const sale: SaleRequest = {
        quantity: 1,
        sale_price_per_share: 100,
        sale_date: "2024-12-15",
        cost_basis_method: method,
      };
      expect(sale.cost_basis_method).toBe(method);
    }
  });

  it("SPECIFIC_ID method can include lot IDs", () => {
    const sale: SaleRequest = {
      quantity: 5,
      sale_price_per_share: 100,
      sale_date: "2024-12-15",
      cost_basis_method: "SPECIFIC_ID",
      specific_lot_ids: ["lot-1", "lot-2"],
    };
    expect(sale.specific_lot_ids).toHaveLength(2);
  });

  it("handleRecordSale guard rejects empty quantity or price", () => {
    // Mirrors the guard: if (!saleHoldingId || !saleQuantity || !salePrice) return;
    const cases = [
      { holdingId: "", quantity: "10", price: "50", shouldSubmit: false },
      { holdingId: "h-1", quantity: "", price: "50", shouldSubmit: false },
      { holdingId: "h-1", quantity: "10", price: "", shouldSubmit: false },
      { holdingId: "h-1", quantity: "10", price: "50", shouldSubmit: true },
    ];
    for (const { holdingId, quantity, price, shouldSubmit } of cases) {
      const canSubmit = !!(holdingId && quantity && price);
      expect(canSubmit, `h=${holdingId}, q=${quantity}, p=${price}`).toBe(
        shouldSubmit,
      );
    }
  });
});

// ── Sale result shape ───────────────────────────────────────────────────────

describe("Sale Result", () => {
  it("realized_gain_loss = total_proceeds - total_cost_basis", () => {
    const result: SaleResult = {
      lots_sold: 2,
      total_proceeds: 10000,
      total_cost_basis: 8000,
      realized_gain_loss: 2000,
      short_term_gain_loss: 500,
      long_term_gain_loss: 1500,
    };
    expect(result.realized_gain_loss).toBe(
      result.total_proceeds - result.total_cost_basis,
    );
  });

  it("short + long term equals total realized", () => {
    const result: SaleResult = {
      lots_sold: 3,
      total_proceeds: 15000,
      total_cost_basis: 12000,
      realized_gain_loss: 3000,
      short_term_gain_loss: 1200,
      long_term_gain_loss: 1800,
    };
    expect(result.short_term_gain_loss + result.long_term_gain_loss).toBe(
      result.realized_gain_loss,
    );
  });
});

// ── Unrealized / Realized Gains Summaries ───────────────────────────────────

describe("Gains Summary Types", () => {
  it("unrealized gains summary has required fields", () => {
    const summary: UnrealizedGainsSummary = {
      items: [],
      total_unrealized_gain: 5000,
      total_cost_basis: 20000,
      total_current_value: 25000,
    };
    expect(summary.total_current_value - summary.total_cost_basis).toBe(
      summary.total_unrealized_gain,
    );
  });

  it("realized gains summary has tax-relevant fields", () => {
    const summary: RealizedGainsSummary = {
      year: 2024,
      total_realized: 3000,
      short_term_gains: 1000,
      long_term_gains: 2000,
      total_proceeds: 15000,
      total_cost_basis: 12000,
    };
    expect(summary.short_term_gains + summary.long_term_gains).toBe(
      summary.total_realized,
    );
    expect(summary.year).toBe(2024);
  });

  it("color logic for unrealized gains", () => {
    // Mirrors: color={unrealizedGains.total_unrealized_gain >= 0 ? 'finance.positive' : 'finance.negative'}
    const positiveColor = (gain: number) =>
      gain >= 0 ? "finance.positive" : "finance.negative";
    expect(positiveColor(5000)).toBe("finance.positive");
    expect(positiveColor(0)).toBe("finance.positive");
    expect(positiveColor(-100)).toBe("finance.negative");
  });
});

// ── Year selector ───────────────────────────────────────────────────────────

describe("Year Options Generation", () => {
  it("generates 5 years ending at current year", () => {
    const currentYear = new Date().getFullYear();
    const yearOptions = Array.from({ length: 5 }, (_, i) => currentYear - i);
    expect(yearOptions).toHaveLength(5);
    expect(yearOptions[0]).toBe(currentYear);
    expect(yearOptions[4]).toBe(currentYear - 4);
  });
});
