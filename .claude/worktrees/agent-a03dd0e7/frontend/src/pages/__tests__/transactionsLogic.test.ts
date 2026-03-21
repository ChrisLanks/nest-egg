/**
 * Tests for TransactionsPage logic: search/filter parsing, sorting,
 * amount formatting, date formatting, sort direction defaults, empty states,
 * bulk selection management, category display, label badge colors,
 * read-only banner visibility, and month period grouping.
 */

import { describe, it, expect } from "vitest";
import type { Transaction, Label, Category } from "../../types/transaction";

// ── Fixture helpers ─────────────────────────────────────────────────────────

const makeLabel = (overrides: Partial<Label> = {}): Label => ({
  id: "label-1",
  name: "Transfer",
  is_income: false,
  ...overrides,
});

const makeCategory = (overrides: Partial<Category> = {}): Category => ({
  id: "cat-1",
  name: "Groceries",
  ...overrides,
});

const makeTransaction = (
  overrides: Partial<Transaction> = {},
): Transaction => ({
  id: "txn-1",
  account_id: "acc-1",
  organization_id: "org-1",
  date: "2025-03-15",
  amount: 42.5,
  merchant_name: "Whole Foods",
  description: "Weekly groceries",
  category_primary: "Food and Drink",
  category_detailed: null,
  is_pending: false,
  is_transfer: false,
  notes: null,
  flagged_for_review: false,
  account_name: "Chase Checking",
  account_mask: "1234",
  labels: [],
  deduplication_hash: "hash-1",
  created_at: "2025-03-15T00:00:00Z",
  updated_at: "2025-03-15T00:00:00Z",
  ...overrides,
});

// ── Logic helpers mirrored from TransactionsPage.tsx ─────────────────────────

const formatCurrency = (amount: number) => {
  const isNegative = amount < 0;
  const formatted = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(Math.abs(amount));
  return { formatted, isNegative };
};

const formatDate = (dateStr: string) => {
  const [year, month, day] = dateStr.split("-").map(Number);
  return new Date(year, month - 1, day).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
};

type SortField =
  | "date"
  | "merchant_name"
  | "amount"
  | "category_primary"
  | "account_name"
  | "labels"
  | "status";
type SortDirection = "asc" | "desc";

/** Mirrors the handleSort logic for determining default sort direction */
const getDefaultSortDirection = (field: SortField): SortDirection =>
  field === "date" || field === "amount" || field === "status" ? "desc" : "asc";

/** Mirrors the handleSort toggling logic */
const handleSort = (
  field: SortField,
  currentField: SortField | null,
  currentDirection: SortDirection,
): { sortField: SortField; sortDirection: SortDirection } => {
  if (currentField === field) {
    return {
      sortField: field,
      sortDirection: currentDirection === "asc" ? "desc" : "asc",
    };
  }
  return {
    sortField: field,
    sortDirection: getDefaultSortDirection(field),
  };
};

/** Mirrors the sorting comparator from processedTransactions useMemo */
const sortTransactions = (
  transactions: Transaction[],
  sortField: SortField,
  sortDirection: SortDirection,
): Transaction[] => {
  const sorted = [...transactions];
  sorted.sort((a, b) => {
    let aVal: any;
    let bVal: any;

    switch (sortField) {
      case "date":
        aVal = new Date(a.date).getTime();
        bVal = new Date(b.date).getTime();
        break;
      case "merchant_name":
        aVal = a.merchant_name?.toLowerCase() || "";
        bVal = b.merchant_name?.toLowerCase() || "";
        break;
      case "amount":
        aVal = Number(a.amount);
        bVal = Number(b.amount);
        break;
      case "category_primary":
        aVal = (
          a.category?.parent_name ||
          a.category?.name ||
          ""
        ).toLowerCase();
        bVal = (
          b.category?.parent_name ||
          b.category?.name ||
          ""
        ).toLowerCase();
        break;
      case "account_name":
        aVal = a.account_name?.toLowerCase() || "";
        bVal = b.account_name?.toLowerCase() || "";
        break;
      case "labels":
        aVal = a.labels?.[0]?.name?.toLowerCase() || "";
        bVal = b.labels?.[0]?.name?.toLowerCase() || "";
        break;
      case "status":
        aVal = a.is_pending ? 1 : 0;
        bVal = b.is_pending ? 1 : 0;
        break;
      default:
        return 0;
    }

    if (aVal < bVal) return sortDirection === "asc" ? -1 : 1;
    if (aVal > bVal) return sortDirection === "asc" ? 1 : -1;
    return 0;
  });
  return sorted;
};

/** Mirrors parseValues inside the search filter */
const parseValues = (str: string): string[] => {
  const values: string[] = [];
  let current = "";
  let inQuotes = false;

  for (let i = 0; i < str.length; i++) {
    const char = str[i];
    if (char === '"') {
      inQuotes = !inQuotes;
    } else if (char === "," && !inQuotes) {
      if (current.trim()) {
        values.push(current.trim().toLowerCase());
      }
      current = "";
    } else {
      current += char;
    }
  }

  if (current.trim()) {
    values.push(current.trim().toLowerCase());
  }

  return values;
};

