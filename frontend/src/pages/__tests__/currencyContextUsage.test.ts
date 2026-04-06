/**
 * Tests verifying that pages use CurrencyContext instead of hardcoded "USD".
 *
 * These tests scan source code to ensure currency formatting functions
 * reference the dynamic currency from useCurrency() rather than a hardcoded
 * "USD" string.
 */

import { describe, it, expect } from "vitest";
import { readFileSync, readdirSync } from "fs";
import { join } from "path";

const PAGES_DIR = join(__dirname, "..");

// PreferencesPage legitimately uses "USD" as a default/option value
const EXCLUDED_FILES = ["PreferencesPage.tsx"];

function getPageFiles(): string[] {
  return readdirSync(PAGES_DIR)
    .filter((f) => f.endsWith(".tsx") && !EXCLUDED_FILES.includes(f));
}

describe("currency context usage", () => {
  it("should not have hardcoded currency: \"USD\" in formatting functions", () => {
    const violations: string[] = [];

    for (const file of getPageFiles()) {
      const content = readFileSync(join(PAGES_DIR, file), "utf-8");

      // Match patterns like: currency: "USD" in Intl.NumberFormat or toLocaleString
      const hardcodedPattern = /currency:\s*["']USD["']/g;
      let match;
      while ((match = hardcodedPattern.exec(content)) !== null) {
        // Find line number
        const beforeMatch = content.substring(0, match.index);
        const lineNumber = (beforeMatch.match(/\n/g) || []).length + 1;
        violations.push(`${file}:${lineNumber}`);
      }
    }

    if (violations.length > 0) {
      console.warn(
        `Found ${violations.length} hardcoded currency: "USD" in:\n` +
          violations.map((v) => `  - ${v}`).join("\n"),
      );
    }

    // Allow 0 violations — all pages should use useCurrency()
    expect(violations.length).toBe(0);
  });

  it("pages with currency formatting should import useCurrency", () => {
    const missingImport: string[] = [];

    for (const file of getPageFiles()) {
      const content = readFileSync(join(PAGES_DIR, file), "utf-8");

      // Check if file has any currency formatting
      const hasCurrencyFormatting =
        content.includes("style: \"currency\"") ||
        content.includes('style: "currency"');

      if (hasCurrencyFormatting) {
        const hasUseCurrency = content.includes("useCurrency");
        if (!hasUseCurrency) {
          missingImport.push(file);
        }
      }
    }

    if (missingImport.length > 0) {
      console.warn(
        `Pages with currency formatting but no useCurrency import:\n` +
          missingImport.map((f) => `  - ${f}`).join("\n"),
      );
    }

    expect(missingImport.length).toBe(0);
  });
});
