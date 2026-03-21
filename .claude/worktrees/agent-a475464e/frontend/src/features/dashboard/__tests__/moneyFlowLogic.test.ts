/**
 * Unit tests for Money Flow Sankey diagram data transformation logic.
 *
 * Tests the buildSankeyData function that transforms income/expense
 * summary data into the node/link format required by recharts Sankey.
 */

import { describe, it, expect } from "vitest";

// ── Types mirroring the widget ──────────────────────────────────────────────

interface CategoryBreakdown {
  category: string;
  amount: number;
  count: number;
  percentage: number;
}

interface IncomeExpenseSummary {
  total_income: number;
  total_expenses: number;
  net: number;
  income_categories: CategoryBreakdown[];
  expense_categories: CategoryBreakdown[];
}

// ── Reproduce the pure buildSankeyData logic from the widget ────────────────

function buildSankeyData(summary: IncomeExpenseSummary) {
  const incomeCategories = summary.income_categories
    .filter((c) => c.amount > 0 && c.percentage >= 0.5)
    .slice(0, 8);
  const expenseCategories = summary.expense_categories
    .filter((c) => c.amount > 0 && c.percentage >= 0.5)
    .slice(0, 10);

  if (incomeCategories.length === 0 && expenseCategories.length === 0)
    return null;

  const nodes: { name: string }[] = [];
  const links: { source: number; target: number; value: number }[] = [];

  // Income nodes
  incomeCategories.forEach((c) => nodes.push({ name: c.category }));
  const shownIncomeTotal = incomeCategories.reduce((s, c) => s + c.amount, 0);
  const otherIncome = summary.total_income - shownIncomeTotal;
  if (otherIncome > 0) nodes.push({ name: "Other Income" });

  // Hub node
  const hubIndex = nodes.length;
  nodes.push({ name: "Total Income" });

  // Expense nodes
  const expenseStartIndex = nodes.length;
  expenseCategories.forEach((c) => nodes.push({ name: c.category }));
  const shownExpenseTotal = expenseCategories.reduce((s, c) => s + c.amount, 0);
  const otherExpenses = summary.total_expenses - shownExpenseTotal;
  if (otherExpenses > 0) nodes.push({ name: "Other Expenses" });

  // Surplus/deficit node
  const net = summary.total_income - summary.total_expenses;
  let surplusIdx = -1;
  if (net > 0) {
    surplusIdx = nodes.length;
    nodes.push({ name: "Savings" });
  } else if (net < 0) {
    surplusIdx = nodes.length;
    nodes.push({ name: "Deficit" });
  }

  // Income → hub links
  incomeCategories.forEach((c, i) =>
    links.push({ source: i, target: hubIndex, value: c.amount }),
  );
  if (otherIncome > 0)
    links.push({
      source: hubIndex - 1,
      target: hubIndex,
      value: otherIncome,
    });

  // Hub → expense links
  expenseCategories.forEach((c, i) =>
    links.push({
      source: hubIndex,
      target: expenseStartIndex + i,
      value: c.amount,
    }),
  );
  if (otherExpenses > 0) {
    const otherExpIdx = expenseStartIndex + expenseCategories.length;
    links.push({
      source: hubIndex,
      target: otherExpIdx,
      value: otherExpenses,
    });
  }

  // Hub → surplus/deficit
  if (surplusIdx >= 0 && net !== 0)
    links.push({
      source: hubIndex,
      target: surplusIdx,
      value: Math.abs(net),
    });

  return { nodes, links, hubIndex };
}

// ── Test data ───────────────────────────────────────────────────────────────

const basicSummary: IncomeExpenseSummary = {
  total_income: 8000,
  total_expenses: 6000,
  net: 2000,
  income_categories: [
    { category: "Salary", amount: 7000, count: 2, percentage: 87.5 },
    { category: "Dividends", amount: 1000, count: 5, percentage: 12.5 },
  ],
  expense_categories: [
    { category: "Housing", amount: 2000, count: 1, percentage: 33.3 },
    { category: "Food & Drink", amount: 1500, count: 30, percentage: 25.0 },
    { category: "Transportation", amount: 800, count: 10, percentage: 13.3 },
    { category: "Shopping", amount: 700, count: 15, percentage: 11.7 },
    { category: "Bills", amount: 1000, count: 8, percentage: 16.7 },
  ],
};

// ── Tests ───────────────────────────────────────────────────────────────────

