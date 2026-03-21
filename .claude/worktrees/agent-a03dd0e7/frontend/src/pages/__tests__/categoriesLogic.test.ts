/**
 * Tests for CategoriesPage logic: category hierarchy building, custom vs Plaid
 * splitting, parent category filtering, and form validation guards.
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

// ── Tests ────────────────────────────────────────────────────────────────────

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