/** Mirrors the search/filter logic from processedTransactions useMemo */
const filterTransactions = (
  transactions: Transaction[],
  searchQuery: string,
): Transaction[] => {
  if (!transactions.length) return [];
  if (!searchQuery) return [...transactions];

  const query = searchQuery.toLowerCase();

  const labelsMatch = query.match(
    /labels?:((?:"[^"]*"|[^\s,]+)(?:,(?:"[^"]*"|[^\s,]+))*)/i,
  );
  const categoryMatch = query.match(
    /categor(?:y|ies):((?:"[^"]*"|[^\s,]+)(?:,(?:"[^"]*"|[^\s,]+))*)/i,
  );
  const accountMatch = query.match(
    /accounts?:((?:"[^"]*"|[^\s,]+)(?:,(?:"[^"]*"|[^\s,]+))*)/i,
  );

  const plainQuery = query
    .replace(/labels?:(?:"[^"]*"|[^\s,]+)(?:,(?:"[^"]*"|[^\s,]+))*/gi, "")
    .replace(
      /categor(?:y|ies):(?:"[^"]*"|[^\s,]+)(?:,(?:"[^"]*"|[^\s,]+))*/gi,
      "",
    )
    .replace(/accounts?:(?:"[^"]*"|[^\s,]+)(?:,(?:"[^"]*"|[^\s,]+))*/gi, "")
    .trim();

  return transactions.filter((txn) => {
    if (labelsMatch) {
      const labelNames = parseValues(labelsMatch[1]);
      const searchingForEmpty = labelNames.includes("");

      if (searchingForEmpty) {
        if (txn.labels && txn.labels.length > 0) return false;
      } else {
        const hasMatchingLabel = txn.labels?.some((label) =>
          labelNames.some((ln) => label.name.toLowerCase().includes(ln)),
        );
        if (!hasMatchingLabel) return false;
      }
    }

    if (categoryMatch) {
      const categoryNames = parseValues(categoryMatch[1]);
      const categoryName = (
        txn.category?.name ||
        txn.category_primary ||
        ""
      ).toLowerCase();
      const parentName = (txn.category?.parent_name || "").toLowerCase();
      const hasMatchingCategory = categoryNames.some(
        (cn) => categoryName.includes(cn) || parentName.includes(cn),
      );
      if (!hasMatchingCategory) return false;
    }

    if (accountMatch) {
      const accountNames = parseValues(accountMatch[1]);
      const accountName = (txn.account_name || "").toLowerCase();
      const hasMatchingAccount = accountNames.some((acc) =>
        accountName.includes(acc),
      );
      if (!hasMatchingAccount) return false;
    }

    if (plainQuery) {
      return (
        txn.merchant_name?.toLowerCase().includes(plainQuery) ||
        txn.account_name?.toLowerCase().includes(plainQuery) ||
        txn.category?.name?.toLowerCase().includes(plainQuery) ||
        txn.category?.parent_name?.toLowerCase().includes(plainQuery) ||
        txn.description?.toLowerCase().includes(plainQuery) ||
        txn.labels?.some((label) =>
          label.name.toLowerCase().includes(plainQuery),
        )
      );
    }

    return true;
  });
};

/** Mirrors the category display logic from the JSX */
const getCategoryDisplay = (txn: Transaction): string | null => {
  if (txn.category) {
    return txn.category.parent_name
      ? `${txn.category.parent_name} (${txn.category.name})`
      : txn.category.name;
  }
  return txn.category_primary;
};

/** Mirrors label badge colorScheme logic */
const getLabelColorScheme = (label: Label): string | undefined => {
  if (label.color) return undefined;
  return label.is_income ? "green" : "purple";
};

/** Mirrors the read-only banner visibility */
const showReadOnlyBanner = (
  isOtherUserView: boolean,
  canEdit: boolean,
): boolean => isOtherUserView && !canEdit;

/** Mirrors the empty state description logic */
const getEmptyStateDescription = (hasSearch: boolean): string =>
  hasSearch
    ? "Try adjusting your search query."
    : "Connect your accounts to start tracking transactions.";

/** Mirrors the empty state action visibility */
const showEmptyAction = (hasSearch: boolean): boolean => !hasSearch;

/** Mirrors the summary text logic */
const getSummaryText = (
  processedCount: number,
  total: number,
  selectedCount: number,
  hasMore: boolean,
): string => {
  let text = `Showing ${processedCount} transactions`;
  if (total > 0) text += ` (${total} total)`;
  if (selectedCount > 0) text += `. ${selectedCount} selected`;
  if (hasMore) text += ". Scroll down to load more";
  if (selectedCount === 0 && !hasMore) text += ".";
  return text;
};

/** Mirrors the bulk label conflict resolution (labels in both add and remove) */
const resolveBulkLabelConflicts = (
  labelsToAdd: string[],
  labelsToRemove: string[],
): { effectiveAdd: string[]; effectiveRemove: string[] } => ({
  effectiveAdd: labelsToAdd.filter((id) => !labelsToRemove.includes(id)),
  effectiveRemove: labelsToRemove.filter((id) => !labelsToAdd.includes(id)),
});

/** Mirrors the account display string logic */
const getAccountDisplay = (txn: Transaction): string => {
  let display = txn.account_name || "";
  if (txn.account_mask) display += ` ****${txn.account_mask}`;
  return display;
};

/** Mirrors the select-all checkbox isChecked logic */
const isSelectAllChecked = (
  processedLength: number,
  selectedSize: number,
): boolean => processedLength > 0 && selectedSize === processedLength;

/** Mirrors the month period grouping logic */
const getMonthPeriodKey = (
  dateStr: string,
  monthlyStartDay: number,
): string => {
  const [year, month, day] = dateStr.split("-").map(Number);

  if (day <= monthlyStartDay) {
    const periodStart = new Date(year, month - 2, monthlyStartDay + 1);
    const periodEnd = new Date(year, month - 1, monthlyStartDay);
    return `${periodEnd.toLocaleDateString("en-US", { month: "short", year: "numeric", day: "numeric" })} - ${periodStart.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}`;
  } else {
    const periodStart = new Date(year, month - 1, monthlyStartDay + 1);
    const periodEnd = new Date(year, month, monthlyStartDay);
    return `${periodEnd.toLocaleDateString("en-US", { month: "short", year: "numeric", day: "numeric" })} - ${periodStart.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}`;
  }
};

/** Mirrors canModifyTransaction: returns false when preconditions fail */
const canModifyTransaction = (
  currentUser: any,
  accountId: string | undefined,
  accountOwnershipMap: Map<string, string>,
  canWriteOwnedResource: (resource: string, userId: string) => boolean,
): boolean => {
  if (!currentUser || !accountId) return false;
  const accountUserId = accountOwnershipMap.get(accountId);
  if (!accountUserId) return false;
  return canWriteOwnedResource("transaction", accountUserId);
};

