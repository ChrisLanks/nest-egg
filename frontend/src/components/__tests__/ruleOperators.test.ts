/**
 * Unit tests for rule condition operator filtering.
 *
 * Verifies that each field type exposes exactly the operators that make
 * semantic sense, and that nonsensical combinations are absent.
 */

import { describe, it, expect } from 'vitest';
import { FIELD_OPERATORS, resolveOperatorForField } from '../../utils/ruleUtils';
import { ConditionField, ConditionOperator } from '../../types/rule';

// ── helpers ──────────────────────────────────────────────────────────────────

const TEXT_OPERATORS = new Set([
  ConditionOperator.EQUALS,
  ConditionOperator.CONTAINS,
  ConditionOperator.STARTS_WITH,
  ConditionOperator.ENDS_WITH,
  ConditionOperator.REGEX,
]);

const NUMERIC_OPERATORS = new Set([
  ConditionOperator.EQUALS,
  ConditionOperator.GREATER_THAN,
  ConditionOperator.LESS_THAN,
  ConditionOperator.BETWEEN,
]);

// ── FIELD_OPERATORS shape ─────────────────────────────────────────────────────

describe('FIELD_OPERATORS', () => {
  it('defines operators for every ConditionField', () => {
    const allFields = Object.values(ConditionField);
    for (const field of allFields) {
      expect(FIELD_OPERATORS[field], `missing operators for field "${field}"`).toBeDefined();
      expect(FIELD_OPERATORS[field].length).toBeGreaterThan(0);
    }
  });

  // ── text fields ─────────────────────────────────────────────────────────────

  describe('merchant_name (text)', () => {
    const ops = new Set(FIELD_OPERATORS[ConditionField.MERCHANT_NAME]);

    it('includes text operators', () => {
      expect(ops.has(ConditionOperator.EQUALS)).toBe(true);
      expect(ops.has(ConditionOperator.CONTAINS)).toBe(true);
      expect(ops.has(ConditionOperator.STARTS_WITH)).toBe(true);
      expect(ops.has(ConditionOperator.ENDS_WITH)).toBe(true);
      expect(ops.has(ConditionOperator.REGEX)).toBe(true);
    });

    it('excludes numeric operators', () => {
      expect(ops.has(ConditionOperator.GREATER_THAN)).toBe(false);
      expect(ops.has(ConditionOperator.LESS_THAN)).toBe(false);
      expect(ops.has(ConditionOperator.BETWEEN)).toBe(false);
    });
  });

  describe('description (text)', () => {
    const ops = new Set(FIELD_OPERATORS[ConditionField.DESCRIPTION]);

    it('includes text operators', () => {
      for (const op of TEXT_OPERATORS) {
        expect(ops.has(op), `missing operator "${op}"`).toBe(true);
      }
    });

    it('excludes numeric operators', () => {
      expect(ops.has(ConditionOperator.GREATER_THAN)).toBe(false);
      expect(ops.has(ConditionOperator.LESS_THAN)).toBe(false);
      expect(ops.has(ConditionOperator.BETWEEN)).toBe(false);
    });
  });

  // ── numeric fields ──────────────────────────────────────────────────────────

  describe.each([
    ['amount', ConditionField.AMOUNT],
    ['amount_exact', ConditionField.AMOUNT_EXACT],
  ] as const)('%s (numeric)', (_name, field) => {
    it('includes numeric operators', () => {
      const ops = new Set(FIELD_OPERATORS[field]);
      for (const op of NUMERIC_OPERATORS) {
        expect(ops.has(op), `missing operator "${op}"`).toBe(true);
      }
    });

    it('excludes text-only operators', () => {
      const ops = new Set(FIELD_OPERATORS[field]);
      expect(ops.has(ConditionOperator.CONTAINS)).toBe(false);
      expect(ops.has(ConditionOperator.STARTS_WITH)).toBe(false);
      expect(ops.has(ConditionOperator.ENDS_WITH)).toBe(false);
      expect(ops.has(ConditionOperator.REGEX)).toBe(false);
    });
  });

  // ── category (restricted) ───────────────────────────────────────────────────

  describe('category', () => {
    const ops = new Set(FIELD_OPERATORS[ConditionField.CATEGORY]);

    it('allows equals and contains', () => {
      expect(ops.has(ConditionOperator.EQUALS)).toBe(true);
      expect(ops.has(ConditionOperator.CONTAINS)).toBe(true);
    });

    it('excludes numeric operators — "category greater than" makes no sense', () => {
      expect(ops.has(ConditionOperator.GREATER_THAN)).toBe(false);
      expect(ops.has(ConditionOperator.LESS_THAN)).toBe(false);
      expect(ops.has(ConditionOperator.BETWEEN)).toBe(false);
    });

    it('excludes positional text operators — categories are whole words', () => {
      expect(ops.has(ConditionOperator.STARTS_WITH)).toBe(false);
      expect(ops.has(ConditionOperator.ENDS_WITH)).toBe(false);
      expect(ops.has(ConditionOperator.REGEX)).toBe(false);
    });
  });
});

// ── resolveOperatorForField ───────────────────────────────────────────────────
//
// When the user changes the field, the current operator should be kept if still
// valid, or reset to the first valid operator for the new field.

describe('resolveOperatorForField', () => {
  it('keeps operator when it is still valid for the new field', () => {
    // "equals" is valid for both merchant_name and amount
    const result = resolveOperatorForField(ConditionOperator.EQUALS, ConditionField.AMOUNT);
    expect(result).toBe(ConditionOperator.EQUALS);
  });

  it('resets to first valid operator when switching text → numeric', () => {
    // "contains" is not valid for amount
    const result = resolveOperatorForField(ConditionOperator.CONTAINS, ConditionField.AMOUNT);
    expect(FIELD_OPERATORS[ConditionField.AMOUNT]).toContain(result);
    expect(result).not.toBe(ConditionOperator.CONTAINS);
  });

  it('resets to first valid operator when switching numeric → category', () => {
    // "greater_than" is not valid for category
    const result = resolveOperatorForField(ConditionOperator.GREATER_THAN, ConditionField.CATEGORY);
    expect(FIELD_OPERATORS[ConditionField.CATEGORY]).toContain(result);
    expect(result).not.toBe(ConditionOperator.GREATER_THAN);
  });

  it('resets when switching amount → merchant_name with "between"', () => {
    // "between" is not valid for merchant_name
    const result = resolveOperatorForField(ConditionOperator.BETWEEN, ConditionField.MERCHANT_NAME);
    expect(FIELD_OPERATORS[ConditionField.MERCHANT_NAME]).toContain(result);
    expect(result).not.toBe(ConditionOperator.BETWEEN);
  });

  it('keeps "contains" when switching merchant_name → description (both text fields)', () => {
    const result = resolveOperatorForField(ConditionOperator.CONTAINS, ConditionField.DESCRIPTION);
    expect(result).toBe(ConditionOperator.CONTAINS);
  });
});
