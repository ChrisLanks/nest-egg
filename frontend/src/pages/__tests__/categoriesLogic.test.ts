/**
 * Tests for CategoriesPage logic: category hierarchy building, custom vs Plaid
 * splitting, parent category filtering, and form validation guards.
 * Also tests Labels tab logic: CRUD helpers, is_income mapping, system label
 * guards, parent dropdown filtering, and explanation banner text.
 */

import { describe, it, expect } from "vitest";

// ── Types (mirrored from CategoriesPage.tsx) ────────────────────────────────

interface Category {
  id: string | null;
  name: string;
  color?: string;
  parent_category_id?: string;
  is_custom: boolean;
  transaction_count: number;
}

interface CategoryWithChildren extends Category {
  children?: CategoryWithChildren[];
}

interface Label {
  id: string;
  name: string;
  color?: string;
  is_income?: boolean | null;
  is_system?: boolean;
  parent_label_id?: string | null;
  transaction_count?: number;
}

// ── Logic helpers (mirrored from CategoriesPage.tsx) ─────────────────────────

function buildCategoryTree(categories: Category[]): {
  customCategories: CategoryWithChildren[];
  plaidCategories: Category[];
} {
  if (!categories) return { customCategories: [], plaidCategories: [] };

  const custom = categories.filter((c) => c.is_custom);
  const plaid = categories.filter((c) => !c.is_custom);

  const categoryMap = new Map<string, CategoryWithChildren>();
  const roots: CategoryWithChildren[] = [];

  custom.forEach((category) => {
    if (category.id) {
      categoryMap.set(category.id, { ...category, children: [] });
    }
  });

  custom.forEach((category) => {
    if (!category.id) return;
    const categoryWithChildren = categoryMap.get(category.id)!;
    if (category.parent_category_id) {
      const parent = categoryMap.get(category.parent_category_id);
      if (parent) {
        parent.children!.push(categoryWithChildren);
      } else {
        roots.push(categoryWithChildren);
      }
    } else {
      roots.push(categoryWithChildren);
    }
  });

  return { customCategories: roots, plaidCategories: plaid };
}

function getParentCategories(categories: Category[]): Category[] {
  return categories.filter((c) => c.is_custom && !c.parent_category_id);
}

// ── Label helpers (mirrored from CategoriesPage.tsx) ─────────────────────────

type LabelIncomeState = "income" | "expense" | "any";

function incomeStateToValue(state: LabelIncomeState): boolean | null {
  if (state === "income") return true;
  if (state === "expense") return false;
  return null;
}

function valueToIncomeState(value: boolean | null | undefined): LabelIncomeState {
  if (value === true) return "income";
  if (value === false) return "expense";
  return "any";
}

function getRootLabels(labels: Label[]): Label[] {
  return labels.filter((l) => !l.parent_label_id);
}

function canDeleteLabel(label: Label): boolean {
  return !label.is_system;
}

function getLabelTypeName(label: Label): string {
  if (label.is_income === true) return "Income";
  if (label.is_income === false) return "Expense";
  return "Any";
}

// ── Fixtures ─────────────────────────────────────────────────────────────────

const CUSTOM_ROOT: Category = {
  id: "c1",
  name: "Housing",
  color: "#FF0000",
  is_custom: true,
  transaction_count: 10,
};

const CUSTOM_CHILD: Category = {
  id: "c2",
  name: "Rent",
  color: "#00FF00",
  parent_category_id: "c1",
  is_custom: true,
  transaction_count: 5,
};

const CUSTOM_ROOT2: Category = {
  id: "c3",
  name: "Food",
  is_custom: true,
  transaction_count: 20,
};

const PLAID_CAT: Category = {
  id: null,
  name: "Travel",
  is_custom: false,
  transaction_count: 3,
};

const PLAID_CAT2: Category = {
  id: null,
  name: "Entertainment",
  is_custom: false,
  transaction_count: 7,
};

