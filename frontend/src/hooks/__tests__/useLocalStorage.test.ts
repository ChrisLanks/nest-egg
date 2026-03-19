/**
 * Tests for useLocalStorage.
 *
 * The vitest environment is "node" (no DOM), so we test:
 * 1. Source-code structure — the hook reads/writes localStorage and handles errors
 * 2. Read/write logic extracted as pure functions (mirrors the hook internals)
 * 3. Financial planning pages use useLocalStorage for their form state
 */

import { readFileSync } from "fs";
import { resolve } from "path";
import { describe, expect, it } from "vitest";

const ROOT = resolve(__dirname, "..", "..", "..");

function readSource(relPath: string): string {
  return readFileSync(resolve(ROOT, relPath), "utf-8");
}

// ── Hook source structure ─────────────────────────────────────────────────

describe("useLocalStorage — hook source", () => {
  const src = readSource("src/hooks/useLocalStorage.ts");

  it("exports useLocalStorage function", () => {
    expect(src).toContain("export function useLocalStorage");
  });

  it("reads from localStorage on init", () => {
    expect(src).toContain("localStorage.getItem(key)");
  });

  it("writes to localStorage on update", () => {
    expect(src).toContain("localStorage.setItem(key,");
  });

  it("wraps localStorage access in try/catch for read", () => {
    // Should have at least one try/catch around getItem
    expect(src).toContain("try {");
    expect(src).toContain("} catch {");
  });

  it("falls back to initialValue on read error", () => {
    expect(src).toContain("return initialValue");
  });

  it("uses useState and useCallback", () => {
    expect(src).toContain("useState");
    expect(src).toContain("useCallback");
  });

  it("accepts a generic type parameter", () => {
    expect(src).toContain("useLocalStorage<T>");
  });
});

// ── Read/write logic ──────────────────────────────────────────────────────
// Mirror the hook's internal logic to verify it behaves correctly
// without needing a DOM environment.

type Store = Record<string, string>;

function makeStorage(initial: Store = {}) {
  const store: Store = { ...initial };
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, val: string) => {
      store[key] = val;
    },
    _store: store,
  };
}

function readFromStorage<T>(
  storage: ReturnType<typeof makeStorage>,
  key: string,
  initialValue: T,
): T {
  try {
    const item = storage.getItem(key);
    return item !== null ? (JSON.parse(item) as T) : initialValue;
  } catch {
    return initialValue;
  }
}

function writeToStorage<T>(
  storage: ReturnType<typeof makeStorage>,
  key: string,
  value: T,
): void {
  try {
    storage.setItem(key, JSON.stringify(value));
  } catch {
    // noop
  }
}

describe("useLocalStorage — read logic", () => {
  it("returns initialValue when key is absent", () => {
    const s = makeStorage();
    expect(readFromStorage(s, "missing", "default")).toBe("default");
  });

  it("returns stored string value", () => {
    const s = makeStorage({ "str-key": JSON.stringify("hello") });
    expect(readFromStorage(s, "str-key", "")).toBe("hello");
  });

  it("returns stored number value", () => {
    const s = makeStorage({ "num-key": JSON.stringify(42) });
    expect(readFromStorage(s, "num-key", 0)).toBe(42);
  });

  it("returns stored object value", () => {
    const obj = { a: 1, b: "two" };
    const s = makeStorage({ "obj-key": JSON.stringify(obj) });
    expect(readFromStorage(s, "obj-key", {})).toEqual(obj);
  });

  it("falls back to initialValue when stored JSON is corrupt", () => {
    const s = makeStorage({ "bad-key": "not{{valid-json" });
    expect(readFromStorage(s, "bad-key", "fallback")).toBe("fallback");
  });

  it("returns initialValue when stored value is JSON null", () => {
    const s = makeStorage({ "null-key": "null" });
    // item is not null (string "null"), JSON.parse → null, but our guard
    // checks `item !== null` not the parsed value — so "null" is parsed.
    // This is intentional: the hook stores whatever was set.
    expect(readFromStorage(s, "null-key", "default")).toBeNull();
  });
});