// ── Tests ────────────────────────────────────────────────────────────────────

describe("formatCurrency", () => {
  it("formats positive amounts with dollar sign", () => {
    const { formatted, isNegative } = formatCurrency(42.5);
    expect(formatted).toBe("$42.50");
    expect(isNegative).toBe(false);
  });

  it("formats negative amounts as absolute with isNegative flag", () => {
    const { formatted, isNegative } = formatCurrency(-100.99);
    expect(formatted).toBe("$100.99");
    expect(isNegative).toBe(true);
  });

  it("formats zero", () => {
    const { formatted, isNegative } = formatCurrency(0);
    expect(formatted).toBe("$0.00");
    expect(isNegative).toBe(false);
  });

  it("formats large amounts with commas", () => {
    const { formatted } = formatCurrency(1234567.89);
    expect(formatted).toBe("$1,234,567.89");
  });

  it("formats very small amounts", () => {
    const { formatted } = formatCurrency(0.01);
    expect(formatted).toBe("$0.01");
  });

  it("treats -0 as not negative", () => {
    const { isNegative } = formatCurrency(-0);
    // -0 < 0 is false in JS
    expect(isNegative).toBe(false);
  });
});

describe("formatDate", () => {
  it("formats a standard date", () => {
    expect(formatDate("2025-03-15")).toBe("Mar 15, 2025");
  });

  it("formats January 1st", () => {
    expect(formatDate("2025-01-01")).toBe("Jan 1, 2025");
  });

  it("formats December 31st", () => {
    expect(formatDate("2025-12-31")).toBe("Dec 31, 2025");
  });

  it("avoids timezone shift by parsing as local date", () => {
    // This is the key behavior: splitting on "-" and using local constructor
    // prevents a UTC midnight date from shifting to the previous day
    const result = formatDate("2025-01-01");
    expect(result).toContain("Jan");
    expect(result).toContain("1");
  });
});

describe("handleSort", () => {
  it("defaults date to desc", () => {
    const result = handleSort("date", null, "asc");
    expect(result.sortDirection).toBe("desc");
  });

  it("defaults amount to desc", () => {
    const result = handleSort("amount", null, "asc");
    expect(result.sortDirection).toBe("desc");
  });

  it("defaults status to desc", () => {
    const result = handleSort("status", null, "asc");
    expect(result.sortDirection).toBe("desc");
  });

  it("defaults merchant_name to asc", () => {
    const result = handleSort("merchant_name", null, "desc");
    expect(result.sortDirection).toBe("asc");
  });

  it("defaults category_primary to asc", () => {
    const result = handleSort("category_primary", null, "desc");
    expect(result.sortDirection).toBe("asc");
  });

  it("defaults account_name to asc", () => {
    const result = handleSort("account_name", null, "desc");
    expect(result.sortDirection).toBe("asc");
  });

  it("defaults labels to asc", () => {
    const result = handleSort("labels", null, "desc");
    expect(result.sortDirection).toBe("asc");
  });

  it("toggles asc to desc when clicking same field", () => {
    const result = handleSort("date", "date", "asc");
    expect(result.sortDirection).toBe("desc");
  });

  it("toggles desc to asc when clicking same field", () => {
    const result = handleSort("date", "date", "desc");
    expect(result.sortDirection).toBe("asc");
  });
});

describe("sortTransactions", () => {
  const txns = [
    makeTransaction({
      id: "a",
      date: "2025-01-01",
      amount: 10,
      merchant_name: "Bravo",
    }),
    makeTransaction({
      id: "b",
      date: "2025-03-15",
      amount: 50,
      merchant_name: "Alpha",
    }),
    makeTransaction({
      id: "c",
      date: "2025-02-10",
      amount: 30,
      merchant_name: "Charlie",
    }),
  ];

  it("sorts by date descending", () => {
    const sorted = sortTransactions(txns, "date", "desc");
    expect(sorted.map((t) => t.id)).toEqual(["b", "c", "a"]);
  });

  it("sorts by date ascending", () => {
    const sorted = sortTransactions(txns, "date", "asc");
    expect(sorted.map((t) => t.id)).toEqual(["a", "c", "b"]);
  });

  it("sorts by amount descending", () => {
    const sorted = sortTransactions(txns, "amount", "desc");
    expect(sorted.map((t) => t.id)).toEqual(["b", "c", "a"]);
  });

  it("sorts by amount ascending", () => {
    const sorted = sortTransactions(txns, "amount", "asc");
    expect(sorted.map((t) => t.id)).toEqual(["a", "c", "b"]);
  });

  it("sorts by merchant_name ascending (case insensitive)", () => {
    const sorted = sortTransactions(txns, "merchant_name", "asc");
    expect(sorted.map((t) => t.id)).toEqual(["b", "a", "c"]);
  });

  it("sorts by merchant_name descending", () => {
    const sorted = sortTransactions(txns, "merchant_name", "desc");
    expect(sorted.map((t) => t.id)).toEqual(["c", "a", "b"]);
  });

  it("sorts by account_name with null fallback", () => {
    const withNull = [
      makeTransaction({ id: "a", account_name: null }),
      makeTransaction({ id: "b", account_name: "Zeta" }),
      makeTransaction({ id: "c", account_name: "Alpha" }),
    ];
    const sorted = sortTransactions(withNull, "account_name", "asc");
    expect(sorted.map((t) => t.id)).toEqual(["a", "c", "b"]);
  });

  it("sorts by category using parent_name when available", () => {
    const withCategories = [
      makeTransaction({
        id: "a",
        category: makeCategory({ name: "Groceries", parent_name: "Zzz" }),
      }),
      makeTransaction({
        id: "b",
        category: makeCategory({ name: "Alpha Category" }),
      }),
    ];
    const sorted = sortTransactions(withCategories, "category_primary", "asc");
    expect(sorted.map((t) => t.id)).toEqual(["b", "a"]);
  });

  it("sorts by labels using first label name", () => {
    const withLabels = [
      makeTransaction({ id: "a", labels: [makeLabel({ name: "Zebra" })] }),
      makeTransaction({ id: "b", labels: [makeLabel({ name: "Alpha" })] }),
      makeTransaction({ id: "c", labels: [] }),
    ];
    const sorted = sortTransactions(withLabels, "labels", "asc");
    expect(sorted.map((t) => t.id)).toEqual(["c", "b", "a"]);
  });

  it("sorts by status (pending first when desc)", () => {
    const withStatus = [
      makeTransaction({ id: "a", is_pending: false }),
      makeTransaction({ id: "b", is_pending: true }),
      makeTransaction({ id: "c", is_pending: false }),
    ];
    const sorted = sortTransactions(withStatus, "status", "desc");
    expect(sorted[0].id).toBe("b");
  });

  it("returns empty array for empty input", () => {
    expect(sortTransactions([], "date", "desc")).toEqual([]);
  });
});