const LABEL_ROOT: Label = {
  id: "l1",
  name: "Tax Deductible",
  color: "#FF6600",
  is_income: null,
  is_system: false,
};

const LABEL_CHILD: Label = {
  id: "l2",
  name: "Business Travel",
  color: "#0066FF",
  is_income: false,
  parent_label_id: "l1",
  is_system: false,
};

const LABEL_INCOME: Label = {
  id: "l3",
  name: "Freelance Income",
  color: "#00AA00",
  is_income: true,
  is_system: false,
};

const LABEL_SYSTEM: Label = {
  id: "l4",
  name: "Transfer",
  is_income: null,
  is_system: true,
};

// ── Tests: buildCategoryTree ──────────────────────────────────────────────────

describe("buildCategoryTree", () => {
  it("splits categories into custom and plaid groups", () => {
    const { customCategories, plaidCategories } = buildCategoryTree([
      CUSTOM_ROOT,
      PLAID_CAT,
      CUSTOM_ROOT2,
      PLAID_CAT2,
    ]);
    expect(customCategories).toHaveLength(2);
    expect(plaidCategories).toHaveLength(2);
  });

  it("nests child categories under their parent", () => {
    const { customCategories } = buildCategoryTree([CUSTOM_ROOT, CUSTOM_CHILD]);
    expect(customCategories).toHaveLength(1);
    expect(customCategories[0].name).toBe("Housing");
    expect(customCategories[0].children).toHaveLength(1);
    expect(customCategories[0].children![0].name).toBe("Rent");
  });

  it("treats orphaned children as roots when parent is missing", () => {
    const orphan: Category = {
      id: "c99",
      name: "Orphan",
      parent_category_id: "nonexistent",
      is_custom: true,
      transaction_count: 1,
    };
    const { customCategories } = buildCategoryTree([orphan]);
    expect(customCategories).toHaveLength(1);
    expect(customCategories[0].name).toBe("Orphan");
  });

  it("returns empty arrays for empty input", () => {
    const { customCategories, plaidCategories } = buildCategoryTree([]);
    expect(customCategories).toHaveLength(0);
    expect(plaidCategories).toHaveLength(0);
  });

  it("skips custom categories with null id", () => {
    const nullId: Category = {
      id: null,
      name: "NullCustom",
      is_custom: true,
      transaction_count: 0,
    };
    const { customCategories } = buildCategoryTree([nullId]);
    // null-id custom categories are skipped during map building
    expect(customCategories).toHaveLength(0);
  });

  it("does not nest plaid categories even if they share names", () => {
    const { plaidCategories, customCategories } = buildCategoryTree([
      PLAID_CAT,
      PLAID_CAT2,
    ]);
    expect(plaidCategories).toHaveLength(2);
    expect(customCategories).toHaveLength(0);
  });
});

describe("getParentCategories", () => {
  it("returns only custom root categories", () => {
    const parents = getParentCategories([
      CUSTOM_ROOT,
      CUSTOM_CHILD,
      CUSTOM_ROOT2,
      PLAID_CAT,
    ]);
    expect(parents).toHaveLength(2);
    expect(parents.map((p) => p.name)).toEqual(["Housing", "Food"]);
  });

  it("excludes plaid categories", () => {
    const parents = getParentCategories([PLAID_CAT, PLAID_CAT2]);
    expect(parents).toHaveLength(0);
  });

  it("excludes child categories", () => {
    const parents = getParentCategories([CUSTOM_CHILD]);
    expect(parents).toHaveLength(0);
  });
});

describe("Form validation guards", () => {
  it("rejects empty name for create", () => {
    const name = "   ";
    expect(name.trim()).toBe("");
  });

  it("accepts non-empty name", () => {
    const name = "Groceries";
    expect(name.trim()).not.toBe("");
  });

  it("rejects empty name for edit when no editing category", () => {
    const editingCategory = null;
    const name = "Test";
    const canSubmit = !!editingCategory && !!name.trim();
    expect(canSubmit).toBe(false);
  });

  it("allows edit when both editing category and name exist", () => {
    const editingCategory = CUSTOM_ROOT;
    const name = "Updated Housing";
    const canSubmit = !!editingCategory && !!name.trim();
    expect(canSubmit).toBe(true);
  });
});