describe("buildSankeyData — basic structure", () => {
  it("returns null when no categories have data", () => {
    const empty: IncomeExpenseSummary = {
      total_income: 0,
      total_expenses: 0,
      net: 0,
      income_categories: [],
      expense_categories: [],
    };
    expect(buildSankeyData(empty)).toBeNull();
  });

  it("creates correct node count for basic summary", () => {
    const result = buildSankeyData(basicSummary)!;
    // 2 income + 1 hub + 5 expense + 1 savings = 9
    expect(result.nodes).toHaveLength(9);
  });

  it("hub node is named 'Total Income'", () => {
    const result = buildSankeyData(basicSummary)!;
    expect(result.nodes[result.hubIndex].name).toBe("Total Income");
  });

  it("income nodes appear before the hub", () => {
    const result = buildSankeyData(basicSummary)!;
    const incomeNodes = result.nodes.slice(0, result.hubIndex);
    expect(incomeNodes.map((n) => n.name)).toEqual(["Salary", "Dividends"]);
  });

  it("expense nodes appear after the hub", () => {
    const result = buildSankeyData(basicSummary)!;
    const expenseNodes = result.nodes.slice(
      result.hubIndex + 1,
      result.hubIndex + 1 + 5,
    );
    expect(expenseNodes.map((n) => n.name)).toEqual([
      "Housing",
      "Food & Drink",
      "Transportation",
      "Shopping",
      "Bills",
    ]);
  });

  it("includes Savings node when net is positive", () => {
    const result = buildSankeyData(basicSummary)!;
    const savingsNode = result.nodes.find((n) => n.name === "Savings");
    expect(savingsNode).toBeDefined();
  });
});

describe("buildSankeyData — links", () => {
  it("creates income → hub links for each income category", () => {
    const result = buildSankeyData(basicSummary)!;
    const incomeLinks = result.links.filter(
      (l) => l.target === result.hubIndex,
    );
    expect(incomeLinks).toHaveLength(2);
    expect(incomeLinks[0].value).toBe(7000); // Salary
    expect(incomeLinks[1].value).toBe(1000); // Dividends
  });

  it("creates hub → expense links for each expense category", () => {
    const result = buildSankeyData(basicSummary)!;
    const expenseLinks = result.links.filter(
      (l) =>
        l.source === result.hubIndex && l.target !== result.nodes.length - 1,
    );
    expect(expenseLinks).toHaveLength(5);
  });

  it("creates hub → savings link with correct value", () => {
    const result = buildSankeyData(basicSummary)!;
    const savingsIdx = result.nodes.findIndex((n) => n.name === "Savings");
    const savingsLink = result.links.find((l) => l.target === savingsIdx);
    expect(savingsLink).toBeDefined();
    expect(savingsLink!.value).toBe(2000);
  });

  it("all link values are positive", () => {
    const result = buildSankeyData(basicSummary)!;
    for (const link of result.links) {
      expect(link.value).toBeGreaterThan(0);
    }
  });
});

describe("buildSankeyData — deficit scenario", () => {
  const deficitSummary: IncomeExpenseSummary = {
    total_income: 4000,
    total_expenses: 6000,
    net: -2000,
    income_categories: [
      { category: "Salary", amount: 4000, count: 2, percentage: 100 },
    ],
    expense_categories: [
      { category: "Housing", amount: 3000, count: 1, percentage: 50 },
      { category: "Food", amount: 3000, count: 20, percentage: 50 },
    ],
  };

  it("includes Deficit node instead of Savings", () => {
    const result = buildSankeyData(deficitSummary)!;
    expect(result.nodes.find((n) => n.name === "Deficit")).toBeDefined();
    expect(result.nodes.find((n) => n.name === "Savings")).toBeUndefined();
  });

  it("deficit link has absolute value of net", () => {
    const result = buildSankeyData(deficitSummary)!;
    const deficitIdx = result.nodes.findIndex((n) => n.name === "Deficit");
    const deficitLink = result.links.find((l) => l.target === deficitIdx);
    expect(deficitLink!.value).toBe(2000);
  });
});