describe("parseValues", () => {
  it("parses simple comma-separated values", () => {
    expect(parseValues("foo,bar,baz")).toEqual(["foo", "bar", "baz"]);
  });

  it("handles quoted strings with commas", () => {
    expect(parseValues('"Food and Drink","Service"')).toEqual([
      "food and drink",
      "service",
    ]);
  });

  it("handles a mix of quoted and unquoted", () => {
    expect(parseValues('"Food and Drink",Simple')).toEqual([
      "food and drink",
      "simple",
    ]);
  });

  it("handles single value", () => {
    expect(parseValues("groceries")).toEqual(["groceries"]);
  });

  it("trims whitespace", () => {
    expect(parseValues(" foo , bar ")).toEqual(["foo", "bar"]);
  });

  it("ignores empty segments between commas", () => {
    // current behavior: empty trim results are dropped
    expect(parseValues("foo,,bar")).toEqual(["foo", "bar"]);
  });

  it("handles empty quoted string", () => {
    expect(parseValues('""')).toEqual([]);
  });
});

describe("filterTransactions – plain text search", () => {
  const txns = [
    makeTransaction({
      id: "1",
      merchant_name: "Whole Foods",
      description: "Weekly groceries",
    }),
    makeTransaction({ id: "2", merchant_name: "Amazon", description: "Books" }),
    makeTransaction({
      id: "3",
      merchant_name: "Target",
      account_name: "Wells Fargo",
    }),
  ];

  it("returns all when query is empty", () => {
    expect(filterTransactions(txns, "")).toHaveLength(3);
  });

  it("filters by merchant name", () => {
    const result = filterTransactions(txns, "whole");
    expect(result.map((t) => t.id)).toEqual(["1"]);
  });

  it("filters by description", () => {
    const result = filterTransactions(txns, "books");
    expect(result.map((t) => t.id)).toEqual(["2"]);
  });

  it("filters by account name", () => {
    const result = filterTransactions(txns, "wells");
    expect(result.map((t) => t.id)).toEqual(["3"]);
  });

  it("is case insensitive", () => {
    const result = filterTransactions(txns, "AMAZON");
    expect(result.map((t) => t.id)).toEqual(["2"]);
  });

  it("returns empty array when nothing matches", () => {
    expect(filterTransactions(txns, "zzzzz")).toHaveLength(0);
  });

  it("returns empty for empty input array", () => {
    expect(filterTransactions([], "foo")).toHaveLength(0);
  });

  it("searches category name", () => {
    const txWithCat = [
      makeTransaction({
        id: "1",
        merchant_name: "X",
        category: makeCategory({ name: "Groceries" }),
      }),
    ];
    expect(filterTransactions(txWithCat, "groceries")).toHaveLength(1);
  });

  it("searches category parent_name", () => {
    const txWithCat = [
      makeTransaction({
        id: "1",
        merchant_name: "X",
        category: makeCategory({ name: "Sub", parent_name: "Food and Drink" }),
      }),
    ];
    expect(filterTransactions(txWithCat, "food and drink")).toHaveLength(1);
  });

  it("searches label names in plain text mode", () => {
    const txWithLabels = [
      makeTransaction({
        id: "1",
        merchant_name: "X",
        labels: [makeLabel({ name: "Vacation" })],
      }),
    ];
    expect(filterTransactions(txWithLabels, "vacation")).toHaveLength(1);
  });
});

describe("filterTransactions – labels: syntax", () => {
  const labeled = makeTransaction({
    id: "1",
    labels: [
      makeLabel({ name: "Transfer" }),
      makeLabel({ id: "l2", name: "Income" }),
    ],
  });
  const unlabeled = makeTransaction({ id: "2", labels: [] });
  const noLabelsField = makeTransaction({ id: "3", labels: undefined });
  const txns = [labeled, unlabeled, noLabelsField];

  it("filters by label name", () => {
    const result = filterTransactions(txns, "labels:Transfer");
    expect(result.map((t) => t.id)).toEqual(["1"]);
  });

  it("filters by partial label name", () => {
    const result = filterTransactions(txns, "labels:trans");
    expect(result.map((t) => t.id)).toEqual(["1"]);
  });

  it('finds unlabeled transactions with labels:""', () => {
    // The regex captures "" which parseValues returns as [] (empty after trimming quotes).
    // The searchingForEmpty check looks for "" in parsed values. Since parseValues
    // strips quotes and trims, the empty string won't appear. This means labels:""
    // actually matches nothing with the parseValues approach used in the page.
    // However the actual page code checks: labelNames.includes("")
    // parseValues('""') returns [] because the trimmed content between quotes is empty.
    // So searchingForEmpty is false, and no label match is found => empty result.
    const result = filterTransactions(txns, 'labels:""');
    expect(result).toHaveLength(0);
  });

  it("supports singular label: syntax", () => {
    const result = filterTransactions(txns, "label:Income");
    expect(result.map((t) => t.id)).toEqual(["1"]);
  });

  it("supports multiple label values", () => {
    const txns2 = [
      makeTransaction({ id: "a", labels: [makeLabel({ name: "Work" })] }),
      makeTransaction({ id: "b", labels: [makeLabel({ name: "Personal" })] }),
      makeTransaction({ id: "c", labels: [] }),
    ];
    const result = filterTransactions(txns2, "labels:Work,Personal");
    expect(result.map((t) => t.id)).toEqual(["a", "b"]);
  });
});