describe("Delete guards", () => {
  it("blocks deletion of plaid categories (null id)", () => {
    const canDelete = PLAID_CAT.id !== null;
    expect(canDelete).toBe(false);
  });

  it("allows deletion of custom categories with id", () => {
    const canDelete = CUSTOM_ROOT.id !== null;
    expect(canDelete).toBe(true);
  });
});

describe("Transaction count pluralization", () => {
  it("uses singular for 1 transaction", () => {
    const count = 1;
    const label = `${count} transaction${count !== 1 ? "s" : ""}`;
    expect(label).toBe("1 transaction");
  });

  it("uses plural for 0 or many transactions", () => {
    const zero = 0;
    const five = 5;
    expect(`${zero} transaction${zero !== 1 ? "s" : ""}`).toBe(
      "0 transactions",
    );
    expect(`${five} transaction${five !== 1 ? "s" : ""}`).toBe(
      "5 transactions",
    );
  });
});

// ── Tests: Label is_income mapping ───────────────────────────────────────────

describe("incomeStateToValue", () => {
  it('maps "income" to true', () => {
    expect(incomeStateToValue("income")).toBe(true);
  });

  it('maps "expense" to false', () => {
    expect(incomeStateToValue("expense")).toBe(false);
  });

  it('maps "any" to null', () => {
    expect(incomeStateToValue("any")).toBeNull();
  });
});

describe("valueToIncomeState", () => {
  it("maps true to income", () => {
    expect(valueToIncomeState(true)).toBe("income");
  });

  it("maps false to expense", () => {
    expect(valueToIncomeState(false)).toBe("expense");
  });

  it("maps null to any", () => {
    expect(valueToIncomeState(null)).toBe("any");
  });

  it("maps undefined to any", () => {
    expect(valueToIncomeState(undefined)).toBe("any");
  });
});

// ── Tests: Label CRUD logic ───────────────────────────────────────────────────

describe("Label create form validation", () => {
  it("rejects empty name", () => {
    expect("".trim()).toBe("");
  });

  it("accepts valid name", () => {
    expect("Business Expense".trim()).not.toBe("");
  });

  it("create payload uses correct is_income for income state", () => {
    const state: LabelIncomeState = "income";
    expect(incomeStateToValue(state)).toBe(true);
  });

  it("create payload uses correct is_income for expense state", () => {
    const state: LabelIncomeState = "expense";
    expect(incomeStateToValue(state)).toBe(false);
  });

  it("create payload uses null is_income for any state", () => {
    const state: LabelIncomeState = "any";
    expect(incomeStateToValue(state)).toBeNull();
  });
});

describe("Label edit form validation", () => {
  it("rejects edit when editingLabel is null", () => {
    const editingLabel = null;
    const canSubmit = !!editingLabel && !!"Some Name".trim();
    expect(canSubmit).toBe(false);
  });

  it("allows edit when editingLabel and name exist", () => {
    const editingLabel = LABEL_ROOT;
    const canSubmit = !!editingLabel && !!"Updated Name".trim();
    expect(canSubmit).toBe(true);
  });

  it("pre-fills incomeState correctly for income label", () => {
    const state = valueToIncomeState(LABEL_INCOME.is_income);
    expect(state).toBe("income");
  });

  it("pre-fills incomeState correctly for expense label", () => {
    const state = valueToIncomeState(LABEL_CHILD.is_income);
    expect(state).toBe("expense");
  });

  it("pre-fills incomeState correctly for any label", () => {
    const state = valueToIncomeState(LABEL_ROOT.is_income);
    expect(state).toBe("any");
  });
});

