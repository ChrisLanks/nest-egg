/**
 * Notification types and interfaces
 */

export enum NotificationType {
  SYNC_FAILED = "sync_failed",
  REAUTH_REQUIRED = "reauth_required",
  SYNC_STALE = "sync_stale",
  ACCOUNT_CONNECTED = "account_connected",
  ACCOUNT_ERROR = "account_error",
  BUDGET_ALERT = "budget_alert",
  TRANSACTION_DUPLICATE = "transaction_duplicate",
  LARGE_TRANSACTION = "large_transaction",
  MILESTONE = "milestone",
  ALL_TIME_HIGH = "all_time_high",
  HOUSEHOLD_MEMBER_JOINED = "household_member_joined",
  HOUSEHOLD_MEMBER_LEFT = "household_member_left",
  GOAL_COMPLETED = "goal_completed",
  GOAL_FUNDED = "goal_funded",
  FIRE_COAST_FI = "fire_coast_fi",
  FIRE_INDEPENDENT = "fire_independent",
  RETIREMENT_SCENARIO_STALE = "retirement_scenario_stale",
}

export enum NotificationPriority {
  LOW = "low",
  MEDIUM = "medium",
  HIGH = "high",
  URGENT = "urgent",
}

export interface Notification {
  id: string;
  organization_id: string;
  user_id: string | null;
  type: NotificationType;
  priority: NotificationPriority;
  title: string;
  message: string;
  related_entity_type: string | null;
  related_entity_id: string | null;
  is_read: boolean;
  is_dismissed: boolean;
  read_at: string | null;
  dismissed_at: string | null;
  action_url: string | null;
  action_label: string | null;
  created_at: string;
  expires_at: string | null;
}

export interface NotificationCreate {
  type: NotificationType;
  priority: NotificationPriority;
  title: string;
  message: string;
  related_entity_type?: string;
  related_entity_id?: string;
  action_url?: string;
  action_label?: string;
  user_id?: string;
  expires_in_days?: number;
}

export interface UnreadCountResponse {
  count: number;
}