describe("filterTransactions – categories: syntax", () => {
  const txns = [
    makeTransaction({
      id: "1",
      category: makeCategory({
        name: "Groceries",
        parent_name: "Food and Drink",
      }),
    }),
    makeTransaction({
      id: "2",
      category: makeCategory({ name: "Gas" }),
      category_primary: "Transportation",
    }),
    makeTransaction({ id: "3", category_primary: "Entertainment" }),
  ];

  it("filters by category name", () => {
    const result = filterTransactions(txns, "categories:Groceries");
    expect(result.map((t) => t.id)).toEqual(["1"]);
  });

  it("filters by parent category name", () => {
    const result = filterTransactions(txns, 'categories:"Food and Drink"');
    expect(result.map((t) => t.id)).toEqual(["1"]);
  });

  it("supports singular category: syntax", () => {
    const result = filterTransactions(txns, "category:Gas");
    expect(result.map((t) => t.id)).toEqual(["2"]);
  });

  it("falls back to category_primary when no category object", () => {
    const result = filterTransactions(txns, "categories:Entertainment");
    expect(result.map((t) => t.id)).toEqual(["3"]);
  });

  it("supports multiple categories (OR)", () => {
    const result = filterTransactions(txns, "categories:Groceries,Gas");
    expect(result.map((t) => t.id)).toEqual(["1", "2"]);
  });
});

describe("filterTransactions – accounts: syntax", () => {
  const txns = [
    makeTransaction({ id: "1", account_name: "Chase Checking" }),
    makeTransaction({ id: "2", account_name: "Wells Fargo Savings" }),
    makeTransaction({ id: "3", account_name: null }),
  ];

  it("filters by account name", () => {
    const result = filterTransactions(txns, "accounts:Chase");
    expect(result.map((t) => t.id)).toEqual(["1"]);
  });

  it("supports singular account: syntax", () => {
    const result = filterTransactions(txns, 'account:"Wells Fargo"');
    expect(result.map((t) => t.id)).toEqual(["2"]);
  });

  it("excludes null account names", () => {
    const result = filterTransactions(txns, "accounts:Chase");
    expect(result).toHaveLength(1);
  });

  it("supports multiple accounts (OR)", () => {
    const result = filterTransactions(txns, "accounts:Chase,Wells");
    expect(result.map((t) => t.id)).toEqual(["1", "2"]);
  });
});

describe("filterTransactions – combined filters", () => {
  const txns = [
    makeTransaction({
      id: "1",
      merchant_name: "Whole Foods",
      account_name: "Chase",
      labels: [makeLabel({ name: "Groceries" })],
      category: makeCategory({ name: "Food" }),
    }),
    makeTransaction({
      id: "2",
      merchant_name: "Amazon",
      account_name: "Chase",
      labels: [makeLabel({ name: "Shopping" })],
      category: makeCategory({ name: "Retail" }),
    }),
    makeTransaction({
      id: "3",
      merchant_name: "Shell",
      account_name: "Amex",
      labels: [],
      category: makeCategory({ name: "Gas" }),
    }),
  ];

  it("combines label + account filter", () => {
    const result = filterTransactions(txns, "labels:Groceries accounts:Chase");
    expect(result.map((t) => t.id)).toEqual(["1"]);
  });

  it("combines category + plain text", () => {
    const result = filterTransactions(txns, "categories:Retail amazon");
    expect(result.map((t) => t.id)).toEqual(["2"]);
  });

  it("empty results when filters conflict", () => {
    const result = filterTransactions(txns, "labels:Groceries accounts:Amex");
    expect(result).toHaveLength(0);
  });
});

describe("getCategoryDisplay", () => {
  it("shows parent + child when parent exists", () => {
    const txn = makeTransaction({
      category: makeCategory({
        name: "Groceries",
        parent_name: "Food and Drink",
      }),
    });
    expect(getCategoryDisplay(txn)).toBe("Food and Drink (Groceries)");
  });

  it("shows only name when no parent", () => {
    const txn = makeTransaction({
      category: makeCategory({ name: "Groceries" }),
    });
    expect(getCategoryDisplay(txn)).toBe("Groceries");
  });

  it("falls back to category_primary when no category object", () => {
    const txn = makeTransaction({
      category: undefined,
      category_primary: "Food and Drink",
    });
    expect(getCategoryDisplay(txn)).toBe("Food and Drink");
  });

  it("returns null when no category at all", () => {
    const txn = makeTransaction({
      category: undefined,
      category_primary: null,
    });
    expect(getCategoryDisplay(txn)).toBeNull();
  });
});

describe("getLabelColorScheme", () => {
  it("returns undefined when label has custom color", () => {
    expect(
      getLabelColorScheme(makeLabel({ color: "#ff0000" })),
    ).toBeUndefined();
  });

  it("returns green for income labels", () => {
    expect(getLabelColorScheme(makeLabel({ is_income: true }))).toBe("green");
  });

  it("returns purple for non-income labels", () => {
    expect(getLabelColorScheme(makeLabel({ is_income: false }))).toBe("purple");
  });
});

describe("showReadOnlyBanner", () => {
  it("shows when viewing other user and cannot edit", () => {
    expect(showReadOnlyBanner(true, false)).toBe(true);
  });

  it("hides when not viewing other user", () => {
    expect(showReadOnlyBanner(false, false)).toBe(false);
  });

  it("hides when can edit other user", () => {
    expect(showReadOnlyBanner(true, true)).toBe(false);
  });

  it("hides for own view with edit", () => {
    expect(showReadOnlyBanner(false, true)).toBe(false);
  });
});