describe("Label delete guards", () => {
  it("blocks deletion of system labels", () => {
    expect(canDeleteLabel(LABEL_SYSTEM)).toBe(false);
  });

  it("allows deletion of non-system labels", () => {
    expect(canDeleteLabel(LABEL_ROOT)).toBe(true);
    expect(canDeleteLabel(LABEL_INCOME)).toBe(true);
  });

  it("is_system true means cannot delete regardless of other fields", () => {
    const systemLabel: Label = {
      id: "sys1",
      name: "Transfer",
      is_system: true,
    };
    expect(canDeleteLabel(systemLabel)).toBe(false);
  });
});

// ── Tests: Label hierarchy / parent dropdown ──────────────────────────────────

describe("getRootLabels (parent label dropdown)", () => {
  it("returns only labels without a parent_label_id", () => {
    const roots = getRootLabels([LABEL_ROOT, LABEL_CHILD, LABEL_INCOME, LABEL_SYSTEM]);
    expect(roots).toHaveLength(3);
    expect(roots.map((l) => l.name)).toContain("Tax Deductible");
    expect(roots.map((l) => l.name)).toContain("Freelance Income");
    expect(roots.map((l) => l.name)).toContain("Transfer");
  });

  it("excludes child labels (those with parent_label_id)", () => {
    const roots = getRootLabels([LABEL_ROOT, LABEL_CHILD]);
    expect(roots).toHaveLength(1);
    expect(roots[0].name).toBe("Tax Deductible");
  });

  it("returns empty array when all labels are children", () => {
    const child1: Label = { id: "x1", name: "A", parent_label_id: "p1" };
    const child2: Label = { id: "x2", name: "B", parent_label_id: "p2" };
    expect(getRootLabels([child1, child2])).toHaveLength(0);
  });
});

// ── Tests: getLabelTypeName ───────────────────────────────────────────────────

describe("getLabelTypeName", () => {
  it('returns "Income" for is_income true', () => {
    expect(getLabelTypeName(LABEL_INCOME)).toBe("Income");
  });

  it('returns "Expense" for is_income false', () => {
    expect(getLabelTypeName(LABEL_CHILD)).toBe("Expense");
  });

  it('returns "Any" for is_income null', () => {
    expect(getLabelTypeName(LABEL_ROOT)).toBe("Any");
  });

  it('returns "Any" for is_income undefined', () => {
    const label: Label = { id: "u1", name: "Uncategorized" };
    expect(getLabelTypeName(label)).toBe("Any");
  });
});

// ── Tests: Explanation banner text ───────────────────────────────────────────

const CATEGORIES_BANNER =
  "Categories classify what a transaction is — Groceries, Dining, Utilities. They come from your bank (provider categories) or you can create custom ones. Used in budgets, trends, and reports.";

const LABELS_BANNER =
  'Labels are freeform tags you apply to transactions for cross-cutting purposes — "Business Expense", "Tax Deductible", "Freelance Income". A transaction can have multiple labels. Used in the Variable Income Planner, Tax Deductible page, and Rules.';

describe("Explanation banner text", () => {
  it("shows categories banner when tab index is 0", () => {
    const tabIndex = 0;
    const bannerText = tabIndex === 0 ? CATEGORIES_BANNER : LABELS_BANNER;
    expect(bannerText).toContain("Categories classify");
    expect(bannerText).toContain("budgets, trends, and reports");
  });

  it("shows labels banner when tab index is 1", () => {
    const tabIndex = 1;
    const bannerText = tabIndex === 0 ? CATEGORIES_BANNER : LABELS_BANNER;
    expect(bannerText).toContain("freeform tags");
    expect(bannerText).toContain("Variable Income Planner");
  });

  it("categories banner mentions provider categories", () => {
    expect(CATEGORIES_BANNER).toContain("provider categories");
  });

  it("labels banner mentions Tax Deductible", () => {
    expect(LABELS_BANNER).toContain("Tax Deductible");
  });

  it("labels banner mentions multiple labels per transaction", () => {
    expect(LABELS_BANNER).toContain("multiple labels");
  });
});
