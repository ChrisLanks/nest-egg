/**
 * Pure rule-building utilities — no React, no API imports.
 * Extracted here so they can be unit-tested without browser globals.
 */

import { ConditionField, ConditionOperator } from '../types/rule';

/** Operators that make semantic sense for each condition field. */
export const FIELD_OPERATORS: Record<ConditionField, ConditionOperator[]> = {
  [ConditionField.MERCHANT_NAME]: [
    ConditionOperator.EQUALS,
    ConditionOperator.CONTAINS,
    ConditionOperator.STARTS_WITH,
    ConditionOperator.ENDS_WITH,
    ConditionOperator.REGEX,
  ],
  [ConditionField.AMOUNT]: [
    ConditionOperator.EQUALS,
    ConditionOperator.GREATER_THAN,
    ConditionOperator.LESS_THAN,
    ConditionOperator.BETWEEN,
  ],
  [ConditionField.AMOUNT_EXACT]: [
    ConditionOperator.EQUALS,
    ConditionOperator.GREATER_THAN,
    ConditionOperator.LESS_THAN,
    ConditionOperator.BETWEEN,
  ],
  [ConditionField.CATEGORY]: [
    ConditionOperator.EQUALS,
    ConditionOperator.CONTAINS,
  ],
  [ConditionField.DESCRIPTION]: [
    ConditionOperator.EQUALS,
    ConditionOperator.CONTAINS,
    ConditionOperator.STARTS_WITH,
    ConditionOperator.ENDS_WITH,
    ConditionOperator.REGEX,
  ],
};

/**
 * Returns the operator to use after a field change.
 * If the current operator is still valid for the new field it is kept;
 * otherwise the first valid operator for that field is returned.
 */
export function resolveOperatorForField(
  currentOperator: ConditionOperator,
  newField: ConditionField,
): ConditionOperator {
  const validOps = FIELD_OPERATORS[newField];
  return validOps.includes(currentOperator) ? currentOperator : validOps[0];
}