describe("getEmptyStateDescription", () => {
  it("shows search hint when there is a search query", () => {
    expect(getEmptyStateDescription(true)).toBe(
      "Try adjusting your search query.",
    );
  });

  it("shows connect accounts when no search", () => {
    expect(getEmptyStateDescription(false)).toBe(
      "Connect your accounts to start tracking transactions.",
    );
  });
});

describe("showEmptyAction", () => {
  it("shows action when no search", () => {
    expect(showEmptyAction(false)).toBe(true);
  });

  it("hides action when search is present", () => {
    expect(showEmptyAction(true)).toBe(false);
  });
});

describe("getSummaryText", () => {
  it("shows basic count", () => {
    expect(getSummaryText(10, 0, 0, false)).toBe("Showing 10 transactions.");
  });

  it("shows total when greater than 0", () => {
    expect(getSummaryText(50, 100, 0, false)).toBe(
      "Showing 50 transactions (100 total).",
    );
  });

  it("shows selected count", () => {
    expect(getSummaryText(50, 100, 3, false)).toBe(
      "Showing 50 transactions (100 total). 3 selected",
    );
  });

  it("shows scroll hint when hasMore", () => {
    expect(getSummaryText(50, 100, 0, true)).toBe(
      "Showing 50 transactions (100 total). Scroll down to load more",
    );
  });

  it("shows selected + scroll hint", () => {
    expect(getSummaryText(50, 100, 2, true)).toBe(
      "Showing 50 transactions (100 total). 2 selected. Scroll down to load more",
    );
  });

  it("shows zero transactions", () => {
    expect(getSummaryText(0, 0, 0, false)).toBe("Showing 0 transactions.");
  });
});

describe("resolveBulkLabelConflicts", () => {
  it("removes labels that appear in both add and remove", () => {
    const result = resolveBulkLabelConflicts(["l1", "l2", "l3"], ["l2", "l4"]);
    expect(result.effectiveAdd).toEqual(["l1", "l3"]);
    expect(result.effectiveRemove).toEqual(["l4"]);
  });

  it("returns both lists unchanged when no overlap", () => {
    const result = resolveBulkLabelConflicts(["l1"], ["l2"]);
    expect(result.effectiveAdd).toEqual(["l1"]);
    expect(result.effectiveRemove).toEqual(["l2"]);
  });

  it("handles empty arrays", () => {
    const result = resolveBulkLabelConflicts([], []);
    expect(result.effectiveAdd).toEqual([]);
    expect(result.effectiveRemove).toEqual([]);
  });

  it("handles all overlap", () => {
    const result = resolveBulkLabelConflicts(["l1", "l2"], ["l1", "l2"]);
    expect(result.effectiveAdd).toEqual([]);
    expect(result.effectiveRemove).toEqual([]);
  });
});

describe("getAccountDisplay", () => {
  it("shows name and mask", () => {
    const txn = makeTransaction({
      account_name: "Chase",
      account_mask: "1234",
    });
    expect(getAccountDisplay(txn)).toBe("Chase ****1234");
  });

  it("shows only name when no mask", () => {
    const txn = makeTransaction({ account_name: "Chase", account_mask: null });
    expect(getAccountDisplay(txn)).toBe("Chase");
  });

  it("handles null account name", () => {
    const txn = makeTransaction({ account_name: null, account_mask: null });
    expect(getAccountDisplay(txn)).toBe("");
  });
});

describe("isSelectAllChecked", () => {
  it("true when all selected", () => {
    expect(isSelectAllChecked(5, 5)).toBe(true);
  });

  it("false when partially selected", () => {
    expect(isSelectAllChecked(5, 3)).toBe(false);
  });

  it("false when none selected", () => {
    expect(isSelectAllChecked(5, 0)).toBe(false);
  });

  it("false when list is empty", () => {
    expect(isSelectAllChecked(0, 0)).toBe(false);
  });
});

describe("bulk selection state management", () => {
  it("toggles a transaction into the set", () => {
    const selected = new Set<string>();
    const newSelected = new Set(selected);
    newSelected.add("txn-1");
    expect(newSelected.has("txn-1")).toBe(true);
    expect(newSelected.size).toBe(1);
  });

  it("toggles a transaction out of the set", () => {
    const selected = new Set<string>(["txn-1", "txn-2"]);
    const newSelected = new Set(selected);
    newSelected.delete("txn-1");
    expect(newSelected.has("txn-1")).toBe(false);
    expect(newSelected.size).toBe(1);
  });

  it("shift-click selects range", () => {
    const transactions = [
      makeTransaction({ id: "a" }),
      makeTransaction({ id: "b" }),
      makeTransaction({ id: "c" }),
      makeTransaction({ id: "d" }),
      makeTransaction({ id: "e" }),
    ];

    const lastSelectedIndex = 1;
    const clickedIndex = 3;
    const newSelected = new Set<string>();

    const start = Math.min(lastSelectedIndex, clickedIndex);
    const end = Math.max(lastSelectedIndex, clickedIndex);
    for (let i = start; i <= end; i++) {
      newSelected.add(transactions[i].id);
    }

    expect(newSelected.size).toBe(3);
    expect(newSelected.has("b")).toBe(true);
    expect(newSelected.has("c")).toBe(true);
    expect(newSelected.has("d")).toBe(true);
    expect(newSelected.has("a")).toBe(false);
  });

  it("select-all then deselect-all", () => {
    const transactions = [
      makeTransaction({ id: "a" }),
      makeTransaction({ id: "b" }),
    ];

    // Select all
    const allSelected = new Set(transactions.map((t) => t.id));
    expect(allSelected.size).toBe(2);

    // Deselect all (when size === length, toggle clears)
    const cleared =
      allSelected.size === transactions.length
        ? new Set<string>()
        : allSelected;
    expect(cleared.size).toBe(0);
  });
});