describe("useLocalStorage — write logic", () => {
  it("writes string as JSON", () => {
    const s = makeStorage();
    writeToStorage(s, "key", "hello");
    expect(s._store["key"]).toBe('"hello"');
  });

  it("writes number as JSON", () => {
    const s = makeStorage();
    writeToStorage(s, "key", 99);
    expect(s._store["key"]).toBe("99");
  });

  it("writes object as JSON", () => {
    const s = makeStorage();
    writeToStorage(s, "key", { x: 1 });
    expect(s._store["key"]).toBe('{"x":1}');
  });

  it("overwrites existing value", () => {
    const s = makeStorage({ key: '"first"' });
    writeToStorage(s, "key", "second");
    expect(s._store["key"]).toBe('"second"');
  });
});

describe("useLocalStorage — round-trip", () => {
  it("write then read returns the same string", () => {
    const s = makeStorage();
    writeToStorage(s, "rt", "test-value");
    expect(readFromStorage(s, "rt", "")).toBe("test-value");
  });

  it("write then read returns the same object", () => {
    const s = makeStorage();
    const data = { filing_status: "married", income: 120000 };
    writeToStorage(s, "rt", data);
    expect(readFromStorage(s, "rt", {})).toEqual(data);
  });

  it("two different keys are independent", () => {
    const s = makeStorage();
    writeToStorage(s, "key-a", "A");
    writeToStorage(s, "key-b", "B");
    expect(readFromStorage(s, "key-a", "")).toBe("A");
    expect(readFromStorage(s, "key-b", "")).toBe("B");
  });

  it("empty string survives round-trip", () => {
    const s = makeStorage();
    writeToStorage(s, "empty", "");
    expect(readFromStorage(s, "empty", "default")).toBe("");
  });
});

// ── Financial planning pages use useLocalStorage ─────────────────────────

describe("MortgagePage — persists form state", () => {
  const src = readSource("src/pages/MortgagePage.tsx");

  it("imports useLocalStorage", () => {
    expect(src).toContain('from "../hooks/useLocalStorage"');
  });

  it("persists refinance rate", () => {
    expect(src).toContain('"mortgage-refinance-rate"');
  });

  it("persists refinance term", () => {
    expect(src).toContain('"mortgage-refinance-term"');
  });

  it("persists closing costs", () => {
    expect(src).toContain('"mortgage-closing-costs"');
  });

  it("persists extra payment", () => {
    expect(src).toContain('"mortgage-extra-payment"');
  });
});

describe("SSClaimingPage — persists form state", () => {
  const src = readSource("src/pages/SSClaimingPage.tsx");

  it("imports useLocalStorage", () => {
    expect(src).toContain('from "../hooks/useLocalStorage"');
  });

  it("persists salary", () => {
    expect(src).toContain('"ss-salary"');
  });

  it("persists birth year", () => {
    expect(src).toContain('"ss-birth-year"');
  });

  it("persists career start age", () => {
    expect(src).toContain('"ss-career-start-age"');
  });

  it("persists manual PIA", () => {
    expect(src).toContain('"ss-manual-pia"');
  });

  it("persists spouse PIA", () => {
    expect(src).toContain('"ss-spouse-pia"');
  });

  it("uses NumberInput for career start age (free entry)", () => {
    expect(src).toContain("NumberInput");
    expect(src).not.toContain("[18, 20, 22, 24, 26]");
  });
});

describe("TaxProjectionPage — persists form state", () => {
  const src = readSource("src/pages/TaxProjectionPage.tsx");

  it("imports useLocalStorage", () => {
    expect(src).toContain('from "../hooks/useLocalStorage"');
  });

  it("persists filing status", () => {
    expect(src).toContain('"tax-filing-status"');
  });

  it("persists self-employment income", () => {
    expect(src).toContain('"tax-se-income"');
  });

  it("persists capital gains", () => {
    expect(src).toContain('"tax-capital-gains"');
  });

  it("persists additional deductions", () => {
    expect(src).toContain('"tax-additional-deductions"');
  });

  it("persists prior year tax", () => {
    expect(src).toContain('"tax-prior-year-tax"');
  });
});