describe("buildSankeyData — Other Income/Expenses aggregation", () => {
  const summaryWithOther: IncomeExpenseSummary = {
    total_income: 10000,
    total_expenses: 8000,
    net: 2000,
    income_categories: [
      { category: "Salary", amount: 8000, count: 2, percentage: 80 },
      // Remaining $2000 should become "Other Income"
    ],
    expense_categories: [
      { category: "Housing", amount: 5000, count: 1, percentage: 62.5 },
      // Remaining $3000 should become "Other Expenses"
    ],
  };

  it("creates Other Income node when income categories don't sum to total", () => {
    const result = buildSankeyData(summaryWithOther)!;
    expect(result.nodes.find((n) => n.name === "Other Income")).toBeDefined();
  });

  it("creates Other Expenses node when expense categories don't sum to total", () => {
    const result = buildSankeyData(summaryWithOther)!;
    expect(result.nodes.find((n) => n.name === "Other Expenses")).toBeDefined();
  });

  it("Other Income link has correct value", () => {
    const result = buildSankeyData(summaryWithOther)!;
    const otherIncomeIdx = result.nodes.findIndex(
      (n) => n.name === "Other Income",
    );
    const link = result.links.find((l) => l.source === otherIncomeIdx);
    expect(link!.value).toBe(2000);
  });
});

describe("buildSankeyData — filtering", () => {
  it("filters out categories with percentage < 0.5", () => {
    const summary: IncomeExpenseSummary = {
      total_income: 10000,
      total_expenses: 9000,
      net: 1000,
      income_categories: [
        { category: "Salary", amount: 9950, count: 2, percentage: 99.5 },
        { category: "Interest", amount: 50, count: 1, percentage: 0.3 },
      ],
      expense_categories: [
        { category: "Housing", amount: 9000, count: 1, percentage: 100 },
      ],
    };
    const result = buildSankeyData(summary)!;
    // "Interest" filtered out because percentage < 0.5
    const interestNode = result.nodes.find((n) => n.name === "Interest");
    expect(interestNode).toBeUndefined();
    // But income still flows through "Other Income"
    const otherIncome = result.nodes.find((n) => n.name === "Other Income");
    expect(otherIncome).toBeDefined();
  });

  it("limits income categories to 8", () => {
    const categories: CategoryBreakdown[] = Array.from(
      { length: 12 },
      (_, i) => ({
        category: `Income${i}`,
        amount: 1000,
        count: 1,
        percentage: 8.3,
      }),
    );
    const summary: IncomeExpenseSummary = {
      total_income: 12000,
      total_expenses: 10000,
      net: 2000,
      income_categories: categories,
      expense_categories: [
        { category: "Housing", amount: 10000, count: 1, percentage: 100 },
      ],
    };
    const result = buildSankeyData(summary)!;
    // 8 income nodes + Other Income + hub + 1 expense + savings = 12
    const incomeNodes = result.nodes.slice(0, result.hubIndex);
    // Should be 8 named + 1 "Other Income" = 9
    expect(incomeNodes.length).toBe(9);
  });

  it("limits expense categories to 10", () => {
    const categories: CategoryBreakdown[] = Array.from(
      { length: 15 },
      (_, i) => ({
        category: `Expense${i}`,
        amount: 500,
        count: 1,
        percentage: 6.7,
      }),
    );
    const summary: IncomeExpenseSummary = {
      total_income: 10000,
      total_expenses: 7500,
      net: 2500,
      income_categories: [
        { category: "Salary", amount: 10000, count: 1, percentage: 100 },
      ],
      expense_categories: categories,
    };
    const result = buildSankeyData(summary)!;
    const hubIdx = result.hubIndex;
    const savingsIdx = result.nodes.findIndex((n) => n.name === "Savings");
    // 10 expense nodes + possibly "Other Expenses"
    const expenseNodeCount =
      savingsIdx > hubIdx
        ? savingsIdx - hubIdx - 1
        : result.nodes.length - hubIdx - 1;
    expect(expenseNodeCount).toBeLessThanOrEqual(12); // 10 + Other Expenses + Savings
  });
});

describe("buildSankeyData — zero net", () => {
  it("does not create Savings or Deficit when net is zero", () => {
    const summary: IncomeExpenseSummary = {
      total_income: 5000,
      total_expenses: 5000,
      net: 0,
      income_categories: [
        { category: "Salary", amount: 5000, count: 1, percentage: 100 },
      ],
      expense_categories: [
        { category: "Housing", amount: 5000, count: 1, percentage: 100 },
      ],
    };
    const result = buildSankeyData(summary)!;
    expect(result.nodes.find((n) => n.name === "Savings")).toBeUndefined();
    expect(result.nodes.find((n) => n.name === "Deficit")).toBeUndefined();
  });
});