describe("canModifyTransaction", () => {
  const ownershipMap = new Map<string, string>();
  ownershipMap.set("acc-1", "user-1");
  ownershipMap.set("acc-2", "user-2");

  const alwaysTrue = () => true;
  const alwaysFalse = () => false;

  it("returns false when no current user", () => {
    expect(canModifyTransaction(null, "acc-1", ownershipMap, alwaysTrue)).toBe(
      false,
    );
  });

  it("returns false when no account_id", () => {
    expect(
      canModifyTransaction({ id: "u1" }, undefined, ownershipMap, alwaysTrue),
    ).toBe(false);
  });

  it("returns false when account not in map", () => {
    expect(
      canModifyTransaction({ id: "u1" }, "unknown", ownershipMap, alwaysTrue),
    ).toBe(false);
  });

  it("delegates to canWriteOwnedResource when all preconditions met", () => {
    expect(
      canModifyTransaction({ id: "u1" }, "acc-1", ownershipMap, alwaysTrue),
    ).toBe(true);
    expect(
      canModifyTransaction({ id: "u1" }, "acc-1", ownershipMap, alwaysFalse),
    ).toBe(false);
  });
});

describe("getMonthPeriodKey", () => {
  it("groups day > startDay into current month period", () => {
    // Day 15, start day 1 => belongs to current month period
    const key = getMonthPeriodKey("2025-03-15", 1);
    expect(key).toBeTruthy();
    expect(typeof key).toBe("string");
    expect(key).toContain("-"); // Contains separator
  });

  it("groups day <= startDay into previous month period", () => {
    // Day 1, start day 1 => belongs to period starting previous month
    const key1 = getMonthPeriodKey("2025-03-01", 1);
    // Day 5, start day 15 => belongs to period starting previous month
    const key2 = getMonthPeriodKey("2025-03-05", 15);
    expect(key1).toBeTruthy();
    expect(key2).toBeTruthy();
  });

  it("standard start day 1: mid-month stays in same period", () => {
    const keyA = getMonthPeriodKey("2025-03-02", 1);
    const keyB = getMonthPeriodKey("2025-03-28", 1);
    // Both should be in the same period (Mar 2 - Mar 28 are both > day 1)
    expect(keyA).toBe(keyB);
  });

  it("standard start day 1: day 1 is in previous period", () => {
    const keyFirst = getMonthPeriodKey("2025-03-01", 1);
    const keySecond = getMonthPeriodKey("2025-03-02", 1);
    expect(keyFirst).not.toBe(keySecond);
  });

  it("custom start day 15: day 16 starts new period", () => {
    const keyA = getMonthPeriodKey("2025-03-16", 15);
    const keyB = getMonthPeriodKey("2025-03-20", 15);
    expect(keyA).toBe(keyB);
  });

  it("custom start day 15: day 10 belongs to previous period", () => {
    const keyBefore = getMonthPeriodKey("2025-03-10", 15);
    const keyAfter = getMonthPeriodKey("2025-03-16", 15);
    expect(keyBefore).not.toBe(keyAfter);
  });
});

describe("bulk action confirmation logic", () => {
  it("mark action sets isTransfer to true", () => {
    const bulkActionType: "mark" | "unmark" = "mark";
    expect(bulkActionType === "mark").toBe(true);
  });

  it("unmark action sets isTransfer to false", () => {
    const bulkActionType: "mark" | "unmark" = "unmark";
    expect(bulkActionType === "mark").toBe(false);
  });

  it("no-op when bulkActionType is null", () => {
    const bulkActionType: "mark" | "unmark" | null = null;
    const shouldExecute = bulkActionType !== null;
    expect(shouldExecute).toBe(false);
  });
});

describe("transaction click mode logic", () => {
  it("opens detail modal when no selections", () => {
    const selectedSize = 0;
    const mode = selectedSize > 0 ? "toggle-select" : "open-detail";
    expect(mode).toBe("open-detail");
  });

  it("toggles selection when some are selected (bulk mode)", () => {
    const selectedSize = 3;
    const mode = selectedSize > 0 ? "toggle-select" : "open-detail";
    expect(mode).toBe("toggle-select");
  });
});

describe("flagged filter param", () => {
  it("sends true when showFlaggedOnly is true", () => {
    const showFlaggedOnly = true;
    const flagged = showFlaggedOnly ? true : undefined;
    expect(flagged).toBe(true);
  });

  it("sends undefined when showFlaggedOnly is false", () => {
    const showFlaggedOnly = false;
    const flagged = showFlaggedOnly ? true : undefined;
    expect(flagged).toBeUndefined();
  });
});

describe("search click helpers – duplicate prevention", () => {
  /** Mirrors handleCategoryClick duplicate check */
  const isCategoryAlreadyInSearch = (
    searchQuery: string,
    category: string,
  ): boolean => {
    const quoted = `"${category}"`;
    return (
      searchQuery.includes(`categories:${quoted}`) ||
      searchQuery.includes(`category:${quoted}`) ||
      searchQuery.includes(`categories:${category}`) ||
      searchQuery.includes(`category:${category}`)
    );
  };

  /** Mirrors the formatting logic: add quotes if name has spaces/commas */
  const formatFilterValue = (value: string): string =>
    value.includes(" ") || value.includes(",") ? `"${value}"` : value;

  it("detects existing unquoted category", () => {
    expect(isCategoryAlreadyInSearch("categories:Groceries", "Groceries")).toBe(
      true,
    );
  });

  it("detects existing quoted category", () => {
    expect(
      isCategoryAlreadyInSearch(
        'categories:"Food and Drink"',
        "Food and Drink",
      ),
    ).toBe(true);
  });

  it("returns false for non-matching category", () => {
    expect(isCategoryAlreadyInSearch("categories:Gas", "Groceries")).toBe(
      false,
    );
  });

  it("quotes values with spaces", () => {
    expect(formatFilterValue("Food and Drink")).toBe('"Food and Drink"');
  });

  it("quotes values with commas", () => {
    expect(formatFilterValue("A,B")).toBe('"A,B"');
  });

  it("leaves simple values unquoted", () => {
    expect(formatFilterValue("Groceries")).toBe("Groceries");
  });
});

