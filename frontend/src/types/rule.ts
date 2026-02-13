/**
 * Rule types for transaction automation
 */

export enum RuleMatchType {
  ALL = 'all',
  ANY = 'any',
}

export enum RuleApplyTo {
  NEW_ONLY = 'new_only',
  EXISTING_ONLY = 'existing_only',
  BOTH = 'both',
  SINGLE = 'single',
}

export enum ConditionField {
  MERCHANT_NAME = 'merchant_name',
  AMOUNT = 'amount',
  AMOUNT_EXACT = 'amount_exact',
  CATEGORY = 'category',
  DESCRIPTION = 'description',
}

export enum ConditionOperator {
  EQUALS = 'equals',
  CONTAINS = 'contains',
  STARTS_WITH = 'starts_with',
  ENDS_WITH = 'ends_with',
  GREATER_THAN = 'greater_than',
  LESS_THAN = 'less_than',
  BETWEEN = 'between',
  REGEX = 'regex',
}

export enum ActionType {
  SET_CATEGORY = 'set_category',
  ADD_LABEL = 'add_label',
  REMOVE_LABEL = 'remove_label',
  SET_MERCHANT = 'set_merchant',
}

export interface RuleCondition {
  id?: string;
  rule_id?: string;
  field: ConditionField;
  operator: ConditionOperator;
  value: string;
  value_max?: string;
  created_at?: string;
}

export interface RuleAction {
  id?: string;
  rule_id?: string;
  action_type: ActionType;
  action_value: string;
  created_at?: string;
}

export interface Rule {
  id: string;
  organization_id: string;
  name: string;
  description?: string;
  match_type: RuleMatchType;
  apply_to: RuleApplyTo;
  priority: number;
  is_active: boolean;
  times_applied: number;
  last_applied_at?: string;
  created_at: string;
  updated_at: string;
  conditions: RuleCondition[];
  actions: RuleAction[];
}

export interface RuleCreate {
  name: string;
  description?: string;
  match_type: RuleMatchType;
  apply_to: RuleApplyTo;
  priority: number;
  is_active: boolean;
  conditions: Omit<RuleCondition, 'id' | 'rule_id' | 'created_at'>[];
  actions: Omit<RuleAction, 'id' | 'rule_id' | 'created_at'>[];
}

export interface RuleUpdate {
  name?: string;
  description?: string;
  is_active?: boolean;
  priority?: number;
}