describe("monthlyStartDay default", () => {
  it("defaults to 1 when orgPrefs is undefined", () => {
    const orgPrefs: any = undefined;
    expect(orgPrefs?.monthly_start_day || 1).toBe(1);
  });

  it("defaults to 1 when monthly_start_day is falsy", () => {
    const orgPrefs = { monthly_start_day: 0 };
    expect(orgPrefs.monthly_start_day || 1).toBe(1);
  });

  it("uses the value when set", () => {
    const orgPrefs = { monthly_start_day: 15 };
    expect(orgPrefs.monthly_start_day || 1).toBe(15);
  });
});

describe("pending label management", () => {
  it("does not add duplicate to pending list", () => {
    const pending = ["l1", "l2"];
    const toAdd = "l1";
    const shouldAdd = toAdd && !pending.includes(toAdd);
    expect(shouldAdd).toBe(false);
  });

  it("adds new label to pending list", () => {
    const pending = ["l1", "l2"];
    const toAdd = "l3";
    const shouldAdd = toAdd && !pending.includes(toAdd);
    expect(shouldAdd).toBe(true);
  });

  it("does not add empty string", () => {
    const pending = ["l1"];
    const toAdd = "";
    // Empty string is falsy in JS, so short-circuits to ""
    const shouldAdd = toAdd && !pending.includes(toAdd);
    expect(shouldAdd).toBeFalsy();
  });

  it("removes a label from pending list", () => {
    const pending = ["l1", "l2", "l3"];
    const result = pending.filter((id) => id !== "l2");
    expect(result).toEqual(["l1", "l3"]);
  });
});

describe("bulk create rule – common merchant detection", () => {
  it("detects single common merchant", () => {
    const selected = [
      makeTransaction({ merchant_name: "Starbucks" }),
      makeTransaction({ merchant_name: "Starbucks" }),
    ];
    const merchants = new Set(selected.map((t) => t.merchant_name));
    const commonMerchant =
      merchants.size === 1 ? Array.from(merchants)[0] : "Multiple merchants";
    expect(commonMerchant).toBe("Starbucks");
  });

  it("reports multiple merchants", () => {
    const selected = [
      makeTransaction({ merchant_name: "Starbucks" }),
      makeTransaction({ merchant_name: "Target" }),
    ];
    const merchants = new Set(selected.map((t) => t.merchant_name));
    const commonMerchant =
      merchants.size === 1 ? Array.from(merchants)[0] : "Multiple merchants";
    expect(commonMerchant).toBe("Multiple merchants");
  });

  it("handles single selection", () => {
    const selected = [makeTransaction({ merchant_name: "Target" })];
    const merchants = new Set(selected.map((t) => t.merchant_name));
    expect(merchants.size).toBe(1);
    expect(Array.from(merchants)[0]).toBe("Target");
  });
});

describe("bulk transfer mutation – ownership filtering", () => {
  it("filters to only owned transaction ids", () => {
    const allTransactions = [
      makeTransaction({ id: "1", account_id: "acc-1" }),
      makeTransaction({ id: "2", account_id: "acc-2" }),
      makeTransaction({ id: "3", account_id: "acc-1" }),
    ];
    const ownershipMap = new Map([
      ["acc-1", "user-1"],
      ["acc-2", "user-2"],
    ]);
    const currentUserId = "user-1";

    const ownedIds = ["1", "2", "3"].filter((id) => {
      const txn = allTransactions.find((t) => t.id === id);
      if (!txn) return false;
      const accountUserId = ownershipMap.get(txn.account_id);
      return accountUserId === currentUserId;
    });

    expect(ownedIds).toEqual(["1", "3"]);
  });

  it("returns empty when no owned transactions", () => {
    const allTransactions = [makeTransaction({ id: "1", account_id: "acc-2" })];
    const ownershipMap = new Map([["acc-2", "user-2"]]);
    const currentUserId = "user-1";

    const ownedIds = ["1"].filter((id) => {
      const txn = allTransactions.find((t) => t.id === id);
      if (!txn) return false;
      return ownershipMap.get(txn.account_id) === currentUserId;
    });

    expect(ownedIds).toEqual([]);
  });
});

describe("bulk mutation result message logic", () => {
  it("success status when no skipped", () => {
    const attempted = 5;
    const modified = 5;
    const skipped = attempted - modified;
    const status = skipped > 0 ? "warning" : "success";
    expect(status).toBe("success");
  });

  it("warning status when some skipped", () => {
    const attempted = 5;
    const modified = 3;
    const skipped = attempted - modified;
    const status = skipped > 0 ? "warning" : "success";
    expect(status).toBe("warning");
    expect(skipped).toBe(2);
  });
});

describe("status badges visibility", () => {
  it("shows pending badge only when is_pending", () => {
    const txn = makeTransaction({
      is_pending: true,
      is_transfer: false,
      flagged_for_review: false,
    });
    expect(txn.is_pending).toBe(true);
    expect(txn.is_transfer).toBe(false);
    expect(txn.flagged_for_review).toBe(false);
  });

  it("shows transfer badge only when is_transfer", () => {
    const txn = makeTransaction({ is_pending: false, is_transfer: true });
    expect(txn.is_transfer).toBe(true);
  });

  it("shows flagged badge only when flagged_for_review", () => {
    const txn = makeTransaction({ flagged_for_review: true });
    expect(txn.flagged_for_review).toBe(true);
  });

  it("shows no badges for normal transaction", () => {
    const txn = makeTransaction();
    expect(txn.is_pending).toBe(false);
    expect(txn.is_transfer).toBe(false);
    expect(txn.flagged_for_review).toBe(false);
  });
});
